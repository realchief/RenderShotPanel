from django.conf.urls import url
from django.urls import re_path

from system.consumers import *

websocket_urlpatterns = [
   url(r'^ws/system/$', SystemConsumer.as_asgi()),
]
