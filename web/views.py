"""
Vues de l'interface web - Application de gestion MBCODE.

Cette interface reproduit, page par page, la maquette fournie par le
client (tableau de bord, ventes & facturation, gestion des clients,
camps & formations, location d'espaces, depenses & tresorerie, rapports).
"""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum, Q, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from gestion import models
from gestion.permissions import verifier_facture_non_verrouillee, verifier_objet_non_verrouille

from . import charts, forms


# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------

class ConnexionView(LoginView):
    template_name = "web/connexion.html"
    authentication_form = forms.ConnexionForm
    redirect_authenticated_user = True


def deconnexion(request):
    auth_logout(request)
    messages.info(request, "Vous avez ete deconnecte.")
    return redirect("web:connexion")


def _admin_requis(request):
    if not request.user.est_admin:
        raise PermissionDenied("Cette action est reservee a un administrateur.")


# ---------------------------------------------------------------------------
# Tableau de bord
# ---------------------------------------------------------------------------

@login_required
def tableau_de_bord(request):
    aujourdhui = timezone.now().date()
    debut_mois = aujourdhui.replace(day=1)
    debut_mois_dernier = (debut_mois - timedelta(days=1)).replace(day=1)
    debut_semaine = aujourdhui - timedelta(days=aujourdhui.weekday())

    factures_mois = models.Facture.objects.filter(date_emission__date__gte=debut_mois)
    chiffre_affaires = sum((f.montant_paye for f in factures_mois), start=0)

    factures_mois_dernier = models.Facture.objects.filter(
        date_emission__date__gte=debut_mois_dernier, date_emission__date__lt=debut_mois
    )
    ca_mois_dernier = sum((f.montant_paye for f in factures_mois_dernier), start=0)
    variation_ca = round(((chiffre_affaires - ca_mois_dernier) / ca_mois_dernier) * 100, 1) if ca_mois_dernier else None

    eleves_actifs = models.InscriptionCamp.objects.filter(
        statut=models.InscriptionCamp.Statut.CONFIRMEE
    ).count() + models.InscriptionFormation.objects.filter(
        statut=models.InscriptionFormation.Statut.CONFIRMEE
    ).count()
    nouveaux_eleves_semaine = models.InscriptionCamp.objects.filter(
        date_inscription__date__gte=debut_semaine
    ).count() + models.InscriptionFormation.objects.filter(
        date_inscription__date__gte=debut_semaine
    ).count()

    espaces_total = models.Espace.objects.count()
    reservations_en_cours = models.Reservation.objects.filter(
        statut__in=[models.Reservation.Statut.CONFIRMEE, models.Reservation.Statut.EN_COURS]
    ).count()
    taux_occupation = round((reservations_en_cours / espaces_total) * 100) if espaces_total else 0

    factures_impayees = models.Facture.objects.exclude(statut=models.Facture.Statut.PAYEE)
    paiements_en_attente = sum((f.solde for f in factures_impayees if f.solde > 0), start=0)
    nb_factures_en_retard = factures_impayees.count()

    activites = []
    for f in models.Facture.objects.select_related("client").order_by("-date_emission")[:5]:
        activites.append({
            "titre": f"Vente {f.numero}",
            "detail": f"{f.client.nom} - {f.montant_total} {devise_ctx()}",
            "date": f.date_emission,
        })

    labels_mois, valeurs_mois = _revenus_six_derniers_mois(aujourdhui)
    graphique = charts.line_chart(valeurs_mois)

    contexte = {
        "chiffre_affaires": chiffre_affaires,
        "variation_ca": variation_ca,
        "eleves_actifs": eleves_actifs,
        "nouveaux_eleves_semaine": nouveaux_eleves_semaine,
        "taux_occupation": taux_occupation,
        "paiements_en_attente": paiements_en_attente,
        "nb_factures_en_retard": nb_factures_en_retard,
        "activites": activites,
        "graphique": graphique,
        "labels_mois": labels_mois,
        "titre_page": "Tableau de bord",
    }
    return render(request, "web/tableau_de_bord.html", contexte)


