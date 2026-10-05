"""
Modele de donnees - Application de gestion MBCODE

Location de bureaux/coworking/salles de reunion, camps de formation
(robotique, codage, IA) et formations pour etudiants et professionnels.

Base de donnees cible : PostgreSQL
"""

from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# COMPTES UTILISATEURS (AUTH_USER_MODEL = "gestion.Utilisateur")
# ---------------------------------------------------------------------------

class Utilisateur(AbstractUser):
    """
    Deux profils :
    - ADMIN  : tous les droits (creer, modifier, supprimer, cloturer la caisse).
    - AGENT  : peut enregistrer une vente / un paiement et imprimer la facture
               correspondante. Ne peut en revanche jamais modifier ni supprimer
               une vente deja enregistree, meme la sienne - la verification est
               appliquee dans permissions.py, pas ici, mais le champ `role`
               sert de source de verite pour ces regles.
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrateur"
        AGENT = "AGENT", "Agent de vente"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.AGENT)
    telephone = models.CharField(max_length=20, blank=True)

    @property
    def est_admin(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


# ---------------------------------------------------------------------------
# CLIENTS ET ENFANTS
# ---------------------------------------------------------------------------

class Client(models.Model):
    class TypeClient(models.TextChoices):
        PARTICULIER = "PARTICULIER", "Particulier"
        PARENT_ENFANT = "PARENT_ENFANT", "Parent-enfant"
        ENTREPRISE = "ENTREPRISE", "Entreprise / organisation"

    nom = models.CharField(max_length=150)
    type_client = models.CharField(
        max_length=20, choices=TypeClient.choices, default=TypeClient.PARTICULIER
    )
    telephone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)
    adresse = models.CharField(max_length=255, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nom"]
        indexes = [models.Index(fields=["telephone"])]
        verbose_name = "Client"
        verbose_name_plural = "Clients"

    def clean(self):
        super().clean()
        if self.type_client == self.TypeClient.PARENT_ENFANT and self.pk is not None and not self.enfants.exists():
            raise ValidationError(
                "Un client de type Parent-enfant doit avoir au moins un enfant enregistre."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


class Enfant(models.Model):
    parent = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="enfants")
    nom = models.CharField(max_length=150)
    prenom = models.CharField(max_length=150)
    date_naissance = models.DateField()

    class Meta:
        verbose_name = "Enfant"
        verbose_name_plural = "Enfants"

    def clean(self):
        super().clean()
        if self.parent_id and self.parent.type_client != Client.TypeClient.PARENT_ENFANT:
            raise ValidationError({
                "parent": "Un enfant doit être rattaché à un client de type Parent-enfant."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.prenom} {self.nom} (parent : {self.parent.nom})"

    @property
    def age(self):
        today = timezone.now().date()
        return today.year - self.date_naissance.year - (
            (today.month, today.day) < (self.date_naissance.month, self.date_naissance.day)
        )


# ---------------------------------------------------------------------------
# FORMATEURS
# ---------------------------------------------------------------------------

class Formateur(models.Model):
    nom = models.CharField(max_length=150)
    specialite = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "Formateur"
        verbose_name_plural = "Formateurs"

    def __str__(self):
        return self.nom


# ---------------------------------------------------------------------------
# ESPACES (BUREAUX / COWORKING) ET RESERVATIONS
# ---------------------------------------------------------------------------

class Espace(models.Model):
    class TypeEspace(models.TextChoices):
        BUREAU = "BUREAU", "Bureau prive"
        COWORKING = "COWORKING", "Espace coworking"
        SALLE_REUNION = "SALLE_REUNION", "Salle de reunion"

    nom = models.CharField(max_length=100)
    type_espace = models.CharField(max_length=20, choices=TypeEspace.choices)
    capacite = models.PositiveIntegerField(default=1)
    tarif_heure = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tarif_jour = models.DecimalField(max_digits=10, decimal_places=2)
    tarif_mois = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    disponible = models.BooleanField(default=True)
    equipements = models.CharField(
        max_length=255, blank=True,
        help_text="Ex : videoprojecteur, ecran, visioconference.",
    )
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="espaces/%Y/%m/", blank=True, null=True)

    class Meta:
        ordering = ["type_espace", "nom"]
        verbose_name = "Espace"
        verbose_name_plural = "Espaces"

    def __str__(self):
        return f"{self.get_type_espace_display()} - {self.nom}"


class Reservation(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente"
        CONFIRMEE = "CONFIRMEE", "Confirmee"
        EN_COURS = "EN_COURS", "En cours"
        TERMINEE = "TERMINEE", "Terminee"
        ANNULEE = "ANNULEE", "Annulee"

    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="reservations")
    espace = models.ForeignKey(Espace, on_delete=models.PROTECT, related_name="reservations")
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    montant = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    date_creation = models.DateTimeField(auto_now_add=True)
    enregistree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reservations_enregistrees",
    )

    class Meta:
        ordering = ["-date_debut"]
        verbose_name = "Reservation"
        verbose_name_plural = "Reservations"
        constraints = [
            models.CheckConstraint(
                check=models.Q(date_fin__gt=models.F("date_debut")),
                name="reservation_date_fin_apres_debut",
            )
        ]
        indexes = [models.Index(fields=["espace", "date_debut", "date_fin"])]

    def __str__(self):
        return f"Reservation {self.espace} - {self.client}"


# ---------------------------------------------------------------------------
# CAMPS DE FORMATION (ENFANTS)
# ---------------------------------------------------------------------------

class Camp(models.Model):
    """
    Camp de formation pour enfants. L'inscription a un camp comporte deux
    composantes financieres distinctes : des frais d'inscription (payes
    une fois) et le cout de la formation proprement dite. Seul un
    administrateur peut creer, modifier ou supprimer un camp (permission
    EstAdminPourEcriture cote API).
    """

    class Theme(models.TextChoices):
        ROBOTIQUE = "ROBOTIQUE", "Robotique"
        CODAGE = "CODAGE", "Codage"
        IA = "IA", "Intelligence artificielle"

    theme = models.CharField(max_length=20, choices=Theme.choices)
    titre = models.CharField(max_length=150)
    formateurs = models.ManyToManyField(Formateur, related_name="camps", blank=True)
    date_debut = models.DateField()
    date_fin = models.DateField()
    age_min = models.PositiveIntegerField()
    age_max = models.PositiveIntegerField()
    capacite = models.PositiveIntegerField()
    frais_inscription = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Frais payes une seule fois, a l'inscription de l'enfant.",
    )
    cout_formation = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Cout du camp proprement dit (hors frais d'inscription), facture au parent.",
    )
    nombre_enseignants = models.PositiveIntegerField(
        default=1, help_text="Nombre d'enseignants/formateurs mobilises pour ce camp.",
    )
    montant_remuneration_enseignants = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Montant total a verser aux enseignants pour cette session (charge, pas un revenu).",
    )
    photo = models.ImageField(upload_to="camps/%Y/%m/", blank=True, null=True)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="camps_crees",
    )

    class Meta:
        ordering = ["-date_debut"]
        verbose_name = "Camp"
        verbose_name_plural = "Camps"

    def __str__(self):
        return f"{self.get_theme_display()} - {self.titre}"

    @property
    def duree_jours(self):
        return (self.date_fin - self.date_debut).days + 1

    @property
    def montant_total_inscription(self):
        """Montant du par enfant inscrit : frais d'inscription + cout de la formation."""
        return self.frais_inscription + self.cout_formation

    @property
    def places_restantes(self):
        occupees = self.inscriptions.filter(statut=InscriptionCamp.Statut.CONFIRMEE).count()
        return self.capacite - occupees

    @property
    def taux_remplissage(self):
        if not self.capacite:
            return 0
        occupees = self.inscriptions.filter(statut=InscriptionCamp.Statut.CONFIRMEE).count()
        return round(min(occupees, self.capacite) / self.capacite * 100)

    def creer_depense_remuneration(self, enregistre_par):
        """Enregistre la remuneration des enseignants de ce camp comme Depense (categorie FORMATEUR)."""
        if self.montant_remuneration_enseignants <= 0:
            return None
        return Depense.objects.create(
            categorie=Depense.Categorie.FORMATEUR,
            libelle=f"Remuneration enseignants - {self.titre}",
            montant=self.montant_remuneration_enseignants,
            mode_paiement=Depense.Mode.ESPECES,
            enregistre_par=enregistre_par,
        )


