from django.urls import re_path
from api import consumers

websocket_urlpatterns = [
    re_path(r'ws/stock/(?P<symbol>\w+)/$', consumers.StockConsumer.as_asgi()),
]