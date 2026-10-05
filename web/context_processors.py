"""
Variables globales injectees dans tous les templates de l'interface web.
"""
from django.conf import settings


def mbcode_context(request):
    return {
        "nom_entreprise": getattr(settings, "NOM_ENTREPRISE", "MBCODE"),
        "devise": getattr(settings, "DEVISE", "FCFA"),
    }
