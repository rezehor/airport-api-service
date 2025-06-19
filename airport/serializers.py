from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from airport.models import (
    AirplaneType,
    Airplane,
    Airport,
    Route,
    Crew,
    Flight,
    Ticket,
    Order
)


class AirplaneTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirplaneType
        fields = ("id", "name")


class AirplaneTypeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirplaneType
        fields = ("id", "name", "image")


class AirplaneTypeImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirplaneType
        fields = ("id", "image")


class AirplaneSerializer(serializers.ModelSerializer):

    class Meta:
        model = Airplane
        fields = ("id", "name", "rows", "seats_in_row", "airplane_type", "capacity")


class AirplaneListSerializer(AirplaneSerializer):
    airplane_type = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field="name",
    )


class AirplaneDetailSerializer(AirplaneSerializer):
    airplane_type = AirplaneTypeListSerializer()


class AirportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = ("id", "name", "closest_big_city")


class AirportListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = ("id", "name", "closest_big_city", "image")


class AirportImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = ("id", "image")


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")


class RouteListSerializer(RouteSerializer):
    source = serializers.StringRelatedField(read_only=True)
    destination = serializers.StringRelatedField(read_only=True)


class RouteDetailSerializer(RouteSerializer):
    source = AirportSerializer(read_only=True)
    destination = AirportSerializer(read_only=True)


class CrewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name", "full_name")


class CrewListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name", "full_name", "image")


class CrewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ("id", "image")


class FlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flight
        fields = (
            "id",
            "route",
            "airplane",
            "crew",
            "departure_time",
            "arrival_time"
        )


class FlightListSerializer(serializers.ModelSerializer):
    departure_airport = serializers.CharField(source="route.source.closest_big_city", read_only=True)
    arrival_airport = serializers.CharField(source="route.destination.closest_big_city", read_only=True)
    airplane = serializers.StringRelatedField(read_only=True)
    crew = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="full_name",
    )
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Flight
        fields = (
            "id",
            "departure_airport",
            "arrival_airport",
            "airplane",
            "crew",
            "departure_time",
            "arrival_time",
            "tickets_available",
        )


class FlightDetailSerializer(FlightSerializer):
    route = RouteDetailSerializer(read_only=True)
    airplane = AirplaneListSerializer(read_only=True)
    crew = CrewSerializer(many=True, read_only=True)


class TicketSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        data = super(TicketSerializer, self).validate(attrs=attrs)
        Ticket.validate_ticket(
            attrs["row"],
            attrs["seat"],
            attrs["flight"].airplane,
            ValidationError
        )
        return data

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "flight")


class TicketListSerializer(TicketSerializer):
    flight = FlightListSerializer(many=False, read_only=True)


class TicketDetailSerializer(TicketSerializer):
    flight = FlightDetailSerializer(many=False, read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order

    class Meta:
        model = Order
        fields = ("id", "created_at", "tickets")


class OrderListSerializer(OrderSerializer):
    tickets = TicketListSerializer(many=True, read_only=True)


class OrderDetailSerializer(OrderSerializer):
    tickets = TicketDetailSerializer(many=True, read_only=True)