from .access import get_role

ROLE_LABELS = {"admin": "Administrator", "customer": "Customer", "rider": "Rider"}


def navigation(request):
    """Gives every template `role`, `role_label` and `active` (the current page's url name)."""
    user = getattr(request, "user", None)
    role = get_role(user) if user is not None else None
    match = getattr(request, "resolver_match", None)
    name = match.url_name if match and match.url_name else ""
    if name.endswith("_edit"):
        name = name[: -len("_edit")]
    return {"role": role, "role_label": ROLE_LABELS.get(role, ""), "active": name}
