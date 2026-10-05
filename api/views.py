"""
ViewSets Django REST Framework - Application de gestion MBCODE.

Chaque ViewSet applique la permission definie dans gestion/permissions.py
correspondant au tableau des droits ADMIN / AGENT du cahier des charges.
"""
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from gestion import models
from gestion.permissions import (
    EstAdminOuLectureSeuleApresCreation,
    EstAdminPourEcriture,
    EstAdminSeulement,
    EstAuthentifie,
    verifier_cloture_modifiable,
    verifier_facture_non_verrouillee,
    verifier_objet_non_verrouille,
)

from . import serializers


class UtilisateurViewSet(viewsets.ModelViewSet):
    """Gestion des comptes ADMIN et AGENT - reservee aux administrateurs."""

    queryset = models.Utilisateur.objects.all().order_by("username")
    serializer_class = serializers.UtilisateurSerializer
    permission_classes = [EstAdminSeulement]
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "first_name", "last_name", "email"]


class ClientViewSet(viewsets.ModelViewSet):
    queryset = models.Client.objects.all().prefetch_related("enfants")
    serializer_class = serializers.ClientSerializer
    permission_classes = [EstAuthentifie]
    filterset_fields = ["type_client"]
    search_fields = ["nom", "telephone", "email"]


class EnfantViewSet(viewsets.ModelViewSet):
    queryset = models.Enfant.objects.select_related("parent").all()
    serializer_class = serializers.EnfantSerializer
    permission_classes = [EstAuthentifie]
    filterset_fields = ["parent"]
    search_fields = ["nom", "parent__nom"]


class FormateurViewSet(viewsets.ModelViewSet):
    queryset = models.Formateur.objects.all()
    serializer_class = serializers.FormateurSerializer
    permission_classes = [EstAuthentifie]
    search_fields = ["nom", "specialite"]


class EspaceViewSet(viewsets.ModelViewSet):
    queryset = models.Espace.objects.all()
    serializer_class = serializers.EspaceSerializer
    permission_classes = [EstAuthentifie]
    filterset_fields = ["type_espace", "disponible"]
    search_fields = ["nom"]


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = models.Reservation.objects.select_related("client", "espace").all()
    serializer_class = serializers.ReservationSerializer
    permission_classes = [EstAdminOuLectureSeuleApresCreation]
    filterset_fields = ["statut", "espace"]
    search_fields = ["client__nom", "espace__nom"]

    def perform_create(self, serializer):
        serializer.save(enregistree_par=self.request.user)


class CampViewSet(viewsets.ModelViewSet):
    """Catalogue des camps - creation/modification reservees a un administrateur."""

    queryset = models.Camp.objects.all().prefetch_related("formateurs", "inscriptions")
    serializer_class = serializers.CampSerializer
    permission_classes = [EstAdminPourEcriture]
    filterset_fields = ["theme"]
    search_fields = ["titre"]

    def perform_create(self, serializer):
        serializer.save(cree_par=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[EstAdminPourEcriture])
    def generer_depense_remuneration(self, request, pk=None):
        camp = self.get_object()
        depense = camp.creer_depense_remuneration(request.user)
        if depense is None:
            return Response({"detail": "Aucune remuneration a generer pour ce camp."}, status=400)
        return Response(serializers.DepenseSerializer(depense).data, status=201)


class InscriptionCampViewSet(viewsets.ModelViewSet):
    queryset = models.InscriptionCamp.objects.select_related("enfant", "camp").all()
    serializer_class = serializers.InscriptionCampSerializer
    permission_classes = [EstAdminOuLectureSeuleApresCreation]
    filterset_fields = ["statut", "camp", "paiement_echelonne"]

    def perform_create(self, serializer):
        inscription = serializer.save(enregistree_par=self.request.user)
        inscription.generer_facture(enregistre_par=self.request.user)


class FormationIAViewSet(viewsets.ModelViewSet):
    """Catalogue des formations - creation/modification reservees a un administrateur."""

    queryset = models.FormationIA.objects.all().prefetch_related("formateurs", "inscriptions")
    serializer_class = serializers.FormationIASerializer
    permission_classes = [EstAdminPourEcriture]
    filterset_fields = ["niveau", "public_cible"]
    search_fields = ["titre"]

    def perform_create(self, serializer):
        serializer.save(cree_par=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[EstAdminPourEcriture])
    def generer_depense_remuneration(self, request, pk=None):
        formation = self.get_object()
        depense = formation.creer_depense_remuneration(request.user)
        if depense is None:
            return Response({"detail": "Aucune remuneration a generer pour cette formation."}, status=400)
        return Response(serializers.DepenseSerializer(depense).data, status=201)


class InscriptionFormationViewSet(viewsets.ModelViewSet):
    queryset = models.InscriptionFormation.objects.select_related("client", "formation").all()
    serializer_class = serializers.InscriptionFormationSerializer
    permission_classes = [EstAdminOuLectureSeuleApresCreation]
    filterset_fields = ["statut", "formation", "paiement_echelonne"]

    def perform_create(self, serializer):
        serializer.save(enregistree_par=self.request.user)


