"""
Serializers Django REST Framework - Application de gestion MBCODE.
"""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from gestion import models


class UtilisateurSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])

    class Meta:
        model = models.Utilisateur
        fields = (
            "id", "username", "first_name", "last_name", "email",
            "telephone", "role", "is_active", "password",
        )

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        utilisateur = models.Utilisateur(**validated_data)
        if password:
            utilisateur.set_password(password)
        utilisateur.save()
        return utilisateur

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class EnfantSerializer(serializers.ModelSerializer):
    age = serializers.ReadOnlyField()

    class Meta:
        model = models.Enfant
        fields = ("id", "parent", "nom", "prenom", "date_naissance", "age")


class ClientSerializer(serializers.ModelSerializer):
    enfants = EnfantSerializer(many=True, read_only=True)

    class Meta:
        model = models.Client
        fields = (
            "id", "nom", "type_client", "telephone", "email", "adresse",
            "date_creation", "enfants",
        )

    def validate(self, attrs):
        type_client = attrs.get("type_client", getattr(self.instance, "type_client", None))
        if type_client == models.Client.TypeClient.PARENT_ENFANT:
            parent = self.instance
            if parent is None:
                raise serializers.ValidationError(
                    {"type_client": "Un client de type Parent-enfant doit être complété par au moins un enfant."}
                )
            if not parent.enfants.exists():
                raise serializers.ValidationError(
                    {"type_client": "Un client de type Parent-enfant doit avoir au moins un enfant enregistré."}
                )
        return attrs


class FormateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Formateur
        fields = ("id", "nom", "specialite", "telephone", "email")


class EspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Espace
        fields = (
            "id", "nom", "type_espace", "capacite", "tarif_heure", "tarif_jour",
            "tarif_mois", "disponible", "equipements", "description", "photo",
        )


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Reservation
        fields = (
            "id", "client", "espace", "date_debut", "date_fin", "statut",
            "montant", "date_creation", "enregistree_par",
        )
        read_only_fields = ("enregistree_par",)

    def validate(self, attrs):
        date_debut = attrs.get("date_debut", getattr(self.instance, "date_debut", None))
        date_fin = attrs.get("date_fin", getattr(self.instance, "date_fin", None))
        if date_debut and date_fin and date_fin <= date_debut:
            raise serializers.ValidationError("La date de fin doit etre posterieure a la date de debut.")
        return attrs


class CampSerializer(serializers.ModelSerializer):
    places_restantes = serializers.ReadOnlyField()
    montant_total_inscription = serializers.ReadOnlyField()
    duree_jours = serializers.ReadOnlyField()

    class Meta:
        model = models.Camp
        fields = (
            "id", "theme", "titre", "formateurs", "date_debut", "date_fin",
            "age_min", "age_max", "capacite", "frais_inscription", "cout_formation",
            "nombre_enseignants", "montant_remuneration_enseignants", "photo",
            "places_restantes", "montant_total_inscription", "duree_jours",
        )

    def validate(self, attrs):
        age_min = attrs.get("age_min", getattr(self.instance, "age_min", None))
        age_max = attrs.get("age_max", getattr(self.instance, "age_max", None))
        if age_min is not None and age_max is not None and age_min > age_max:
            raise serializers.ValidationError("L'age minimum ne peut pas depasser l'age maximum.")
        return attrs


class InscriptionCampSerializer(serializers.ModelSerializer):
    tranche_age_libelle = serializers.ReadOnlyField()

    class Meta:
        model = models.InscriptionCamp
        fields = (
            "id", "enfant", "camp", "statut", "paiement_echelonne",
            "date_inscription", "tranche_age_libelle", "enregistree_par",
        )
        read_only_fields = ("enregistree_par",)


