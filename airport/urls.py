from django.urls import path, include
from rest_framework.routers import DefaultRouter
from airport.views import (
    AirplaneViewSet,
    AirplaneTypeViewSet,
    AirportViewSet,
    RouteViewSet,
    CrewViewSet,
    FlightViewSet,
    OrderViewSet)

app_name = "airport"

router = DefaultRouter()

router.register(
    "airplane_types",
    AirplaneTypeViewSet,
    basename="airplane_types")
router.register(
    "airplanes",
    AirplaneViewSet,
    basename="airplanes"
)
router.register("airports", AirportViewSet, basename="airports")
router.register("routes", RouteViewSet, basename="routes")
router.register("crews", CrewViewSet, basename="crews")
router.register("flights", FlightViewSet, basename="flights")
router.register("orders", OrderViewSet, basename="orders")

urlpatterns = [
    path("", include(router.urls)),
]
