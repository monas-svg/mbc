"""
Formulaires de l'interface web - Application de gestion MBCODE.
"""
from django import forms
from django.contrib.auth.forms import AuthenticationForm

from gestion import models

INPUT_CLASSES = "champ-saisie"


class ConnexionForm(AuthenticationForm):
    username = forms.CharField(
        label="Identifiant",
        widget=forms.TextInput(attrs={"class": INPUT_CLASSES, "autofocus": True, "placeholder": "Identifiant"}),
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASSES, "placeholder": "Mot de passe"}),
    )


def _style(form):
    for field in form.fields.values():
        existing = field.widget.attrs.get("class", "")
        field.widget.attrs["class"] = (existing + " " + INPUT_CLASSES).strip()
    return form


class ClientForm(forms.ModelForm):
    class Meta:
        model = models.Client
        fields = ["nom", "type_client", "telephone", "email", "adresse"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)


class EnfantForm(forms.ModelForm):
    class Meta:
        model = models.Enfant
        fields = ["parent", "nom", "prenom", "date_naissance"]
        labels = {
            "parent": "Parent",
            "nom": "Nom",
            "prenom": "Prénom",
            "date_naissance": "Date de naissance",
        }
        widgets = {"date_naissance": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)


class EspaceForm(forms.ModelForm):
    class Meta:
        model = models.Espace
        fields = [
            "nom", "type_espace", "capacite", "tarif_heure", "tarif_jour",
            "tarif_mois", "disponible", "equipements", "description", "photo",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)


class ReservationForm(forms.ModelForm):
    class Meta:
        model = models.Reservation
        fields = ["client", "espace", "date_debut", "date_fin", "statut", "montant"]
        widgets = {
            "date_debut": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "date_fin": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)

    def clean(self):
        cleaned = super().clean()
        debut, fin = cleaned.get("date_debut"), cleaned.get("date_fin")
        if debut and fin and fin <= debut:
            raise forms.ValidationError("La date de fin doit etre posterieure a la date de debut.")
        return cleaned


class CampForm(forms.ModelForm):
    class Meta:
        model = models.Camp
        fields = [
            "theme", "titre", "formateurs", "date_debut", "date_fin", "age_min",
            "age_max", "capacite", "frais_inscription", "cout_formation",
            "nombre_enseignants", "montant_remuneration_enseignants", "photo",
        ]
        widgets = {
            "date_debut": forms.DateInput(attrs={"type": "date"}),
            "date_fin": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)


class InscriptionCampForm(forms.ModelForm):
    class Meta:
        model = models.InscriptionCamp
        fields = ["enfant", "camp", "statut", "paiement_echelonne"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)


class FormationForm(forms.ModelForm):
    class Meta:
        model = models.FormationIA
        fields = [
            "titre", "niveau", "public_cible", "formateurs", "date_debut",
            "duree_heures", "capacite", "frais_inscription", "cout_formation",
            "nombre_enseignants", "montant_remuneration_enseignants",
        ]
        widgets = {"date_debut": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)


class InscriptionFormationForm(forms.ModelForm):
    class Meta:
        model = models.InscriptionFormation
        fields = ["client", "formation", "statut", "paiement_echelonne"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)


class VenteForm(forms.Form):
    """Formulaire simplifie de creation de vente : une facture avec une ligne et un premier paiement."""

    client = forms.ModelChoiceField(queryset=models.Client.objects.all(), label="Client")
    type_service = forms.ChoiceField(choices=models.LigneFacture.TypeService.choices, label="Type de prestation")
    description = forms.CharField(max_length=255, label="Description")
    quantite = forms.IntegerField(min_value=1, initial=1, label="Quantite")
    prix_unitaire = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0, label="Prix unitaire (FCFA)")
    mode_paiement = forms.ChoiceField(choices=models.Paiement.Mode.choices, label="Mode de paiement")
    reference_transaction = forms.CharField(max_length=100, required=False, label="Reference de transaction")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)

    def clean(self):
        cleaned = super().clean()
        type_service = cleaned.get("type_service")
        mode = cleaned.get("mode_paiement")
        reference = cleaned.get("reference_transaction")
        especes = (models.Paiement.Mode.CASH_IN, models.Paiement.Mode.CASH_OUT)
        if type_service in (models.LigneFacture.TypeService.CAMP, models.LigneFacture.TypeService.FORMATION_IA):
            if mode not in especes:
                raise forms.ValidationError(
                    "Les camps et les formations IA se reglent uniquement en especes."
                )
        if mode in (models.Paiement.Mode.ORANGE_MONEY, models.Paiement.Mode.MTN_MOMO) and not reference:
            self.add_error(
                "reference_transaction",
                "La reference de transaction est obligatoire pour Orange Money et MTN Mobile Money.",
            )
        return cleaned


class DepenseForm(forms.ModelForm):
    class Meta:
        model = models.Depense
        fields = ["categorie", "libelle", "montant", "mode_paiement", "piece_justificative"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)


class MouvementCaisseForm(forms.ModelForm):
    class Meta:
        model = models.MouvementCaisse
        fields = ["mode", "montant", "motif"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)


class ChargeFixeForm(forms.ModelForm):
    class Meta:
        model = models.ChargeFixe
        fields = [
            "libelle", "categorie", "montant", "mode_paiement",
            "jour_prelevement", "actif", "date_debut", "date_fin",
        ]
        widgets = {
            "date_debut": forms.DateInput(attrs={"type": "date"}),
            "date_fin": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)


class ClotureCaisseForm(forms.ModelForm):
    class Meta:
        model = models.ClotureCaisse
        fields = ["especes_reel", "observations"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)
