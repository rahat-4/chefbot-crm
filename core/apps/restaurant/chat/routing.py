from django.urls import re_path

from .consumers import RealtimeConsumer

websocket_urlpatterns = [
    re_path(r"ws/realtime/(?P<client_uid>[^/]+)/$", RealtimeConsumer.as_asgi()),
]
