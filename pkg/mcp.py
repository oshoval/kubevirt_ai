"""
Model Context Protocol (MCP) client classes for KubeVirt AI agent.
"""

import os
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from rich.console import Console

console = Console()


class MCPClient:
    """Official MCP client using the mcp package."""

    def __init__(self, mcp_config: Dict[str, Any]):
        self.name = mcp_config.get("name", "unknown")
        self.command = mcp_config.get("command", "")
        self.args = mcp_config.get("args", [])
        self.cwd = mcp_config.get("cwd", ".")
        self.session = None
        self.exit_stack = None
        self.tools = []

    async def connect(self):
        """Connect to the MCP server."""
        try:
            self.exit_stack = AsyncExitStack()

            # Create server parameters
            server_params = StdioServerParameters(
                command=self.command,
                args=self.args,
                env=os.environ.copy(),  # Inherit parent environment variables
            )

            # Connect to server
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            stdio, write = stdio_transport

            # Create session
            self.session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))

            # Initialize session
            await self.session.initialize()

            # Get available tools
            response = await self.session.list_tools()
            self.tools = response.tools

            console.print(f"[green]✓ Connected to MCP server '{self.name}' with {len(self.tools)} tools[/green]")
            return True

        except Exception as e:
            console.print(f"[red]✗ Failed to connect to MCP server '{self.name}': {e}[/red]")
            if self.exit_stack:
                await self.exit_stack.aclose()
            return False

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> str:
        """Call an MCP tool and return the result."""
        if not self.session:
            raise Exception("MCP client not connected")

        try:
            result = await self.session.call_tool(tool_name, arguments or {})
            if hasattr(result, "content") and result.content:
                return result.content[0].text if result.content else "No content"
            return str(result)
        except Exception as e:
            raise Exception(f"Failed to call tool '{tool_name}': {e}")

    def get_tools_for_anthropic(self) -> List[Dict[str, Any]]:
        """Get tools in Anthropic SDK format."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in self.tools
        ]

    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.exit_stack:
            await self.exit_stack.aclose()


class MCPRegistry:
    """Registry for Model Context Protocol (MCP) servers."""

    def __init__(self):
        self.mcps: List[Dict[str, Any]] = []
        self.clients: Dict[str, MCPClient] = {}
        self.connected_clients: Dict[str, MCPClient] = {}

    def add_mcp(self, name: str, config: Dict[str, Any]):
        """Add an MCP server configuration and create a client."""
        mcp_entry = {"name": name, "config": config}
        self.mcps.append(mcp_entry)

        # Create MCP client
        client_config = config.copy()
        client_config["name"] = name
        self.clients[name] = MCPClient(client_config)

    async def connect_all(self):
        """Connect to all MCP servers."""
        for name, client in self.clients.items():
            if await client.connect():
                self.connected_clients[name] = client

    def list_mcps(self) -> List[Dict[str, Any]]:
        """List all registered MCP servers."""
        return self.mcps

    def get_mcp(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific MCP server by name."""
        for mcp in self.mcps:
            if mcp["name"] == name:
                return mcp
        return None

    def get_client(self, name: str) -> Optional[MCPClient]:
        """Get a connected MCP client by name."""
        return self.connected_clients.get(name)

    def get_all_tools_for_anthropic(self) -> List[Dict[str, Any]]:
        """Get all tools from all connected clients in Anthropic format."""
        all_tools = []
        for client in self.connected_clients.values():
            all_tools.extend(client.get_tools_for_anthropic())

        # Add built-in shell execution tools
        all_tools.extend(
            [
                {
                    "name": "execute_shell_command",
                    "description": (
                        "Execute shell commands like kubectl, virtctl, or any command. "
                        "Use MCP tools to detect and set KUBECONFIG automatically."
                    ),
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": (
                                    "The shell command to execute, including any environment variables needed"
                                ),
                            }
                        },
                        "required": ["command"],
                    },
                }
            ]
        )
        return all_tools

    async def disconnect_all(self):
        """Disconnect from all MCP servers."""
        for client in self.connected_clients.values():
            await client.disconnect()
        self.connected_clients.clear()
