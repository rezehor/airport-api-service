import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from airport.models import AirplaneType, Airplane
from airport.serializers import AirplaneTypeListSerializer, AirplaneListSerializer, AirplaneDetailSerializer

AIRPLANE_TYPE_URL = reverse("airport:airplane_types-list")
AIRPLANE_URL = reverse("airport:airplanes-list")

def detail_airplane_type_url(airplane_type_id):
    return reverse("airport:airplane_types-detail", args=[airplane_type_id])

def detail_airplane_url(airplane_id):
    return reverse("airport:airplanes-detail", args=[airplane_id])

def sample_airplane_type(**params):
    defaults = {
        "name": "Test Airplane Type",
    }
    defaults.update(params)
    return AirplaneType.objects.create(**defaults)

def sample_airplane(**params):
    airplane_type = AirplaneType.objects.create(
        name="Test Airplane Type"
    )

    defaults = {
        "name": "Test Airplane",
        "rows": 15,
        "seats_in_row": 30,
        "airplane_type": airplane_type,
    }
    defaults.update(params)
    return Airplane.objects.create(**defaults)

def image_upload_url(airplane_type_id):
    """Return URL for recipe image upload"""
    return reverse("airport:airplane_types-upload-image", args=[airplane_type_id])


class BaseAirplaneApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.authenticate()

    def authenticate(self):
        pass

    def test_airplane_type_list(self):
        sample_airplane_type()

        res = self.client.get(AIRPLANE_TYPE_URL)
        airplane_types = AirplaneType.objects.all()
        serializer = AirplaneTypeListSerializer(airplane_types, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_airplane_list(self):
        sample_airplane()

        res = self.client.get(AIRPLANE_URL)
        airplane = Airplane.objects.all()
        serializer = AirplaneListSerializer(airplane, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_retrieve_airplane_type_detail(self):
        airplane_type = sample_airplane_type()

        url = detail_airplane_type_url(airplane_type.id)

        res = self.client.get(url)

        serializer = AirplaneTypeListSerializer(airplane_type)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_airplane_detail(self):
        airplane = sample_airplane()

        url = detail_airplane_url(airplane.id)

        res = self.client.get(url)

        serializer = AirplaneDetailSerializer(airplane)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)



class UnauthenticatedAirplaneApiTests(BaseAirplaneApiTests):
    def authenticate(self):
        # No authentication
        pass

    def test_create_airplane_type_forbidden(self):
        payload = {
            "name": "Test Airplane Type",
        }

        res = self.client.post(AIRPLANE_TYPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_airplane_forbidden(self):
        airplane_type = AirplaneType.objects.create(
            name="Test Airplane Type"
        )
        payload = {
            "name": "Test Airplane",
            "rows": 15,
            "seats_in_row": 30,
            "airplane_type": airplane_type,
        }

        res = self.client.post(AIRPLANE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirplaneApiTests(BaseAirplaneApiTests):
    def authenticate(self):
        user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword",
        )
        self.client.force_authenticate(user)

    def test_create_airplane_type_forbidden(self):
        payload = {
            "name": "Test Airplane Type",
        }

        res = self.client.post(AIRPLANE_TYPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_airplane_forbidden(self):
        airplane_type = AirplaneType.objects.create(
            name="Test Airplane Type"
        )
        payload = {
            "name": "Test Airplane",
            "rows": 15,
            "seats_in_row": 30,
            "airplane_type": airplane_type,
        }

        res = self.client.post(AIRPLANE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminBusTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_create_airplane_type(self):
        payload = {
            "name": "Test Airplane Type",
        }

        res = self.client.post(AIRPLANE_TYPE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_airplane(self):
        airplane_type = AirplaneType.objects.create(
            name="Test Airplane Type"
        )
        payload = {
            "name": "Test Airplane",
            "rows": 15,
            "seats_in_row": 30,
            "airplane_type": airplane_type.id,
        }

        res = self.client.post(AIRPLANE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_delete_airplane_type(self):
        airplane_type = sample_airplane_type()

        url = detail_airplane_type_url(airplane_type.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_airplane(self):
        airplane = sample_airplane()

        url = detail_airplane_url(airplane.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)


class AirplaneTypeImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.airplane_type = sample_airplane_type()

    def tearDown(self):
        self.airplane_type.image.delete()

    def test_upload_image_to_airplane_type(self):
        """Test uploading an image to airplane_type"""
        url = image_upload_url(self.airplane_type.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.airplane_type.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.airplane_type.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.airplane_type.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_image_url_is_shown_on_airplane_type_detail(self):
        url = image_upload_url(self.airplane_type.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_airplane_type_url(self.airplane_type.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_airplane_type_list(self):
        url = image_upload_url(self.airplane_type.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(AIRPLANE_TYPE_URL)

        self.assertIn("image", res.data["results"][0].keys())
