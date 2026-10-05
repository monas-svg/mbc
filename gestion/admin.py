from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from . import models


@admin.register(models.Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = ("username", "get_full_name", "role", "email", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Profil MBCODE", {"fields": ("role", "telephone")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "email",
                    "role",
                    "telephone",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(models.Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("nom", "type_client", "telephone", "email", "date_creation")
    list_filter = ("type_client",)
    search_fields = ("nom", "telephone", "email")


@admin.register(models.Enfant)
class EnfantAdmin(admin.ModelAdmin):
    list_display = ("prenom", "nom", "parent", "date_naissance", "age")
    search_fields = ("prenom", "nom", "parent__nom")


@admin.register(models.Formateur)
class FormateurAdmin(admin.ModelAdmin):
    list_display = ("nom", "specialite", "telephone", "email")
    search_fields = ("nom", "specialite")


@admin.register(models.Espace)
class EspaceAdmin(admin.ModelAdmin):
    list_display = ("nom", "type_espace", "capacite", "tarif_jour", "disponible")
    list_filter = ("type_espace", "disponible")


@admin.register(models.Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("espace", "client", "date_debut", "date_fin", "statut", "montant")
    list_filter = ("statut", "espace__type_espace")
    date_hierarchy = "date_debut"


class InscriptionCampInline(admin.TabularInline):
    model = models.InscriptionCamp
    extra = 0


@admin.register(models.Camp)
class CampAdmin(admin.ModelAdmin):
    list_display = ("titre", "theme", "date_debut", "date_fin", "capacite", "places_restantes")
    list_filter = ("theme",)
    filter_horizontal = ("formateurs",)
    inlines = [InscriptionCampInline]


@admin.register(models.InscriptionCamp)
class InscriptionCampAdmin(admin.ModelAdmin):
    list_display = ("enfant", "camp", "statut", "paiement_echelonne", "date_inscription")
    list_filter = ("statut", "paiement_echelonne")


class InscriptionFormationInline(admin.TabularInline):
    model = models.InscriptionFormation
    extra = 0


@admin.register(models.FormationIA)
class FormationIAAdmin(admin.ModelAdmin):
    list_display = ("titre", "niveau", "public_cible", "date_debut", "capacite")
    list_filter = ("niveau", "public_cible")
    filter_horizontal = ("formateurs",)
    inlines = [InscriptionFormationInline]


@admin.register(models.InscriptionFormation)
class InscriptionFormationAdmin(admin.ModelAdmin):
    list_display = ("client", "formation", "statut", "paiement_echelonne", "date_inscription")
    list_filter = ("statut", "paiement_echelonne")


class LigneFactureInline(admin.TabularInline):
    model = models.LigneFacture
    extra = 0


class PaiementInline(admin.TabularInline):
    model = models.Paiement
    extra = 0


@admin.register(models.Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = ("numero", "client", "date_emission", "statut", "montant_total", "verrouillee")
    list_filter = ("statut", "verrouillee")
    search_fields = ("numero", "client__nom")
    inlines = [LigneFactureInline, PaiementInline]
    readonly_fields = ("numero",)


@admin.register(models.MouvementCaisse)
class MouvementCaisseAdmin(admin.ModelAdmin):
    list_display = ("motif", "mode", "montant", "date_mouvement", "verrouille")
    list_filter = ("mode", "verrouille")


@admin.register(models.Depense)
class DepenseAdmin(admin.ModelAdmin):
    list_display = ("libelle", "categorie", "montant", "mode_paiement", "date_depense", "verrouille")
    list_filter = ("categorie", "mode_paiement", "verrouille")
    search_fields = ("libelle",)


@admin.register(models.ChargeFixe)
class ChargeFixeAdmin(admin.ModelAdmin):
    list_display = ("libelle", "categorie", "montant", "jour_prelevement", "actif")
    list_filter = ("categorie", "actif")


@admin.register(models.ClotureCaisse)
class ClotureCaisseAdmin(admin.ModelAdmin):
    list_display = ("date_jour", "statut", "especes_theorique", "especes_reel", "solde_global_theorique")
    list_filter = ("statut",)
    date_hierarchy = "date_jour"


@admin.register(models.RecapPeriode)
class RecapPeriodeAdmin(admin.ModelAdmin):
    list_display = ("type_periode", "date_debut", "date_fin", "total_general", "total_depenses", "solde_net")
    list_filter = ("type_periode",)