class FormationIASerializer(serializers.ModelSerializer):
    places_restantes = serializers.ReadOnlyField()
    montant_total_inscription = serializers.ReadOnlyField()

    class Meta:
        model = models.FormationIA
        fields = (
            "id", "titre", "niveau", "public_cible", "formateurs", "date_debut",
            "duree_heures", "capacite", "frais_inscription", "cout_formation",
            "nombre_enseignants", "montant_remuneration_enseignants",
            "places_restantes", "montant_total_inscription",
        )


class InscriptionFormationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.InscriptionFormation
        fields = (
            "id", "client", "formation", "statut", "paiement_echelonne",
            "date_inscription", "enregistree_par",
        )
        read_only_fields = ("enregistree_par",)


class LigneFactureSerializer(serializers.ModelSerializer):
    montant_ligne = serializers.ReadOnlyField()

    class Meta:
        model = models.LigneFacture
        fields = (
            "id", "facture", "type_service", "description", "reservation",
            "inscription_camp", "inscription_formation", "quantite",
            "prix_unitaire", "montant_ligne",
        )


class PaiementSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Paiement
        fields = (
            "id", "facture", "mode", "sens", "montant", "reference_transaction",
            "date_paiement", "enregistre_par",
        )
        read_only_fields = ("enregistre_par",)

    def validate(self, attrs):
        instance = models.Paiement(**{**(self.instance.__dict__ if self.instance else {}), **attrs})
        instance.clean()
        return attrs


class FactureSerializer(serializers.ModelSerializer):
    lignes = LigneFactureSerializer(many=True, read_only=True)
    paiements = PaiementSerializer(many=True, read_only=True)
    montant_total = serializers.ReadOnlyField()
    montant_paye = serializers.ReadOnlyField()
    solde = serializers.ReadOnlyField()

    class Meta:
        model = models.Facture
        fields = (
            "id", "numero", "client", "date_emission", "statut", "verrouillee",
            "enregistree_par", "lignes", "paiements", "montant_total",
            "montant_paye", "solde",
        )
        read_only_fields = ("numero", "enregistree_par", "verrouillee")


class MouvementCaisseSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MouvementCaisse
        fields = (
            "id", "mode", "montant", "motif", "date_mouvement",
            "verrouille", "enregistre_par",
        )
        read_only_fields = ("verrouille", "enregistre_par")


class DepenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Depense
        fields = (
            "id", "categorie", "libelle", "montant", "mode_paiement",
            "date_depense", "piece_justificative", "charge_fixe",
            "verrouille", "enregistre_par",
        )
        read_only_fields = ("verrouille", "enregistre_par", "charge_fixe")


class ChargeFixeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ChargeFixe
        fields = (
            "id", "libelle", "categorie", "montant", "mode_paiement",
            "jour_prelevement", "actif", "date_debut", "date_fin", "cree_par",
        )
        read_only_fields = ("cree_par",)


class ClotureCaisseSerializer(serializers.ModelSerializer):
    ecart_especes = serializers.ReadOnlyField()
    solde_global_theorique = serializers.ReadOnlyField()

    class Meta:
        model = models.ClotureCaisse
        fields = (
            "id", "date_jour", "statut", "especes_theorique", "especes_reel",
            "orange_money_total", "mtn_momo_total", "total_depenses",
            "heure_cloture", "cloturee_par", "observations",
            "ecart_especes", "solde_global_theorique",
        )
        read_only_fields = (
            "especes_theorique", "orange_money_total", "mtn_momo_total",
            "total_depenses", "cloturee_par",
        )


class RecapPeriodeSerializer(serializers.ModelSerializer):
    total_general = serializers.ReadOnlyField()
    solde_net = serializers.ReadOnlyField()

    class Meta:
        model = models.RecapPeriode
        fields = (
            "id", "type_periode", "date_debut", "date_fin", "total_especes",
            "total_orange_money", "total_mtn_momo", "total_depenses",
            "genere_le", "genere_par", "total_general", "solde_net",
        )
        read_only_fields = (
            "total_especes", "total_orange_money", "total_mtn_momo",
            "total_depenses", "genere_par",
        )
