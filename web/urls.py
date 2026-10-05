"""
Routage de l'interface web - Application de gestion MBCODE.
"""
from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    # Authentification
    path("connexion/", views.ConnexionView.as_view(), name="connexion"),
    path("deconnexion/", views.deconnexion, name="deconnexion"),

    # Tableau de bord
    path("", views.tableau_de_bord, name="tableau_de_bord"),

    # Ventes & facturation
    path("ventes/", views.ventes_liste, name="ventes_liste"),
    path("ventes/nouvelle/", views.vente_creer, name="vente_creer"),
    path("factures/<int:pk>/", views.facture_detail, name="facture_detail"),

    # Gestion des clients
    path("clients/", views.clients_liste, name="clients_liste"),
    path("clients/nouveau/", views.client_creer, name="client_creer"),
    path("clients/<int:pk>/", views.client_detail, name="client_detail"),
    path("clients/enfants/nouveau/", views.enfant_creer_rapide, name="enfant_creer_rapide"),
    path("clients/<int:client_pk>/enfants/nouveau/", views.enfant_creer, name="enfant_creer"),

    # Camps & formations
    path("camps-formations/", views.camps_liste, name="camps_liste"),
    path("camps-formations/camps/nouveau/", views.camp_creer, name="camp_creer"),
    path("camps-formations/formations/nouvelle/", views.formation_creer, name="formation_creer"),
    path("camps-formations/inscriptions/nouvelle/", views.inscription_camp_creer, name="inscription_camp_creer"),

    # Location d'espaces
    path("espaces/", views.espaces_liste, name="espaces_liste"),
    path("espaces/nouveau/", views.espace_creer, name="espace_creer"),
    path("espaces/reservations/nouvelle/", views.reservation_creer, name="reservation_creer"),

    # Depenses & tresorerie
    path("depenses/", views.depenses_liste, name="depenses_liste"),
    path("depenses/nouvelle/", views.depense_creer, name="depense_creer"),
    path("depenses/mouvements/nouveau/", views.mouvement_creer, name="mouvement_creer"),
    path("depenses/charges-fixes/", views.charges_fixes_liste, name="charges_fixes_liste"),
    path("depenses/charges-fixes/nouvelle/", views.charge_fixe_creer, name="charge_fixe_creer"),
    path("depenses/cloture/", views.cloture_jour, name="cloture_jour"),

    # Rapports
    path("rapports/", views.rapports, name="rapports"),
]