class InscriptionCamp(models.Model):
    """
    Inscription d'un enfant a un camp. Les frais d'inscription se reglent
    en une fois ; les frais de formation (Camp.cout_formation) peuvent, a
    la demande du parent, etre regles en 2 tranches maximum
    (paiement_echelonne) via deux Paiement distincts sur la meme Facture.
    """

    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente"
        CONFIRMEE = "CONFIRMEE", "Confirmee"
        ANNULEE = "ANNULEE", "Annulee"

    enfant = models.ForeignKey(Enfant, on_delete=models.CASCADE, related_name="inscriptions_camps")
    camp = models.ForeignKey(Camp, on_delete=models.CASCADE, related_name="inscriptions")
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    paiement_echelonne = models.BooleanField(
        default=False,
        help_text="Si vrai, les frais de formation (hors frais d'inscription) sont regles en 2 tranches maximum.",
    )
    date_inscription = models.DateTimeField(auto_now_add=True)
    enregistree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="inscriptions_camps_enregistrees",
    )

    class Meta:
        unique_together = ("enfant", "camp")
        verbose_name = "Inscription a un camp"
        verbose_name_plural = "Inscriptions aux camps"

    @property
    def tranche_age_libelle(self):
        return f"{self.camp.age_min}-{self.camp.age_max} ans"

    def __str__(self):
        return f"{self.enfant.nom} - {self.camp.titre}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.statut == self.Statut.CONFIRMEE:
            self.generer_facture(enregistre_par=self.enregistree_par)

    def generer_facture(self, enregistre_par=None):
        """Crée une facture pour le parent de l'enfant inscrit au camp."""
        parent = getattr(self.enfant, "parent", None)
        if parent is None or parent.type_client != Client.TypeClient.PARENT_ENFANT:
            return None

        facture_existante = Facture.objects.filter(client=parent, lignes__inscription_camp=self).first()
        if facture_existante is not None:
            return facture_existante

        facture = Facture.objects.create(
            client=parent,
            enregistree_par=enregistre_par,
            statut=Facture.Statut.EMISE,
        )

        lignes = []
        if self.camp.frais_inscription > 0:
            lignes.append(
                LigneFacture(
                    facture=facture,
                    type_service=LigneFacture.TypeService.CAMP,
                    description=f"Frais d'inscription - {self.camp.titre}",
                    inscription_camp=self,
                    quantite=1,
                    prix_unitaire=self.camp.frais_inscription,
                )
            )
        if self.camp.cout_formation > 0:
            lignes.append(
                LigneFacture(
                    facture=facture,
                    type_service=LigneFacture.TypeService.CAMP,
                    description=f"Formation - {self.camp.titre}",
                    inscription_camp=self,
                    quantite=1,
                    prix_unitaire=self.camp.cout_formation,
                )
            )

        if lignes:
            LigneFacture.objects.bulk_create(lignes)

        return facture


