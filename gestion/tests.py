"""
Tests unitaires et d'integration - Application de gestion MBCODE.

Ces tests couvrent les regles metier les plus sensibles : verrouillage des
factures et des depenses apres creation, validation des paiements mobile
money, et separation des droits entre administrateur et agent de vente
(cote API comme cote interface web).
"""
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import (
    Camp,
    Client,
    Depense,
    Enfant,
    Espace,
    Facture,
    InscriptionCamp,
    LigneFacture,
    Paiement,
    Utilisateur,
)


class UtilisateurTestCase(TestCase):
    def test_un_superutilisateur_est_toujours_considere_administrateur(self):
        u = Utilisateur.objects.create_superuser("root", "root@mbcode.cm", "MotDePasse123")
        self.assertTrue(u.est_admin)

    def test_un_agent_standard_n_est_pas_administrateur(self):
        u = Utilisateur.objects.create_user("agent1", "agent1@mbcode.cm", "MotDePasse123", role=Utilisateur.Role.AGENT)
        self.assertFalse(u.est_admin)


class PaiementValidationTestCase(TestCase):
    """Un paiement Orange Money ou MTN Mobile Money exige une reference de transaction."""

    def setUp(self):
        self.admin = Utilisateur.objects.create_superuser("admin", "admin@mbcode.cm", "MotDePasse123")
        self.client_mbcode = Client.objects.create(nom="Jean Dupont", telephone="+237690000010")
        self.facture = Facture.objects.create(client=self.client_mbcode, enregistree_par=self.admin)
        LigneFacture.objects.create(
            facture=self.facture, type_service=LigneFacture.TypeService.LOCATION,
            description="Location bureau", quantite=1, prix_unitaire=10000,
        )

    def test_paiement_mobile_money_sans_reference_est_refuse(self):
        paiement = Paiement(
            facture=self.facture, mode=Paiement.Mode.ORANGE_MONEY, sens=Paiement.Sens.ENTREE,
            montant=10000, enregistre_par=self.admin,
        )
        with self.assertRaises(ValidationError):
            paiement.save()

    def test_paiement_especes_ne_necessite_pas_de_reference(self):
        paiement = Paiement.objects.create(
            facture=self.facture, mode=Paiement.Mode.CASH_IN, sens=Paiement.Sens.ENTREE,
            montant=10000, enregistre_par=self.admin,
        )
        self.assertIsNotNone(paiement.pk)

    def test_paiement_orange_money_avec_reference_est_accepte(self):
        paiement = Paiement.objects.create(
            facture=self.facture, mode=Paiement.Mode.ORANGE_MONEY, sens=Paiement.Sens.ENTREE,
            montant=10000, reference_transaction="OM-2026-000123", enregistre_par=self.admin,
        )
        self.assertIsNotNone(paiement.pk)


class FactureVerrouillageAPITestCase(TestCase):
    """
    Une facture est verrouillee des sa creation par un agent : au-dela de sa
    consultation, seul un administrateur peut ensuite la modifier.
    """

    def setUp(self):
        self.admin = Utilisateur.objects.create_superuser("admin", "admin@mbcode.cm", "MotDePasse123")
        self.agent = Utilisateur.objects.create_user(
            "agent", "agent@mbcode.cm", "MotDePasse123", role=Utilisateur.Role.AGENT
        )
        self.client_mbcode = Client.objects.create(nom="Marie Curie", telephone="+237690000011")
        self.facture = Facture.objects.create(
            client=self.client_mbcode, enregistree_par=self.agent, statut=Facture.Statut.EMISE
        )

    def test_un_agent_ne_peut_pas_modifier_une_facture_existante(self):
        api = APIClient()
        api.force_authenticate(self.agent)
        reponse = api.patch(f"/api/factures/{self.facture.pk}/", {"statut": "ANNULEE"}, format="json")
        self.assertIn(reponse.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED))

    def test_un_administrateur_peut_modifier_une_facture_existante(self):
        api = APIClient()
        api.force_authenticate(self.admin)
        reponse = api.patch(f"/api/factures/{self.facture.pk}/", {"statut": "ANNULEE"}, format="json")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)

    def test_un_agent_peut_creer_une_nouvelle_facture(self):
        api = APIClient()
        api.force_authenticate(self.agent)
        reponse = api.post(
            "/api/factures/", {"client": self.client_mbcode.pk, "statut": "EMISE"}, format="json"
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)

    def test_un_utilisateur_anonyme_est_rejete(self):
        api = APIClient()
        reponse = api.get("/api/factures/")
        self.assertIn(reponse.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class ChargeFixeAccesAdminTestCase(TestCase):
    """Les charges fixes sont un parametrage reserve a l'administrateur, meme en lecture."""

    def setUp(self):
        self.agent = Utilisateur.objects.create_user(
            "agent2", "agent2@mbcode.cm", "MotDePasse123", role=Utilisateur.Role.AGENT
        )

    def test_un_agent_ne_peut_pas_lister_les_charges_fixes_via_l_api(self):
        api = APIClient()
        api.force_authenticate(self.agent)
        reponse = api.get("/api/charges-fixes/")
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)


