from datetime import datetime

from django.db.models import F, Count
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from airport.models import (
    Airplane,
    AirplaneType,
    Airport,
    Route,
    Crew,
    Flight,
    Order,
)
from airport.permissions import IsAdminOrIfAuthenticatedReadOnly
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
    OrderListSerializer,
    OrderDetailSerializer,
    RouteDetailSerializer,
    AirplaneTypeImageSerializer,
    AirplaneTypeListSerializer,
    AirportListSerializer,
    AirportImageSerializer, CrewListSerializer, CrewImageSerializer,
)


class AirplaneTypeViewSet(viewsets.ModelViewSet):
    queryset = AirplaneType.objects.all()
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return AirplaneTypeListSerializer
        elif self.action == "upload_image":
            return AirplaneTypeImageSerializer
        return AirplaneTypeSerializer

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        """Endpoint for uploading image to specific airplane type"""
        airplane_type = self.get_object()
        serializer = self.get_serializer(airplane_type, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AirplaneViewSet(viewsets.ModelViewSet):
    queryset = Airplane.objects.all().select_related("airplane_type")
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly, )

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return AirplaneListSerializer
        return AirplaneSerializer


class AirportViewSet(viewsets.ModelViewSet):
    queryset = Airport.objects.all()
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly, )

    def get_queryset(self):
        city = self.request.query_params.get("city")

        queryset = self.queryset

        if city:
            queryset = queryset.filter(closest_big_city__icontains=city)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return AirportListSerializer
        elif self.action == "upload_image":
            return AirportImageSerializer
        return AirportSerializer

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        """Endpoint for uploading image to specific airport"""
        airport = self.get_object()
        serializer = self.get_serializer(airport, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all().select_related("source", "destination")
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly, )

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer
        elif self.action == "retrieve":
            return RouteDetailSerializer
        return RouteSerializer


class CrewViewSet(viewsets.ModelViewSet):
    queryset = Crew.objects.all()
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly, )

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return CrewListSerializer
        elif self.action == "upload_image":
            return CrewImageSerializer
        return CrewSerializer

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        """Endpoint for uploading image to specific crew"""
        crew = self.get_object()
        serializer = self.get_serializer(crew, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly, )

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


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    queryset = Order.objects.all()
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = self.queryset.filter(user=self.request.user)
        if self.action == "list":
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
