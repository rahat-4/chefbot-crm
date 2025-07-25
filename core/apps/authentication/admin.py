from django.contrib import admin

from .models import User, RegistrationSession, Customer

admin.site.register(User)
admin.site.register(RegistrationSession)
admin.site.register(Customer)
