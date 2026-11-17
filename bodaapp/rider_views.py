"""Pages a logged-in rider can see. Everything is limited to that rider's own records."""
from datetime import timedelta

from django.contrib import messages
from django.db.models import Avg, Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .access import role_required
from .forms import RateCustomerForm
from .models import Boda, CustomerRating, RiderRating, Trip


def average_display(value):
    """Format an average score, or a dash when there are no ratings yet."""
    return f"{value:.1f}" if value is not None else "—"


def current_rider(request):
    return request.user.profile.rider


def own_trips(request):
    return Trip.objects.filter(rider=current_rider(request)).select_related("customer", "boda")


# Not decorated: reached through index_view, which has already checked the role.
def dashboard(request):
    me = current_rider(request)
    trips = own_trips(request)
    return render(request, "rider/dashboard.html", {
        "me": me,
        "trip_count": trips.count(),
        "open_count": trips.filter(status__in=["pending", "ongoing"]).count(),
        "earned": trips.filter(status="completed").aggregate(t=Sum("fare"))["t"] or 0,
        "avg_rating": average_display(RiderRating.objects.filter(rider=me).aggregate(a=Avg("score"))["a"]),
        "recent_trips": trips.order_by("-start_time")[:5],
    })


@role_required("rider")
def bodas(request):
    """The motorcycles assigned to you (read-only)."""
    mine = Boda.objects.filter(rider=current_rider(request)).select_related("boda_type").order_by("plate_number")
    return render(request, "rider/bodas.html", {"bodas": mine})


@role_required("rider")
def trips(request):
    """Your trips, with buttons to start, complete or cancel them."""
    return render(request, "rider/trips.html", {"trips": own_trips(request).order_by("-start_time")})


@role_required("rider")
@require_POST
def trip_action(request, pk, action):
    trip = get_object_or_404(Trip, pk=pk, rider=current_rider(request))
    if action == "start" and trip.status == "pending":
        trip.status = "ongoing"
        done = "started"
    elif action == "complete" and trip.status == "ongoing":
        trip.status = "completed"
        trip.end_time = max(timezone.now(), trip.start_time + timedelta(minutes=1))
        done = "completed"
    elif action == "cancel" and trip.status in ("pending", "ongoing"):
        trip.status = "cancelled"
        done = "cancelled"
    else:
        messages.error(request, f"Trip #{trip.pk} is {trip.status}, so that action isn't available.")
        return redirect("rid_trips")
    trip.save()
    messages.success(request, f"Trip #{trip.pk} {done}.")
    return redirect("rid_trips")


@role_required("rider")
def rate_customer(request):
    """Rate the customer of a completed trip, and see the ratings you have given."""
    me = current_rider(request)
    if request.method == "POST":
        form = RateCustomerForm(request.POST, rider=me)
        if form.is_valid():
            rating = form.save()
            messages.success(request, f"Thanks! You rated {rating.customer} {rating.score}/5.")
            return redirect("rid_rate_customer")
        messages.error(request, "Please fix the highlighted errors and try again.")
    else:
        form = RateCustomerForm(rider=me)
    given = CustomerRating.objects.filter(rated_by=me).select_related("customer").order_by("-pk")
    return render(request, "rider/rate_customer.html", {"form": form, "ratings": given})


@role_required("rider")
def ratings(request):
    """Ratings customers have given you (read-only)."""
    me = current_rider(request)
    received = RiderRating.objects.filter(rider=me).select_related("rated_by").order_by("-pk")
    return render(request, "rider/ratings.html", {
        "ratings": received,
        "avg_rating": average_display(received.aggregate(a=Avg("score"))["a"]),
    })


@role_required("rider")
def earnings(request):
    """What you have earned from completed trips."""
    trips_qs = own_trips(request).order_by("-start_time")
    by_status = {r["status"]: r for r in trips_qs.values("status").annotate(n=Count("pk"), total=Sum("fare"))}
    done = by_status.get("completed", {"n": 0, "total": 0})
    pending = sum((by_status.get(s, {}).get("total") or 0) for s in ("pending", "ongoing"))
    return render(request, "rider/earnings.html", {
        "trips": trips_qs, "earned": done["total"] or 0, "earned_count": done["n"], "pending": pending,
    })
