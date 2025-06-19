import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from airport.models import Airport, Route
from airport.serializers import AirportListSerializer, RouteListSerializer, RouteDetailSerializer

AIRPORT_URL = reverse("airport:airports-list")
ROUTE_URL = reverse("airport:routes-list")

def detail_airport_url(airport_id):
    return reverse("airport:airports-detail", args=[airport_id])

def detail_route_url(route_id):
    return reverse("airport:routes-detail", args=[route_id])

def sample_airport(**params):
    defaults = {
        "name": "Test Airport",
        "closest_big_city": "Test City",
    }
    defaults.update(params)
    return Airport.objects.create(**defaults)

def sample_route(**params):
    source = Airport.objects.create(
        name="Source Airport",
        closest_big_city="Source City",
    )
    destination = Airport.objects.create(
        name="Destination Airport",
        closest_big_city="Destination City",
    )

    defaults = {
        "source": source,
        "destination": destination,
        "distance": 1000,
    }
    defaults.update(params)
    return Route.objects.create(**defaults)

def image_upload_url(airports_id):
    """Return URL for recipe image upload"""
    return reverse("airport:airports-upload-image", args=[airports_id])

class BaseAirportApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.authenticate()

    def authenticate(self):
        pass

    def test_airport_list(self):
        sample_airport()

        res = self.client.get(AIRPORT_URL)
        airport = Airport.objects.all()
        serializer = AirportListSerializer(airport, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_route_list(self):
        sample_route()

        res = self.client.get(ROUTE_URL)
        route = Route.objects.all()
        serializer = RouteListSerializer(route, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_retrieve_airport_detail(self):
        airport = sample_airport()

        url = detail_airport_url(airport.id)

        res = self.client.get(url)

        serializer = AirportListSerializer(airport)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_route_detail(self):
        route = sample_route()

        url = detail_route_url(route.id)

        res = self.client.get(url)

        serializer = RouteDetailSerializer(route)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_airports_by_cities(self):
        airport_1 = sample_airport(closest_big_city="City 1")
        airport_2 = sample_airport(closest_big_city="City 2")
        airport_3 = sample_airport(closest_big_city="Town")

        res = self.client.get(AIRPORT_URL, {"city": "City"})

        serializer1 = AirportListSerializer(airport_1)
        serializer2 = AirportListSerializer(airport_2)
        serializer3 = AirportListSerializer(airport_3)

        self.assertIn(serializer1.data, res.data["results"])
        self.assertIn(serializer2.data, res.data["results"])
        self.assertNotIn(serializer3.data, res.data["results"])


class UnauthenticatedAirportApiTests(BaseAirportApiTests):
    def authenticate(self):
        # No authentication
        pass

    def test_create_airport_forbidden(self):
        payload = {
            "name": "Test Airport",
            "closest_big_city": "Test City",
        }

        res = self.client.post(AIRPORT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_route_forbidden(self):
        source = Airport.objects.create(
            name="Source Airport",
            closest_big_city="Source City",
        )
        destination = Airport.objects.create(
            name="Destination Airport",
            closest_big_city="Destination City",
        )

        payload = {
            "source": source,
            "destination": destination,
            "distance": 1000,
        }

        res = self.client.post(ROUTE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirportApiTests(BaseAirportApiTests):
    def authenticate(self):
        user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword",
        )
        self.client.force_authenticate(user)

    def test_create_airplane_type_forbidden(self):
        payload = {
            "name": "Test Airport",
            "closest_big_city": "Test City",
        }

        res = self.client.post(AIRPORT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_airplane_forbidden(self):
        source = Airport.objects.create(
            name="Source Airport",
            closest_big_city="Source City",
        )
        destination = Airport.objects.create(
            name="Destination Airport",
            closest_big_city="Destination City",
        )

        payload = {
            "source": source,
            "destination": destination,
            "distance": 1000,
        }

        res = self.client.post(ROUTE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_create_airport(self):
        payload = {
            "name": "Test Airport",
            "closest_big_city": "Test City",
        }

        res = self.client.post(AIRPORT_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_route(self):
        source = Airport.objects.create(
            name="Source Airport",
            closest_big_city="Source City",
        )
        destination = Airport.objects.create(
            name="Destination Airport",
            closest_big_city="Destination City",
        )

        payload = {
            "source": source.id,
            "destination": destination.id,
            "distance": 1000,
        }

        res = self.client.post(ROUTE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_delete_airport(self):
        airport = sample_airport()

        url = detail_airport_url(airport.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_route(self):
        route = sample_route()

        url = detail_route_url(route.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)


class AirportImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.airport = sample_airport()

    def tearDown(self):
        self.airport.image.delete()

    def test_upload_image_to_airport(self):
        """Test uploading an image to airport"""
        url = image_upload_url(self.airport.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.airport.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.airport.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.airport.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_image_url_is_shown_on_airport_detail(self):
        url = image_upload_url(self.airport.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_airport_url(self.airport.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_airport_list(self):
        url = image_upload_url(self.airport.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(AIRPORT_URL)

        self.assertIn("image", res.data["results"][0].keys())