from django.contrib import admin

from .models import Boda, BodaType, Customer, CustomerRating, Profile, Rider, RiderRating, Trip

for model in (Customer, Rider, BodaType, Boda, Trip, RiderRating, CustomerRating):
    admin.site.register(model)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Use this to link an existing login to a customer or rider record."""

    list_display = ("user", "role", "customer", "rider")
    list_filter = ("role",)
