from django.contrib import admin

from .models import Organization, Address, OpeningHours, Services


admin.site.register(Organization)
admin.site.register(Address)
admin.site.register(OpeningHours)
admin.site.register(Services)
