# Déploiement Azure / AKS / Terraform / GitHub Actions

## Architecture cible

L'application MBCODE est déployée sur Azure dans un environnement produit basé sur :

- Azure Kubernetes Service (AKS) comme orchestrateur de conteneurs
- Azure Container Registry (ACR) pour stocker les images
- Azure Database for PostgreSQL Flexible Server pour la base de données
- Azure Key Vault pour les secrets sensibles
- Azure Log Analytics pour la collecte des logs et métriques
- GitHub Actions pour CI/CD avec OIDC Azure
- Terraform pour la provisionning d'infrastructure

## Principes de sécurité appliqués

1. OIDC GitHub → Azure, jamais de secrets Azure stockés dans le code.
2. ACR avec accès restreint ; les nœuds AKS utilisent une identité dédiée avec rôle AcrPull.
3. Secrets externes : `DJANGO_SECRET_KEY`, `DATABASE_URL`, etc. dans Azure Key Vault ou GitHub secrets, jamais en clair dans les manifests.
4. Kubernetes hardened : `runAsNonRoot`, `allowPrivilegeEscalation: false`, réduction des capacités, `readOnlyRootFilesystem` si possible selon besoin applicatif.
5. Réseau : NetworkPolicy appliqué pour restreindre le trafic entrant/sortant vers le service web.
6. TLS : terminaison via nginx ingress + cert-manager / Let's Encrypt.
7. Infra as code : tout est provisionné via Terraform ; pas de création manuelle dans le portail Azure.

## Structure du dépôt

- `.github/workflows/ci.yml`: validation du code et du conteneur
- `.github/workflows/cd.yml`: provisionnement Terraform + déploiement sur AKS
- `infra/terraform/`: code Terraform pour Azure
- `k8s/`: manifests Kubernetes de déploiement, service, ingress, autoscaling, networking and secrets example

## Pré-requis Azure

Avant premier déploiement :

```bash
az login
az account set --subscription "<subscription-id>"
az group create --name rg-mbcode-shared --location westeurope
az storage account create --name <unique-tfstate-name> --resource-group rg-mbcode-shared --location westeurope --sku Standard_LRS
az storage container create --name tfstate --account-name <unique-tfstate-name>
```

Ensuite renseigner dans GitHub Actions les secrets suivants :

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `TFSTATE_STORAGE_ACCOUNT`
- `DJANGO_SECRET_KEY`
- `DATABASE_URL`

## Déploiement Terraform

```bash
cd infra/terraform
terraform init -backend-config="resource_group_name=rg-mbcode-shared" \
  -backend-config="storage_account_name=<unique-tfstate-name>" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=mbcode/prod.tfstate"

terraform plan
terraform apply
```

## Déploiement applicatif

Le workflow GitHub Actions `CD` s’occupe de :

1. authentifier Azure via OIDC,
2. provisionner l’infra avec Terraform,
3. construire l’image Docker,
4. la pousser vers ACR,
5. récupérer le kubeconfig AKS,
6. appliquer les manifestes Kubernetes.

## Bonnes pratiques complémentaires

- utiliser des namespaces séparés par environnement,
- créer des quotas Kubernetes et des budgets de coût,
- activer Azure Defender / Microsoft Defender for Cloud,
- stocker les secrets dans Azure Key Vault et les injecter par CSI driver ou secret store,
- activer les alertes sur les ressources AKS / ACR / PostgreSQL,
- intégrer un scan SAST/SCA et container image security dans la pipeline avant promotion.