def devise_ctx():
    from django.conf import settings
    return getattr(settings, "DEVISE", "FCFA")


def _revenus_six_derniers_mois(aujourdhui):
    labels, valeurs = [], []
    for i in range(5, -1, -1):
        mois_ref = (aujourdhui.replace(day=1) - timedelta(days=30 * i))
        annee, mois = mois_ref.year, mois_ref.month
        total = sum(
            (f.montant_paye for f in models.Facture.objects.filter(
                date_emission__year=annee, date_emission__month=mois
            )), start=0
        )
        labels.append(mois_ref.strftime("%b"))
        valeurs.append(float(total))
    return labels, valeurs


# ---------------------------------------------------------------------------
# Ventes & facturation
# ---------------------------------------------------------------------------

@login_required
def ventes_liste(request):
    factures = models.Facture.objects.select_related("client").all()
    recherche = request.GET.get("q")
    if recherche:
        factures = factures.filter(Q(numero__icontains=recherche) | Q(client__nom__icontains=recherche))

    debut_mois = timezone.now().date().replace(day=1)
    revenus_mois = sum(
        (f.montant_paye for f in models.Facture.objects.filter(date_emission__date__gte=debut_mois)), start=0
    )
    impayees = models.Facture.objects.exclude(statut=models.Facture.Statut.PAYEE)
    montant_impaye = sum((f.solde for f in impayees if f.solde > 0), start=0)

    contexte = {
        "factures": factures[:100],
        "revenus_mois": revenus_mois,
        "montant_impaye": montant_impaye,
        "nb_impayees": impayees.count(),
        "titre_page": "Ventes & Facturation",
    }
    return render(request, "web/ventes_liste.html", contexte)


@login_required
def vente_creer(request):
    if request.method == "POST":
        form = forms.VenteForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                facture = models.Facture.objects.create(
                    client=form.cleaned_data["client"],
                    enregistree_par=request.user,
                    statut=models.Facture.Statut.EMISE,
                )
                ligne = models.LigneFacture.objects.create(
                    facture=facture,
                    type_service=form.cleaned_data["type_service"],
                    description=form.cleaned_data["description"],
                    quantite=form.cleaned_data["quantite"],
                    prix_unitaire=form.cleaned_data["prix_unitaire"],
                )
                paiement = models.Paiement(
                    facture=facture,
                    mode=form.cleaned_data["mode_paiement"],
                    sens=models.Paiement.Sens.ENTREE,
                    montant=ligne.montant_ligne,
                    reference_transaction=form.cleaned_data["reference_transaction"],
                    enregistre_par=request.user,
                )
                paiement.save()
                if facture.solde <= 0:
                    facture.statut = models.Facture.Statut.PAYEE
                    facture.save()
            messages.success(request, f"Facture {facture.numero} enregistree avec succes.")
            return redirect("web:facture_detail", pk=facture.pk)
    else:
        form = forms.VenteForm()
    return render(request, "web/formulaire_generique.html", {"form": form, "titre_page": "Nouvelle vente", "sous_titre": "Facture, ligne de prestation et premier paiement en une seule étape.", "retour_url": reverse_lazy("web:ventes_liste")})


@login_required
def facture_detail(request, pk):
    facture = get_object_or_404(models.Facture.objects.select_related("client"), pk=pk)
    return render(request, "web/facture_detail.html", {"facture": facture, "titre_page": f"Facture {facture.numero}"})


# ---------------------------------------------------------------------------
# Gestion des clients
# ---------------------------------------------------------------------------

@login_required
def clients_liste(request):
    clients = models.Client.objects.all()
    recherche = request.GET.get("q")
    if recherche:
        clients = clients.filter(Q(nom__icontains=recherche) | Q(telephone__icontains=recherche))
    return render(request, "web/clients_liste.html", {"clients": clients, "titre_page": "Gestion des clients"})


