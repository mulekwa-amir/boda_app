from django.conf import settings
from django.db import models


class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    contact = models.CharField(max_length=15, unique=True)
    email = models.EmailField(max_length=100, unique=True)
    home_location = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Rider(models.Model):
    rider_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    contact = models.CharField(max_length=15, unique=True)
    license = models.CharField(max_length=30, unique=True)
    experience_years = models.IntegerField()
    age = models.IntegerField()
    gender = models.CharField(max_length=6)
    home_location = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class BodaType(models.Model):
    boda_type_id = models.AutoField(primary_key=True)
    type_name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.type_name


class Boda(models.Model):
    boda_id = models.AutoField(primary_key=True)
    boda_type = models.ForeignKey(BodaType, on_delete=models.PROTECT, db_column="boda_type_id")
    model = models.CharField(max_length=50)
    plate_number = models.CharField(max_length=20, unique=True)
    rider = models.ForeignKey(Rider, on_delete=models.PROTECT, db_column="rider_id")

    def __str__(self):
        return f"{self.plate_number} — {self.model}"


class Trip(models.Model):
    trip_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, db_column="customer_id")
    rider = models.ForeignKey(Rider, on_delete=models.PROTECT, db_column="rider_id")
    boda = models.ForeignKey(Boda, on_delete=models.PROTECT, db_column="boda_id")
    pickup_location = models.CharField(max_length=100)
    dropoff_location = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20)
    fare = models.DecimalField(max_digits=10, decimal_places=2)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"Trip #{self.trip_id}: {self.pickup_location} → {self.dropoff_location}"


class RiderRating(models.Model):

    rate_id = models.AutoField(primary_key=True)
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, db_column="trip_id")
    rider = models.ForeignKey(Rider, on_delete=models.PROTECT, db_column="rider_id")
    rated_by = models.ForeignKey(Customer, on_delete=models.PROTECT, db_column="rated_by")
    score = models.IntegerField()
    comment = models.TextField(null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trip #{self.trip_id} — {self.score}/5 for {self.rider}"


class CustomerRating(models.Model):

    rate_id = models.AutoField(primary_key=True)
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, db_column="trip_id")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, db_column="customer_id")
    rated_by = models.ForeignKey(Rider, on_delete=models.PROTECT, db_column="rated_by")
    score = models.IntegerField()
    comment = models.TextField(null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trip #{self.trip_id} — {self.score}/5 for {self.customer}"


class Profile(models.Model):
    """Links a login account to the customer or rider record it belongs to.

    Staff / superusers are administrators and need no profile.
    """

    ROLE_CHOICES = [("customer", "Customer"), ("rider", "Rider")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    customer = models.OneToOneField(Customer, null=True, blank=True, on_delete=models.SET_NULL, related_name="profile")
    rider = models.OneToOneField(Rider, null=True, blank=True, on_delete=models.SET_NULL, related_name="profile")

    def __str__(self):
        return f"{self.user} ({self.role})"
