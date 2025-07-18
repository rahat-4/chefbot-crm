from django.contrib import admin

from .models import Organization, OrganizationUser, OpeningHours, Services


admin.site.register(Organization)
admin.site.register(OrganizationUser)
admin.site.register(OpeningHours)
admin.site.register(Services)
