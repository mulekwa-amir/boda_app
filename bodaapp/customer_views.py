"""Pages a logged-in customer can see. Everything is limited to that customer's own records."""
from django.contrib import messages
from django.db.models import Avg, Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .access import role_required
from .forms import BookTripForm, RateRiderForm
from .models import CustomerRating, RiderRating, Trip


def average_display(value):
    """Format an average score, or a dash when there are no ratings yet."""
    return f"{value:.1f}" if value is not None else "—"


def current_customer(request):
    return request.user.profile.customer


def own_trips(request):
    return Trip.objects.filter(customer=current_customer(request)).select_related("rider", "boda")


# Not decorated: reached through index_view, which has already checked the role.
def dashboard(request):
    me = current_customer(request)
    trips = own_trips(request)
    return render(request, "customer/dashboard.html", {
        "me": me,
        "trip_count": trips.count(),
        "open_count": trips.filter(status__in=["pending", "ongoing"]).count(),
        "spent": trips.filter(status="completed").aggregate(t=Sum("fare"))["t"] or 0,
        "avg_rating": average_display(CustomerRating.objects.filter(customer=me).aggregate(a=Avg("score"))["a"]),
        "recent_trips": trips.order_by("-start_time")[:5],
    })


@role_required("customer")
def trips(request):
    """Book a new trip and see every trip you have made."""
    me = current_customer(request)
    if request.method == "POST":
        form = BookTripForm(request.POST, customer=me)
        if form.is_valid():
            trip = form.save()
            messages.success(request, f"Trip #{trip.pk} booked with {trip.rider}. Waiting for the rider to start it.")
            return redirect("cust_trips")
        messages.error(request, "Please fix the highlighted errors and try again.")
    else:
        form = BookTripForm(customer=me)
    return render(request, "customer/trips.html", {"form": form, "trips": own_trips(request).order_by("-start_time")})


@role_required("customer")
@require_POST
def trip_cancel(request, pk):
    trip = get_object_or_404(Trip, pk=pk, customer=current_customer(request))
    if trip.status == "pending":
        trip.status = "cancelled"
        trip.save(update_fields=["status"])
        messages.success(request, f"Trip #{trip.pk} cancelled.")
    else:
        messages.error(request, "Only trips that haven't started yet can be cancelled.")
    return redirect("cust_trips")


@role_required("customer")
def rate_rider(request):
    """Rate the rider of a completed trip, and see the ratings you have given."""
    me = current_customer(request)
    if request.method == "POST":
        form = RateRiderForm(request.POST, customer=me)
        if form.is_valid():
            rating = form.save()
            messages.success(request, f"Thanks! You rated {rating.rider} {rating.score}/5.")
            return redirect("cust_rate_rider")
        messages.error(request, "Please fix the highlighted errors and try again.")
    else:
        form = RateRiderForm(customer=me)
    given = RiderRating.objects.filter(rated_by=me).select_related("rider").order_by("-pk")
    return render(request, "customer/rate_rider.html", {"form": form, "ratings": given})


@role_required("customer")
def ratings(request):
    """Ratings riders have given you (read-only)."""
    me = current_customer(request)
    received = CustomerRating.objects.filter(customer=me).select_related("rated_by").order_by("-pk")
    return render(request, "customer/ratings.html", {
        "ratings": received,
        "avg_rating": average_display(received.aggregate(a=Avg("score"))["a"]),
    })


@role_required("customer")
def billing(request):
    """What each of your trips cost."""
    trips_qs = own_trips(request).order_by("-start_time")
    by_status = {r["status"]: r for r in trips_qs.values("status").annotate(n=Count("pk"), total=Sum("fare"))}
    paid = by_status.get("completed", {"n": 0, "total": 0})
    due = sum((by_status.get(s, {}).get("total") or 0) for s in ("pending", "ongoing"))
    return render(request, "customer/billing.html", {
        "trips": trips_qs, "paid": paid["total"] or 0, "paid_count": paid["n"], "due": due,
    })