class FactureViewSet(viewsets.ModelViewSet):
    """
    Ventes/factures. Verrouillees des l'enregistrement par un agent : seul
    un administrateur peut ensuite les modifier (permissions.py).
    """

    queryset = models.Facture.objects.select_related("client").prefetch_related("lignes", "paiements").all()
    serializer_class = serializers.FactureSerializer
    permission_classes = [EstAdminOuLectureSeuleApresCreation]
    filterset_fields = ["statut", "client"]
    search_fields = ["numero", "client__nom"]

    def perform_create(self, serializer):
        serializer.save(enregistree_par=self.request.user, verrouillee=True)

    def perform_update(self, serializer):
        verifier_facture_non_verrouillee(self.request.user, self.get_object())
        serializer.save()

    def perform_destroy(self, instance):
        verifier_facture_non_verrouillee(self.request.user, instance)
        instance.delete()


class LigneFactureViewSet(viewsets.ModelViewSet):
    queryset = models.LigneFacture.objects.select_related("facture").all()
    serializer_class = serializers.LigneFactureSerializer
    permission_classes = [EstAdminOuLectureSeuleApresCreation]
    filterset_fields = ["facture", "type_service"]

    def perform_update(self, serializer):
        verifier_facture_non_verrouillee(self.request.user, serializer.instance.facture)
        serializer.save()

    def perform_destroy(self, instance):
        verifier_facture_non_verrouillee(self.request.user, instance.facture)
        instance.delete()


class PaiementViewSet(viewsets.ModelViewSet):
    queryset = models.Paiement.objects.select_related("facture").all()
    serializer_class = serializers.PaiementSerializer
    permission_classes = [EstAdminOuLectureSeuleApresCreation]
    filterset_fields = ["facture", "mode", "sens"]

    def perform_create(self, serializer):
        serializer.save(enregistre_par=self.request.user)


class MouvementCaisseViewSet(viewsets.ModelViewSet):
    queryset = models.MouvementCaisse.objects.all()
    serializer_class = serializers.MouvementCaisseSerializer
    permission_classes = [EstAdminOuLectureSeuleApresCreation]
    filterset_fields = ["mode"]

    def perform_create(self, serializer):
        serializer.save(enregistre_par=self.request.user, verrouille=True)

    def perform_update(self, serializer):
        verifier_objet_non_verrouille(self.request.user, self.get_object())
        serializer.save()

    def perform_destroy(self, instance):
        verifier_objet_non_verrouille(self.request.user, instance)
        instance.delete()


class DepenseViewSet(viewsets.ModelViewSet):
    queryset = models.Depense.objects.all()
    serializer_class = serializers.DepenseSerializer
    permission_classes = [EstAdminOuLectureSeuleApresCreation]
    filterset_fields = ["categorie", "mode_paiement"]
    search_fields = ["libelle"]

    def perform_create(self, serializer):
        serializer.save(enregistre_par=self.request.user, verrouille=True)

    def perform_update(self, serializer):
        verifier_objet_non_verrouille(self.request.user, self.get_object())
        serializer.save()

    def perform_destroy(self, instance):
        verifier_objet_non_verrouille(self.request.user, instance)
        instance.delete()


class ChargeFixeViewSet(viewsets.ModelViewSet):
    """Parametrage des charges recurrentes - entierement reserve a l'administrateur."""

    queryset = models.ChargeFixe.objects.all()
    serializer_class = serializers.ChargeFixeSerializer
    permission_classes = [EstAdminSeulement]
    filterset_fields = ["categorie", "actif"]

    def perform_create(self, serializer):
        serializer.save(cree_par=self.request.user)

    @action(detail=True, methods=["post"])
    def generer_depense_du_mois(self, request, pk=None):
        charge = self.get_object()
        today = timezone.now().date()
        depense = charge.generer_depense_du_mois(today.year, today.month, request.user)
        if depense is None:
            return Response({"detail": "Depense deja generee ce mois-ci ou charge inactive."}, status=400)
        return Response(serializers.DepenseSerializer(depense).data, status=201)


class ClotureCaisseViewSet(viewsets.ModelViewSet):
    queryset = models.ClotureCaisse.objects.all()
    serializer_class = serializers.ClotureCaisseSerializer
    permission_classes = [EstAdminOuLectureSeuleApresCreation]
    filterset_fields = ["statut"]

    def perform_create(self, serializer):
        cloture = serializer.save()
        cloture.calculer_totaux()
        cloture.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        try:
            verifier_cloture_modifiable(instance)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))
        serializer.save()

    def perform_destroy(self, instance):
        try:
            verifier_cloture_modifiable(instance)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))
        instance.delete()

    @action(detail=True, methods=["post"])
    def cloturer(self, request, pk=None):
        """Recalcule les totaux et passe la cloture au statut CLOTUREE (irreversible)."""
        cloture = self.get_object()
        try:
            verifier_cloture_modifiable(cloture)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))
        cloture.calculer_totaux()
        cloture.statut = models.ClotureCaisse.Statut.CLOTUREE
        cloture.heure_cloture = timezone.now()
        cloture.cloturee_par = request.user
        cloture.full_clean()
        cloture.save()
        return Response(serializers.ClotureCaisseSerializer(cloture).data)


class RecapPeriodeViewSet(viewsets.ModelViewSet):
    queryset = models.RecapPeriode.objects.all()
    serializer_class = serializers.RecapPeriodeSerializer
    permission_classes = [EstAdminPourEcriture]
    filterset_fields = ["type_periode"]

    def perform_create(self, serializer):
        recap = serializer.save(genere_par=self.request.user)
        recap.calculer_totaux()
        recap.save()