# ---------------------------------------------------------------------------
# FORMATIONS (ETUDIANTS & PROFESSIONNELS)
# ---------------------------------------------------------------------------

class FormationIA(models.Model):
    """
    Session de formation en intelligence artificielle, ouverte aux etudiants
    et aux professionnels. Comme pour Camp, l'inscription comporte des frais
    d'inscription (payes une fois) et le cout de la formation proprement
    dite. Seul un administrateur peut creer, modifier ou supprimer une
    formation (permission EstAdminPourEcriture cote API) ; la consultation
    du catalogue est ouverte aux agents.
    """

    class Niveau(models.TextChoices):
        DEBUTANT = "DEBUTANT", "Debutant"
        INTERMEDIAIRE = "INTERMEDIAIRE", "Intermediaire"
        AVANCE = "AVANCE", "Avance"

    class PublicCible(models.TextChoices):
        ETUDIANTS = "ETUDIANTS", "Etudiants"
        PROFESSIONNELS = "PROFESSIONNELS", "Professionnels"
        ETUDIANTS_PROFESSIONNELS = "ETUDIANTS_PROFESSIONNELS", "Etudiants et professionnels"

    titre = models.CharField(max_length=150)
    niveau = models.CharField(max_length=20, choices=Niveau.choices)
    public_cible = models.CharField(
        max_length=30, choices=PublicCible.choices, default=PublicCible.ETUDIANTS_PROFESSIONNELS,
    )
    formateurs = models.ManyToManyField(Formateur, related_name="formations", blank=True)
    date_debut = models.DateTimeField()
    duree_heures = models.PositiveIntegerField()
    capacite = models.PositiveIntegerField()
    frais_inscription = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Frais payes une seule fois, a l'inscription du participant.",
    )
    cout_formation = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Cout de la formation proprement dite (hors frais d'inscription), facture au participant.",
    )
    nombre_enseignants = models.PositiveIntegerField(
        default=1, help_text="Nombre d'enseignants/formateurs mobilises pour cette session.",
    )
    montant_remuneration_enseignants = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Montant total a verser aux enseignants pour cette session (charge, pas un revenu).",
    )
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="formations_creees",
    )

    class Meta:
        ordering = ["-date_debut"]
        verbose_name = "Formation IA"
        verbose_name_plural = "Formations IA"

    def __str__(self):
        return self.titre

    @property
    def montant_total_inscription(self):
        """Montant du par participant : frais d'inscription + cout de la formation."""
        return self.frais_inscription + self.cout_formation

    @property
    def places_restantes(self):
        occupees = self.inscriptions.filter(statut=InscriptionFormation.Statut.CONFIRMEE).count()
        return self.capacite - occupees

    def creer_depense_remuneration(self, enregistre_par):
        """Enregistre la remuneration des enseignants de cette session comme Depense (categorie FORMATEUR)."""
        if self.montant_remuneration_enseignants <= 0:
            return None
        return Depense.objects.create(
            categorie=Depense.Categorie.FORMATEUR,
            libelle=f"Remuneration enseignants - {self.titre}",
            montant=self.montant_remuneration_enseignants,
            mode_paiement=Depense.Mode.ESPECES,
            enregistre_par=enregistre_par,
        )


