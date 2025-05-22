# mcp_server.py

import os
import sys
from pathlib import Path
# Get the absolute path to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_channels.settings')
import django
django.setup()

from channels.layers import get_channel_layer

from mcp.server.fastmcp import FastMCP
import asyncio
import uuid

channel_layer = get_channel_layer()

mcp = FastMCP("database_operations")
@mcp.tool()
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
    print(f"[MCP] Received replies: {replies}")
    return {
        "message_id": message_id,
        "replies": replies
    }

# --- Run MCP Server ---
if __name__ == "__main__":
    mcp.run(transport="stdio")