@login_required
def client_creer(request):
    if request.method == "POST":
        form = forms.ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            if client.type_client == models.Client.TypeClient.PARENT_ENFANT:
                messages.info(
                    request,
                    "Le client parent a bien été créé. Ajoutez maintenant au moins un enfant pour finaliser la fiche.",
                )
                return redirect("web:enfant_creer", client_pk=client.pk)
            messages.success(request, f"Client {client.nom} cree avec succes.")
            return redirect("web:clients_liste")
    else:
        form = forms.ClientForm()
    return render(request, "web/formulaire_generique.html", {"form": form, "titre_page": "Nouveau client", "retour_url": reverse_lazy("web:clients_liste")})


@login_required
def client_detail(request, pk):
    client = get_object_or_404(models.Client, pk=pk)
    return render(request, "web/client_detail.html", {"client": client, "titre_page": client.nom})


@login_required
def enfant_creer_rapide(request):
    parents = models.Client.objects.filter(type_client=models.Client.TypeClient.PARENT_ENFANT).order_by("nom")
    if not parents.exists():
        messages.warning(request, "Aucun client parent n'est encore disponible. Créez d'abord un client parent.")
        return redirect("web:client_creer")

    if request.method == "POST":
        form = forms.EnfantForm(request.POST)
        if form.is_valid():
            enfant = form.save()
            messages.success(request, f"Enfant {enfant.nom} ajoute avec succes.")
            return redirect("web:client_detail", pk=enfant.parent.pk)
    else:
        form = forms.EnfantForm()

    form.fields["parent"].queryset = parents
    return render(
        request,
        "web/formulaire_generique.html",
        {"form": form, "titre_page": "Ajouter un enfant", "retour_url": reverse_lazy("web:tableau_de_bord")},
    )


@login_required
def enfant_creer(request, client_pk):
    parent = get_object_or_404(models.Client, pk=client_pk)
    if parent.type_client != models.Client.TypeClient.PARENT_ENFANT:
        raise PermissionDenied("Un enfant ne peut être rattaché qu'à un client de type Parent-enfant.")

    if request.method == "POST":
        form = forms.EnfantForm(request.POST)
        if form.is_valid():
            enfant = form.save()
            messages.success(request, f"Enfant {enfant.nom} ajoute avec succes.")
            return redirect("web:client_detail", pk=parent.pk)
    else:
        form = forms.EnfantForm(initial={"parent": parent})

    form.fields["parent"].queryset = models.Client.objects.filter(
        type_client=models.Client.TypeClient.PARENT_ENFANT
    )

    return render(
        request,
        "web/formulaire_generique.html",
        {"form": form, "titre_page": "Ajouter un enfant", "retour_url": reverse_lazy("web:client_detail", kwargs={"pk": parent.pk})},
    )


# ---------------------------------------------------------------------------
# Camps & formations
# ---------------------------------------------------------------------------

@login_required
def camps_liste(request):
    camps = models.Camp.objects.all().prefetch_related("inscriptions")
    formations = models.FormationIA.objects.all().prefetch_related("inscriptions")
    total_capacite = sum((c.capacite for c in camps), start=0)
    total_inscrits = sum(
        (c.inscriptions.filter(statut=models.InscriptionCamp.Statut.CONFIRMEE).count() for c in camps), start=0
    )
    taux_global = round((total_inscrits / total_capacite) * 100) if total_capacite else 0
    contexte = {
        "camps": camps,
        "formations": formations,
        "formateurs": models.Formateur.objects.all(),
        "taux_global": taux_global,
        "titre_page": "Camps & Formations",
    }
    return render(request, "web/camps_liste.html", contexte)


@login_required
def camp_creer(request):
    _admin_requis(request)
    if request.method == "POST":
        form = forms.CampForm(request.POST, request.FILES)
        if form.is_valid():
            camp = form.save(commit=False)
            camp.cree_par = request.user
            camp.save()
            form.save_m2m()
            messages.success(request, f"Camp « {camp.titre} » cree avec succes.")
            return redirect("web:camps_liste")
    else:
        form = forms.CampForm()
    return render(request, "web/formulaire_generique.html", {"form": form, "titre_page": "Nouveau camp", "retour_url": reverse_lazy("web:camps_liste")})


