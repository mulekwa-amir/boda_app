from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Boda, BodaType, Customer, CustomerRating, Profile, Rider, RiderRating, Trip,
)

PW = "S3cure-pass-77"
ADMIN_PAGES = ["customer", "rider", "bodatype", "boda", "trip", "riderrating", "customerrating", "fare"]
CUSTOMER_PAGES = ["cust_trips", "cust_rate_rider", "cust_ratings", "cust_billing"]
RIDER_PAGES = ["rid_trips", "rid_bodas", "rid_rate_customer", "rid_ratings", "rid_earnings"]


def make_world():
    """A small, internally consistent data set used by several tests."""
    customer = Customer.objects.create(
        first_name="John", last_name="Mukasa", contact="0700111222",
        email="john@email.com", home_location="Kampala",
    )
    other_customer = Customer.objects.create(
        first_name="Mary", last_name="Nakato", contact="0700999000",
        email="mary@email.com", home_location="Jinja",
    )
    rider = Rider.objects.create(
        first_name="James", last_name="Kato", contact="0700333444", license="DL-1001",
        experience_years=5, age=28, gender="Male", home_location="Kampala",
    )
    other_rider = Rider.objects.create(
        first_name="Moses", last_name="Wanyama", contact="0700555666", license="DL-1002",
        experience_years=3, age=30, gender="Male", home_location="Jinja",
    )
    btype = BodaType.objects.create(type_name="Standard")
    boda = Boda.objects.create(boda_type=btype, model="Bajaj Boxer", plate_number="UAB123A", rider=rider)
    other_boda = Boda.objects.create(boda_type=btype, model="TVS Star", plate_number="UAC456B", rider=other_rider)
    start = timezone.now() - timedelta(hours=2)
    trip = Trip.objects.create(
        customer=customer, rider=rider, boda=boda, pickup_location="Kampala Road",
        dropoff_location="Ntinda", start_time=start, end_time=start + timedelta(minutes=25),
        status="completed", fare=8000, distance_km="6.4",
    )
    return dict(customer=customer, other_customer=other_customer, rider=rider, other_rider=other_rider,
                btype=btype, boda=boda, other_boda=other_boda, trip=trip)


def make_admin():
    return User.objects.create_user("boss", password=PW, is_staff=True)


def make_customer_user(customer, name="cust"):
    user = User.objects.create_user(name, password=PW)
    Profile.objects.create(user=user, role="customer", customer=customer)
    return user


def make_rider_user(rider, name="ride"):
    user = User.objects.create_user(name, password=PW)
    Profile.objects.create(user=user, role="rider", rider=rider)
    return user


# --------------------------------------------------------------------------- #
# Who can see what
# --------------------------------------------------------------------------- #
class AccessControl(TestCase):
    def setUp(self):
        self.w = make_world()
        self.admin = make_admin()
        self.cust = make_customer_user(self.w["customer"])
        self.ride = make_rider_user(self.w["rider"])

    def test_anonymous_is_sent_to_login_everywhere(self):
        for name in ["index", *ADMIN_PAGES, *CUSTOMER_PAGES, *RIDER_PAGES]:
            with self.subTest(page=name):
                resp = self.client.get(reverse(name))
                self.assertRedirects(resp, f"{reverse('login')}?next={reverse(name)}")

    def test_admin_reaches_admin_pages_only(self):
        self.client.force_login(self.admin)
        for name in ["index", *ADMIN_PAGES]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        for name in CUSTOMER_PAGES + RIDER_PAGES:
            with self.subTest(blocked=name):
                self.assertRedirects(self.client.get(reverse(name)), reverse("index"))

    def test_customer_reaches_customer_pages_only(self):
        self.client.force_login(self.cust)
        for name in ["index", *CUSTOMER_PAGES]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        for name in ADMIN_PAGES + RIDER_PAGES:
            with self.subTest(blocked=name):
                self.assertRedirects(self.client.get(reverse(name)), reverse("index"))

    def test_rider_reaches_rider_pages_only(self):
        self.client.force_login(self.ride)
        for name in ["index", *RIDER_PAGES]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        for name in ADMIN_PAGES + CUSTOMER_PAGES:
            with self.subTest(blocked=name):
                self.assertRedirects(self.client.get(reverse(name)), reverse("index"))

    def test_blocked_user_sees_a_message(self):
        self.client.force_login(self.cust)
        resp = self.client.get(reverse("customer"), follow=True)
        self.assertContains(resp, "don&#x27;t have access")

    def test_non_admin_cannot_post_admin_actions(self):
        self.client.force_login(self.cust)
        self.client.post(reverse("customer_delete", args=[self.w["other_customer"].pk]))
        self.assertTrue(Customer.objects.filter(pk=self.w["other_customer"].pk).exists())
        self.client.post(reverse("bodatype"), {"type_name": "Sneaky"})
        self.assertFalse(BodaType.objects.filter(type_name="Sneaky").exists())

    def test_user_without_a_linked_record_sees_setup_page(self):
        User.objects.create_user("lost", password=PW)
        self.client.login(username="lost", password=PW)
        resp = self.client.get(reverse("index"))
        self.assertContains(resp, "isn't linked to a customer or rider")
        self.assertRedirects(self.client.get(reverse("cust_trips")), reverse("index"))

    def test_profile_whose_record_was_deleted_loses_access(self):
        orphan = Customer.objects.create(first_name="O", last_name="P", contact="0711000111",
                                         email="o@p.com", home_location="X")
        user = make_customer_user(orphan, "orphan")
        orphan.delete()
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse("index")), "isn't linked to a customer or rider")


