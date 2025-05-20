import os
import sys
import json
import asyncio
from contextlib import AsyncExitStack
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Union, AsyncGenerator
from datetime import datetime

from django.conf import settings

# Import the central socket handler
from ..socket_handler import create_socket_handler, send_to_client, run_with_tracking

# Set up logging
logger = logging.getLogger(__name__)

# Import Anthropic client
try:
    from anthropic import Anthropic
except ImportError:
    logger.error("Anthropic package not installed.")
    raise ImportError("Anthropic package not installed. Install with 'pip install anthropic'")

# Import for MCP
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    logger.warning("MCP packages not installed. Some functionality will be limited.")

# Import for LangChain
try:
    from langchain_mcp_adapters.tools import load_mcp_tools
    from langgraph.prebuilt import create_react_agent
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import AIMessage
except ImportError:
    logger.warning("LangChain packages not installed. Agent functionality will be limited.")

# Try to import Django settings, but handle case when running standalone
try:
    from django.conf import settings
    from wp_ai_api.apps.workspace.models import Workspace, UserSession
    DJANGO_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    DJANGO_AVAILABLE = False
    logger.info("Django not available, running in standalone mode")
except Exception:
    # This catches ImproperlyConfigured when Django is installed but not configured
    DJANGO_AVAILABLE = False
    logger.warning("Django improperly configured, running in standalone mode")

# Enable debug mode
DEBUG = os.environ.get("MCP_DEBUG", "false").lower() == "true"

def debug_print(*args, **kwargs):
    """Print only when debug mode is enabled."""
    if DEBUG:
        logger.debug(" ".join(str(arg) for arg in args))

# Custom encoder to print agent responses nicely if needed
class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, "content"):
            return {"type": o.__class__.__name__, "content": o.content}
        return super().default(o)


