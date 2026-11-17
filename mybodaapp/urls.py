from django.contrib import admin
from django.urls import path

from bodaapp import customer_views, rider_views, views

urlpatterns = [
    path('admin/', admin.site.urls),

    # shared: dashboard (a different page for each role) and authentication
    path('', views.index_view, name='index'),
    path('home/', views.home_view, name='home'),
    path('rating/', views.rating_view, name='rating'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),
    path('signup/<str:role>/', views.signup_form_view, name='signup_form'),

    # ── administrator pages ─────────────────────────────────────────────
    path('customer/', views.customer_view, name='customer'),
    path('customer/<int:pk>/edit/', views.customer_view, name='customer_edit'),
    path('customer/<int:pk>/delete/', views.customer_delete, name='customer_delete'),

    path('rider/', views.rider_view, name='rider'),
    path('rider/<int:pk>/edit/', views.rider_view, name='rider_edit'),
    path('rider/<int:pk>/delete/', views.rider_delete, name='rider_delete'),

    path('bodatype/', views.bodatype_view, name='bodatype'),
    path('bodatype/<int:pk>/edit/', views.bodatype_view, name='bodatype_edit'),
    path('bodatype/<int:pk>/delete/', views.bodatype_delete, name='bodatype_delete'),

    path('boda/', views.boda_view, name='boda'),
    path('boda/<int:pk>/edit/', views.boda_view, name='boda_edit'),
    path('boda/<int:pk>/delete/', views.boda_delete, name='boda_delete'),

    path('trip/', views.trip_view, name='trip'),
    path('trip/<int:pk>/edit/', views.trip_view, name='trip_edit'),
    path('trip/<int:pk>/delete/', views.trip_delete, name='trip_delete'),

    path('riderrating/', views.riderrating_view, name='riderrating'),
    path('riderrating/<int:pk>/edit/', views.riderrating_view, name='riderrating_edit'),
    path('riderrating/<int:pk>/delete/', views.riderrating_delete, name='riderrating_delete'),

    path('customerrating/', views.customerrating_view, name='customerrating'),
    path('customerrating/<int:pk>/edit/', views.customerrating_view, name='customerrating_edit'),
    path('customerrating/<int:pk>/delete/', views.customerrating_delete, name='customerrating_delete'),

    path('fare/', views.fare_view, name='fare'),

    # ── customer pages ──────────────────────────────────────────────────
    path('customer-area/trips/', customer_views.trips, name='cust_trips'),
    path('customer-area/trips/<int:pk>/cancel/', customer_views.trip_cancel, name='cust_trip_cancel'),
    path('customer-area/rate-rider/', customer_views.rate_rider, name='cust_rate_rider'),
    path('customer-area/my-ratings/', customer_views.ratings, name='cust_ratings'),
    path('customer-area/billing/', customer_views.billing, name='cust_billing'),

    # ── rider pages ─────────────────────────────────────────────────────
    path('rider-area/bodas/', rider_views.bodas, name='rid_bodas'),
    path('rider-area/trips/', rider_views.trips, name='rid_trips'),
    path('rider-area/trips/<int:pk>/<str:action>/', rider_views.trip_action, name='rid_trip_action'),
    path('rider-area/rate-customer/', rider_views.rate_customer, name='rid_rate_customer'),
    path('rider-area/my-ratings/', rider_views.ratings, name='rid_ratings'),
    path('rider-area/earnings/', rider_views.earnings, name='rid_earnings'),
]
