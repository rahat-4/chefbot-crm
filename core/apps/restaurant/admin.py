from django.contrib import admin

from .models import (
    SalesLevel,
    Menu,
    Reward,
    PromotionTrigger,
    Promotion,
    Reservation,
    RestaurantTable,
    Client,
    ClientMessage,
)

admin.site.register(Menu)
admin.site.register(SalesLevel)
admin.site.register(Reward)
admin.site.register(PromotionTrigger)
admin.site.register(Promotion)
admin.site.register(Reservation)
admin.site.register(RestaurantTable)
admin.site.register(Client)
admin.site.register(ClientMessage)
