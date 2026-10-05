#!/bin/sh
# ---------------------------------------------------------------------------
# Point d'entree du conteneur web MBCODE.
#
# - Attend que la base de donnees PostgreSQL soit disponible
# - Applique les migrations
# - Collecte les fichiers statiques
# - Cree automatiquement un compte administrateur au premier demarrage
#   si les variables DJANGO_SUPERUSER_* sont renseignees
# - Demarre enfin la commande fournie (gunicorn par defaut)
# ---------------------------------------------------------------------------
set -e

if [ -n "$DATABASE_URL" ]; then
  echo "Attente de la base de donnees..."
  python - <<'PYEOF'
import os
import sys
import time

import environ

env = environ.Env()
db_config = env.db("DATABASE_URL")

if db_config["ENGINE"].endswith("sqlite3"):
    sys.exit(0)

import psycopg2

for attempt in range(1, 31):
    try:
        conn = psycopg2.connect(
            dbname=db_config["NAME"],
            user=db_config["USER"],
            password=db_config["PASSWORD"],
            host=db_config["HOST"],
            port=db_config["PORT"],
        )
        conn.close()
        print("Base de donnees disponible.")
        break
    except psycopg2.OperationalError:
        print(f"Base de donnees indisponible (tentative {attempt}/30)...")
        time.sleep(2)
else:
    print("Impossible de joindre la base de donnees.", file=sys.stderr)
    sys.exit(1)
PYEOF
fi

echo "Application des migrations..."
python manage.py migrate --noinput

echo "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "Verification du compte administrateur..."
  python manage.py shell <<'PYEOF'
import os

from gestion.models import Utilisateur

username = os.environ["DJANGO_SUPERUSER_USERNAME"]
password = os.environ["DJANGO_SUPERUSER_PASSWORD"]
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@mbcode.cm")

u = Utilisateur.objects.filter(username=username).first()
if u is None:
    u = Utilisateur.objects.create_superuser(username=username, email=email, password=password)
    print(f"Compte administrateur cree : {username}")
else:
    u.email = email
    u.is_staff = True
    u.is_superuser = True
    u.role = Utilisateur.Role.ADMIN
    u.set_password(password)
    u.save(update_fields=["email", "is_staff", "is_superuser", "role", "password"])
    print(f"Compte administrateur mis a jour : {username}")

u.role = Utilisateur.Role.ADMIN
u.is_staff = True
u.is_superuser = True
u.set_password(password)
u.save(update_fields=["role", "is_staff", "is_superuser", "password"])
PYEOF
fi

echo "Demarrage de l'application..."
exec "$@"
