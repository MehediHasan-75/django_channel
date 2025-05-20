from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

def send_ws_message(message):
    """
    Utility function to send message to all WebSocket clients
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "broadcast_group",
        {
            "type": "broadcast_message",
            "message": message
        }
    )
    # print("Message sent!")