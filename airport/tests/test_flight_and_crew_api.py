import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from airport.models import Crew, Flight
from airport.serializers import CrewListSerializer, FlightListSerializer, FlightDetailSerializer
from airport.tests.test_airplane_api import sample_airplane
from airport.tests.test_airport_and_route_api import sample_route, sample_airport
from airport.views import FlightViewSet

CREW_URL = reverse("airport:crews-list")
FLIGHT_URL = reverse("airport:flights-list")

def detail_crew_url(crew_id):
    return reverse("airport:crews-detail", args=[crew_id])

def detail_flight_url(flight_id):
    return reverse("airport:flights-detail", args=[flight_id])

def sample_crew(**params):
    defaults = {
        "first_name": "John",
        "last_name": "Doe"
    }
    defaults.update(params)
    return Crew.objects.create(**defaults)

def sample_flight(**params):
    route = sample_route()
    airplane = sample_airplane()

    defaults = {
        "route": route,
        "airplane": airplane,
        "departure_time": "2025-06-05T09:00:00Z",
        "arrival_time": "2025-06-05T13:30:00Z"
    }
    defaults.update(params)
    return Flight.objects.create(**defaults)

def image_upload_url(crews_id):
    """Return URL for recipe image upload"""
    return reverse("airport:crews-upload-image", args=[crews_id])


class BaseFlightApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.authenticate()

    def authenticate(self):
        pass

    def test_crew_list(self):
        sample_crew()

        res = self.client.get(CREW_URL)
        crew = Crew.objects.all()
        serializer = CrewListSerializer(crew, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_flight_list(self):
        flight = sample_flight()
        crew = sample_crew()

        flight.crew.add(crew)

        res = self.client.get(FLIGHT_URL)
        flight = FlightViewSet.queryset
        serializer = FlightListSerializer(flight, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_retrieve_crew_detail(self):
        crew = sample_crew()

        url = detail_crew_url(crew.id)

        res = self.client.get(url)

        serializer = CrewListSerializer(crew)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_flight_detail(self):
        flight = sample_flight()

        url = detail_flight_url(flight.id)

        res = self.client.get(url)

        serializer = FlightDetailSerializer(flight)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_flights_by_departure_airport_and_arrival_airport_and_departure_time(self):
        airport_1 = sample_airport(closest_big_city="City")
        airport_2 = sample_airport(closest_big_city="Town")
        route_1 = sample_route(source=airport_1, destination=airport_2)
        route_2 = sample_route(source=airport_2, destination=airport_1)
        flight_1 = sample_flight(route=route_1, departure_time="2025-06-05T09:00:00Z")
        flight_2 = sample_flight(route=route_2, departure_time="2025-06-05T09:00:00Z")
        flight_3 = sample_flight(route=route_1, departure_time="2025-07-20T15:30:00Z")

        res_departure_air = self.client.get(FLIGHT_URL, {"departure-airport": airport_1.id})
        res_arrival_air = self.client.get(FLIGHT_URL, {"arrival-airport": airport_1.id})
        res_departure_date = self.client.get(FLIGHT_URL, {"date": "2025-06-05"})

        res_departure_air_ids = [flight["id"] for flight in res_departure_air.data["results"]]
        res_arrival_air_ids = [flight["id"] for flight in res_arrival_air.data["results"]]
        res_departure_date_ids = [flight["id"] for flight in res_departure_date.data["results"]]

        self.assertIn(flight_1.id, res_departure_air_ids)
        self.assertNotIn(flight_2.id, res_departure_air_ids)
        self.assertIn(flight_2.id, res_arrival_air_ids)
        self.assertNotIn(flight_1.id, res_arrival_air_ids)
        self.assertIn(flight_1.id, res_departure_date_ids)

        self.assertIn(flight_2.id, res_departure_date_ids)
        self.assertNotIn(flight_3, res_departure_date_ids)


class UnauthenticatedFlightApiTests(BaseFlightApiTests):
    def authenticate(self):
        # No authentication
        pass

    def test_create_crew_forbidden(self):
        payload = {
            "first_name": "John",
            "last_name": "Doe"
        }

        res = self.client.post(CREW_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_flight_forbidden(self):
        route = sample_route()
        airplane = sample_airplane()

        payload = {
            "route": route,
            "airplane": airplane,
            "departure_time": "2025-06-05T09:00:00Z",
            "arrival_time": "2025-06-05T13:30:00Z"
        }

        res = self.client.post(FLIGHT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedFlightApiTests(BaseFlightApiTests):
    def authenticate(self):
        user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword",
        )
        self.client.force_authenticate(user)

    def test_create_crew_forbidden(self):
        payload = {
            "first_name": "John",
            "last_name": "Doe"
        }

        res = self.client.post(CREW_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_flight_forbidden(self):
        route = sample_route()
        airplane = sample_airplane()

        payload = {
            "route": route,
            "airplane": airplane,
            "departure_time": "2025-06-05T09:00:00Z",
            "arrival_time": "2025-06-05T13:30:00Z"
        }

        res = self.client.post(FLIGHT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_create_crew(self):
        payload = {
            "first_name": "John",
            "last_name": "Doe"
        }

        res = self.client.post(CREW_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_flight(self):
        route = sample_route()
        airplane = sample_airplane()
        crew = sample_crew()

        payload = {
            "route": route.id,
            "airplane": airplane.id,
            "crew": (crew.id,),
            "departure_time": "2025-06-05T09:00:00Z",
            "arrival_time": "2025-06-05T13:30:00Z"
        }

        res = self.client.post(FLIGHT_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_delete_crew(self):
        crew = sample_crew()

        url = detail_crew_url(crew.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_flight(self):
        flight = sample_flight()

        url = detail_flight_url(flight.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)


class CrewImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.crew = sample_crew()

    def tearDown(self):
        self.crew.image.delete()

    def test_upload_image_to_crew(self):
        """Test uploading an image to crew"""
        url = image_upload_url(self.crew.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.crew.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.crew.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.crew.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_image_url_is_shown_on_crew_detail(self):
        url = image_upload_url(self.crew.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_crew_url(self.crew.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_crew_list(self):
        url = image_upload_url(self.crew.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(CREW_URL)

        self.assertIn("image", res.data["results"][0].keys())
