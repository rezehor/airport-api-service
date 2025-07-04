from django.contrib import admin

from airport.models import (
    Route,
    Airport,
    Crew,
    Flight,
    Ticket,
    Airplane,
    AirplaneType,
    Order
)


class TicketInLine(admin.TabularInline):
    model = Ticket
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [TicketInLine]


admin.site.register(Route)
admin.site.register(Airport)
admin.site.register(Crew)
admin.site.register(Flight)
admin.site.register(Ticket)
admin.site.register(Airplane)
admin.site.register(AirplaneType)
