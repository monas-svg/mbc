"""
Routage de l'API REST - Application de gestion MBCODE.
"""
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.urls import include, path

from . import views

router = DefaultRouter()
router.register("utilisateurs", views.UtilisateurViewSet, basename="utilisateur")
router.register("clients", views.ClientViewSet, basename="client")
router.register("enfants", views.EnfantViewSet, basename="enfant")
router.register("formateurs", views.FormateurViewSet, basename="formateur")
router.register("espaces", views.EspaceViewSet, basename="espace")
router.register("reservations", views.ReservationViewSet, basename="reservation")
router.register("camps", views.CampViewSet, basename="camp")
router.register("inscriptions-camps", views.InscriptionCampViewSet, basename="inscriptioncamp")
router.register("formations", views.FormationIAViewSet, basename="formationia")
router.register("inscriptions-formations", views.InscriptionFormationViewSet, basename="inscriptionformation")
router.register("factures", views.FactureViewSet, basename="facture")
router.register("lignes-facture", views.LigneFactureViewSet, basename="lignefacture")
router.register("paiements", views.PaiementViewSet, basename="paiement")
router.register("mouvements-caisse", views.MouvementCaisseViewSet, basename="mouvementcaisse")
router.register("depenses", views.DepenseViewSet, basename="depense")
router.register("charges-fixes", views.ChargeFixeViewSet, basename="chargefixe")
router.register("clotures-caisse", views.ClotureCaisseViewSet, basename="cloturecaisse")
router.register("recaps-periode", views.RecapPeriodeViewSet, basename="recapperiode")

urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("", include(router.urls)),
]
