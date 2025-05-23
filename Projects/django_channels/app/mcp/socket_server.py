# # mcp_server.py

# import os
# import sys
# from pathlib import Path
# # Get the absolute path to the project root
# PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
# sys.path.append(str(PROJECT_ROOT))

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_channels.settings')
# import django
# django.setup()

# from channels.layers import get_channel_layer

# from mcp.server.fastmcp import FastMCP
# import asyncio
# import uuid

# channel_layer = get_channel_layer()

# mcp = FastMCP("database_operations")
# @mcp.tool()
# async def send_broadcast_message(message: str) -> dict:
#     message_id = str(uuid.uuid4())
#     reply_channel = f"reply_{message_id}"
#     replies = []

#     await channel_layer.group_add(reply_channel, reply_channel)

#     try:
#         await channel_layer.group_send(
#             "broadcast_group",
#             {
#                 "type": "broadcast_message",
#                 "message": message,
#                 "message_id": message_id,
#                 "reply_channel": reply_channel,
#                 "command": "request_reply"
#             }
#         )

#         print(f"[MCP] Sent message with ID {message_id}. Awaiting replies...")

#         end_time = asyncio.get_event_loop().time() + 10
#         while asyncio.get_event_loop().time() < end_time:
#             try:
#                 received = await asyncio.wait_for(channel_layer.receive(reply_channel), timeout=0.05)
#                 if received.get("type") == "websocket.reply":
#                     replies.append(received["content"])
#             except asyncio.TimeoutError:
#                 continue
#     finally:
#         await channel_layer.group_discard(reply_channel, reply_channel)
#     print(f"[MCP] Received replies: {replies}")
#     return {
#         "message_id": message_id,
#         "replies": replies
#     }

# # --- Run MCP Server ---
# if __name__ == "__main__":
#     mcp.run(transport="stdio")

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
mcp = FastMCP("folder_operations")

@mcp.tool()
async def read_folder() -> dict:
    """Request folder structure from frontend clients"""
    message_id = str(uuid.uuid4())
    reply_channel = f"folder_reply_{message_id}"
    folder_responses = []
    path = "app/mcp"
    await channel_layer.group_add(reply_channel, reply_channel)
    
    try:
        # Send folder request to all connected clients
        await channel_layer.group_send(
            "broadcast_group",
            {
                "type": "folder_request",
                "path": path,
                "message_id": message_id
            }
        )
        
        print(f"[MCP] Sent folder request for path: '{path}' with ID {message_id}")
        
        # Wait for responses from clients
        end_time = asyncio.get_event_loop().time() + 15  # 15 second timeout
        while asyncio.get_event_loop().time() < end_time:
            try:
                received = await asyncio.wait_for(
                    channel_layer.receive(reply_channel), 
                    timeout=0.1
                )
                
                if received.get("type") == "folder_reply":
                    content = received.get("content", {})
                    folder_responses.append({
                        "channel": content.get("channel_name"),
                        "path": content.get("path"),
                        "folder_structure": content.get("folder_structure"),
                        "status": content.get("status")
                    })
                    print(f"[MCP] Received folder response from {content.get('channel_name')}")
                    
            except asyncio.TimeoutError:
                continue
                
    finally:
        await channel_layer.group_discard(reply_channel, reply_channel)
    
    if folder_responses:
        print(f"[MCP] Collected {len(folder_responses)} folder responses")
        return {
            "status": "success",
            "path": path,
            "responses": folder_responses,
            "message_id": message_id
        }
    else:
        print(f"[MCP] No folder responses received for path: '{path}'")
        return {
            "status": "error",
            "message": "No folder responses received from clients",
            "path": path,
            "message_id": message_id
        }

@mcp.tool()
async def update_folder(path: str, folder_structure: dict) -> dict:
    """Send folder update to frontend clients"""
    message_id = str(uuid.uuid4())
    reply_channel = f"update_reply_{message_id}"
    update_responses = []
    
    await channel_layer.group_add(reply_channel, reply_channel)
    
    try:
        # Send folder update to all connected clients
        await channel_layer.group_send(
            "broadcast_group",
            {
                "type": "folder_update",
                "path": path,
                "folder_structure": folder_structure,
                "message_id": message_id
            }
        )
        
        print(f"[MCP] Sent folder update for path: '{path}' with ID {message_id}")
        
        # Wait for confirmation responses from clients
        end_time = asyncio.get_event_loop().time() + 15  # 15 second timeout
        while asyncio.get_event_loop().time() < end_time:
            try:
                received = await asyncio.wait_for(
                    channel_layer.receive(reply_channel), 
                    timeout=0.1
                )
                
                if received.get("type") == "update_reply":
                    content = received.get("content", {})
                    update_responses.append({
                        "channel": content.get("channel_name"),
                        "status": content.get("status"),
                        "message": content.get("message")
                    })
                    print(f"[MCP] Received update confirmation from {content.get('channel_name')}")
                    
            except asyncio.TimeoutError:
                continue
                
    finally:
        await channel_layer.group_discard(reply_channel, reply_channel)
    
    if update_responses:
        print(f"[MCP] Collected {len(update_responses)} update confirmations")
        return {
            "status": "success",
            "path": path,
            "confirmations": update_responses,
            "message_id": message_id
        }
    else:
        print(f"[MCP] No update confirmations received for path: '{path}'")
        return {
            "status": "warning",
            "message": "Update sent but no confirmations received",
            "path": path,
            "message_id": message_id
        }

if __name__ == "__main__":
    print("[MCP] Starting MCP server with folder operations...")
    print("[MCP] Available tools:")
    print("  - send_broadcast_message: Send messages to WebSocket clients")
    print("  - read_folder: Request folder structure from frontend")
    print("  - update_folder: Send folder updates to frontend")
    print("  - create_plugin_structure: Create new plugin and send to frontend")
    print("  - read_plugin_folder: Read specific plugin folder")
    print("  - update_plugin_file: Update specific file in plugin")
    
    mcp.run(transport="stdio")