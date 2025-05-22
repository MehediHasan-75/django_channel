# import os
# import sys
# import django
# import argparse

# # Add the project root directory to sys.path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_channels.settings')
# django.setup()

# from app.utils import send_ws_message

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description='Send WebSocket message')
#     parser.add_argument('message', nargs='?', default="Hello from backend!",
#                       help='Message to send (default: Hello from backend!)')
    
#     args = parser.parse_args()
#     try:
#         print(f"Sending message: {args.message}")
#         send_ws_message(args.message)
#         print("Message sent successfully!")
#     except Exception as e:
#         print(f"Error sending message: {e}")

#!/usr/bin/env python
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import os
import django
import sys
import json

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_channels.settings')

try:
    django.setup()
except Exception as e:
    print(f"Failed to initialize Django: {e}")
    print("Make sure to update 'your_project_name' with your actual Django project name.")
    sys.exit(1)

async def send_ws_message(message):
    """
    Utility function to send message to all WebSocket clients
    """
    try:
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            "broadcast_group",
            {
                "type": "broadcast_message",
                "message": message
            }
        )
        print(f"✅ Message successfully sent: {message}")
        return True
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False

# FIXED DATA - Edit these values as needed
MESSAGE_DATA = {
    "status": "success",
    "message": "This is a test message",
    "data": {
        "id": 12345,
        "timestamp": "2025-05-20T10:30:00Z",
        "values": [10, 20, 30, 40, 50]
    }
}

# Call the function with fixed data
if __name__ == "__main__":
    print("Sending fixed WebSocket message...")
    send_ws_message(MESSAGE_DATA)