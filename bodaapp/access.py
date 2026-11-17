"""Role detection and access control.

Roles
-----
admin     any user with is_staff / is_superuser (full access to every record)
customer  a user whose Profile is linked to a Customer record
rider     a user whose Profile is linked to a Rider record
None      logged in but not linked to anything yet (sees only a "contact an admin" page)
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect


def get_role(user):
    if not user.is_authenticated:
        return None
    if user.is_staff or user.is_superuser:
        return "admin"
    profile = getattr(user, "profile", None)
    if profile is None:
        return None
    if profile.role == "customer" and profile.customer_id:
        return "customer"
    if profile.role == "rider" and profile.rider_id:
        return "rider"
    return None


def role_required(*roles):
    """Only let users with one of the given roles in; send everyone else somewhere sensible."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if get_role(request.user) not in roles:
                messages.error(request, "You don't have access to that page.")
                return redirect("index")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
