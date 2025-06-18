from datetime import datetime

from django.db.models import F, Count
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination

from airport.models import (
    Airplane,
    AirplaneType,
    Airport,
    Route,
    Crew,
    Flight,
    Order,
)
from airport.serializers import (
    AirplaneSerializer,
    AirplaneTypeSerializer,
    AirportSerializer,
    RouteSerializer,
    CrewSerializer,
    FlightSerializer,
    OrderSerializer,
    AirplaneListSerializer,
    RouteListSerializer,
    FlightListSerializer,
    FlightDetailSerializer,
    OrderListSerializer, OrderDetailSerializer, RouteDetailSerializer,
)


class AirplaneTypeViewSet(viewsets.ModelViewSet):
    queryset = AirplaneType.objects.all()
    serializer_class = AirplaneTypeSerializer


class AirplaneViewSet(viewsets.ModelViewSet):
    queryset = Airplane.objects.all().select_related("airplane_type")

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return AirplaneListSerializer
        return AirplaneSerializer


class AirportViewSet(viewsets.ModelViewSet):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer

    def get_queryset(self):
        city = self.request.query_params.get("city")

        queryset = self.queryset

        if city:
            queryset = queryset.filter(closest_big_city__icontains=city)

        return queryset.distinct()


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all().select_related("source", "destination")
    serializer_class = RouteSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer
        elif self.action == "retrieve":
            return RouteDetailSerializer
        return RouteSerializer


class CrewViewSet(viewsets.ModelViewSet):
    queryset = Crew.objects.all()
    serializer_class = CrewSerializer


class FlightViewSet(viewsets.ModelViewSet):
    queryset = (
        Flight.objects.all()
        .select_related(
    "route__source",
        "route__destination",
        "airplane__airplane_type",
        )
        .prefetch_related("crew")
        .annotate(
            tickets_available=(
                F("airplane__rows") * F("airplane__seats_in_row")
                - Count("tickets")
            )
        )
    )

    @staticmethod
    def _params_to_ints(qs):
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        """Retrieve the flights with filters"""
        departure_airport = self.request.query_params.get("departure_airport")
        arrival_airport = self.request.query_params.get("arrival_airport")
        date = self.request.query_params.get("date")

        queryset = self.queryset

        if departure_airport:
            departure_airport_ids = self._params_to_ints(departure_airport)
            queryset = queryset.filter(route__source__id__in=departure_airport_ids)

        if arrival_airport:
            arrival_airport_ids = self._params_to_ints(arrival_airport)
            queryset = queryset.filter(route__destination__id__in=arrival_airport_ids)

        if date:
            date = datetime.strptime(date, "%Y-%m-%d").date()
            queryset = queryset.filter(departure_time__date=date)

        return queryset.distinct()


    def get_serializer_class(self):
        if self.action == "list":
            return FlightListSerializer
        elif self.action == "retrieve":
            return FlightDetailSerializer
        return FlightSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()

    def get_queryset(self):
        queryset = self.queryset.filter(user=self.request.user)
        if self.action == "list":
            queryset = queryset.prefetch_related(
                "tickets__flight__route",
                "tickets__flight__airplane",
                "tickets__flight__crew",
            )
        elif self.action == "retrieve":
            queryset = queryset.prefetch_related(
                "tickets__flight__route",
                "tickets__flight__airplane",
                "tickets__flight__crew",
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        elif self.action == "retrieve":
            return OrderDetailSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
