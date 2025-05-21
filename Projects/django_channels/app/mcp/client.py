import os
import sys
import json
from contextlib import AsyncExitStack

from django.conf import settings

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage


DEBUG = os.environ.get("MCP_DEBUG", "false").lower() == "true"

def debug_print(*args, **kwargs):
    if DEBUG:
        print("[DEBUG]", *args, **kwargs)


PROMPT_TEMPLATE = """
You are an intelligent expense tracker and database assistant.

Your job is to understand the user's query and invoke the appropriate database tool function using structured tool calls.

You have access to the following tools:

1. `insert_user(name: str, email: str)`  
   → Use this when the user wants to create a new user account or registers with a name and email.

2. `insert_category_table(use_id: str, table_category: str, table: dict)`  
   → Use this when the user shares a structured table (with rows, columns, notes) for a specific category, like transport, food, or health logs.

Instructions:
- Always extract structured data (user ID, category, table, name, email, etc.) from the query.
- Use tool calls only when you have enough information.
- If information is missing, ask for clarification.
- Do not reply with natural sentences unless clarification is needed.
- Format your response as a JSON tool invocation if possible.

Example 1 (new user):
User: "create user named Mehedi with email mehedi@gmail.com"
→ Tool: `insert_user(name="Mehedi", email="mehedi@gmail.com")`

Example 2 (structured category table):
User: "insert this into table for user 1, category transport: columns [Date, Amount, Vendor], rows [...], note: transport logs"
→ Tool: `insert_category_table(use_id="1", table_category="transport", table={...})`
"""


class ExpenseMCPClient:

    def __init__(self, anthropic_api_key=None):
        self.anthropic_api_key = anthropic_api_key or getattr(
            settings, "ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY")
        )
        if not self.anthropic_api_key:
            raise ValueError("Anthropic API key is required.")
        self.exit_stack = None
        self.client = None
        self.agent = None
        self.available_tools = []
        self.sessions = {}

    @staticmethod
    def read_config_json():
        config_path = os.getenv("mcpConfig")
        if not config_path:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, "mcpConfig.json")
            print(f"[INFO] mcpConfig not set. Falling back to: {config_path}")
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Failed to read config file: {e}")
            sys.exit(1)

    async def connect(self):
        config = self.read_config_json()
        mcp_servers = config.get("mcpServers", {})
        if not mcp_servers:
            print("❌ No MCP servers found in the configuration.")
            return

        self.exit_stack = AsyncExitStack()
        tools = []

        try:
            for server_name, server_info in mcp_servers.items():
                print(f"\n🔗 Connecting to MCP Server: {server_name}...")
                server_params = StdioServerParameters(
                    command=server_info["command"],
                    args=server_info["args"]
                )
                try:
                    read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
                    session = await self.exit_stack.enter_async_context(ClientSession(read, write))
                    await session.initialize()
                    server_tools = await load_mcp_tools(session)
                    for tool in server_tools:
                        print(f"🔧 Loaded tool: {tool.name}")
                        tools.append(tool)
                    print(f"✅ Loaded {len(server_tools)} tools from {server_name}")
                    if not self.client:
                        self.client = session
                    self.sessions[server_name] = session
                except Exception as e:
                    print(f"❌ Failed to connect to server '{server_name}': {e}")

            if not tools:
                print("❌ No tools loaded from any server.")
                return

            self.available_tools = tools

        except Exception as e:
            print(f"❌ Exception during MCP connection: {e}")
            return

        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20240620",
            temperature=0,
            anthropic_api_key=self.anthropic_api_key
        )

        self.agent = create_react_agent(llm, self.available_tools)
        return self.agent

    async def disconnect(self):
        if self.exit_stack:
            await self.exit_stack.aclose()
            self.exit_stack = None
            self.client = None
            self.available_tools = []
            self.sessions = {}
            self.agent = None
            return "✅ Disconnected"
        return "ℹ️ Not connected"

    async def process_query(self, query):
        if not self.agent:
            await self.connect()
        if not self.agent:
            return "❌ Agent not initialized"

        full_prompt = f"""{PROMPT_TEMPLATE}
USER QUERY: {query}
"""

        try:
            response = await self.agent.ainvoke({"messages": full_prompt}, {"recursion_limit": 100})

            if isinstance(response, dict) and "tool_name" in response and "args" in response:
                print(f"🛠️ Tool called: {response['tool_name']}")
                print(f"🧾 Tool arguments: {json.dumps(response['args'], indent=2)}")
                return response

            elif isinstance(response, AIMessage):
                return response.content

            return str(response)

        except Exception as e:
            error_msg = f"❌ Error processing query: {str(e)}"
            print(error_msg)
            return error_msg

    async def run_interactive_loop(self):
        if not self.agent:
            await self.connect()
        print("\n🚀 Expense MCP Client Ready! Type 'quit' to exit.")
        while True:
            query = input("\nQuery: ").strip()
            if query.lower() in {"quit", "exit"}:
                break
            print("\n⚙️ Processing...")
            response = await self.process_query(query)
            print("\n📤 Response:")
            print(response)
