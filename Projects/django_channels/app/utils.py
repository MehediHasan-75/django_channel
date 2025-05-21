import sys
import os
import django
import asyncio
import uuid
import time
import json
from asgiref.sync import async_to_sync

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_channels.settings')
django.setup()

from channels.layers import get_channel_layer

# Synchronous approach to send message and get reply
def send_message_sync():
    """
    Send a message to the broadcast group and wait for replies
    using a synchronous approach compatible with your existing consumers
    """
    # Generate a unique ID for this message
    message_id = str(uuid.uuid4())
    
    # Get the channel layer
    channel_layer = get_channel_layer()
    
    # Create a unique reply channel for this request
    reply_channel = f"reply_{message_id}"
    
    # Add ourselves to the reply channel group to receive responses
    async_to_sync(channel_layer.group_add)(
        reply_channel,
        reply_channel
    )
    
    try:
        # Send message to broadcast group
        async_to_sync(channel_layer.group_send)(
            "broadcast_group",
            {
                "type": "broadcast_message",
                "message": f"Message from script with ID: {message_id}",
                "message_id": message_id,
                "reply_channel": reply_channel,
                "command": "request_reply"  # Special command to indicate reply is requested
            }
        )
        
        print(f"Message sent to broadcast group. Message ID: {message_id}")
        print(f"Waiting for replies on channel: {reply_channel}")
        
        # Wait for replies with timeout
        start_time = time.time()
        timeout = 10  # seconds
        replies = []
        
        while time.time() - start_time < timeout:
            try:
                # Try to receive message from reply channel
                message = async_to_sync(channel_layer.receive)(reply_channel)
                
                if message.get("type") == "websocket.reply":
                    print(f"Reply received: {message['content']}")
                    replies.append(message["content"])
                    
                    # If we don't expect more replies, we can break
                    # For example, if we received replies from all connected clients
                    # if len(replies) >= expected_replies:
                    #     break
            except:
                # No message available yet, sleep briefly
                time.sleep(0.1)
        
        if not replies:
            print("No replies received within timeout period")
        else:
            print(f"Received {len(replies)} replies")
            
        return replies
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up by removing from reply channel group
        async_to_sync(channel_layer.group_discard)(
            reply_channel,
            reply_channel
        )

# Asynchronous approach to send message and get reply
async def send_message_async():
    """
    Send a message to the broadcast group and wait for replies
    using an asynchronous approach compatible with your existing consumers
    """
    # Generate a unique ID for this message
    message_id = str(uuid.uuid4())
    
    # Get the channel layer
    channel_layer = get_channel_layer()
    
    # Create a unique reply channel for this request
    reply_channel = f"reply_{message_id}"
    
    # Add ourselves to the reply channel group to receive responses
    await channel_layer.group_add(
        reply_channel,
        reply_channel
    )
    
    try:
        # Send message to broadcast group
        await channel_layer.group_send(
            "broadcast_group",
            {
                "type": "broadcast_message",
                "message": f"Message from async script with ID: {message_id}",
                "message_id": message_id,
                "reply_channel": reply_channel,
                "command": "request_reply"  # Special command to indicate reply is requested
            }
        )
        
        print(f"Message sent to broadcast group. Message ID: {message_id}")
        print(f"Waiting for replies on channel: {reply_channel}")
        
        # Wait for replies with timeout
        replies = []
        try:
            # Set a total timeout for collecting replies
            end_time = asyncio.get_event_loop().time() + 10  # 10 seconds timeout
            
            while asyncio.get_event_loop().time() < end_time:
                try:
                    # Use a shorter timeout for each receive attempt
                    message = await asyncio.wait_for(
                        channel_layer.receive(reply_channel),
                        timeout=0.5
                    )
                    
                    if message.get("type") == "websocket.reply":
                        print(f"Reply received: {message['content']}")
                        replies.append(message["content"])
                except asyncio.TimeoutError:
                    # No message in this interval, continue waiting
                    pass
        except Exception as e:
            print(f"Error waiting for replies: {e}")
            
        if not replies:
            print("No replies received within timeout period")
        else:
            print(f"Received {len(replies)} replies")
            
        return replies
        
    finally:
        # Clean up
        await channel_layer.group_discard(
            reply_channel,
            reply_channel
        )

# Entry point
if __name__ == "__main__":
    # Choose which approach to use (sync or async)
    use_async = True  # Set to False to use the sync method
    
    if use_async:
        asyncio.run(send_message_async())
    else:
        send_message_sync()