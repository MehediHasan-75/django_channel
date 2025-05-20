from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import sys, os, django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_channels.settings')
django.setup()

import json

def send_ws_message():
    """
    Utility function to send message to all WebSocket clients
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "broadcast_group",
        {
            "type": "broadcast_message",
            "message": "sent from utils"
        }
    )
    channel_layer = get_channel_layer()
    # print("Message sent!")
if __name__ == "__main__":
    send_ws_message()