# MBCODE — Application de gestion

Application web de gestion pour un centre proposant location de bureaux et
d'espaces de coworking, camps de formation pour enfants et formations en
intelligence artificielle pour étudiants et professionnels.

Elle couvre la gestion des clients, la facturation, les réservations
d'espaces, les inscriptions aux camps et formations, ainsi que le suivi de
la caisse et des dépenses (charges fixes, clôtures journalières,
récapitulatifs périodiques).

---

## Sommaire

- [Aperçu fonctionnel](#aperçu-fonctionnel)
- [Stack technique](#stack-technique)
- [Structure du projet](#structure-du-projet)
- [Rôles et permissions](#rôles-et-permissions)
- [Démarrage rapide avec Docker](#démarrage-rapide-avec-docker)
- [Installation manuelle (sans Docker)](#installation-manuelle-sans-docker)
- [Variables d'environnement](#variables-denvironnement)
- [Tâches planifiées](#tâches-planifiées)
- [Tests](#tests)
- [API REST](#api-rest)
- [Sécurité](#sécurité)
- [Déploiement en production](#déploiement-en-production)
- [Support](#support)

---

## Aperçu fonctionnel

**Tableau de bord** — chiffre d'affaires du mois, élèves actifs, taux
d'occupation des espaces, paiements en attente, évolution des revenus et
activités récentes.

**Ventes & facturation** — création de factures (location, camp, formation),
encaissement des paiements (espèces, Orange Money, MTN Mobile Money),
suivi des impayés. Une facture est verrouillée dès son enregistrement par
un agent ; seule la modification par un administrateur reste possible.

**Gestion des clients** — clients particuliers et entreprises, enfants
rattachés à un client, historique des factures et des réservations.

**Camps & formations** — camps de formation pour enfants (robotique,
codage, IA) et formations IA pour étudiants et professionnels, gestion des
formateurs, inscriptions avec option de paiement échelonné en deux
tranches.

**Location d'espaces** — bureaux privés, salles de réunion, espaces de
coworking ; réservations et suivi du taux d'occupation.

**Dépenses & trésorerie** — dépenses ponctuelles, charges fixes (loyer,
abonnement Internet...) générées automatiquement chaque mois, clôture de
caisse journalière avec calcul de l'écart entre les espèces théoriques et
les espèces réellement comptées, récapitulatifs hebdomadaires et mensuels.

**Rapports & analyses** — revenu annuel, marge nette, évolution des
revenus et des dépenses, répartition des revenus locatifs par type
d'espace, performance des camps et formations, meilleurs clients.

---

## Stack technique

| Composant           | Choix                                          |
|----------------------|------------------------------------------------|
| Langage / framework  | Python 3.12, Django 5                          |
| API                  | Django REST Framework, authentification JWT    |
| Base de données      | PostgreSQL 16                                  |
| Serveur d'application| Gunicorn                                       |
| Fichiers statiques   | WhiteNoise (compression, hachage de version)   |
| Interface web        | Templates Django, CSS maison (sans dépendance CDN) |
| Conteneurisation     | Docker, Docker Compose                         |

Aucune bibliothèque JavaScript tierce n'est chargée depuis un CDN : les
graphiques du tableau de bord et des rapports sont générés côté serveur en
SVG. Ce choix limite la surface d'attaque de l'application et évite toute
dépendance à un service externe pour l'affichage des pages.

---

## Structure du projet

```
mbcode/
├── config/                 # Configuration Django (settings, urls, wsgi/asgi)
├── gestion/                 # Modèles métier, permissions, admin, tests
│   └── management/commands/ # Commandes : generer_charges_fixes, seed_demo
├── api/                     # Sérialiseurs et endpoints REST
├── web/                     # Vues, formulaires et logique de l'interface web
├── templates/                # Templates HTML (interface + pages d'erreur)
├── static/                   # CSS, JavaScript et icônes de l'interface
├── docker/                   # Script de démarrage du conteneur
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Rôles et permissions

L'application distingue deux profils :

- **Administrateur** — accès complet : gestion des comptes, création du
  catalogue (espaces, camps, formations), configuration des charges
  fixes, modification ou suppression de tout enregistrement, y compris
  après verrouillage.
- **Agent de vente** — peut enregistrer une vente (facture, ligne de
  facturation, paiement), une dépense, un mouvement de caisse, et
  effectuer la clôture de caisse du jour. Il ne peut ni modifier ni
  supprimer un enregistrement déjà créé, même le sien : toute correction
  passe par un administrateur. Il ne peut pas créer d'espace, de camp, de
  formation, ni accéder aux charges fixes.

Ces règles sont appliquées à deux niveaux : dans les classes de permission
de l'API (`gestion/permissions.py`) et dans les vues de l'interface web
(`web/mixins.py`, contrôles `_admin_requis`), de façon à ce qu'un agent ne
puisse contourner une restriction ni par l'API ni par l'interface.

---

## Démarrage rapide avec Docker

Prérequis : Docker et Docker Compose installés.

```bash
# 1. Cloner ou copier le projet, puis se placer dans le dossier
cd mbcode

# 2. Créer le fichier d'environnement à partir du modèle fourni
cp .env.example .env

# 3. Adapter .env : cle secrete, mot de passe de la base de donnees,
#    et identifiants du compte administrateur initial
nano .env

# 4. Construire les images et démarrer les services
docker compose up --build -d

# 5. Suivre les journaux au premier démarrage (migrations, collecte des
#    fichiers statiques, création du compte administrateur)
docker compose logs -f web
```

L'application est ensuite accessible sur **http://localhost:8001** (si le port 8000 est déjà utilisé par un autre service, Docker expose alors le service sur 8001).

Si les variables `DJANGO_SUPERUSER_USERNAME` et `DJANGO_SUPERUSER_PASSWORD`
sont renseignées dans `.env`, un compte administrateur est créé
automatiquement au premier démarrage. Pour charger un jeu de données de
démonstration (clients, espaces, camps, formateurs) :

```bash
docker compose exec web python manage.py seed_demo
```

Pour arrêter les services :

```bash
docker compose down
```

Pour arrêter les services et supprimer les données (base de données,
fichiers statiques, médias) :

```bash
docker compose down -v
```

---

## Installation manuelle (sans Docker)

Prérequis : Python 3.12, PostgreSQL 14 ou supérieur (ou SQLite pour un
essai local rapide).

```bash
# 1. Créer et activer un environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer l'environnement
cp .env.example .env
# Modifier DATABASE_URL pour pointer vers votre base PostgreSQL, ou la
# laisser vide pour utiliser une base SQLite locale (db.sqlite3)

# 4. Appliquer les migrations
python manage.py migrate

# 5. Créer un compte administrateur
python manage.py createsuperuser

# 6. Collecter les fichiers statiques
python manage.py collectstatic --noinput

# 7. Lancer le serveur de développement
python manage.py runserver
```

L'application est accessible sur **http://127.0.0.1:8000** si aucun autre service n'utilise ce port ; sinon adaptez le port de votre serveur local.

---

## Variables d'environnement

Toutes les variables sont documentées dans `.env.example`. Les
principales :

| Variable                    | Description                                                        |
|-------------------------------|----------------------------------------------------------------------|
| `DJANGO_SECRET_KEY`           | Clé secrète Django. À régénérer pour chaque environnement.          |
| `DEBUG`                       | `True` en développement uniquement, `False` en production.          |
| `ALLOWED_HOSTS`                | Liste des noms d'hôte autorisés, séparés par des virgules.          |
| `CSRF_TRUSTED_ORIGINS`         | Origines de confiance pour la protection CSRF (avec schéma https). |
| `DATABASE_URL`                 | URL de connexion PostgreSQL (`postgres://user:pass@host:port/nom`).|
| `TIME_ZONE`                     | Fuseau horaire de l'application (`Africa/Douala` par défaut).       |
| `SECURE_SSL_REDIRECT`           | Force la redirection HTTPS en production.                          |
| `DJANGO_SUPERUSER_USERNAME/PASSWORD/EMAIL` | Compte administrateur créé automatiquement au premier démarrage du conteneur. |

**Aucun secret ne doit être versionné.** Le fichier `.env` est exclu du
suivi de version via `.gitignore`.

---

## Tâches planifiées

La génération mensuelle des dépenses issues des charges fixes (loyer,
abonnement Internet, etc.) n'est pas automatique : elle doit être
déclenchée par une tâche planifiée qui exécute, une fois par jour :

```bash
python manage.py generer_charges_fixes
```

Sous Docker, cette commande peut être ajoutée à une tâche cron de l'hôte
appelant `docker compose exec -T web python manage.py
generer_charges_fixes`, ou intégrée à un ordonnanceur externe
(cron classique, tâche planifiée du système d'exploitation, etc.). Chaque
charge fixe ne génère sa dépense qu'une seule fois par mois : la commande
peut être exécutée plusieurs fois sans créer de doublon.

---

## Tests

La suite de tests couvre les règles métier sensibles : verrouillage des
factures, validation des paiements mobile money, séparation des droits
entre administrateur et agent (API et interface web).

```bash
python manage.py test
```

---

## API REST

L'API est exposée sous le préfixe `/api/`. L'authentification se fait par
jeton JWT ou par session (utile pour les tests depuis l'interface
navigable de Django REST Framework).

```bash
# Obtenir un jeton d'accès
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "votre_identifiant", "password": "votre_mot_de_passe"}'

# Utiliser le jeton
curl http://localhost:8000/api/factures/ \
  -H "Authorization: Bearer <access_token>"
```

Principales ressources disponibles : `clients`, `enfants`, `formateurs`,
`espaces`, `reservations`, `camps`, `inscriptions-camps`, `formations`,
`inscriptions-formations`, `factures`, `lignes-facture`, `paiements`,
`mouvements-caisse`, `depenses`, `charges-fixes`, `clotures-caisse`,
`recaps-periode`.

L'API applique une limitation de débit (throttling) par défaut : 1000
requêtes/heure pour un utilisateur authentifié, 50/heure pour un
utilisateur anonyme.

---

## Sécurité

- Secrets et paramètres sensibles exclusivement lus depuis des variables
  d'environnement, jamais codés en dur.
- Mots de passe soumis aux validateurs Django (longueur minimale, rejet
  des mots de passe courants ou trop proches des informations du compte).
- En dehors du mode développement (`DEBUG=False`) : cookies de session et
  CSRF marqués `Secure`, en-têtes HSTS, redirection HTTPS forcée,
  protection contre le clickjacking (`X-Frame-Options: DENY`).
- Verrouillage applicatif des enregistrements sensibles (factures,
  dépenses, mouvements de caisse, clôtures) après création, avec double
  contrôle côté API et côté interface web.
- Aucune dépendance JavaScript chargée depuis un service tiers.
- Conteneur applicatif exécuté avec un utilisateur non privilégié
  (`mbcode`), image construite en plusieurs étapes pour limiter sa
  surface.
- Journalisation des erreurs serveur pour faciliter le diagnostic sans
  exposer d'informations sensibles à l'utilisateur final.

---

## Déploiement en production

- Positionner l'application derrière un reverse proxy TLS (Nginx,
  Traefik ou équivalent) qui termine le HTTPS et transmet les requêtes à
  Gunicorn.
- Renseigner `ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS` avec le nom de
  domaine réel.
- Conserver les volumes Docker `mbcode_postgres_data` et `mbcode_media`
  dans une stratégie de sauvegarde régulière.
- Prévoir une tâche planifiée pour `generer_charges_fixes` (voir ci-dessus).
- Surveiller le point de contrôle de santé exposé par le conteneur
  (`HEALTHCHECK` du Dockerfile, basé sur la page de connexion).

---

## Support

Pour toute question relative au fonctionnement de l'application, contacter
l'équipe MBCODE :

**MBCODE** — Quartier Makepe, Douala, Cameroun
Téléphone : +237 6 59 17 27 62 — Email : infos@mbcode.cm

*Together We Can Do More.*