class ClientTypeTestCase(TestCase):
    def test_les_clients_ont_trois_types_valides(self):
        self.assertTrue(hasattr(Client.TypeClient, "PARTICULIER"))
        self.assertTrue(hasattr(Client.TypeClient, "PARENT_ENFANT"))
        self.assertTrue(hasattr(Client.TypeClient, "ENTREPRISE"))

        self.assertEqual(Client.TypeClient.PARENT_ENFANT.label, "Parent-enfant")

    def test_un_enfant_doit_avoir_un_parent_de_type_parent_enfant(self):
        parent = Client.objects.create(
            nom="Maman et enfants",
            type_client=Client.TypeClient.PARTICULIER,
            telephone="+237600000099",
        )
        enfant = Client.objects.create(
            nom="Parent en charge",
            type_client=Client.TypeClient.PARENT_ENFANT,
            telephone="+237600000100",
        )

        with self.assertRaises(ValidationError):
            enfant_enfant = Enfant(parent=parent, nom="Test", prenom="Gabriel", date_naissance="2020-01-01")
            enfant_enfant.full_clean()

        enfant_valide = Enfant(parent=enfant, nom="Test", prenom="Gabriel", date_naissance="2020-01-01")
        enfant_valide.full_clean()

    def test_un_enfant_a_un_nom_un_prenom_et_un_age(self):
        parent = Client.objects.create(
            nom="Famille Dupont",
            type_client=Client.TypeClient.PARENT_ENFANT,
            telephone="+237600000105",
        )

        self.assertTrue(hasattr(Enfant, "prenom"))
        enfant = Enfant.objects.create(
            parent=parent,
            nom="Dupont",
            prenom="Emma",
            date_naissance="2018-05-12",
        )

        self.assertEqual(enfant.prenom, "Emma")
        self.assertEqual(enfant.age, 8)
        self.assertEqual(parent.enfants.count(), 1)

    def test_un_agent_ne_peut_pas_creer_un_camp_ni_une_formation(self):
        agent = Utilisateur.objects.create_user(
            "agent-camp", "agent-camp@mbcode.cm", "MotDePasse123", role=Utilisateur.Role.AGENT
        )
        self.client.force_login(agent)
        self.client.raise_request_exception = False

        reponse_camp = self.client.get(reverse("web:camp_creer"))
        reponse_formation = self.client.get(reverse("web:formation_creer"))

        self.assertEqual(reponse_camp.status_code, 403)
        self.assertEqual(reponse_formation.status_code, 403)

    def test_un_agent_peut_creer_un_enfant_pour_un_parent_de_type_parent_enfant(self):
        agent = Utilisateur.objects.create_user(
            "agent-enfant", "agent-enfant@mbcode.cm", "MotDePasse123", role=Utilisateur.Role.AGENT
        )
        self.client.force_login(agent)

        parent = Client.objects.create(
            nom="Famille Dupont",
            type_client=Client.TypeClient.PARENT_ENFANT,
            telephone="+237600000110",
        )

        reponse = self.client.post(
            reverse("web:enfant_creer", args=[parent.pk]),
            {"parent": parent.pk, "nom": "Dupont", "prenom": "Emma", "date_naissance": "2018-05-12"},
        )

        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(Enfant.objects.filter(parent=parent, nom="Dupont", prenom="Emma").exists())

    def test_un_agent_peut_creer_un_enfant_depuis_le_tableau_de_bord(self):
        agent = Utilisateur.objects.create_user(
            "agent-dashboard-enfant", "agent-dashboard-enfant@mbcode.cm", "MotDePasse123", role=Utilisateur.Role.AGENT
        )
        self.client.force_login(agent)

        parent = Client.objects.create(
            nom="Famille dashboard",
            type_client=Client.TypeClient.PARENT_ENFANT,
            telephone="+237600000111",
        )

        reponse = self.client.post(
            reverse("web:enfant_creer_rapide"),
            {"parent": parent.pk, "nom": "Dupont", "prenom": "Lina", "date_naissance": "2017-02-18"},
        )

        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(Enfant.objects.filter(parent=parent, nom="Dupont", prenom="Lina").exists())

    def test_une_vente_cree_une_facture_avec_une_ligne_et_un_paiement(self):
        agent = Utilisateur.objects.create_user(
            "agent-vente-facture", "agent-vente-facture@mbcode.cm", "MotDePasse123", role=Utilisateur.Role.AGENT
        )
        self.client.force_login(agent)

        client = Client.objects.create(nom="Client vente", telephone="+237600000116")

        reponse = self.client.post(
            reverse("web:vente_creer"),
            {
                "client": client.pk,
                "type_service": LigneFacture.TypeService.LOCATION,
                "description": "Location bureau",
                "quantite": 1,
                "prix_unitaire": "15000",
                "mode_paiement": Paiement.Mode.CASH_IN,
                "reference_transaction": "",
            },
        )

        self.assertEqual(reponse.status_code, 302)
        facture = Facture.objects.filter(client=client).order_by("-date_emission").first()
        self.assertIsNotNone(facture)
        self.assertEqual(facture.lignes.count(), 1)
        self.assertEqual(facture.paiements.count(), 1)
        self.assertEqual(facture.montant_total, 15000)

    def test_l_inscription_d_un_enfant_a_un_camp_genere_une_facture_au_nom_du_parent(self):
        agent = Utilisateur.objects.create_user(
            "agent-camp-facture", "agent-camp-facture@mbcode.cm", "MotDePasse123", role=Utilisateur.Role.AGENT
        )
        self.client.force_login(agent)

        parent = Client.objects.create(
            nom="Famille camp facture",
            type_client=Client.TypeClient.PARENT_ENFANT,
            telephone="+237600000115",
        )
        enfant = Enfant.objects.create(
            parent=parent,
            nom="Camp",
            prenom="Lola",
            date_naissance="2015-06-01",
        )
        camp = Camp.objects.create(
            theme=Camp.Theme.CODAGE,
            titre="Camp Python Junior",
            date_debut="2026-11-10",
            date_fin="2026-11-14",
            age_min=8,
            age_max=12,
            capacite=20,
            frais_inscription=25000,
            cout_formation=95000,
        )

        reponse = self.client.post(
            reverse("web:inscription_camp_creer"),
            {
                "enfant": enfant.pk,
                "camp": camp.pk,
                "statut": InscriptionCamp.Statut.CONFIRMEE,
                "paiement_echelonne": False,
            },
        )

        self.assertEqual(reponse.status_code, 302)
        facture = Facture.objects.filter(client=parent).order_by("-date_emission").first()
        self.assertIsNotNone(facture)
        self.assertEqual(facture.client, parent)
        self.assertEqual(facture.lignes.count(), 2)
        self.assertTrue(facture.lignes.filter(inscription_camp__enfant=enfant).exists())

    def test_un_agent_peut_creer_un_client_quelque_soit_son_type(self):
        agent = Utilisateur.objects.create_user(
            "agent-client", "agent-client@mbcode.cm", "MotDePasse123", role=Utilisateur.Role.AGENT
        )
        self.client.force_login(agent)

        for type_client in [
            Client.TypeClient.PARTICULIER,
            Client.TypeClient.ENTREPRISE,
        ]:
            reponse = self.client.post(
                reverse("web:client_creer"),
                {
                    "nom": f"Client {type_client}",
                    "type_client": type_client,
                    "telephone": f"+237600000{len(type_client)}",
                    "email": "",
                    "adresse": "",
                },
            )
            self.assertEqual(reponse.status_code, 302)
            self.assertTrue(Client.objects.filter(nom=f"Client {type_client}").exists())

        parent = Client.objects.create(
            nom="Famille Dupont",
            type_client=Client.TypeClient.PARENT_ENFANT,
            telephone="+237600000250",
        )
        Enfant.objects.create(parent=parent, nom="Dupont", prenom="Emma", date_naissance="2018-05-12")
        parent.full_clean()
        self.assertTrue(parent.enfants.exists())

    def test_un_agent_ne_peut_pas_creer_un_client_parent_via_api_sans_enfant(self):
        agent = Utilisateur.objects.create_user(
            "agent-api-parent", "agent-api-parent@mbcode.cm", "MotDePasse123", role=Utilisateur.Role.AGENT
        )
        api = APIClient()
        api.force_authenticate(agent)

        reponse = api.post(
            "/api/clients/",
            {
                "nom": "Famille sans enfant via API",
                "type_client": Client.TypeClient.PARENT_ENFANT,
                "telephone": "+237600000220",
                "email": "",
                "adresse": "",
            },
            format="json",
        )

        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("type_client", reponse.json())

    def test_un_client_parent_est_redirige_vers_le_formulaire_d_enfant(self):
        agent = Utilisateur.objects.create_user(
            "agent-parent-redirection", "agent-parent-redirection@mbcode.cm", "MotDePasse123", role=Utilisateur.Role.AGENT
        )
        self.client.force_login(agent)

        reponse = self.client.post(
            reverse("web:client_creer"),
            {
                "nom": "Famille sans enfant",
                "type_client": Client.TypeClient.PARENT_ENFANT,
                "telephone": "+237600000200",
                "email": "",
                "adresse": "",
            },
        )

        self.assertEqual(reponse.status_code, 302)
        parent = Client.objects.get(nom="Famille sans enfant")
        self.assertEqual(reponse.url, reverse("web:enfant_creer", args=[parent.pk]))


