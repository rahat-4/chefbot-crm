from django.contrib import admin

from .models import User, RegistrationSession, Client

admin.site.register(User)
admin.site.register(RegistrationSession)
admin.site.register(Client)