class InscriptionFormation(models.Model):
    """
    Inscription d'un client (etudiant ou professionnel) a une formation.
    Les frais d'inscription se reglent en une fois ; les frais de formation
    (FormationIA.cout_formation) peuvent, a la demande du participant, etre
    regles en 2 tranches maximum (paiement_echelonne), comme pour les camps.
    """

    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente"
        CONFIRMEE = "CONFIRMEE", "Confirmee"
        ANNULEE = "ANNULEE", "Annulee"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="inscriptions_formations")
    formation = models.ForeignKey(FormationIA, on_delete=models.CASCADE, related_name="inscriptions")
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    paiement_echelonne = models.BooleanField(
        default=False,
        help_text="Si vrai, les frais de formation (hors frais d'inscription) sont regles en 2 tranches maximum.",
    )
    date_inscription = models.DateTimeField(auto_now_add=True)
    enregistree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="inscriptions_formations_enregistrees",
    )

    class Meta:
        unique_together = ("client", "formation")
        verbose_name = "Inscription a une formation"
        verbose_name_plural = "Inscriptions aux formations"

    def __str__(self):
        return f"{self.client.nom} - {self.formation.titre}"


# ---------------------------------------------------------------------------
# FACTURATION
# ---------------------------------------------------------------------------

class Facture(models.Model):
    class Statut(models.TextChoices):
        BROUILLON = "BROUILLON", "Brouillon"
        EMISE = "EMISE", "Emise"
        PAYEE = "PAYEE", "Payee"
        PARTIELLE = "PARTIELLE", "Partiellement payee"
        ANNULEE = "ANNULEE", "Annulee"

    numero = models.CharField(max_length=30, unique=True, editable=False)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="factures")
    date_emission = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.BROUILLON)

    # Tracabilite et verrouillage : des qu'un agent enregistre la vente,
    # la facture est verrouillee. Seul un compte ADMIN peut la modifier
    # (controle applique dans gestion/permissions.py au niveau des vues/API).
    enregistree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="factures_enregistrees",
    )
    verrouillee = models.BooleanField(
        default=True,
        help_text="True des la creation : seul un administrateur peut modifier la facture.",
    )

    class Meta:
        ordering = ["-date_emission"]
        verbose_name = "Facture"
        verbose_name_plural = "Factures"

    @property
    def montant_total(self):
        return sum((l.montant_ligne for l in self.lignes.all()), start=0)

    @property
    def montant_paye(self):
        entrees = self.paiements.filter(sens=Paiement.Sens.ENTREE)
        sorties = self.paiements.filter(sens=Paiement.Sens.SORTIE)
        return sum((p.montant for p in entrees), start=0) - sum((p.montant for p in sorties), start=0)

    @property
    def solde(self):
        return self.montant_total - self.montant_paye

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = f"FA-{timezone.now():%Y%m}-{Facture.objects.count() + 1:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.numero