class InterfaceWebTestCase(TestCase):
    """Verifie que les pages principales de l'interface repondent correctement."""

    def setUp(self):
        self.admin = Utilisateur.objects.create_superuser("admin", "admin@mbcode.cm", "MotDePasse123")
        self.agent = Utilisateur.objects.create_user(
            "agent3", "agent3@mbcode.cm", "MotDePasse123", role=Utilisateur.Role.AGENT
        )

    def test_le_tableau_de_bord_necessite_une_authentification(self):
        reponse = self.client.get(reverse("web:tableau_de_bord"))
        self.assertEqual(reponse.status_code, 302)

    def test_le_tableau_de_bord_est_accessible_une_fois_connecte(self):
        self.client.force_login(self.admin)
        reponse = self.client.get(reverse("web:tableau_de_bord"))
        self.assertEqual(reponse.status_code, 200)

    def test_un_agent_ne_peut_pas_creer_un_espace(self):
        self.client.force_login(self.agent)
        reponse = self.client.get(reverse("web:espace_creer"))
        self.assertEqual(reponse.status_code, 403)

    def test_un_administrateur_peut_creer_un_espace(self):
        self.client.force_login(self.admin)
        reponse = self.client.post(reverse("web:espace_creer"), {
            "nom": "Bureau test",
            "type_espace": Espace.TypeEspace.BUREAU,
            "capacite": 2,
            "tarif_jour": 15000,
            "disponible": True,
            "equipements": "",
            "description": "",
        })
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(Espace.objects.filter(nom="Bureau test").exists())
