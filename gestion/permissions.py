"""
Regles d'acces - Application de gestion MBCODE

ADMIN  : acces complet (creer, lire, modifier, supprimer tout objet,
         gerer les comptes agents, creer le catalogue de camps/formations).
AGENT  : peut creer une vente (Facture + LigneFacture + Paiement), un
         mouvement de caisse, une depense, et cloturer la caisse du jour ;
         peut aussi consulter les recapitulatifs hebdomadaires/mensuels.
         Il ne peut en revanche jamais modifier ni supprimer un
         enregistrement deja cree (vente, mouvement de caisse, depense),
         meme le sien : toute correction passe par un ADMIN. Il ne peut
         pas non plus creer un camp, une formation, ou un compte agent.

A utiliser comme `permission_classes` sur les ViewSets Django REST
Framework correspondants (voir docstring de chaque classe).
"""

from rest_framework import permissions


class EstAdminOuLectureSeuleApresCreation(permissions.BasePermission):
    """
    - Un ADMIN a tous les droits.
    - Un AGENT peut creer (POST) et lire (GET/HEAD/OPTIONS).
    - Un AGENT ne peut ni modifier (PUT/PATCH) ni supprimer (DELETE),
      meme son propre enregistrement.

    A utiliser sur les ViewSets Facture, LigneFacture, Paiement,
    MouvementCaisse, Depense et ClotureCaisse : dans les quatre premiers
    cas le verrou est porte par le champ `verrouillee`/`verrouille` du
    modele ; pour ClotureCaisse, l'immuabilite apres validation est en
    plus appliquee au niveau du modele (clean()), donc meme un ADMIN ne
    peut plus modifier une cloture deja passee au statut CLOTUREE.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.est_admin:
            return True
        # Un agent peut uniquement lister/consulter/creer
        return request.method in (*permissions.SAFE_METHODS, "POST")

    def has_object_permission(self, request, view, obj):
        if request.user.est_admin:
            return True
        # Objet deja enregistre : lecture seule pour un agent
        return request.method in permissions.SAFE_METHODS


class EstAdminSeulement(permissions.BasePermission):
    """
    Reservee a la gestion des comptes utilisateurs (UtilisateurViewSet :
    creation, modification, suppression des comptes admin et agents) et a
    la configuration des charges fixes (ChargeFixeViewSet : loyer,
    abonnement Starlink...). Contrairement a Depense, une ChargeFixe n'est
    pas une operation de caisse au jour le jour mais un parametrage
    financier structurel : entierement fermee aux agents, y compris en
    lecture.
    """

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.est_admin
        )


class EstAdminPourEcriture(permissions.BasePermission):
    """
    Consultable par tous les utilisateurs authentifies (admin ou agent),
    mais seul un administrateur peut creer, modifier ou supprimer :
    - le catalogue des camps et des formations (CampViewSet,
      FormationIAViewSet) - un agent ne peut pas ouvrir de nouvelle
      session lui-meme, seulement y inscrire un client/enfant ;
    - les recapitulatifs hebdomadaires/mensuels (RecapPeriodeViewSet) -
      un agent peut les consulter mais pas en declencher la generation.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.est_admin


class EstAuthentifie(permissions.BasePermission):
    """
    Permission generique pour les objets de reference partages (Client,
    Enfant, Formateur, Espace) : lecture et ecriture ouvertes a tout
    utilisateur authentifie (admin ou agent), la suppression restant
    reservee a l'administrateur afin de proteger l'integrite de
    l'historique commercial.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method == "DELETE":
            return request.user.est_admin
        return True


# ---------------------------------------------------------------------------
# Filet de securite cote modele (en complement des permissions ci-dessus,
# a appeler explicitement dans les serializers/vues avant tout update/delete)
# ---------------------------------------------------------------------------

def verifier_objet_non_verrouille(utilisateur, objet, champ_verrou="verrouille"):
    """
    Leve une exception si un utilisateur non-admin tente de modifier un
    objet deja verrouille. Fonctionne pour tout modele exposant un booleen
    de verrouillage : Facture (champ_verrou="verrouillee"), MouvementCaisse
    et Depense (champ_verrou="verrouille", valeur par defaut).

    A appeler dans les serializers ou dans perform_update()/perform_destroy()
    des ViewSets correspondants.
    """
    from django.core.exceptions import PermissionDenied

    if getattr(objet, champ_verrou, False) and not utilisateur.est_admin:
        raise PermissionDenied(
            "Cet enregistrement est deja verrouille. Seul un administrateur peut le modifier."
        )


def verifier_facture_non_verrouillee(utilisateur, facture):
    """Raccourci de verifier_objet_non_verrouille pour le modele Facture."""
    verifier_objet_non_verrouille(utilisateur, facture, champ_verrou="verrouillee")


def verifier_cloture_modifiable(cloture):
    """
    Leve une exception si la cloture visee est deja validee (statut
    CLOTUREE) : personne, pas meme un administrateur, ne peut alors la
    modifier - c'est une garantie deja appliquee par ClotureCaisse.clean(),
    mais ce controle explicite permet un message d'erreur adapte cote API
    avant meme la tentative de sauvegarde.
    """
    from django.core.exceptions import PermissionDenied

    if cloture.pk and cloture.statut == cloture.Statut.CLOTUREE:
        raise PermissionDenied(
            "Cette cloture est deja validee et ne peut plus etre modifiee."
        )