class LigneFacture(models.Model):
    """
    Detail d'une prestation facturee. Pour un camp ou une formation IA, une
    inscription donne lieu a deux lignes distinctes sur la facture : une
    ligne "Frais d'inscription" et une ligne "Cout de la formation", afin
    que chaque montant reste visible separement.
    """

    class TypeService(models.TextChoices):
        LOCATION = "LOCATION", "Location d'espace"
        CAMP = "CAMP", "Camp de formation"
        FORMATION_IA = "FORMATION_IA", "Formation IA"

    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, related_name="lignes")
    type_service = models.CharField(max_length=20, choices=TypeService.choices)
    description = models.CharField(max_length=255)

    # Liens optionnels vers la prestation d'origine (un seul rempli selon type_service)
    reservation = models.ForeignKey(
        Reservation, on_delete=models.SET_NULL, null=True, blank=True, related_name="lignes_facture"
    )
    inscription_camp = models.ForeignKey(
        InscriptionCamp, on_delete=models.SET_NULL, null=True, blank=True, related_name="lignes_facture"
    )
    inscription_formation = models.ForeignKey(
        InscriptionFormation, on_delete=models.SET_NULL, null=True, blank=True, related_name="lignes_facture"
    )

    quantite = models.PositiveIntegerField(default=1)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Ligne de facture"
        verbose_name_plural = "Lignes de facture"

    @property
    def montant_ligne(self):
        return self.quantite * self.prix_unitaire

    def __str__(self):
        return f"{self.description} ({self.montant_ligne} FCFA)"


class Paiement(models.Model):
    """
    Reglement d'une facture. Orange Money et MTN Mobile Money sont acceptes
    pour la location d'espaces, mais PAS pour les camps de formation ni les
    formations IA : ces deux services se reglent exclusivement en especes
    (voir clean()).
    """

    class Mode(models.TextChoices):
        ORANGE_MONEY = "ORANGE_MONEY", "Orange Money"
        MTN_MOMO = "MTN_MOMO", "MTN Mobile Money"
        CASH_IN = "CASH_IN", "Especes - encaissement"
        CASH_OUT = "CASH_OUT", "Especes - decaissement / remboursement"

    MODES_ESPECES = (Mode.CASH_IN, Mode.CASH_OUT)

    class Sens(models.TextChoices):
        ENTREE = "ENTREE", "Entree (encaissement)"
        SORTIE = "SORTIE", "Sortie (remboursement)"

    facture = models.ForeignKey(Facture, on_delete=models.PROTECT, related_name="paiements")
    mode = models.CharField(max_length=20, choices=Mode.choices)
    sens = models.CharField(max_length=10, choices=Sens.choices, default=Sens.ENTREE)
    montant = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    reference_transaction = models.CharField(
        max_length=100, blank=True,
        help_text="Identifiant de transaction Orange Money / MTN MoMo (obligatoire pour le mobile money)",
    )
    date_paiement = models.DateTimeField(auto_now_add=True)
    enregistre_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="paiements_enregistres",
    )

    class Meta:
        ordering = ["-date_paiement"]
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"

    def clean(self):
        if self.mode in (self.Mode.ORANGE_MONEY, self.Mode.MTN_MOMO) and not self.reference_transaction:
            raise ValidationError(
                "La reference de transaction est obligatoire pour Orange Money et MTN Mobile Money."
            )

        if self.facture_id and self.mode not in self.MODES_ESPECES:
            types_reserves_especes = {
                LigneFacture.TypeService.CAMP,
                LigneFacture.TypeService.FORMATION_IA,
            }
            types_facture = set(
                self.facture.lignes.values_list("type_service", flat=True)
            )
            if types_reserves_especes & types_facture:
                raise ValidationError(
                    "Les camps de formation et les formations IA se reglent uniquement en "
                    "especes (Cash In / Cash Out) : Orange Money et MTN Mobile Money ne sont "
                    "pas autorises pour ce type de facture."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_mode_display()} - {self.montant} FCFA ({self.get_sens_display()})"


