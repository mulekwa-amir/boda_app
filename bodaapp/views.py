"""Admin pages, dashboards, billing and authentication.

Customer-only pages live in customer_views.py and rider-only pages in rider_views.py.
Every admin page passes plain querysets to its own template under templates/staff/.
"""
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, Sum
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import customer_views, rider_views
from .access import get_role, role_required
from .forms import (
    BodaForm, BodaTypeForm, CustomerForm, CustomerRatingForm, LoginForm,
    RiderForm, RiderRatingForm, SignUpForm, TripForm,
)
from .models import Boda, BodaType, Customer, CustomerRating, Profile, Rider, RiderRating, Trip


# --------------------------------------------------------------------------- #
# Helpers shared by the admin pages
# --------------------------------------------------------------------------- #
def process_form(request, form_class, instance, url_name, noun):
    """Validate and save on POST. Returns (form, redirect_response_or_None)."""
    if request.method != "POST":
        return form_class(instance=instance), None
    form = form_class(request.POST, instance=instance)
    if form.is_valid():
        obj = form.save()
        action = "updated" if instance else "added"
        messages.success(request, f"{noun.capitalize()} “{obj}” {action} successfully.")
        return form, redirect(url_name)
    messages.error(request, "Please fix the highlighted errors and try again.")
    return form, None


def delete_object(request, model, pk, url_name, noun):
    obj = get_object_or_404(model, pk=pk)
    label = str(obj)
    try:
        obj.delete()
    except ProtectedError as error:
        messages.error(
            request,
            f"Cannot delete {noun} “{label}” — it is still used by "
            f"{len(error.protected_objects)} other record(s). Remove or reassign those first.",
        )
    else:
        messages.success(request, f"{noun.capitalize()} “{label}” deleted.")
    return redirect(url_name)


# --------------------------------------------------------------------------- #
# Dashboard: one URL, a different page for each role
# --------------------------------------------------------------------------- #
@login_required
def index_view(request):
    role = get_role(request.user)
    if role == "admin":
        return admin_dashboard(request)
    if role == "customer":
        return customer_views.dashboard(request)
    if role == "rider":
        return rider_views.dashboard(request)
    return render(request, "no_role.html")


def admin_dashboard(request):
    revenue = Trip.objects.filter(status="completed").aggregate(total=Sum("fare"))["total"] or 0
    return render(request, "staff/dashboard.html", {
        "stats": {
            "customers": Customer.objects.count(),
            "riders": Rider.objects.count(),
            "bodas": Boda.objects.count(),
            "trips": Trip.objects.count(),
            "revenue": f"{revenue:,.0f}",
            "avg_rating": RiderRating.objects.aggregate(a=Avg("score"))["a"],
        },
    })


@login_required
def home_view(request):
    return redirect("index")


@login_required
def rating_view(request):
    return redirect("riderrating")


# --------------------------------------------------------------------------- #
# Admin: customers
# --------------------------------------------------------------------------- #
@role_required("admin")
def customer_view(request, pk=None):
    editing = get_object_or_404(Customer, pk=pk) if pk else None
    form, done = process_form(request, CustomerForm, editing, "customer", "customer")
    if done:
        return done
    return render(request, "staff/customer.html", {
        "form": form, "editing": editing, "customers": Customer.objects.order_by("-pk"),
    })


@role_required("admin")
@require_POST
def customer_delete(request, pk):
    return delete_object(request, Customer, pk, "customer", "customer")


# --------------------------------------------------------------------------- #
# Admin: riders
# --------------------------------------------------------------------------- #
@role_required("admin")
def rider_view(request, pk=None):
    editing = get_object_or_404(Rider, pk=pk) if pk else None
    form, done = process_form(request, RiderForm, editing, "rider", "rider")
    if done:
        return done
    return render(request, "staff/rider.html", {
        "form": form, "editing": editing, "riders": Rider.objects.order_by("-pk"),
    })


@role_required("admin")
@require_POST
def rider_delete(request, pk):
    return delete_object(request, Rider, pk, "rider", "rider")


# --------------------------------------------------------------------------- #
# Admin: boda types
# --------------------------------------------------------------------------- #
@role_required("admin")
def bodatype_view(request, pk=None):
    editing = get_object_or_404(BodaType, pk=pk) if pk else None
    form, done = process_form(request, BodaTypeForm, editing, "bodatype", "boda type")
    if done:
        return done
    return render(request, "staff/bodatype.html", {
        "form": form, "editing": editing, "boda_types": BodaType.objects.order_by("type_name"),
    })


@role_required("admin")
@require_POST
def bodatype_delete(request, pk):
    return delete_object(request, BodaType, pk, "bodatype", "boda type")


