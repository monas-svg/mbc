Configuration du backend Terraform (Azure Storage)
===============================================

Objectif
--------
Stocker l'état Terraform de façon centralisée et verrouillée dans un compte de stockage Azure.

Étapes rapides (avec Azure CLI)
-------------------------------
Remplacez `<RG>`, `<LOCATION>`, `<STORAGE_ACCOUNT>` par vos valeurs.

```bash
# se connecter
az login

# créer le groupe de ressources
az group create -n <RG> -l <LOCATION>

# créer le compte de stockage (choisir un nom unique)
az storage account create -n <STORAGE_ACCOUNT> -g <RG> -l <LOCATION> --sku Standard_LRS

# créer le container pour les états
az storage container create --name tfstate --account-name <STORAGE_ACCOUNT>

# récupérer la clé de compte (pour usage local uniquement)
az storage account keys list -g <RG> -n <STORAGE_ACCOUNT> --query "[0].value" -o tsv

# Exemple: copier le fichier d'exemple
cp infra/terraform/environments/backend.tf.example infra/terraform/environments/backend.tf
# Editez backend.tf avec les valeurs : resource_group_name, storage_account_name, container_name, key

```

Script d'automatisation
-----------------------
Un script `create_backend.sh` est fourni pour automatiser la création du groupe de ressources,
du compte de stockage et du container, puis générer `infra/terraform/environments/backend.tf`.

Exemple d'utilisation:

```bash
chmod +x infra/terraform/environments/create_backend.sh
infra/terraform/environments/create_backend.sh -g rg-mbcode-dev -l westeurope -s mbcodebackenddev
```

Le script nécessite que vous soyez connecté via `az login` et qu'il ait les droits suffisants.


Configurer CI (GitHub Actions)
------------------------------
- Préférez OIDC (azure/login) pour éviter de stocker des secrets persistants.
- Si vous utilisez une clé SAS ou un principal de service, stockez les valeurs dans `Secrets` :
  - `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` — pour `azure/login`
  - `TF_STATE_STORAGE_ACCOUNT` — nom du storage account (optionnel)
  - `TF_STATE_CONTAINER` — nom du container (optionnel)

Sécurité et bonnes pratiques
---------------------------
- Restreindre l'accès au Storage Account (firewall, trusted services, private endpoints).
- Activer la protection contre la suppression (soft delete) et la protection purge sur Key Vault si utilisé.
- Ne pas committer de secrets dans le dépôt.