# ---------------------------------------------------------------------------
# CAISSE : APPROVISIONNEMENTS, DEPENSES, CLOTURE ET RECAPITULATIFS PERIODIQUES
# ---------------------------------------------------------------------------

class MouvementCaisse(models.Model):
    """
    Entree d'argent en caisse qui ne provient pas d'une vente (ex : apport
    de fonds du gerant, reapprovisionnement de la caisse especes, virement
    recu). Les encaissements de ventes restent dans `Paiement`, et les
    sorties d'argent hors vente sont tracees dans `Depense` :
    `MouvementCaisse` ne couvre donc que les entrees.
    """

    class Mode(models.TextChoices):
        ESPECES = "ESPECES", "Especes"
        ORANGE_MONEY = "ORANGE_MONEY", "Orange Money"
        MTN_MOMO = "MTN_MOMO", "MTN Mobile Money"

    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.ESPECES)
    montant = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    motif = models.CharField(max_length=255)
    date_mouvement = models.DateTimeField(auto_now_add=True)
    verrouille = models.BooleanField(
        default=True,
        help_text="True des la creation : seul un administrateur peut modifier ou supprimer ce mouvement.",
    )
    enregistre_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="mouvements_caisse",
    )

    class Meta:
        ordering = ["-date_mouvement"]
        verbose_name = "Mouvement de caisse"
        verbose_name_plural = "Mouvements de caisse"

    def __str__(self):
        return f"Entree caisse - {self.montant} FCFA ({self.motif})"


class Depense(models.Model):
    """
    Depense de l'entreprise (fournitures, loyer, salaires, transport...).
    Chaque depense est rattachee a un mode de reglement afin d'etre deduite
    du bon canal (especes ou mobile money) dans la cloture journaliere et
    les recapitulatifs periodiques.
    """

    class Categorie(models.TextChoices):
        FOURNITURES = "FOURNITURES", "Fournitures et consommables"
        LOYER = "LOYER", "Loyer et charges locatives"
        ABONNEMENT = "ABONNEMENT", "Abonnement (Internet/Starlink, logiciels...)"
        SALAIRE = "SALAIRE", "Salaires et avances sur salaire"
        TRANSPORT = "TRANSPORT", "Transport et deplacement"
        MAINTENANCE = "MAINTENANCE", "Maintenance et reparations"
        FORMATEUR = "FORMATEUR", "Remuneration de formateur"
        AUTRE = "AUTRE", "Autre depense"

    class Mode(models.TextChoices):
        ESPECES = "ESPECES", "Especes"
        ORANGE_MONEY = "ORANGE_MONEY", "Orange Money"
        MTN_MOMO = "MTN_MOMO", "MTN Mobile Money"

    categorie = models.CharField(max_length=20, choices=Categorie.choices)
    libelle = models.CharField(max_length=255)
    montant = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    mode_paiement = models.CharField(max_length=20, choices=Mode.choices, default=Mode.ESPECES)
    date_depense = models.DateTimeField(auto_now_add=True)
    piece_justificative = models.FileField(upload_to="justificatifs_depenses/%Y/%m/", blank=True, null=True)
    charge_fixe = models.ForeignKey(
        "ChargeFixe", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="depenses_generees",
        help_text="Renseigne automatiquement si cette depense provient d'une charge fixe.",
    )
    verrouille = models.BooleanField(
        default=True,
        help_text="True des la creation : seul un administrateur peut modifier ou supprimer cette depense.",
    )
    enregistre_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="depenses_enregistrees",
    )

    class Meta:
        ordering = ["-date_depense"]
        verbose_name = "Depense"
        verbose_name_plural = "Depenses"

    def __str__(self):
        return f"{self.get_categorie_display()} - {self.montant} FCFA ({self.libelle})"


