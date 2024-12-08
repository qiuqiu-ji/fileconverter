from django.urls import re_path
from apps.converter import consumers

websocket_urlpatterns = [
    re_path(r'ws/conversion/(?P<task_id>\w+)/$', consumers.ConversionProgressConsumer.as_asgi()),
] 