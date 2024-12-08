from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/conversion/(?P<task_id>[0-9a-f-]+)/$',
        consumers.ConversionProgressConsumer.as_asgi()
    ),
    re_path(
        r'ws/batch/(?P<batch_id>[0-9a-f-]+)/$',
        consumers.BatchProgressConsumer.as_asgi()
    ),
] 