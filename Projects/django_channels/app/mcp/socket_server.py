# mcp_server.py

import os
import sys
import django
import asyncio
import uuid
import time
from modelcontextprotocol import MCPServer, tool
from channels.layers import get_channel_layer

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_channels.settings')
django.setup()

channel_layer = get_channel_layer()

@tool(name="send_broadcast_message", description="Send a message via Django Channels and receive replies.")
async def send_broadcast_message(message: str) -> dict:
    message_id = str(uuid.uuid4())
    reply_channel = f"reply_{message_id}"
    replies = []

    await channel_layer.group_add(reply_channel, reply_channel)

    try:
        await channel_layer.group_send(
            "broadcast_group",
            {
                "type": "broadcast_message",
                "message": message,
                "message_id": message_id,
                "reply_channel": reply_channel,
                "command": "request_reply"
            }
        )

        print(f"[MCP] Sent message with ID {message_id}. Awaiting replies...")

        end_time = asyncio.get_event_loop().time() + 10
        while asyncio.get_event_loop().time() < end_time:
            try:
                received = await asyncio.wait_for(channel_layer.receive(reply_channel), timeout=0.05)
                if received.get("type") == "websocket.reply":
                    replies.append(received["content"])
            except asyncio.TimeoutError:
                continue
    finally:
        await channel_layer.group_discard(reply_channel, reply_channel)

    return {
        "message_id": message_id,
        "replies": replies
    }

# --- Run MCP Server ---
if __name__ == "__main__":
    server = MCPServer()
    server.register_tool(send_broadcast_message)
    server.run()
