from django.contrib import admin

from .models import Organization, OrganizationUser, OpeningHours, WhatsappBot


admin.site.register(Organization)
admin.site.register(OrganizationUser)
admin.site.register(OpeningHours)
admin.site.register(WhatsappBot)
