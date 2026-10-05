"""
Commande de gestion : cree un jeu de donnees de demonstration (clients,
espaces, camps, formations, formateurs) afin de decouvrir rapidement
l'application apres installation.

Cette commande est idempotente : elle peut etre executee plusieurs fois
sans dupliquer les enregistrements (utilisation de get_or_create).

Exemple :
    python manage.py seed_demo
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from gestion import models


class Command(BaseCommand):
    help = "Cree des donnees de demonstration (clients, espaces, camps, formateurs)."

    def handle(self, *args, **options):
        aujourdhui = timezone.now().date()

        formateurs = [
            ("Sophie Dubois", "Lead Robotique"),
            ("Marc Lambert", "Expert Developpement Web"),
            ("Julie Martin", "Intervenante Intelligence Artificielle"),
        ]
        for nom, specialite in formateurs:
            models.Formateur.objects.get_or_create(nom=nom, defaults={"specialite": specialite})
        self.stdout.write(self.style.SUCCESS(f"{len(formateurs)} formateur(s) verifie(s)."))

        espaces = [
            ("Bureau Prive 1", models.Espace.TypeEspace.BUREAU, 2, 15000),
            ("Salle de Reunion A", models.Espace.TypeEspace.SALLE_REUNION, 8, 25000),
            ("Espace Coworking", models.Espace.TypeEspace.COWORKING, 1, 2500),
            ("Salle de Formation", models.Espace.TypeEspace.SALLE_REUNION, 15, 50000),
        ]
        for nom, type_espace, capacite, tarif in espaces:
            models.Espace.objects.get_or_create(
                nom=nom,
                defaults={"type_espace": type_espace, "capacite": capacite, "tarif_jour": tarif, "disponible": True},
            )
        self.stdout.write(self.style.SUCCESS(f"{len(espaces)} espace(s) verifie(s)."))

        clients = [
            ("Jean Dupont", models.Client.TypeClient.PARTICULIER, "+237690000001", "jean.dupont@example.cm"),
            ("TechCorp Industries", models.Client.TypeClient.ENTREPRISE, "+237690000002", "contact@techcorp.cm"),
            ("Marie Curie", models.Client.TypeClient.PARTICULIER, "+237690000003", "marie.curie@example.cm"),
        ]
        for nom, type_client, telephone, email in clients:
            models.Client.objects.get_or_create(
                telephone=telephone,
                defaults={"nom": nom, "type_client": type_client, "email": email},
            )
        self.stdout.write(self.style.SUCCESS(f"{len(clients)} client(s) verifie(s)."))

        camp, cree = models.Camp.objects.get_or_create(
            titre="Camp d'ete Bot-Builders",
            defaults={
                "theme": models.Camp.Theme.ROBOTIQUE,
                "date_debut": aujourdhui,
                "date_fin": aujourdhui + timedelta(days=10),
                "age_min": 8,
                "age_max": 15,
                "capacite": 30,
                "frais_inscription": 5000,
                "cout_formation": 40000,
                "nombre_enseignants": 2,
                "montant_remuneration_enseignants": 150000,
            },
        )
        if cree:
            camp.formateurs.set(models.Formateur.objects.filter(nom="Sophie Dubois"))
        self.stdout.write(self.style.SUCCESS("Camp de demonstration verifie."))

        charges = [
            ("Loyer local MBCODE", models.Depense.Categorie.LOYER, 500000, 1),
            ("Internet haut debit Starlink", models.Depense.Categorie.ABONNEMENT, 75000, 5),
        ]
        for libelle, categorie, montant, jour in charges:
            models.ChargeFixe.objects.get_or_create(
                libelle=libelle,
                defaults={
                    "categorie": categorie, "montant": montant, "jour_prelevement": jour,
                    "mode_paiement": models.Depense.Mode.ORANGE_MONEY,
                    "date_debut": aujourdhui,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"{len(charges)} charge(s) fixe(s) verifiee(s)."))

        self.stdout.write(self.style.SUCCESS("Jeu de donnees de demonstration pret."))