class SidebarDiffersByRole(TestCase):
    def setUp(self):
        self.w = make_world()

    def links(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("index")).content.decode()

    def test_admin_sidebar(self):
        html = self.links(make_admin())
        for name in ["customer", "rider", "bodatype", "boda", "trip", "riderrating", "customerrating", "fare"]:
            self.assertIn(f'href="{reverse(name)}"', html)
        self.assertIn('href="/admin/"', html)
        self.assertNotIn(reverse("cust_trips"), html)
        self.assertNotIn(reverse("rid_trips"), html)
        self.assertIn("Administrator", html)

    def test_customer_sidebar(self):
        html = self.links(make_customer_user(self.w["customer"]))
        for name in CUSTOMER_PAGES:
            self.assertIn(f'href="{reverse(name)}"', html)
        self.assertIn("Book a Trip", html)
        for name in ADMIN_PAGES + RIDER_PAGES:
            self.assertNotIn(f'href="{reverse(name)}"', html)
        self.assertNotIn('href="/admin/"', html)

    def test_rider_sidebar(self):
        html = self.links(make_rider_user(self.w["rider"]))
        for name in RIDER_PAGES:
            self.assertIn(f'href="{reverse(name)}"', html)
        self.assertIn("My Earnings", html)
        for name in ADMIN_PAGES + CUSTOMER_PAGES:
            self.assertNotIn(f'href="{reverse(name)}"', html)
        self.assertNotIn("Book a Trip", html)

    def test_current_page_is_highlighted(self):
        self.client.force_login(make_admin())
        html = self.client.get(reverse("trip")).content.decode()
        self.assertRegex(html, r'nav-link active bg-gradient-dark text-white" href="/trip/"')
        self.assertNotRegex(html, r'nav-link active bg-gradient-dark text-white" href="/rider/"')

    def test_edit_page_keeps_its_nav_link_highlighted(self):
        self.client.force_login(make_admin())
        html = self.client.get(reverse("customer_edit", args=[self.w["customer"].pk])).content.decode()
        self.assertRegex(html, r'nav-link active bg-gradient-dark text-white" href="/customer/"')


# --------------------------------------------------------------------------- #
# Administrator forms (full CRUD)
# --------------------------------------------------------------------------- #
class AdminTestCase(TestCase):
    def setUp(self):
        self.client.force_login(make_admin())


