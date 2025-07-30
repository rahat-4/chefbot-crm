from django.contrib import admin

from .models import User, RegistrationSession, Client, ClientMessage

admin.site.register(User)
admin.site.register(RegistrationSession)
admin.site.register(Client)
admin.site.register(ClientMessage)