@login_required
def formation_creer(request):
    _admin_requis(request)
    if request.method == "POST":
        form = forms.FormationForm(request.POST)
        if form.is_valid():
            formation = form.save(commit=False)
            formation.cree_par = request.user
            formation.save()
            form.save_m2m()
            messages.success(request, f"Formation « {formation.titre} » creee avec succes.")
            return redirect("web:camps_liste")
    else:
        form = forms.FormationForm()
    return render(request, "web/formulaire_generique.html", {"form": form, "titre_page": "Nouvelle formation", "retour_url": reverse_lazy("web:camps_liste")})


@login_required
def inscription_camp_creer(request):
    if request.method == "POST":
        form = forms.InscriptionCampForm(request.POST)
        if form.is_valid():
            inscription = form.save(commit=False)
            inscription.enregistree_par = request.user
            inscription.save()
            facture = inscription.generer_facture(enregistre_par=request.user)
            if facture is not None:
                messages.success(request, f"Inscription enregistree avec succes. Facture {facture.numero} generée pour le parent.")
            else:
                messages.success(request, "Inscription enregistree avec succes.")
            return redirect("web:camps_liste")
    else:
        form = forms.InscriptionCampForm()
    return render(request, "web/formulaire_generique.html", {"form": form, "titre_page": "Inscrire un enfant à un camp", "retour_url": reverse_lazy("web:camps_liste")})


# ---------------------------------------------------------------------------
# Location d'espaces
# ---------------------------------------------------------------------------

@login_required
def espaces_liste(request):
    espaces = models.Espace.objects.all()
    total = espaces.count()
    occupes = models.Reservation.objects.filter(
        statut__in=[models.Reservation.Statut.CONFIRMEE, models.Reservation.Statut.EN_COURS]
    ).values("espace").distinct().count()
    taux_occupation = round((occupes / total) * 100) if total else 0
    debut_mois = timezone.now().date().replace(day=1)
    revenus_locatifs = sum(
        (r.montant for r in models.Reservation.objects.filter(date_creation__date__gte=debut_mois)), start=0
    )
    reservations_recentes = models.Reservation.objects.select_related("client", "espace").order_by("-date_creation")[:10]
    contexte = {
        "espaces": espaces,
        "taux_occupation": taux_occupation,
        "espaces_disponibles": espaces.filter(disponible=True).count(),
        "revenus_locatifs": revenus_locatifs,
        "reservations_recentes": reservations_recentes,
        "titre_page": "Location d'espaces",
    }
    return render(request, "web/espaces_liste.html", contexte)


@login_required
def espace_creer(request):
    _admin_requis(request)
    if request.method == "POST":
        form = forms.EspaceForm(request.POST, request.FILES)
        if form.is_valid():
            espace = form.save()
            messages.success(request, f"Espace « {espace.nom} » cree avec succes.")
            return redirect("web:espaces_liste")
    else:
        form = forms.EspaceForm()
    return render(request, "web/formulaire_generique.html", {"form": form, "titre_page": "Nouvel espace", "retour_url": reverse_lazy("web:espaces_liste")})


@login_required
def reservation_creer(request):
    if request.method == "POST":
        form = forms.ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.enregistree_par = request.user
            reservation.save()
            messages.success(request, "Reservation enregistree avec succes.")
            return redirect("web:espaces_liste")
    else:
        form = forms.ReservationForm()
    return render(request, "web/formulaire_generique.html", {"form": form, "titre_page": "Nouvelle réservation", "retour_url": reverse_lazy("web:espaces_liste")})


# ---------------------------------------------------------------------------
# Depenses & tresorerie
# ---------------------------------------------------------------------------