# --------------------------------------------------------------------------- #
# Admin: bodas
# --------------------------------------------------------------------------- #
@role_required("admin")
def boda_view(request, pk=None):
    editing = get_object_or_404(Boda, pk=pk) if pk else None
    form, done = process_form(request, BodaForm, editing, "boda", "boda")
    if done:
        return done
    return render(request, "staff/boda.html", {
        "form": form, "editing": editing,
        "bodas": Boda.objects.select_related("boda_type", "rider").order_by("-pk"),
    })


@role_required("admin")
@require_POST
def boda_delete(request, pk):
    return delete_object(request, Boda, pk, "boda", "boda")


# --------------------------------------------------------------------------- #
# Admin: trips
# --------------------------------------------------------------------------- #
@role_required("admin")
def trip_view(request, pk=None):
    editing = get_object_or_404(Trip, pk=pk) if pk else None
    form, done = process_form(request, TripForm, editing, "trip", "trip")
    if done:
        return done
    return render(request, "staff/trip.html", {
        "form": form, "editing": editing,
        "trips": Trip.objects.select_related("customer", "rider", "boda").order_by("-pk"),
    })


@role_required("admin")
@require_POST
def trip_delete(request, pk):
    return delete_object(request, Trip, pk, "trip", "trip")


# --------------------------------------------------------------------------- #
# Admin: rider ratings (customer rates rider) and customer ratings (rider rates customer)
# --------------------------------------------------------------------------- #
@role_required("admin")
def riderrating_view(request, pk=None):
    editing = get_object_or_404(RiderRating, pk=pk) if pk else None
    form, done = process_form(request, RiderRatingForm, editing, "riderrating", "rider rating")
    if done:
        return done
    return render(request, "staff/riderrating.html", {
        "form": form, "editing": editing,
        "ratings": RiderRating.objects.select_related("rider", "rated_by").order_by("-pk"),
    })


@role_required("admin")
@require_POST
def riderrating_delete(request, pk):
    return delete_object(request, RiderRating, pk, "riderrating", "rider rating")


@role_required("admin")
def customerrating_view(request, pk=None):
    editing = get_object_or_404(CustomerRating, pk=pk) if pk else None
    form, done = process_form(request, CustomerRatingForm, editing, "customerrating", "customer rating")
    if done:
        return done
    return render(request, "staff/customerrating.html", {
        "form": form, "editing": editing,
        "ratings": CustomerRating.objects.select_related("customer", "rated_by").order_by("-pk"),
    })


@role_required("admin")
@require_POST
def customerrating_delete(request, pk):
    return delete_object(request, CustomerRating, pk, "customerrating", "customer rating")


# --------------------------------------------------------------------------- #
# Admin: billing
# --------------------------------------------------------------------------- #
@role_required("admin")
def fare_view(request):
    trips = Trip.objects.select_related("customer", "rider", "boda").order_by("-start_time")
    totals = {row["status"]: row for row in trips.values("status").annotate(n=Count("pk"), total=Sum("fare"))}
    completed = totals.get("completed", {"n": 0, "total": 0})
    outstanding = sum((totals.get(s, {}).get("total") or 0) for s in ("pending", "ongoing"))
    return render(request, "staff/fare.html", {
        "trips": trips,
        "collected": completed["total"] or 0,
        "completed_count": completed["n"],
        "outstanding": outstanding,
    })


# --------------------------------------------------------------------------- #
# Authentication
# --------------------------------------------------------------------------- #
def safe_next(request):
    target = request.POST.get("next") or request.GET.get("next") or ""
    allowed = url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure())
    return target if allowed else ""


def login_view(request):
    if request.user.is_authenticated:
        return redirect("index")
    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(safe_next(request) or "index")
    return render(request, "login.html", {"form": form, "next": safe_next(request)})


def signup_view(request):
    """Step 1: choose whether you are signing up as a customer or a rider."""
    if request.user.is_authenticated:
        return redirect("index")
    return render(request, "signup.html")


def signup_form_view(request, role):
    """Step 2: account details plus the customer's or rider's own details, saved together."""
    if request.user.is_authenticated:
        return redirect("index")
    if role not in ("customer", "rider"):
        raise Http404
    record_form_class = CustomerForm if role == "customer" else RiderForm
    account_form = SignUpForm(request.POST or None)
    record_form = record_form_class(request.POST or None)
    if request.method == "POST":
        account_ok, record_ok = account_form.is_valid(), record_form.is_valid()  # validate both to show all errors
        if account_ok and record_ok:
            with transaction.atomic():
                record = record_form.save()
                user = account_form.save()
                Profile.objects.create(user=user, role=role, **{role: record})
            login(request, user)
            messages.success(request, f"Welcome, {user.get_username()}! Your {role} account has been created.")
            return redirect("index")
    return render(request, "signup_form.html", {
        "role": role, "account_form": account_form, "record_form": record_form,
    })


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("login")