class ChargeFixe(models.Model):
    """
    Charge recurrente et previsible de l'entreprise (loyer, abonnement
    Starlink, etc.). L'administrateur la parametre une seule fois ; chaque
    mois, generer_depense_du_mois() cree (si elle n'existe pas deja) la
    Depense correspondante, plutot que de la ressaisir manuellement.
    Entierement reservee a l'administrateur (permission EstAdminSeulement).
    """

    libelle = models.CharField(max_length=255, help_text="Ex : Loyer, Abonnement Starlink.")
    categorie = models.CharField(max_length=20, choices=Depense.Categorie.choices)
    montant = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    mode_paiement = models.CharField(max_length=20, choices=Depense.Mode.choices, default=Depense.Mode.ESPECES)
    jour_prelevement = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="Jour du mois auquel la depense doit etre generee (ex : 5 pour le 5 de chaque mois).",
    )
    actif = models.BooleanField(default=True)
    date_debut = models.DateField(default=timezone.now)
    date_fin = models.DateField(null=True, blank=True, help_text="Laisser vide si la charge est permanente.")
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="charges_fixes_creees",
    )

    class Meta:
        ordering = ["libelle"]
        verbose_name = "Charge fixe"
        verbose_name_plural = "Charges fixes"

    def __str__(self):
        return f"{self.libelle} - {self.montant} FCFA/mois"

    def generer_depense_du_mois(self, annee, mois, enregistre_par):
        """Cree la Depense du mois pour cette charge fixe, sauf si deja generee."""
        deja_generee = Depense.objects.filter(
            charge_fixe=self, date_depense__year=annee, date_depense__month=mois
        ).exists()
        if deja_generee or not self.actif:
            return None
        return Depense.objects.create(
            categorie=self.categorie,
            libelle=self.libelle,
            montant=self.montant,
            mode_paiement=self.mode_paiement,
            charge_fixe=self,
            enregistre_par=enregistre_par,
        )