class CustomerCrud(AdminTestCase):
    data = dict(first_name="Mary", last_name="Nakato", contact="0700 666 777",
                email="Mary.Nakato@Email.com", home_location="Gulu")

    def test_create_normalises_and_lists(self):
        resp = self.client.post(reverse("customer"), self.data, follow=True)
        self.assertRedirects(resp, reverse("customer"))
        c = Customer.objects.get()
        self.assertEqual((c.contact, c.email), ("0700666777", "mary.nakato@email.com"))
        self.assertContains(resp, "Mary")
        self.assertContains(resp, "added successfully")

    def test_duplicate_contact_and_email_rejected(self):
        self.client.post(reverse("customer"), self.data)
        resp = self.client.post(reverse("customer"), self.data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertContains(resp, "already exists")

    def test_bad_phone_rejected(self):
        resp = self.client.post(reverse("customer"), {**self.data, "contact": "abc"})
        self.assertEqual(Customer.objects.count(), 0)
        self.assertContains(resp, "valid phone number")

    def test_edit_prefills_and_updates(self):
        c = make_world()["customer"]
        self.assertContains(self.client.get(reverse("customer_edit", args=[c.pk])), 'value="Mukasa"')
        self.client.post(reverse("customer_edit", args=[c.pk]), {
            "first_name": "Johnny", "last_name": "Mukasa", "contact": "0700111222",
            "email": "john@email.com", "home_location": "Entebbe"})
        c.refresh_from_db()
        self.assertEqual((c.first_name, c.home_location), ("Johnny", "Entebbe"))

    def test_edit_missing_record_is_404(self):
        self.assertEqual(self.client.get(reverse("customer_edit", args=[999])).status_code, 404)


class RiderCrud(AdminTestCase):
    data = dict(first_name="Ivan", last_name="Mugisha", contact="0700777888", license="dl-2000",
                experience_years=4, age=26, gender="Male", home_location="Entebbe")

    def test_create(self):
        self.client.post(reverse("rider"), self.data)
        self.assertEqual(Rider.objects.get().license, "DL-2000")

    def test_age_and_experience_rules(self):
        for bad in ({"age": 15}, {"age": 90}, {"experience_years": -1}, {"experience_years": 40}):
            with self.subTest(bad=bad):
                self.client.post(reverse("rider"), {**self.data, **bad})
                self.assertEqual(Rider.objects.count(), 0)

    def test_gender_required(self):
        self.client.post(reverse("rider"), {**self.data, "gender": ""})
        self.assertEqual(Rider.objects.count(), 0)


class FleetCrud(AdminTestCase):
    def test_boda_type_create_and_unique(self):
        self.client.post(reverse("bodatype"), {"type_name": "Premium"})
        resp = self.client.post(reverse("bodatype"), {"type_name": "Premium"})
        self.assertEqual(BodaType.objects.count(), 1)
        self.assertContains(resp, "already exists")

    def test_boda_create_uppercases_plate(self):
        w = make_world()
        self.client.post(reverse("boda"), {
            "boda_type": w["btype"].pk, "model": "Honda", "plate_number": "uad 789c",
            "rider": w["rider"].pk})
        self.assertTrue(Boda.objects.filter(plate_number="UAD789C").exists())

    def test_boda_duplicate_plate_rejected(self):
        w = make_world()
        resp = self.client.post(reverse("boda"), {
            "boda_type": w["btype"].pk, "model": "X", "plate_number": "UAB123A", "rider": w["rider"].pk})
        self.assertEqual(Boda.objects.count(), 2)
        self.assertContains(resp, "already exists")


class TripCrud(AdminTestCase):
    def payload(self, w, **over):
        data = dict(customer=w["customer"].pk, rider=w["rider"].pk, boda=w["boda"].pk,
                    pickup_location="Wandegeya", dropoff_location="Makerere",
                    start_time="2026-11-10T08:00", end_time="2026-11-10T08:20",
                    status="completed", fare="4000", distance_km="2.1")
        data.update(over)
        return data

    def test_create(self):
        w = make_world()
        self.assertRedirects(self.client.post(reverse("trip"), self.payload(w)), reverse("trip"))
        self.assertEqual(Trip.objects.count(), 2)

    def test_pending_trip_without_end_time(self):
        w = make_world()
        self.client.post(reverse("trip"), self.payload(w, end_time="", status="pending"))
        self.assertTrue(Trip.objects.filter(status="pending", end_time__isnull=True).exists())

    def test_validation_rules(self):
        w = make_world()
        cases = {
            "end before start": dict(end_time="2026-11-10T07:00"),
            "zero fare": dict(fare="0"),
            "zero distance": dict(distance_km="0"),
            "completed w/o end": dict(end_time=""),
            "boda not rider's": dict(rider=w["other_rider"].pk),
            "bad status": dict(status="flying"),
        }
        for label, over in cases.items():
            with self.subTest(label):
                resp = self.client.post(reverse("trip"), self.payload(w, **over))
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(Trip.objects.count(), 1)

    def test_edit_form_prefills_datetime_in_local_time(self):
        w = make_world()
        resp = self.client.get(reverse("trip_edit", args=[w["trip"].pk]))
        local = timezone.localtime(w["trip"].start_time).strftime("%Y-%m-%dT%H:%M")
        self.assertContains(resp, f'value="{local}"')

    def test_table_shows_status_badge_and_fare(self):
        make_world()
        html = self.client.get(reverse("trip")).content.decode()
        self.assertIn("badge-sm bg-gradient-success", html)
        self.assertIn("8,000", html)


class RatingCrud(AdminTestCase):
    def test_rider_rating_create_and_one_per_trip(self):
        w = make_world()
        data = dict(trip=w["trip"].pk, rider=w["rider"].pk, rated_by=w["customer"].pk, score=5, comment="Great")
        self.client.post(reverse("riderrating"), data)
        self.assertEqual(RiderRating.objects.count(), 1)
        resp = self.client.post(reverse("riderrating"), data)
        self.assertEqual(RiderRating.objects.count(), 1)
        self.assertContains(resp, "already exists")

    def test_customer_rating_create(self):
        w = make_world()
        self.client.post(reverse("customerrating"), dict(
            trip=w["trip"].pk, customer=w["customer"].pk, rated_by=w["rider"].pk, score=4, comment=""))
        self.assertEqual(CustomerRating.objects.count(), 1)

    def test_score_range(self):
        w = make_world()
        for score in (0, 6, ""):
            with self.subTest(score=score):
                self.client.post(reverse("riderrating"), dict(
                    trip=w["trip"].pk, rider=w["rider"].pk, rated_by=w["customer"].pk, score=score))
                self.assertEqual(RiderRating.objects.count(), 0)

    def test_only_completed_trips_and_matching_people(self):
        w = make_world()
        w["trip"].status = "ongoing"; w["trip"].save()
        self.client.post(reverse("riderrating"), dict(
            trip=w["trip"].pk, rider=w["rider"].pk, rated_by=w["customer"].pk, score=5))
        self.assertEqual(RiderRating.objects.count(), 0)
        w["trip"].status = "completed"; w["trip"].save()
        self.client.post(reverse("riderrating"), dict(
            trip=w["trip"].pk, rider=w["other_rider"].pk, rated_by=w["customer"].pk, score=5))
        self.assertEqual(RiderRating.objects.count(), 0)


class Deleting(AdminTestCase):
    def test_delete_unused_record(self):
        c = Customer.objects.create(first_name="A", last_name="B", contact="0711111111",
                                    email="a@b.com", home_location="X")
        resp = self.client.post(reverse("customer_delete", args=[c.pk]), follow=True)
        self.assertFalse(Customer.objects.exists())
        self.assertContains(resp, "deleted")

    def test_delete_in_use_is_blocked_with_message(self):
        w = make_world()
        resp = self.client.post(reverse("customer_delete", args=[w["customer"].pk]), follow=True)
        self.assertTrue(Customer.objects.filter(pk=w["customer"].pk).exists())
        self.assertContains(resp, "Cannot delete")

    def test_delete_requires_post(self):
        w = make_world()
        self.assertEqual(self.client.get(reverse("customer_delete", args=[w["customer"].pk])).status_code, 405)

    def test_deleting_trip_removes_its_rating(self):
        w = make_world()
        RiderRating.objects.create(trip=w["trip"], rider=w["rider"], rated_by=w["customer"], score=5)
        self.client.post(reverse("trip_delete", args=[w["trip"].pk]))
        self.assertFalse(RiderRating.objects.exists())


class Billing(AdminTestCase):
    def test_totals(self):
        make_world()
        resp = self.client.get(reverse("fare"))
        self.assertEqual(resp.context["collected"], 8000)
        self.assertEqual(resp.context["completed_count"], 1)
        self.assertContains(resp, "8,000")

    def test_dashboard_stats(self):
        make_world()
        stats = self.client.get(reverse("index")).context["stats"]
        self.assertEqual((stats["customers"], stats["riders"], stats["bodas"], stats["trips"]), (2, 2, 2, 1))
        self.assertEqual(stats["revenue"], "8,000")


# --------------------------------------------------------------------------- #
# Customer area
# --------------------------------------------------------------------------- #
class CustomerArea(TestCase):
    def setUp(self):
        self.w = make_world()
        self.client.force_login(make_customer_user(self.w["customer"]))

    def test_dashboard_shows_own_numbers_only(self):
        other_start = timezone.now()
        Trip.objects.create(customer=self.w["other_customer"], rider=self.w["rider"], boda=self.w["boda"],
                            pickup_location="A", dropoff_location="B", start_time=other_start,
                            status="completed", end_time=other_start + timedelta(minutes=5),
                            fare=50000, distance_km="1")
        resp = self.client.get(reverse("index"))
        self.assertEqual(resp.context["trip_count"], 1)
        self.assertEqual(resp.context["spent"], 8000)
        self.assertEqual(resp.context["avg_rating"], "—")
        self.assertTemplateUsed(resp, "customer/dashboard.html")

    def test_book_a_trip(self):
        resp = self.client.post(reverse("cust_trips"), dict(
            boda=self.w["other_boda"].pk, pickup_location="Wandegeya", dropoff_location="Makerere",
            distance_km="2.5", fare="3000"))
        self.assertRedirects(resp, reverse("cust_trips"))
        trip = Trip.objects.exclude(pk=self.w["trip"].pk).get()
        self.assertEqual(trip.customer, self.w["customer"])
        self.assertEqual(trip.rider, self.w["other_rider"])      # taken from the boda
        self.assertEqual(trip.status, "pending")
        self.assertAlmostEqual(trip.start_time.timestamp(), timezone.now().timestamp(), delta=30)

    def test_booking_validation(self):
        for bad in ({"fare": "0"}, {"distance_km": "0"}, {"boda": ""}, {"pickup_location": ""}):
            with self.subTest(bad=bad):
                data = dict(boda=self.w["boda"].pk, pickup_location="A", dropoff_location="B",
                            distance_km="2", fare="3000")
                data.update(bad)
                self.client.post(reverse("cust_trips"), data)
                self.assertEqual(Trip.objects.count(), 1)

    def test_cannot_book_for_someone_else_via_extra_fields(self):
        self.client.post(reverse("cust_trips"), dict(
            boda=self.w["boda"].pk, pickup_location="A", dropoff_location="B", distance_km="2", fare="3000",
            customer=self.w["other_customer"].pk, status="completed", rider=self.w["other_rider"].pk))
        trip = Trip.objects.exclude(pk=self.w["trip"].pk).get()
        self.assertEqual((trip.customer, trip.status, trip.rider),
                         (self.w["customer"], "pending", self.w["rider"]))

    def test_trip_list_is_only_my_trips(self):
        Trip.objects.create(customer=self.w["other_customer"], rider=self.w["rider"], boda=self.w["boda"],
                            pickup_location="SECRET-A", dropoff_location="SECRET-B",
                            start_time=timezone.now(), status="pending", fare=1, distance_km="1")
        resp = self.client.get(reverse("cust_trips"))
        self.assertContains(resp, "Ntinda")
        self.assertNotContains(resp, "SECRET-A")

    def test_cancel_pending_trip_only(self):
        pending = Trip.objects.create(customer=self.w["customer"], rider=self.w["rider"], boda=self.w["boda"],
                                      pickup_location="A", dropoff_location="B", start_time=timezone.now(),
                                      status="pending", fare=1000, distance_km="1")
        self.client.post(reverse("cust_trip_cancel", args=[pending.pk]))
        pending.refresh_from_db()
        self.assertEqual(pending.status, "cancelled")
        self.client.post(reverse("cust_trip_cancel", args=[self.w["trip"].pk]))
        self.w["trip"].refresh_from_db()
        self.assertEqual(self.w["trip"].status, "completed")

    def test_cannot_cancel_someone_elses_trip(self):
        other = Trip.objects.create(customer=self.w["other_customer"], rider=self.w["rider"], boda=self.w["boda"],
                                    pickup_location="A", dropoff_location="B", start_time=timezone.now(),
                                    status="pending", fare=1000, distance_km="1")
        self.assertEqual(self.client.post(reverse("cust_trip_cancel", args=[other.pk])).status_code, 404)
        other.refresh_from_db()
        self.assertEqual(other.status, "pending")

    def test_rate_rider(self):
        resp = self.client.post(reverse("cust_rate_rider"), dict(trip=self.w["trip"].pk, score=5, comment="Super"))
        self.assertRedirects(resp, reverse("cust_rate_rider"))
        rating = RiderRating.objects.get()
        self.assertEqual((rating.rider, rating.rated_by, rating.score), (self.w["rider"], self.w["customer"], 5))

    def test_rate_rider_only_once_and_only_own_completed_trips(self):
        self.client.post(reverse("cust_rate_rider"), dict(trip=self.w["trip"].pk, score=5))
        self.client.post(reverse("cust_rate_rider"), dict(trip=self.w["trip"].pk, score=1))
        self.assertEqual(RiderRating.objects.count(), 1)
        now = timezone.now()
        theirs = Trip.objects.create(customer=self.w["other_customer"], rider=self.w["rider"], boda=self.w["boda"],
                                     pickup_location="A", dropoff_location="B", start_time=now,
                                     end_time=now + timedelta(minutes=5), status="completed",
                                     fare=1000, distance_km="1")
        self.client.post(reverse("cust_rate_rider"), dict(trip=theirs.pk, score=1))
        ongoing = Trip.objects.create(customer=self.w["customer"], rider=self.w["rider"], boda=self.w["boda"],
                                      pickup_location="A", dropoff_location="B", start_time=now,
                                      status="ongoing", fare=1000, distance_km="1")
        self.client.post(reverse("cust_rate_rider"), dict(trip=ongoing.pk, score=1))
        self.assertEqual(RiderRating.objects.count(), 1)

    def test_rate_rider_score_range(self):
        for score in ("0", "6", ""):
            self.client.post(reverse("cust_rate_rider"), dict(trip=self.w["trip"].pk, score=score))
        self.assertEqual(RiderRating.objects.count(), 0)

    def test_ratings_about_me_and_billing_pages(self):
        CustomerRating.objects.create(trip=self.w["trip"], customer=self.w["customer"],
                                      rated_by=self.w["rider"], score=4, comment="Polite")
        resp = self.client.get(reverse("cust_ratings"))
        self.assertContains(resp, "Polite")
        self.assertEqual(resp.context["avg_rating"], "4.0")
        billing = self.client.get(reverse("cust_billing"))
        self.assertEqual(billing.context["paid"], 8000)
        self.assertContains(billing, "8,000")


# --------------------------------------------------------------------------- #
# Rider area
# --------------------------------------------------------------------------- #
class RiderArea(TestCase):
    def setUp(self):
        self.w = make_world()
        self.client.force_login(make_rider_user(self.w["rider"]))

    def new_trip(self, status="pending", **over):
        data = dict(customer=self.w["customer"], rider=self.w["rider"], boda=self.w["boda"],
                    pickup_location="A", dropoff_location="B", start_time=timezone.now() - timedelta(minutes=10),
                    status=status, fare=5000, distance_km="3")
        data.update(over)
        return Trip.objects.create(**data)

    def test_dashboard_and_bodas_show_own_data_only(self):
        resp = self.client.get(reverse("index"))
        self.assertTemplateUsed(resp, "rider/dashboard.html")
        self.assertEqual((resp.context["trip_count"], resp.context["earned"]), (1, 8000))
        bodas = self.client.get(reverse("rid_bodas"))
        self.assertContains(bodas, "UAB123A")
        self.assertNotContains(bodas, "UAC456B")

    def test_trips_list_only_mine(self):
        Trip.objects.create(customer=self.w["customer"], rider=self.w["other_rider"], boda=self.w["other_boda"],
                            pickup_location="SECRET-A", dropoff_location="SECRET-B",
                            start_time=timezone.now(), status="pending", fare=1, distance_km="1")
        resp = self.client.get(reverse("rid_trips"))
        self.assertContains(resp, "Ntinda")
        self.assertNotContains(resp, "SECRET-A")

    def test_start_then_complete_a_trip(self):
        trip = self.new_trip()
        self.client.post(reverse("rid_trip_action", args=[trip.pk, "start"]))
        trip.refresh_from_db()
        self.assertEqual((trip.status, trip.end_time), ("ongoing", None))
        self.client.post(reverse("rid_trip_action", args=[trip.pk, "complete"]))
        trip.refresh_from_db()
        self.assertEqual(trip.status, "completed")
        self.assertGreater(trip.end_time, trip.start_time)

    def test_cancel_a_trip(self):
        trip = self.new_trip()
        self.client.post(reverse("rid_trip_action", args=[trip.pk, "cancel"]))
        trip.refresh_from_db()
        self.assertEqual(trip.status, "cancelled")

    def test_invalid_transitions_are_refused(self):
        trip = self.new_trip()
        self.client.post(reverse("rid_trip_action", args=[trip.pk, "complete"]))   # must start first
        trip.refresh_from_db()
        self.assertEqual(trip.status, "pending")
        self.client.post(reverse("rid_trip_action", args=[self.w["trip"].pk, "start"]))  # already completed
        self.client.post(reverse("rid_trip_action", args=[self.w["trip"].pk, "cancel"]))
        self.w["trip"].refresh_from_db()
        self.assertEqual(self.w["trip"].status, "completed")
        self.client.post(reverse("rid_trip_action", args=[trip.pk, "explode"]))
        trip.refresh_from_db()
        self.assertEqual(trip.status, "pending")

    def test_cannot_act_on_someone_elses_trip(self):
        theirs = self.new_trip(rider=self.w["other_rider"], boda=self.w["other_boda"])
        self.assertEqual(self.client.post(reverse("rid_trip_action", args=[theirs.pk, "start"])).status_code, 404)
        theirs.refresh_from_db()
        self.assertEqual(theirs.status, "pending")

    def test_actions_require_post(self):
        trip = self.new_trip()
        self.assertEqual(self.client.get(reverse("rid_trip_action", args=[trip.pk, "start"])).status_code, 405)

    def test_rate_customer(self):
        resp = self.client.post(reverse("rid_rate_customer"), dict(trip=self.w["trip"].pk, score=3, comment="Late"))
        self.assertRedirects(resp, reverse("rid_rate_customer"))
        rating = CustomerRating.objects.get()
        self.assertEqual((rating.customer, rating.rated_by, rating.score), (self.w["customer"], self.w["rider"], 3))
        self.client.post(reverse("rid_rate_customer"), dict(trip=self.w["trip"].pk, score=1))
        self.assertEqual(CustomerRating.objects.count(), 1)

    def test_cannot_rate_a_trip_i_did_not_ride(self):
        now = timezone.now()
        theirs = self.new_trip("completed", rider=self.w["other_rider"], boda=self.w["other_boda"],
                               end_time=now + timedelta(minutes=5))
        self.client.post(reverse("rid_rate_customer"), dict(trip=theirs.pk, score=1))
        self.assertEqual(CustomerRating.objects.count(), 0)

    def test_ratings_about_me_and_earnings(self):
        RiderRating.objects.create(trip=self.w["trip"], rider=self.w["rider"], rated_by=self.w["customer"],
                                   score=5, comment="Brilliant")
        resp = self.client.get(reverse("rid_ratings"))
        self.assertContains(resp, "Brilliant")
        self.assertEqual(resp.context["avg_rating"], "5.0")
        self.new_trip("ongoing")
        earnings = self.client.get(reverse("rid_earnings"))
        self.assertEqual((earnings.context["earned"], earnings.context["pending"]), (8000, 5000))


# --------------------------------------------------------------------------- #
# Authentication and sign-up
# --------------------------------------------------------------------------- #
class Auth(TestCase):
    cust_data = dict(username="newcust", password1=PW, password2=PW, first_name="Ann", last_name="Auma",
                     contact="0712345678", email="ann@email.com", home_location="Gulu")
    rider_data = dict(username="newrider", password1=PW, password2=PW, first_name="Ben", last_name="Opio",
                      contact="0787654321", license="dl-3000", experience_years=2, age=24, gender="Male",
                      home_location="Mbale")

    def test_pages_render(self):
        for url in (reverse("login"), reverse("signup"), reverse("signup_form", args=["customer"]),
                    reverse("signup_form", args=["rider"])):
            self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(reverse("signup_form", args=["admin"])).status_code, 404)

    def test_customer_signup_creates_everything_and_logs_in(self):
        resp = self.client.post(reverse("signup_form", args=["customer"]), self.cust_data)
        self.assertRedirects(resp, reverse("index"))
        user = User.objects.get(username="newcust")
        self.assertFalse(user.is_staff)
        self.assertEqual((user.profile.role, user.profile.customer.email), ("customer", "ann@email.com"))
        page = self.client.get(reverse("index"))
        self.assertTemplateUsed(page, "customer/dashboard.html")
        self.assertContains(page, "Book a Trip")

    def test_rider_signup_creates_everything_and_logs_in(self):
        self.client.post(reverse("signup_form", args=["rider"]), self.rider_data)
        user = User.objects.get(username="newrider")
        self.assertEqual((user.profile.role, user.profile.rider.license), ("rider", "DL-3000"))
        self.assertTemplateUsed(self.client.get(reverse("index")), "rider/dashboard.html")

    def test_signup_is_all_or_nothing(self):
        bad_record = {**self.cust_data, "contact": "nope"}
        self.client.post(reverse("signup_form", args=["customer"]), bad_record)
        self.assertFalse(User.objects.exists() or Customer.objects.exists())
        bad_account = {**self.cust_data, "password2": "different"}
        resp = self.client.post(reverse("signup_form", args=["customer"]), bad_account)
        self.assertFalse(User.objects.exists() or Customer.objects.exists())
        self.assertContains(resp, "password fields didn")

    def test_signup_shows_errors_for_both_forms_at_once(self):
        resp = self.client.post(reverse("signup_form", args=["customer"]),
                                {**self.cust_data, "contact": "nope", "password2": "different"})
        self.assertContains(resp, "valid phone number")
        self.assertContains(resp, "password fields didn")

    def test_signup_with_taken_email_is_rejected(self):
        Customer.objects.create(first_name="X", last_name="Y", contact="0700000001",
                                email="ann@email.com", home_location="Z")
        self.client.post(reverse("signup_form", args=["customer"]), self.cust_data)
        self.assertFalse(User.objects.exists())

    def test_login_logout_and_next(self):
        User.objects.create_user("sam", password=PW, is_staff=True)
        bad = self.client.post(reverse("login"), {"username": "sam", "password": "wrong"})
        self.assertContains(bad, "Please enter a correct")
        ok = self.client.post(reverse("login") + "?next=/trip/", {"username": "sam", "password": PW})
        self.assertRedirects(ok, "/trip/")
        self.assertContains(self.client.get(reverse("index")), "Sign Out")
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_next_is_not_an_open_redirect(self):
        User.objects.create_user("sam", password=PW)
        resp = self.client.post(reverse("login") + "?next=https://evil.example/", {"username": "sam", "password": PW})
        self.assertRedirects(resp, reverse("index"), fetch_redirect_response=False)

    def test_logout_requires_post(self):
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)

    def test_redirect_aliases(self):
        self.client.force_login(make_admin())
        self.assertRedirects(self.client.get(reverse("home")), reverse("index"))
        self.assertRedirects(self.client.get(reverse("rating")), reverse("riderrating"))


