import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    Boda,
    BodaType,
    Customer,
    CustomerRating,
    Rider,
    RiderRating,
    Trip,
)

PHONE_RE = re.compile(r"^\+?\d{7,14}$")

GENDER_CHOICES = [("", "Select gender…"), ("Male", "Male"), ("Female", "Female")]
STATUS_CHOICES = [
    ("pending", "pending"),
    ("ongoing", "ongoing"),
    ("completed", "completed"),
    ("cancelled", "cancelled"),
]
SCORE_CHOICES = [
    ("", "Select score…"),
    (5, "5 — Excellent"),
    (4, "4 — Good"),
    (3, "3 — Average"),
    (2, "2 — Poor"),
    (1, "1 — Very poor"),
]
DATETIME_FORMAT = "%Y-%m-%dT%H:%M"


class StyledFormMixin:
    """Gives every field a visible Bootstrap/Material border and consistent classes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                continue
            base = "form-select" if isinstance(widget, forms.Select) else "form-control"
            widget.attrs["class"] = f"{base} border px-2"


def _clean_phone(value):
    value = re.sub(r"[\s\-()]", "", value or "")
    if not PHONE_RE.match(value):
        raise ValidationError("Enter a valid phone number (7–14 digits, optional leading +).")
    return value


# --------------------------------------------------------------------------- #
# Core records
# --------------------------------------------------------------------------- #
class CustomerForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["first_name", "last_name", "contact", "email", "home_location"]
        labels = {"contact": "Contact (phone)", "home_location": "Home location"}
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "e.g. John"}),
            "last_name": forms.TextInput(attrs={"placeholder": "e.g. Mukasa"}),
            "contact": forms.TextInput(attrs={"placeholder": "0700111222", "type": "tel"}),
            "email": forms.EmailInput(attrs={"placeholder": "john.mukasa@email.com"}),
            "home_location": forms.TextInput(attrs={"placeholder": "e.g. Kampala"}),
        }

    def clean_contact(self):
        return _clean_phone(self.cleaned_data["contact"])

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class RiderForm(StyledFormMixin, forms.ModelForm):
    gender = forms.ChoiceField(choices=GENDER_CHOICES)

    class Meta:
        model = Rider
        fields = [
            "first_name",
            "last_name",
            "contact",
            "license",
            "experience_years",
            "age",
            "gender",
            "home_location",
        ]
        labels = {
            "contact": "Contact (phone)",
            "license": "Licence number",
            "experience_years": "Experience (years)",
            "home_location": "Home location",
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "e.g. James"}),
            "last_name": forms.TextInput(attrs={"placeholder": "e.g. Kato"}),
            "contact": forms.TextInput(attrs={"placeholder": "0700333444", "type": "tel"}),
            "license": forms.TextInput(attrs={"placeholder": "e.g. DL-1001"}),
            "experience_years": forms.NumberInput(attrs={"min": 0, "placeholder": "e.g. 5"}),
            "age": forms.NumberInput(attrs={"min": 18, "max": 80, "placeholder": "e.g. 28"}),
            "home_location": forms.TextInput(attrs={"placeholder": "e.g. Kampala"}),
        }

    def clean_contact(self):
        return _clean_phone(self.cleaned_data["contact"])

    def clean_license(self):
        return self.cleaned_data["license"].strip().upper()

    def clean_age(self):
        age = self.cleaned_data["age"]
        if age < 18 or age > 80:
            raise ValidationError("Age must be between 18 and 80.")
        return age

    def clean_experience_years(self):
        years = self.cleaned_data["experience_years"]
        if years < 0:
            raise ValidationError("Experience cannot be negative.")
        return years

    def clean(self):
        cleaned = super().clean()
        age, years = cleaned.get("age"), cleaned.get("experience_years")
        if age is not None and years is not None and years >= age:
            self.add_error("experience_years", "Experience must be less than the rider's age.")
        return cleaned


class BodaTypeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = BodaType
        fields = ["type_name"]
        labels = {"type_name": "Type name"}
        widgets = {"type_name": forms.TextInput(attrs={"placeholder": "e.g. Standard"})}

    def clean_type_name(self):
        return self.cleaned_data["type_name"].strip()


class BodaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Boda
        fields = ["boda_type", "model", "plate_number", "rider"]
        labels = {"boda_type": "Boda type", "plate_number": "Plate number", "rider": "Assigned rider"}
        widgets = {
            "model": forms.TextInput(attrs={"placeholder": "e.g. Bajaj Boxer"}),
            "plate_number": forms.TextInput(attrs={"placeholder": "e.g. UAB123A"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["boda_type"].empty_label = "Select type…"
        self.fields["rider"].empty_label = "Select rider…"

    def clean_plate_number(self):
        return re.sub(r"\s+", "", self.cleaned_data["plate_number"]).upper()


class TripForm(StyledFormMixin, forms.ModelForm):
    status = forms.ChoiceField(choices=STATUS_CHOICES, initial="pending")

    class Meta:
        model = Trip
        fields = [
            "customer",
            "rider",
            "boda",
            "pickup_location",
            "dropoff_location",
            "start_time",
            "end_time",
            "status",
            "fare",
            "distance_km",
        ]
        labels = {
            "pickup_location": "Pickup location",
            "dropoff_location": "Dropoff location",
            "start_time": "Start time",
            "end_time": "End time",
            "fare": "Fare (UGX)",
            "distance_km": "Distance (km)",
        }
        widgets = {
            "pickup_location": forms.TextInput(attrs={"placeholder": "e.g. Kampala Road"}),
            "dropoff_location": forms.TextInput(attrs={"placeholder": "e.g. Ntinda"}),
            "start_time": forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DATETIME_FORMAT),
            "end_time": forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DATETIME_FORMAT),
            "fare": forms.NumberInput(attrs={"min": 1, "step": 100, "placeholder": "e.g. 8000"}),
            "distance_km": forms.NumberInput(attrs={"min": 0.1, "step": "0.1", "placeholder": "e.g. 6.4"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].empty_label = "Select customer…"
        self.fields["rider"].empty_label = "Select rider…"
        self.fields["boda"].empty_label = "Select boda…"
        for name in ("start_time", "end_time"):
            self.fields[name].input_formats = [
                DATETIME_FORMAT,
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d %H:%M:%S",
            ]
        self.fields["end_time"].help_text = "Leave blank while the trip is pending or ongoing."

    def clean_fare(self):
        fare = self.cleaned_data["fare"]
        if fare <= 0:
            raise ValidationError("Fare must be greater than zero.")
        return fare

    def clean_distance_km(self):
        distance = self.cleaned_data["distance_km"]
        if distance <= 0:
            raise ValidationError("Distance must be greater than zero.")
        return distance

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_time"), cleaned.get("end_time")
        status = cleaned.get("status")
        rider, boda = cleaned.get("rider"), cleaned.get("boda")

        if start and end and end <= start:
            self.add_error("end_time", "End time must be after the start time.")
        if status == "completed" and not end:
            self.add_error("end_time", "A completed trip needs an end time.")
        if rider and boda and boda.rider_id != rider.pk:
            self.add_error("boda", f"{boda.plate_number} is assigned to {boda.rider}, not {rider}.")
        return cleaned


# --------------------------------------------------------------------------- #
# Ratings
# --------------------------------------------------------------------------- #
class _RatingFormBase(StyledFormMixin, forms.ModelForm):
    score = forms.TypedChoiceField(choices=SCORE_CHOICES, coerce=int, empty_value=None)

    def clean_score(self):
        score = self.cleaned_data["score"]
        if score is None or not 1 <= score <= 5:
            raise ValidationError("Score must be between 1 and 5.")
        return score

    def _check_completed(self, trip):
        if trip and trip.status != "completed":
            self.add_error("trip", "Ratings can only be left for completed trips.")


class RiderRatingForm(_RatingFormBase):
    class Meta:
        model = RiderRating
        fields = ["trip", "rider", "rated_by", "score", "comment"]
        labels = {"rider": "Rider being rated", "rated_by": "Rated by (customer)"}
        widgets = {"comment": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional comment about the rider"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["trip"].empty_label = "Select trip…"
        self.fields["rider"].empty_label = "Select rider…"
        self.fields["rated_by"].empty_label = "Select customer…"
        self.fields["trip"].help_text = "Only one rider rating allowed per trip."

    def clean(self):
        cleaned = super().clean()
        trip, rider, customer = cleaned.get("trip"), cleaned.get("rider"), cleaned.get("rated_by")
        self._check_completed(trip)
        if trip and rider and trip.rider_id != rider.pk:
            self.add_error("rider", f"Trip #{trip.pk} was ridden by {trip.rider}.")
        if trip and customer and trip.customer_id != customer.pk:
            self.add_error("rated_by", f"Trip #{trip.pk} was booked by {trip.customer}.")
        return cleaned


class CustomerRatingForm(_RatingFormBase):
    class Meta:
        model = CustomerRating
        fields = ["trip", "customer", "rated_by", "score", "comment"]
        labels = {"customer": "Customer being rated", "rated_by": "Rated by (rider)"}
        widgets = {"comment": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional comment about the customer"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["trip"].empty_label = "Select trip…"
        self.fields["customer"].empty_label = "Select customer…"
        self.fields["rated_by"].empty_label = "Select rider…"
        self.fields["trip"].help_text = "Only one customer rating allowed per trip."

    def clean(self):
        cleaned = super().clean()
        trip, customer, rider = cleaned.get("trip"), cleaned.get("customer"), cleaned.get("rated_by")
        self._check_completed(trip)
        if trip and customer and trip.customer_id != customer.pk:
            self.add_error("customer", f"Trip #{trip.pk} was booked by {trip.customer}.")
        if trip and rider and trip.rider_id != rider.pk:
            self.add_error("rated_by", f"Trip #{trip.pk} was ridden by {trip.rider}.")
        return cleaned


# --------------------------------------------------------------------------- #
# Authentication
# --------------------------------------------------------------------------- #
class LoginForm(StyledFormMixin, AuthenticationForm):
    pass


class SignUpForm(StyledFormMixin, UserCreationForm):
    pass


# --------------------------------------------------------------------------- #
# Customer / rider area forms (the logged-in person is filled in automatically)
# --------------------------------------------------------------------------- #
class BookTripForm(StyledFormMixin, forms.ModelForm):
    """A customer requests a trip. Rider, start time and status are set for them."""

    class Meta:
        model = Trip
        fields = ["boda", "pickup_location", "dropoff_location", "distance_km", "fare"]
        labels = {
            "boda": "Boda",
            "pickup_location": "Pickup location",
            "dropoff_location": "Dropoff location",
            "distance_km": "Distance (km)",
            "fare": "Agreed fare (UGX)",
        }
        widgets = {
            "pickup_location": forms.TextInput(attrs={"placeholder": "e.g. Kampala Road"}),
            "dropoff_location": forms.TextInput(attrs={"placeholder": "e.g. Ntinda"}),
            "distance_km": forms.NumberInput(attrs={"min": 0.1, "step": "0.1", "placeholder": "e.g. 6.4"}),
            "fare": forms.NumberInput(attrs={"min": 1, "step": 100, "placeholder": "e.g. 8000"}),
        }

    def __init__(self, *args, customer, **kwargs):
        super().__init__(*args, **kwargs)
        self.customer = customer
        boda = self.fields["boda"]
        boda.queryset = Boda.objects.select_related("rider", "boda_type").order_by("plate_number")
        boda.empty_label = "Choose a boda…"
        boda.label_from_instance = lambda b: f"{b.plate_number} — {b.model} ({b.boda_type.type_name}), rider {b.rider}"

    def clean_fare(self):
        fare = self.cleaned_data["fare"]
        if fare <= 0:
            raise ValidationError("Fare must be greater than zero.")
        return fare

    def clean_distance_km(self):
        distance = self.cleaned_data["distance_km"]
        if distance <= 0:
            raise ValidationError("Distance must be greater than zero.")
        return distance

    def save(self, commit=True):
        trip = super().save(commit=False)
        trip.customer = self.customer
        trip.rider = trip.boda.rider
        trip.start_time = timezone.now()
        trip.status = "pending"
        if commit:
            trip.save()
        return trip


class RateRiderForm(StyledFormMixin, forms.ModelForm):
    """A customer rates the rider of one of their completed, not-yet-rated trips."""

    score = forms.TypedChoiceField(choices=SCORE_CHOICES, coerce=int, empty_value=None)

    class Meta:
        model = RiderRating
        fields = ["trip", "score", "comment"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional comment about the rider"})}

    def __init__(self, *args, customer, **kwargs):
        super().__init__(*args, **kwargs)
        self.customer = customer
        trips = Trip.objects.filter(customer=customer, status="completed", riderrating__isnull=True)
        trip = self.fields["trip"]
        trip.queryset = trips.select_related("rider").order_by("-start_time")
        trip.empty_label = "Choose a completed trip…"
        trip.label_from_instance = lambda t: f"Trip #{t.pk}: {t.pickup_location} → {t.dropoff_location} (rider {t.rider})"
        if not trips.exists():
            trip.help_text = "You have no completed trips waiting to be rated."

    def clean_score(self):
        score = self.cleaned_data["score"]
        if score is None or not 1 <= score <= 5:
            raise ValidationError("Score must be between 1 and 5.")
        return score

    def save(self, commit=True):
        rating = super().save(commit=False)
        rating.rider = rating.trip.rider
        rating.rated_by = self.customer
        if commit:
            rating.save()
        return rating


class RateCustomerForm(StyledFormMixin, forms.ModelForm):
    """A rider rates the customer of one of their completed, not-yet-rated trips."""

    score = forms.TypedChoiceField(choices=SCORE_CHOICES, coerce=int, empty_value=None)

    class Meta:
        model = CustomerRating
        fields = ["trip", "score", "comment"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional comment about the customer"})}

    def __init__(self, *args, rider, **kwargs):
        super().__init__(*args, **kwargs)
        self.rider = rider
        trips = Trip.objects.filter(rider=rider, status="completed", customerrating__isnull=True)
        trip = self.fields["trip"]
        trip.queryset = trips.select_related("customer").order_by("-start_time")
        trip.empty_label = "Choose a completed trip…"
        trip.label_from_instance = lambda t: f"Trip #{t.pk}: {t.pickup_location} → {t.dropoff_location} (customer {t.customer})"
        if not trips.exists():
            trip.help_text = "You have no completed trips waiting to be rated."

    def clean_score(self):
        score = self.cleaned_data["score"]
        if score is None or not 1 <= score <= 5:
            raise ValidationError("Score must be between 1 and 5.")
        return score

    def save(self, commit=True):
        rating = super().save(commit=False)
        rating.customer = rating.trip.customer
        rating.rated_by = self.rider
        if commit:
            rating.save()
        return rating