class ClotureCaisse(models.Model):
    """
    Bilan de fin de journee. Calcule automatiquement, pour chaque canal
    (especes, Orange Money, MTN Mobile Money) : les encaissements de vente,
    les entrees hors vente et les depenses du jour, afin d'obtenir le solde
    theorique.

    Une fois le statut passe a CLOTUREE, l'enregistrement devient immuable
    pour tous les profils, y compris l'administrateur (voir clean()).
    """

    class Statut(models.TextChoices):
        OUVERTE = "OUVERTE", "En cours"
        CLOTUREE = "CLOTUREE", "Cloturee"

    date_jour = models.DateField(unique=True)
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.OUVERTE)

    especes_theorique = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    especes_reel = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    orange_money_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    mtn_momo_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_depenses = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    heure_cloture = models.DateTimeField(null=True, blank=True)
    cloturee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="clotures_effectuees",
    )
    observations = models.TextField(blank=True)

    class Meta:
        ordering = ["-date_jour"]
        verbose_name = "Cloture de caisse"
        verbose_name_plural = "Clotures de caisse"

    def clean(self):
        if self.pk:
            original = ClotureCaisse.objects.filter(pk=self.pk).first()
            if original and original.statut == self.Statut.CLOTUREE:
                raise ValidationError(
                    "Cette cloture est deja validee : elle ne peut plus etre modifiee, "
                    "y compris par un administrateur."
                )

    @property
    def ecart_especes(self):
        if self.especes_reel is None:
            return None
        return self.especes_reel - self.especes_theorique

    @property
    def solde_global_theorique(self):
        """Solde total, tous canaux confondus (especes + mobile money)."""
        return self.especes_theorique + self.orange_money_total + self.mtn_momo_total

    def calculer_totaux(self):
        """A appeler avant cloture : agrege Paiement, MouvementCaisse et Depense du jour."""
        paiements_jour = Paiement.objects.filter(date_paiement__date=self.date_jour)
        entrees_jour = MouvementCaisse.objects.filter(date_mouvement__date=self.date_jour)
        depenses_jour = Depense.objects.filter(date_depense__date=self.date_jour)

        def total_paiements(mode, sens=Paiement.Sens.ENTREE):
            return sum(
                (p.montant for p in paiements_jour.filter(mode=mode, sens=sens)), start=0
            )

        def total_entrees(mode):
            return sum((m.montant for m in entrees_jour.filter(mode=mode)), start=0)

        def total_depenses(mode):
            return sum((d.montant for d in depenses_jour.filter(mode_paiement=mode)), start=0)

        especes = (
            total_paiements(Paiement.Mode.CASH_IN)
            - total_paiements(Paiement.Mode.CASH_OUT)
            + total_entrees(MouvementCaisse.Mode.ESPECES)
            - total_depenses(Depense.Mode.ESPECES)
        )
        orange_money = (
            total_paiements(Paiement.Mode.ORANGE_MONEY)
            + total_entrees(MouvementCaisse.Mode.ORANGE_MONEY)
            - total_depenses(Depense.Mode.ORANGE_MONEY)
        )
        mtn_momo = (
            total_paiements(Paiement.Mode.MTN_MOMO)
            + total_entrees(MouvementCaisse.Mode.MTN_MOMO)
            - total_depenses(Depense.Mode.MTN_MOMO)
        )

        self.especes_theorique = especes
        self.orange_money_total = orange_money
        self.mtn_momo_total = mtn_momo
        self.total_depenses = sum((d.montant for d in depenses_jour), start=0)

    def __str__(self):
        return f"Cloture du {self.date_jour} ({self.get_statut_display()})"


class RecapPeriode(models.Model):
    """
    Recapitulatif agrege de caisse sur une periode (semaine ou mois),
    calcule a partir des ClotureCaisse et Depense de la periode.
    """

    class TypePeriode(models.TextChoices):
        SEMAINE = "SEMAINE", "Hebdomadaire"
        MOIS = "MOIS", "Mensuel"

    type_periode = models.CharField(max_length=10, choices=TypePeriode.choices)
    date_debut = models.DateField()
    date_fin = models.DateField()

    total_especes = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_orange_money = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_mtn_momo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_depenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    genere_le = models.DateTimeField(auto_now_add=True)
    genere_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="recaps_generes",
    )

    class Meta:
        ordering = ["-date_debut"]
        verbose_name = "Recapitulatif de periode"
        verbose_name_plural = "Recapitulatifs de periode"
        constraints = [
            models.UniqueConstraint(
                fields=["type_periode", "date_debut", "date_fin"], name="recap_periode_unique"
            )
        ]

    @property
    def total_general(self):
        return self.total_especes + self.total_orange_money + self.total_mtn_momo

    @property
    def solde_net(self):
        """Total encaisse sur la periode, depenses deduites."""
        return self.total_general - self.total_depenses

    def calculer_totaux(self):
        """Agrege les ClotureCaisse deja validees sur [date_debut, date_fin]."""
        clotures = ClotureCaisse.objects.filter(
            date_jour__range=(self.date_debut, self.date_fin),
            statut=ClotureCaisse.Statut.CLOTUREE,
        )
        self.total_especes = sum((c.especes_reel or c.especes_theorique for c in clotures), start=0)
        self.total_orange_money = sum((c.orange_money_total for c in clotures), start=0)
        self.total_mtn_momo = sum((c.mtn_momo_total for c in clotures), start=0)
        self.total_depenses = sum((c.total_depenses for c in clotures), start=0)

    def __str__(self):
        return f"Recap {self.get_type_periode_display()} du {self.date_debut} au {self.date_fin}"