@login_required
def depenses_liste(request):
    debut_mois = timezone.now().date().replace(day=1)
    depenses_mois = models.Depense.objects.filter(date_depense__date__gte=debut_mois)
    depenses_totales = sum((d.montant for d in depenses_mois), start=0)
    charges_fixes = models.ChargeFixe.objects.filter(actif=True)
    total_charges_fixes = sum((c.montant for c in charges_fixes), start=0)
    depenses_ponctuelles = depenses_totales - sum(
        (d.montant for d in depenses_mois.filter(charge_fixe__isnull=False)), start=0
    )

    repartition = (
        depenses_mois.values("categorie").annotate(total=Sum("montant")).order_by("-total")
    )

    contexte = {
        "depenses": depenses_mois.order_by("-date_depense")[:50],
        "depenses_totales": depenses_totales,
        "charges_fixes": charges_fixes,
        "total_charges_fixes": total_charges_fixes,
        "depenses_ponctuelles": depenses_ponctuelles,
        "repartition": repartition,
        "solde_caisse": _solde_caisse_disponible(),
        "titre_page": "Depenses & Tresorerie",
    }
    return render(request, "web/depenses_liste.html", contexte)


def _solde_caisse_disponible():
    total_entrees = sum(
        (p.montant for p in models.Paiement.objects.filter(sens=models.Paiement.Sens.ENTREE)), start=0
    )
    total_sorties = sum(
        (p.montant for p in models.Paiement.objects.filter(sens=models.Paiement.Sens.SORTIE)), start=0
    )
    total_mouvements = sum((m.montant for m in models.MouvementCaisse.objects.all()), start=0)
    total_depenses = sum((d.montant for d in models.Depense.objects.all()), start=0)
    return total_entrees - total_sorties + total_mouvements - total_depenses


@login_required
def depense_creer(request):
    if request.method == "POST":
        form = forms.DepenseForm(request.POST, request.FILES)
        if form.is_valid():
            depense = form.save(commit=False)
            depense.enregistre_par = request.user
            depense.verrouille = True
            depense.save()
            messages.success(request, "Depense enregistree avec succes.")
            return redirect("web:depenses_liste")
    else:
        form = forms.DepenseForm()
    return render(request, "web/formulaire_generique.html", {"form": form, "titre_page": "Enregistrer une dépense", "retour_url": reverse_lazy("web:depenses_liste")})


@login_required
def mouvement_creer(request):
    if request.method == "POST":
        form = forms.MouvementCaisseForm(request.POST)
        if form.is_valid():
            mouvement = form.save(commit=False)
            mouvement.enregistre_par = request.user
            mouvement.verrouille = True
            mouvement.save()
            messages.success(request, "Mouvement de caisse enregistre avec succes.")
            return redirect("web:depenses_liste")
    else:
        form = forms.MouvementCaisseForm()
    return render(request, "web/formulaire_generique.html", {"form": form, "titre_page": "Nouveau mouvement de caisse", "retour_url": reverse_lazy("web:depenses_liste")})


@login_required
def charges_fixes_liste(request):
    _admin_requis(request)
    charges = models.ChargeFixe.objects.all()
    return render(request, "web/charges_fixes_liste.html", {"charges": charges, "titre_page": "Charges fixes"})


@login_required
def charge_fixe_creer(request):
    _admin_requis(request)
    if request.method == "POST":
        form = forms.ChargeFixeForm(request.POST)
        if form.is_valid():
            charge = form.save(commit=False)
            charge.cree_par = request.user
            charge.save()
            messages.success(request, f"Charge fixe « {charge.libelle} » creee avec succes.")
            return redirect("web:charges_fixes_liste")
    else:
        form = forms.ChargeFixeForm()
    return render(request, "web/formulaire_generique.html", {"form": form, "titre_page": "Nouvelle charge fixe", "retour_url": reverse_lazy("web:charges_fixes_liste")})


@login_required
def cloture_jour(request):
    aujourdhui = timezone.now().date()
    cloture, _ = models.ClotureCaisse.objects.get_or_create(date_jour=aujourdhui)
    if cloture.statut == models.ClotureCaisse.Statut.OUVERTE:
        cloture.calculer_totaux()
        cloture.save()

    if request.method == "POST" and cloture.statut == models.ClotureCaisse.Statut.OUVERTE:
        form = forms.ClotureCaisseForm(request.POST, instance=cloture)
        if form.is_valid():
            cloture = form.save(commit=False)
            cloture.calculer_totaux()
            cloture.statut = models.ClotureCaisse.Statut.CLOTUREE
            cloture.heure_cloture = timezone.now()
            cloture.cloturee_par = request.user
            cloture.full_clean()
            cloture.save()
            messages.success(request, "Caisse cloturee avec succes pour aujourd'hui.")
            return redirect("web:depenses_liste")
    else:
        form = forms.ClotureCaisseForm(instance=cloture)
    return render(request, "web/cloture_form.html", {"form": form, "cloture": cloture, "titre_page": "Cloture de caisse"})


