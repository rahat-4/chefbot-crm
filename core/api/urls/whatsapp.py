from django.urls import path

from ..views.whatsapp import whatsapp_bot

urlpatterns = [path("/bot", whatsapp_bot, name="whatsapp-bot")]