class WordPressMCPClient:
    """
    Client for interacting with WordPress MCP Server.
    Loads config from mcpConfig or a fallback file.
    """
    def __init__(self, anthropic_api_key=None, user=None):
        """
        Initialize the WordPress MCP Client.
        
        Args:
            anthropic_api_key: API key for Anthropic, if not provided will try to get from environment
            user: User instance if available from Django
        """
        # Get the API key using the centralized API key function
        try:
            from ..anthropic_handler import get_anthropic_api_key
            self.anthropic_api_key = get_anthropic_api_key(anthropic_api_key)
        except (ImportError, Exception) as e:
            # Fallback to getting the API key directly if function not available
            logger.warning(f"Could not import anthropic_handler.get_anthropic_api_key: {str(e)}")
            self.anthropic_api_key = self._get_api_key_fallback(anthropic_api_key)
        
        if not self.anthropic_api_key:
            # Try to create a default API key if not available
            if DJANGO_AVAILABLE:
                try:
                    from django.conf import settings
                    default_key = getattr(settings, "DEFAULT_ANTHROPIC_API_KEY", None)
                    if default_key:
                        logger.info("Using default API key from Django settings")
                        self.anthropic_api_key = default_key
                except Exception as e:
                    logger.warning(f"Could not retrieve default API key: {str(e)}")
            
            # If still no API key, raise error with helpful message
            if not self.anthropic_api_key:
                error_msg = (
                    "Anthropic API key is required. Set ANTHROPIC_API_KEY in settings, .env, or pass directly.\n"
                    "You can get an API key from https://console.anthropic.com/"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        self.exit_stack = None
        self.client = None
        self.agent = None
        self.available_tools = []
        self.sessions = {}
        self.user = user
        self.workspace = None
        self.workspace_group_name = None

    def _get_api_key_fallback(self, provided_key=None):
        """
        Fallback method to get Anthropic API key from various sources.
        Used if the import of the centralized function fails.
        
        Args:
            provided_key: API key provided to constructor
            
        Returns:
            API key from best available source
        """
        # First, try the provided key
        if provided_key:
            return provided_key
            
        # Next, try Django settings
        try:
            from django.conf import settings
            settings_key = getattr(settings, "ANTHROPIC_API_KEY", None)
            if settings_key:
                return settings_key
        except Exception:
            pass
            
        # Finally, try environment variable
        env_key = os.environ.get("ANTHROPIC_API_KEY")
        if env_key:
            return env_key
            
        # Try to find a config file
        try:
            # Look in likely config locations
            config_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "ai_providers.json"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "llm", "config", "ai_providers.json")
            ]
            
            for path in config_paths:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        config = json.load(f)
                        if "providers" in config and "anthropic" in config["providers"]:
                            return config["providers"]["anthropic"].get("api_key")
        except Exception as e:
            logger.warning(f"Error reading config file for API key: {str(e)}")
            
        # No key found
        return None

    @staticmethod
    def read_config_json():
        """Reads config from mcpConfig or fallback."""
        config_path = os.getenv("mcpConfig")
        if not config_path:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, "mcpConfig.json")
            logger.info(f"mcpConfig not set. Falling back to: {config_path}")
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read config file at '{config_path}': {e}")
            sys.exit(1)

    async def connect(self, workspace_id=None):
        """
        Connects to MCP servers and loads tools.
        If workspace_id is provided, also connects to that workspace.
        
        This method is kept for backward compatibility and now delegates to connect_to_workspace
        when a workspace_id is provided.
        """
        # If a workspace_id is provided, connect to it first
        if workspace_id:
            logger.info(f"Redirecting connect({workspace_id}) to connect_to_workspace()")
            return await self.connect_to_workspace(workspace_id)

        config = self.read_config_json()
        mcp_servers = config.get("mcpServers", {})
        if not mcp_servers:
            logger.warning("No MCP servers found in the configuration.")
            return

        self.exit_stack = AsyncExitStack()
        tools = []
        
        # Determine base directory dynamically
        try:
            # Try to get Django's base directory
            from django.conf import settings
            base_dir = getattr(settings, "BASE_DIR", None)
        except:
            base_dir = None
            
        # If Django base_dir isn't available, try to determine base path from script location
        if not base_dir:
            # Get path of the current file
            current_file = os.path.abspath(__file__)
            # Go up 5 levels to reach project root (... -> mcp -> workspace -> apps -> wp_ai_api -> django-backend)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))
            
        # Last resort, use current working directory
        if not os.path.exists(base_dir):
            base_dir = os.getcwd()
            
        logger.info(f"Using base directory: {base_dir}")

        # Detect Windows environment and use alternative setup for subprocess handling
        import platform
        is_windows = platform.system() == "Windows"
        
        # Special handling for Windows - use direct tools implementation
        if is_windows:
            logger.info(f"Windows environment detected. Python path: {sys.executable}")
            # On Windows, we'll use direct tool implementations rather than trying to use MCP servers
            try:
                from wp_ai_api.apps.workspace.mcp.direct_tools import get_direct_tools
                direct_tools = get_direct_tools()
                logger.info(f"Loaded {len(direct_tools)} direct tool implementations for Windows compatibility.")
                tools.extend(direct_tools)
                self.available_tools = tools
                
                # Initialize the agent with direct tools
                llm = ChatAnthropic(
                    model="claude-3-7-sonnet",
                    temperature=1,
                    anthropic_api_key=self.anthropic_api_key,
                    max_tokens=64000,
                    thinking={"type": "enabled", "budget_tokens": 1024}
                )
                self.agent = create_react_agent(llm, tools)
                
                # Associate with workspace if ID is provided
                if workspace_id and DJANGO_AVAILABLE:
                    await self.set_workspace(workspace_id)
                    
                return self.agent
            except Exception as e:
                logger.error(f"Error loading direct tools: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                # We'll continue with the normal approach if direct tools fail
        
        # If we're not on Windows or direct tools failed, proceed with normal MCP server approach
        try:
            for server_name, server_info in mcp_servers.items():
                logger.info(f"Connecting to MCP Server: {server_name}...")
                command = server_info["command"]
                args = server_info["args"]
                
                # Resolve relative paths to absolute paths
                resolved_args = []
                for arg in args:
                    # If it's an absolute path, use it as is
                    if os.path.isabs(arg):
                        resolved_arg = arg
                    else:
                        # Try to resolve the path relative to the base directory
                        potential_paths = [
                            os.path.join(base_dir, arg),  # Relative to base
                            os.path.join(base_dir, "django-backend", arg),  # Relative to django-backend
                        ]
                        
                        # Find the first path that exists
                        resolved_arg = next((p for p in potential_paths if os.path.exists(p)), arg)
                    
                    resolved_args.append(resolved_arg)
                    
                # Check if the server script exists
                if resolved_args and os.path.exists(resolved_args[0]):
                    logger.info(f"Server script exists: {resolved_args[0]}")
                else:
                    logger.error(f"Server script not found: {resolved_args[0] if resolved_args else 'No args provided'}")
                    continue

                server_params = StdioServerParameters(
                    command=command,
                    args=resolved_args
                )
                
                try:
                    read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
                    session = await self.exit_stack.enter_async_context(ClientSession(read, write))
                    await session.initialize()
                    server_tools = await load_mcp_tools(session)
                    for tool in server_tools:
                        logger.debug(f"Loaded tool: {tool.name}")
                        tools.append(tool)
                    logger.info(f"{len(server_tools)} tools loaded from {server_name}.")
                    if not self.client:
                        self.client = session  # Use the first session by default
                    self.sessions[server_name] = session
                except Exception as e:
                    logger.error(f"Failed to connect to server {server_name}: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())

            # Even if no tools were loaded from MCP, still initialize the agent
            self.available_tools = tools
            
            if not tools:
                logger.warning("No tools were loaded from any server. The agent will have limited functionality.")
            
        except Exception as e:
            logger.error(f"Exception during connect: {e}")
            import traceback
            logger.error(traceback.format_exc())

        # Initialize the agent even if no tools were loaded
        llm = ChatAnthropic(
            model="claude-3-7-sonnet",
            temperature=1,
            anthropic_api_key=self.anthropic_api_key,
            max_tokens=64000,
            thinking={"type": "enabled", "budget_tokens": 1024}
        )
        self.available_tools = tools
        self.agent = create_react_agent(llm, self.available_tools)
        
        # Associate with workspace if ID is provided
        if workspace_id and DJANGO_AVAILABLE:
            await self.set_workspace(workspace_id)
            
        return self.agent
    
    async def set_workspace(self, workspace_id):
        """Associate the client with a workspace."""
        if not DJANGO_AVAILABLE:
            logger.warning("Django is not available, cannot associate with workspace")
            return False
            
        try:
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def get_workspace(workspace_id):
                try:
                    return Workspace.objects.get(id=workspace_id)
                except Workspace.DoesNotExist:
                    return None
            
            self.workspace = await get_workspace(workspace_id)
            if self.workspace:
                self.workspace_group_name = f"workspace_{workspace_id}"
                return True
            return False
        except Exception as e:
            logger.error(f"Error associating with workspace: {e}")
            return False
    
    async def create_workspace(self, name, user=None):
        """Create a new workspace and associate it with a user."""
        if not DJANGO_AVAILABLE:
            logger.warning("Django is not available, cannot create workspace")
            return None
            
        try:
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def create_workspace_in_db(name, user):
                from wp_ai_api.apps.workspace.models import Workspace
                workspace = Workspace.objects.create(name=name, owner=user or self.user)
                return workspace
            
            user_to_use = user or self.user
            if not user_to_use:
                logger.warning("No user provided for workspace creation")
                return None
                
            workspace = await create_workspace_in_db(name, user_to_use)
            self.workspace = workspace
            self.workspace_group_name = f"workspace_{workspace.id}"
            return workspace
        except Exception as e:
            logger.error(f"Error creating workspace: {e}")
            return None
    
    async def get_workspace_history(self, workspace_id=None):
        """Get the message history for a workspace."""
        if not DJANGO_AVAILABLE:
            logger.warning("Django is not available, cannot get workspace history")
            return []
            
        try:
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def get_messages(workspace_id):
                from wp_ai_api.apps.workspace.models import Message
                return list(Message.objects.filter(
                    workspace_id=workspace_id or self.workspace.id
                ).order_by('timestamp').values())
            
            if not workspace_id and not self.workspace:
                logger.warning("No workspace ID provided and no workspace associated")
                return []
                
            return await get_messages(workspace_id)
        except Exception as e:
            logger.error(f"Error getting workspace history: {e}")
            return []
    
    async def send_to_workspace_socket(self, message_type, **data):
        """
        Helper method to send messages to the workspace WebSocket group.
        
        Args:
            message_type: The type of message to send
            **data: Additional data to include in the message
        
        Returns:
            True if message was sent, False otherwise
        """
        if not DJANGO_AVAILABLE or not self.workspace_group_name:
            return False
        
        try:
            from channels.layers import get_channel_layer
            
            # Get the channel layer
            channel_layer = get_channel_layer()
            
            # Prepare the message data
            message_data = {
                'type': message_type,
                **data
            }
            
            # Log this message to the response log file
            try:
                from django.conf import settings
                import os
                import json
                from datetime import datetime
                
                log_dir = os.path.join(settings.BASE_DIR, 'logs')
                os.makedirs(log_dir, exist_ok=True)
                response_log_file = os.path.join(log_dir, 'websocket_responses.log')
                
                # Create log entry
                response_log = f"[{datetime.now().isoformat()}] MCP CLIENT RESPONSE: workspace={self.workspace_group_name}, data={json.dumps(message_data)}"
                
                with open(response_log_file, 'a', encoding='utf-8') as f:
                    f.write(response_log + '\n')
                
            except Exception as e:
                logger.error(f"Failed to write MCP message to log file: {str(e)}")
            
            # Send to the group
            await channel_layer.group_send(
                self.workspace_group_name,
                message_data
            )
            return True
        except Exception as e:
            logger.error(f"Error sending to workspace socket: {str(e)}")
            return False

    async def send_tool_result_to_socket(self, tool_name, result):
        """Send a tool result to the workspace socket."""
        return await self.send_to_workspace_socket(
            'tool_result',
            tool_name=tool_name,
            result=result
        )
    
    async def disconnect(self):
        """Disconnect from all MCP servers."""
        if self.exit_stack:
            await self.exit_stack.aclose()
            self.exit_stack = None
            self.client = None
            self.available_tools = []
            self.sessions = {}
            self.agent = None
            return "Disconnected from MCP server(s)"
        return "Not connected to any MCP server"
        
    async def process_query(self, query, mode=None, streaming_callback=None, workspace_id=None, message_id=None):
        """
        Process a user query and return the AI response.
        
        This method handles the complete workflow:
        1. Connects to workspace if needed
        2. Gets proper WordPress prompt
        3. Invokes Claude 3.7 with proper tools
        4. Streams results to client via WebSockets
        5. Handles tool calls when needed
        
        Args:
            query: The user query to process
            mode: Ignored parameter (kept for backward compatibility)
            streaming_callback: Optional callback for streaming updates
            workspace_id: Optional workspace ID to use
            message_id: Optional message ID for tracking
            
        Returns:
            The AI response as a string
        """
        start_time = time.time()
        
        # Connect to workspace if needed
        if workspace_id:
            workspace_id_str = str(workspace_id)
            # If we're not connected to a workspace or connected to a different one, connect
            if not self.workspace or str(self.workspace.id) != workspace_id_str:
                logger.info(f"Connecting to workspace {workspace_id_str} from process_query")
                await self.connect_to_workspace(workspace_id_str)
        
        # Set workspace ID from current workspace if not explicitly provided
        if not workspace_id and self.workspace:
            workspace_id = str(self.workspace.id)
        
        # Set group name directly if we have a workspace_id but no group name yet
        if workspace_id and not self.workspace_group_name:
            self.workspace_group_name = f"workspace_{workspace_id}"
            logger.info(f"Setting workspace_group_name to {self.workspace_group_name}")
        
        # Import the proper prompt
        from ..prompts import get_enhanced_wordpress_prompt
        
        # Get system prompt for WordPress handling
        formatted_prompt = get_enhanced_wordpress_prompt()
        
        # Add context about available tools
        formatted_prompt += "\n\nYou have access to tools for WordPress development, including:\n"
        formatted_prompt += "- Creating files\n"
        formatted_prompt += "- Reading and modifying existing files\n"
        formatted_prompt += "- Running commands including WordPress CLI\n"
        formatted_prompt += "- Creating plugins and themes"
        
        # Generate a message ID for tracking responses if not provided
        if not message_id:
            message_id = str(uuid.uuid4())
        
        try:
            # If we have a workspace, set up streaming through the channel layer
            if workspace_id:
                # First, notify clients that thinking is starting
                await send_to_client(
                    workspace_id,
                    'thinking_update',
                    message_id=message_id,
                    thinking="Starting to process your query..."
                )
                
                # Create assistant message in database
                assistant_message = await self._save_message_to_workspace(
                    "Thinking...",
                    role="assistant"
                )
                
                # Get message ID for tracking
                message_id_str = str(assistant_message.id) if assistant_message and hasattr(assistant_message, 'id') else message_id
                
                # Get anthropic handler - this leverages the centralized handler
                from ..anthropic_handler import get_anthropic_handler
                
                # Create socket handler for this request
                socket_handler = create_socket_handler(workspace_id, message_id_str)
                
                # Get tools from workspace using the centralized function
                from ..tools import get_all_tools
                tool_handlers = get_all_tools(self.workspace)
                
                # Verify that we have tool handlers and log them
                if tool_handlers:
                    logger.info(f"Loaded {len(tool_handlers)} tool handlers: {', '.join(tool_handlers.keys())}")
                else:
                    logger.warning("No tool handlers were loaded!")
                
                # Initialize Anthropic handler with socket handler
                anthropic = get_anthropic_handler(socket_handler=socket_handler, api_key=self.anthropic_api_key)
                
                # Format messages for Anthropic
                formatted_messages = [
                    {"role": "system", "content": formatted_prompt}
                ]
                
                # Add user message
                formatted_messages.append({"role": "user", "content": query})
                
                # Log start of LLM processing with tools
                logger.info(f"Starting process_with_tools with {len(tool_handlers) if tool_handlers else 0} tools and thinking enabled")
                
                # Process with tools and thinking enabled using tracking for cancellation support
                try:
                    collected_response = await run_with_tracking(
                        workspace_id,
                        self._process_with_anthropic(
                            anthropic,
                            formatted_messages,
                            tool_handlers
                        ),
                        message_id=message_id_str
                    )
                    
                    # Log completion
                    logger.info(f"Completed LLM processing, response length: {len(collected_response)}")
                    
                    # Update message with final response
                    await self._save_message_to_workspace(collected_response, role="assistant", message_id=message_id_str)
                    
                    # Send a new_message event with the complete response for client display
                    await send_to_client(
                        workspace_id,
                        'new_message',
                        message_id=message_id_str,
                        sender='assistant',
                        text=collected_response,
                        timestamp=datetime.now().isoformat()
                    )
                    
                    # Send completion status
                    await send_to_client(
                        workspace_id,
                        'message_status',
                        message_id=message_id_str,
                        status='complete'
                    )
                    
                    # Return the collected response
                    return collected_response
                    
                except asyncio.CancelledError:
                    logger.info(f"Process was cancelled for workspace {workspace_id}, message {message_id_str}")
                    # Cancellation is already handled by run_with_tracking
                    raise
                    
                except Exception as e:
                    error_message = f"Error in MCP client process_query: {str(e)}"
                    logger.error(error_message)
                    
                    # Send error message to client
                    await send_to_client(
                        workspace_id,
                        'error',
                        message=error_message,
                        message_id=message_id_str
                    )
                    
                    # Re-raise the exception
                    raise
                
            else:
                # No workspace, use the agent directly - simplify this approach
                if not self.agent:
                    await self.connect()
                
                # Initialize messages for direct Anthropic call if agent isn't available
                from ..anthropic_handler import get_anthropic_handler
                
                # Get system prompt for WordPress handling
                formatted_messages = [
                    {"role": "system", "content": formatted_prompt}
                ]
                
                # Add user message
                formatted_messages.append({"role": "user", "content": query})
                
                try:
                    # Get Anthropic handler 
                    anthropic = get_anthropic_handler()
                    
                    # Process with tools and thinking enabled
                    collected_response = ""
                    async for chunk in anthropic.process_with_tools(
                        messages=formatted_messages,
                        thinking_enabled=True,
                        thinking_budget=1024,
                        max_tokens=64000
                    ):
                        # Track text content for final response
                        if chunk.get("type") == "text":
                            collected_response += chunk.get("content", "")
                            
                        # If streaming callback is provided, use it
                        if streaming_callback:
                            await streaming_callback(chunk)
                    
                    return collected_response
                
                except Exception as e:
                    logger.error(f"Error with direct Anthropic call: {str(e)}")
                    # Fallback to agent if available
                    if self.agent:
                        result = await self.agent.ainvoke({"input": query})
                        return result.get("output", "I couldn't process your request properly.")
                    return f"Error: {str(e)}"
            
        except Exception as e:
            error_message = f"Error processing query: {str(e)}"
            logger.error(error_message)
            
            # Send error to websocket if available
            if workspace_id:
                try:
                    await send_to_client(
                        workspace_id,
                        'error',
                        message=error_message,
                        message_id=message_id
                    )
                except Exception as socket_error:
                    logger.error(f"Error sending to socket: {str(socket_error)}")
                
            return f"Error: {str(e)}"
        finally:
            end_time = time.time()
            logger.info(f"Query processed in {end_time - start_time:.2f} seconds")
    
    async def _process_with_anthropic(self, anthropic, messages, tool_handlers):
        """Helper method to process a request with Anthropic and collect the response."""
        collected_response = ""
        async for chunk in anthropic.process_with_tools(
            messages=messages,
            tool_handlers=tool_handlers,
            thinking_enabled=True,
            thinking_budget=1024,
            max_tokens=64000
        ):
            # Track text content for final response
            if chunk.get("type") == "text":
                collected_response += chunk.get("content", "")
                
        return collected_response

    async def _save_message_to_workspace(self, content, role, message_id=None):
        """Save a message to the workspace history."""
        if not DJANGO_AVAILABLE or not self.workspace:
            # Return a dummy message with an ID for consistency
            from uuid import uuid4
            class DummyMessage:
                def __init__(self):
                    self.id = uuid4()
            return DummyMessage()
            
        try:
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def create_message():
                from wp_ai_api.apps.workspace.models import Message
                return Message.objects.create(
                    workspace=self.workspace,
                    role=role,
                    content=content
                )
            
            message = await create_message()
            
            # Notify clients about the new message
            if self.workspace_group_name:
                from channels.layers import get_channel_layer
                
                channel_layer = get_channel_layer()
                await channel_layer.group_send(
                    self.workspace_group_name,
                    {
                        'type': 'message_update',
                        'role': role,
                        'content': content
                    }
                )
            
            if message_id:
                await channel_layer.group_send(
                    self.workspace_group_name,
                    {
                        'type': 'message_status',
                        'message_id': message_id,
                        'status': 'complete'
                    }
                )
            
            return message
        except Exception as e:
            logger.error(f"Error saving message to workspace: {e}")
            # Return a dummy message with an ID even in case of error
            from uuid import uuid4
            class DummyMessage:
                def __init__(self):
                    self.id = uuid4()
            return DummyMessage()

    async def run_interactive_loop(self):
        """Start an interactive CLI loop for queries using the loaded agent and tools."""
        if not self.agent:
            await self.connect()
        logger.info("\n🚀 WordPress MCP Client Ready! Type 'quit' to exit.")
        while True:
            query = input("\nQuery: ").strip()
            if query.lower() == "quit":
                await self.disconnect()
                break
                
            mode = "plugin"
            if query.lower().startswith("theme:"):
                mode = "theme"
                query = query[6:].strip()
                
            logger.info(f"\nProcessing WordPress {mode} query...")
            response = await self.process_query(query, mode)
            logger.info("\nResponse:")
            logger.info(response)

    async def execute_tool(self, tool_name, params, workspace_id=None):
        """Execute a tool and send the result to the workspace socket."""
        if not self.agent:
            await self.connect()
            
        if workspace_id and not self.workspace:
            await self.set_workspace(workspace_id)
            
        try:
            # Find the tool
            tool = next((t for t in self.available_tools if t.name == tool_name), None)
            if not tool:
                result = {"error": f"Tool '{tool_name}' not found"}
                if self.workspace_group_name:
                    await self.send_tool_result_to_socket(tool_name, result)
                return result
                
            # Execute the tool
            result = await tool.ainvoke(**params)
            
            # Send result to socket if we have a workspace
            if self.workspace_group_name:
                await self.send_tool_result_to_socket(tool_name, result)
                
            return result
        except Exception as e:
            error_result = {"error": f"Error executing tool: {str(e)}"}
            if self.workspace_group_name:
                await self.send_tool_result_to_socket(tool_name, error_result)
            return error_result

    async def connect_to_workspace(self, workspace_id):
        """
        Connect to an existing workspace by ID.
        
        Args:
            workspace_id: The UUID of the workspace to connect to
        
        Returns:
            True if connected successfully, False otherwise
        """
        if not workspace_id:
            logger.warning("No workspace ID provided")
            return False
        
        try:
            # If we're already connected to this workspace, just return
            if hasattr(self, 'workspace') and self.workspace and str(self.workspace.id) == str(workspace_id):
                logger.debug(f"Already connected to workspace {workspace_id}")
                return True
            
            # Check if Django is available
            if not DJANGO_AVAILABLE:
                logger.warning("Django not available, cannot connect to workspace")
                return False
            
            # Import async tools
            from channels.db import database_sync_to_async
            
            @database_sync_to_async
            def get_workspace():
                try:
                    from wp_ai_api.apps.workspace.models import Workspace
                    return Workspace.objects.get(id=workspace_id)
                except Workspace.DoesNotExist:
                    logger.warning(f"Workspace {workspace_id} not found")
                    return None
                
            # Get the workspace
            self.workspace = await get_workspace()
            
            if not self.workspace:
                return False
            
            # Set up the group name for WebSocket communications
            self.workspace_group_name = f"workspace_{workspace_id}"
            
            # Set up the agent if needed
            if not self.agent:
                await self.connect()
                
            logger.info(f"Successfully connected to workspace {workspace_id}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to workspace: {str(e)}")
            return False