# ---------------------------------------------------------------------------
# Rapports
# ---------------------------------------------------------------------------

@login_required
def rapports(request):
    aujourdhui = timezone.now().date()
    debut_annee = aujourdhui.replace(month=1, day=1)

    factures_annee = models.Facture.objects.filter(date_emission__date__gte=debut_annee)
    revenu_annuel = sum((f.montant_paye for f in factures_annee), start=0)
    depenses_annee = models.Depense.objects.filter(date_depense__date__gte=debut_annee)
    total_depenses_annee = sum((d.montant for d in depenses_annee), start=0)
    marge_nette = round((revenu_annuel - total_depenses_annee) / revenu_annuel * 100, 1) if revenu_annuel else 0

    revenus_par_mois = []
    depenses_par_mois = []
    labels_mois = []
    for i in range(11, -1, -1):
        mois_reference = (aujourdhui.replace(day=1) - timedelta(days=30 * i))
        annee, mois = mois_reference.year, mois_reference.month
        revenus = sum(
            (f.montant_paye for f in models.Facture.objects.filter(
                date_emission__year=annee, date_emission__month=mois
            )), start=0
        )
        depenses = sum(
            (d.montant for d in models.Depense.objects.filter(
                date_depense__year=annee, date_depense__month=mois
            )), start=0
        )
        labels_mois.append(mois_reference.strftime("%b"))
        revenus_par_mois.append(float(revenus))
        depenses_par_mois.append(float(depenses))

    top_clients = (
        models.Client.objects.annotate(
            total_factures=Sum("factures__paiements__montant", filter=Q(factures__paiements__sens="ENTREE"))
        ).order_by("-total_factures")[:5]
    )

    programmes = []
    for camp in models.Camp.objects.all():
        inscrits = camp.inscriptions.filter(statut=models.InscriptionCamp.Statut.CONFIRMEE).count()
        programmes.append({
            "nom": camp.titre,
            "participants": inscrits,
            "revenus": inscrits * camp.montant_total_inscription,
        })
    for formation in models.FormationIA.objects.all():
        inscrits = formation.inscriptions.filter(statut=models.InscriptionFormation.Statut.CONFIRMEE).count()
        programmes.append({
            "nom": formation.titre,
            "participants": inscrits,
            "revenus": inscrits * formation.montant_total_inscription,
        })

    graphique = charts.dual_line_chart(revenus_par_mois, depenses_par_mois)

    segments = []
    for type_espace, libelle in models.Espace.TypeEspace.choices:
        total = sum(
            (r.montant for r in models.Reservation.objects.filter(
                espace__type_espace=type_espace, date_creation__date__gte=debut_annee
            )), start=0
        )
        if total:
            segments.append({"label": libelle, "value": float(total)})
    repartition_espaces = charts.donut_chart(segments) if segments else None

    espaces_total = models.Espace.objects.count()
    reservations_en_cours = models.Reservation.objects.filter(
        statut__in=[models.Reservation.Statut.CONFIRMEE, models.Reservation.Statut.EN_COURS]
    ).count()
    taux_occupation = round((reservations_en_cours / espaces_total) * 100) if espaces_total else 0

    contexte = {
        "revenu_annuel": revenu_annuel,
        "marge_nette": marge_nette,
        "total_depenses_annee": total_depenses_annee,
        "labels_mois": labels_mois,
        "revenus_par_mois": revenus_par_mois,
        "depenses_par_mois": depenses_par_mois,
        "graphique": graphique,
        "repartition_espaces": repartition_espaces,
        "taux_occupation": taux_occupation,
        "top_clients": top_clients,
        "programmes": programmes,
        "titre_page": "Rapports & Analyses",
    }
    return render(request, "web/rapports.html", contexte)
