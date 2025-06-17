from django.db import models

from airport_api_service import settings


class AirplaneType(models.Model):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class Airplane(models.Model):
    name = models.CharField(max_length=64)
    rows = models.IntegerField()
    seats_in_row = models.IntegerField()
    airplane_type = models.ForeignKey(AirplaneType, on_delete=models.CASCADE, related_name="airplanes")

    def __str__(self):
        return f"{self.name}: type {self.airplane_type.name}"


class Airport(models.Model):
    name = models.CharField(max_length=64)
    closest_big_city = models.CharField(max_length=64)

    def __str__(self):
        return f"{self.name} ({self.closest_big_city})"


class Route(models.Model):
    source = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name="routes")
    destination = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name="routes")
    distance = models.IntegerField()

    def __str__(self):
        return f"From: {self.source.name} To: {self.destination.name} Distance: {self.distance}km"


class Crew(models.Model):
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Flight(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="flights")
    airplane = models.ForeignKey(Airplane, on_delete=models.CASCADE, related_name="flights")
    crew = models.ManyToManyField(Crew, related_name="flights")
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()

    def __str__(self):
        return (f"Route: {self.route.source} -> {self.route.destination}\n"
                f"Airplane: {self.airplane.name}\n"
                f"Departure: {self.departure_time}\n"
                f"Arrival: {self.arrival_time}")


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return str(self.created_at)


class Ticket(models.Model):
    row = models.IntegerField()
    seat = models.IntegerField()
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name="tickets")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tickets")

    def __str__(self):
        return f"Row: {self.row} Seat: {self.seat} Flight: {self.flight}"

