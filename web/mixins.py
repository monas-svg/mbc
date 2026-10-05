"""
Mixins de controle d'acces pour les vues basees sur des classes de
l'interface web. Reproduisent, pour les pages HTML, la meme logique de
droits que gestion/permissions.py applique cote API :

- ADMIN : acces complet.
- AGENT : peut consulter et creer (ventes, mouvements de caisse, depenses,
  clotures) mais ne peut ni modifier ni supprimer un enregistrement deja
  verrouille, et n'a pas acces au catalogue (camps/formations), aux
  charges fixes ni a la gestion des comptes.
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Reserve la vue aux comptes administrateur."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.est_admin

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("Cette action est reservee a un administrateur.")


class AgentOuAdminRequiredMixin(LoginRequiredMixin):
    """Ouvert a tout utilisateur authentifie (admin ou agent)."""
    pass


class ObjetVerrouilleMixin:
    """
    A utiliser sur les vues de modification/suppression d'un objet
    verrouillable (Facture, MouvementCaisse, Depense...) : bloque l'action
    si l'objet est verrouille et que l'utilisateur n'est pas administrateur.
    """

    champ_verrou = "verrouille"

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        return response

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if getattr(obj, self.champ_verrou, False) and not self.request.user.est_admin:
            raise PermissionDenied("Cet enregistrement est verrouille : seul un administrateur peut le modifier.")
        return obj
