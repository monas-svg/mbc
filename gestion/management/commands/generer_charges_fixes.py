"""
Commande de gestion : genere les depenses du mois pour chaque charge fixe
active (loyer, abonnement Starlink, etc.).

A executer une fois par jour via une tache planifiee (cron / Celery beat) :
chaque ChargeFixe ne genere sa Depense qu'une seule fois par mois grace a la
verification faite dans ChargeFixe.generer_depense_du_mois().

Exemple :
    python manage.py generer_charges_fixes
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from gestion.models import ChargeFixe, Utilisateur


class Command(BaseCommand):
    help = "Genere les depenses mensuelles issues des charges fixes actives."

    def handle(self, *args, **options):
        today = timezone.now().date()
        systeme, _ = Utilisateur.objects.get_or_create(
            username="systeme",
            defaults={
                "role": Utilisateur.Role.ADMIN,
                "is_active": False,
                "first_name": "Automatisation",
                "last_name": "MBCODE",
            },
        )

        charges = ChargeFixe.objects.filter(actif=True, jour_prelevement=today.day)
        total = 0
        for charge in charges:
            depense = charge.generer_depense_du_mois(today.year, today.month, systeme)
            if depense:
                total += 1
                self.stdout.write(self.style.SUCCESS(f"Depense generee : {depense}"))

        if total == 0:
            self.stdout.write("Aucune charge fixe a generer aujourd'hui.")
        else:
            self.stdout.write(self.style.SUCCESS(f"{total} depense(s) generee(s)."))