# --------------------------------------------------------------------------- #
# Forms open in a modal
# --------------------------------------------------------------------------- #
class ModalForms(TestCase):
    def setUp(self):
        self.w = make_world()

    def test_every_form_page_has_an_add_button_and_a_closed_modal(self):
        self.client.force_login(make_admin())
        pages = ["customer", "rider", "bodatype", "boda", "trip", "riderrating", "customerrating"]
        for name in pages:
            with self.subTest(page=name):
                html = self.client.get(reverse(name)).content.decode()
                self.assertIn('id="recordModal"', html)
                self.assertIn('data-bs-toggle="modal" data-bs-target="#recordModal"', html)
                self.assertNotIn("data-auto-open", html)          # closed until the button is clicked
                self.assertNotIn('id="record-form"', html)        # old inline form card is gone

    def test_customer_and_rider_form_pages_use_a_modal(self):
        self.client.force_login(make_customer_user(self.w["customer"]))
        for name in ("cust_trips", "cust_rate_rider"):
            html = self.client.get(reverse(name)).content.decode()
            self.assertIn('id="recordModal"', html)
            self.assertNotIn("data-auto-open", html)
        self.client.force_login(make_rider_user(self.w["rider"]))
        html = self.client.get(reverse("rid_rate_customer")).content.decode()
        self.assertIn('id="recordModal"', html)

    def test_modal_is_rendered_outside_main(self):
        self.client.force_login(make_admin())
        html = self.client.get(reverse("customer")).content.decode()
        self.assertGreater(html.index('id="recordModal"'), html.index("</main>"))

    def test_edit_page_opens_the_modal_prefilled(self):
        self.client.force_login(make_admin())
        html = self.client.get(reverse("customer_edit", args=[self.w["customer"].pk])).content.decode()
        self.assertIn('data-auto-open="1"', html)
        self.assertIn(f'data-reset-url="{reverse("customer")}"', html)
        self.assertIn('value="Mukasa"', html)
        self.assertIn(f"Edit customer #{self.w['customer'].pk}", html)

    def test_failed_save_reopens_the_modal_with_errors(self):
        self.client.force_login(make_admin())
        resp = self.client.post(reverse("customer"), {"first_name": "", "contact": "abc"})
        html = resp.content.decode()
        self.assertIn('data-auto-open="1"', html)
        self.assertIn("valid phone number", html)
        self.assertIn("This field is required", html)

    def test_customer_booking_error_reopens_the_modal(self):
        self.client.force_login(make_customer_user(self.w["customer"]))
        html = self.client.post(reverse("cust_trips"), {"fare": "0"}).content.decode()
        self.assertIn('data-auto-open="1"', html)
        self.assertIn("Fare must be greater than zero", html)
        self.assertEqual(Trip.objects.count(), 1)

    def test_successful_save_redirects_to_a_clean_list(self):
        self.client.force_login(make_admin())
        resp = self.client.post(reverse("bodatype"), {"type_name": "Premium"}, follow=True)
        self.assertNotIn("data-auto-open", resp.content.decode())
        self.assertContains(resp, "Premium")

    def test_edit_links_in_the_table_have_no_anchor(self):
        self.client.force_login(make_admin())
        html = self.client.get(reverse("customer")).content.decode()
        self.assertIn(f'href="{reverse("customer_edit", args=[self.w["customer"].pk])}"', html)
        self.assertNotIn("#record-form", html)
