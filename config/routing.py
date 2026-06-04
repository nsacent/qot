from apps.chats.routing import websocket_urlpatterns as chat_websocket_urlpatterns
from apps.notifications.routing import websocket_urlpatterns as notification_websocket_urlpatterns


websocket_urlpatterns = []

websocket_urlpatterns += chat_websocket_urlpatterns
websocket_urlpatterns += notification_websocket_urlpatterns