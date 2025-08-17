#!/usr/bin/env python3
"""
Main application for KubeVirt AI agent using Anthropic SDK with Vertex AI authentication.
"""

import argparse
import asyncio
import json
import os
import re
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import AsyncExitStack

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from login import get_anthropic_client, AnthropicAuthManager

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
                env=os.environ.copy()  # Inherit parent environment variables
            )
            
            # Connect to server
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write = stdio_transport
            
            # Create session
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )
            
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
            if hasattr(result, 'content') and result.content:
                return result.content[0].text if result.content else "No content"
            return str(result)
        except Exception as e:
            raise Exception(f"Failed to call tool '{tool_name}': {e}")
    
    def get_tools_for_anthropic(self) -> List[Dict[str, Any]]:
        """Get tools in Anthropic SDK format."""
        return [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in self.tools]
    
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
        mcp_entry = {
            "name": name,
            "config": config
        }
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
        all_tools.extend([
            {
                "name": "execute_shell_command",
                "description": "Execute shell commands like kubectl, virtctl, or any command. Use MCP tools to detect and set KUBECONFIG automatically.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute, including any environment variables needed"
                        }
                    },
                    "required": ["command"]
                }
            }
        ])
        return all_tools
    
    async def disconnect_all(self):
        """Disconnect from all MCP servers."""
        for client in self.connected_clients.values():
            await client.disconnect()
        self.connected_clients.clear()


class KubeVirtAIAgent:
    """Main AI agent for KubeVirt operations using Anthropic Claude."""
    
    def __init__(self, auth_method: str = "vertex_ai"):
        self.auth_method = auth_method
        self.client = None
        self.mcp_registry = MCPRegistry()
        self.agent_prompt = self._load_agent_prompt()
        
        # Initialize authentication
        self._authenticate()
        
        # Initialize MCP servers
        self._initialize_mcps()
    
    def _initialize_mcps(self):
        """Initialize MCP servers from config/mcps.json configuration file."""
        mcps_config_path = Path(__file__).parent / "config" / "mcps.json"
        
        try:
            if not mcps_config_path.exists():
                console.print(f"[yellow]Warning: config/mcps.json not found at {mcps_config_path}[/yellow]")
                console.print("[yellow]No MCP servers will be loaded[/yellow]")
                return
            
            with open(mcps_config_path, 'r') as f:
                mcps_config = json.load(f)
            
            mcp_servers = mcps_config.get("mcpServers", {})
            if not mcp_servers:
                console.print("[yellow]No MCP servers found in mcps.json[/yellow]")
                return
            
            for name, config in mcp_servers.items():
                self.add_mcp(name, config)
                
            console.print(f"[green]Loaded {len(mcp_servers)} MCP server(s) from mcps.json[/green]")
            
        except json.JSONDecodeError as e:
            console.print(f"[red]Error parsing mcps.json: {e}[/red]")
            console.print("[yellow]No MCP servers will be loaded[/yellow]")
        except Exception as e:
            console.print(f"[red]Error loading mcps.json: {e}[/red]")
            console.print("[yellow]No MCP servers will be loaded[/yellow]")
    
    def _authenticate(self):
        """Authenticate with Anthropic API using specified method."""
        try:
            console.print(f"[blue]Authenticating with method: {self.auth_method}[/blue]")
            self.client = get_anthropic_client(self.auth_method)
            console.print("[green]Successfully authenticated with Anthropic API[/green]")
        except Exception as e:
            console.print(f"[red]Authentication failed: {e}[/red]")
            raise
    
    def _load_agent_prompt(self) -> str:
        """Load the agent prompt from the agents folder."""
        prompt_path = Path(__file__).parent / "agents" / "kubevirt-ai-agent-prompt.txt"
        try:
            with open(prompt_path, 'r') as f:
                prompt = f.read()
            console.print(f"[green]Loaded agent prompt from: {prompt_path}[/green]")
            return prompt
        except Exception as e:
            console.print(f"[red]Failed to load agent prompt: {e}[/red]")
            return "You are a helpful KubeVirt assistant."
    
    def add_mcp(self, name: str, config: Dict[str, Any]):
        """Add an MCP server to the registry."""
        self.mcp_registry.add_mcp(name, config)
        console.print(f"[green]Added MCP server: {name}[/green]")
    
    def list_mcps(self) -> List[Dict[str, Any]]:
        """List all registered MCP servers."""
        return self.mcp_registry.list_mcps()
    
    async def connect_mcps(self):
        """Connect to all MCP servers."""
        await self.mcp_registry.connect_all()
    
    async def call_mcp_tool(self, mcp_name: str, tool_name: str, arguments: Dict[str, Any] = None) -> str:
        """Call an MCP tool and return the result."""
        client = self.mcp_registry.get_client(mcp_name)
        if not client:
            raise ValueError(f"MCP client '{mcp_name}' not found")
        
        try:
            result = await client.call_tool(tool_name, arguments)
            console.print(f"[green]✓ MCP tool '{tool_name}' executed successfully[/green]")
            return result
        except Exception as e:
            console.print(f"[red]✗ MCP tool '{tool_name}' failed: {e}[/red]")
            raise
    
    async def execute_shell_command(self, command: str) -> str:
        """Execute a shell command and return the result."""
        try:
            console.print(f"[blue]Executing: {command}[/blue]")
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                console.print(f"[green]✓ Command executed successfully[/green]")
                return result.stdout.strip()
            else:
                error_output = result.stderr.strip()
                # Escape Rich markup in error output to prevent parsing errors
                safe_error = error_output.replace("[", "\\[").replace("]", "\\]")
                error_msg = f"✗ Command failed (exit code {result.returncode}): {safe_error}"
                console.print(f"[red]{error_msg}[/red]")
                return f"✗ Command failed (exit code {result.returncode}): {error_output}"
                
        except subprocess.TimeoutExpired:
            error_msg = "Command timed out after 30 seconds"
            console.print(f"[red]✗ {error_msg}[/red]")
            return error_msg
        except Exception as e:
            error_msg = f"Failed to execute command: {e}"
            console.print(f"[red]✗ {error_msg}[/red]")
            return error_msg
    
    async def process_query(self, user_query: str, filename: str = None) -> str:
        """
        Process a user query with the AI agent using clean conversation flow.
        
        Args:
            user_query: The user's query or request
            filename: Optional path to a file for additional context
        
        Returns:
            AI agent response
        """
        try:
            console.print(f"[blue]Processing query: {user_query}[/blue]")
            
            # Ensure MCP servers are connected
            await self.connect_mcps()
            
            # Build the prompt with query and optional file context
            content = self._build_agent_prompt(user_query, filename)
            
            # Get available MCP tools in Anthropic format
            available_tools = self.mcp_registry.get_all_tools_for_anthropic()
            
            # Initialize conversation
            messages = [{"role": "user", "content": content}]
            model = self._get_model_name()
            
            # Continue conversation until model decides it's complete (official Anthropic pattern)
            conversation_turn = 0
            max_safety_turns = 50  # Safety valve to prevent infinite loops
            
            while conversation_turn < max_safety_turns:
                conversation_turn += 1
                console.print(f"[blue]Conversation turn {conversation_turn}[/blue]")
                
                # Make API call
                response = self.client.messages.create(
                    model=model,
                    max_tokens=8000,
                    messages=messages,
                    system=self.agent_prompt,
                    tools=available_tools if available_tools else None
                )
                
                # Check if Claude wants to use tools
                if response.stop_reason == "tool_use":
                    # Add assistant's response to conversation
                    messages.append({"role": "assistant", "content": response.content})
                    
                    # Execute all tool calls
                    tool_calls = self._extract_tool_calls(response)
                    console.print(f"[blue]Executing {len(tool_calls)} tool call(s)[/blue]")
                    
                    for tool_call in tool_calls:
                        tool_result = await self._execute_tool_call(tool_call)
                        
                        # Add tool result to conversation
                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": tool_call.id,
                                "content": tool_result
                            }]
                        })
                    
                    # Continue conversation with tool results
                    continue

                # No tool use - mission complete
                console.print("[green]✓ Mission complete - Claude finished without requesting tools[/green]")
                return self._extract_text_content(response)
            
            # Safety valve reached
            console.print(f"[yellow]Safety limit reached ({max_safety_turns} turns), returning last response[/yellow]")
            return self._extract_text_content(response)
            
        except Exception as e:
            # Escape Rich markup in error messages
            safe_error = str(e).replace("[", "\\[").replace("]", "\\]")
            console.print(f"[red]Error processing query: {safe_error}[/red]")
            raise

    def _extract_tool_calls(self, response):
        """Extract tool calls from response content."""
        tool_calls = []
        for content_block in response.content:
            if hasattr(content_block, 'type') and content_block.type == 'tool_use':
                tool_calls.append(content_block)
        return tool_calls

    def _extract_text_content(self, response):
        """Extract text content from response."""
        text_content = ""
        for content_block in response.content:
            if hasattr(content_block, 'type') and content_block.type == 'text':
                text_content += content_block.text
        return text_content

    async def _execute_tool_call(self, tool_call):
        """Execute a single tool call and return the result."""
        tool_name = tool_call.name
        tool_input = tool_call.input
        console.print(f"[blue]Executing tool: {tool_name}[/blue]")

        # Check if it's a built-in shell command tool
        if tool_name == "execute_shell_command":
            command = tool_input.get("command", "")
            tool_result = await self.execute_shell_command(command)
        else:
            # Find which MCP client has this tool
            tool_result = None
            for client_name, client in self.mcp_registry.connected_clients.items():
                client_tools = [t.name for t in client.tools]
                if tool_name in client_tools:
                    tool_result = await self.call_mcp_tool(client_name, tool_name, tool_input)
                    break

            if tool_result is None:
                tool_result = f"Tool '{tool_name}' not found"
                console.print(f"[red]✗ {tool_result}[/red]")

        console.print(f"[green]✓ Tool {tool_name} executed successfully[/green]")
        return tool_result
    
    def _get_model_name(self, use_fast_model: bool = False) -> str:
        """Get the appropriate model name based on client type and environment variables."""
        # Check if we're using Vertex AI (AnthropicVertex client)
        if hasattr(self.client, 'project_id'):
            # Vertex AI format - use company suggested models
            if use_fast_model:
                return os.environ.get('ANTHROPIC_SMALL_FAST_MODEL', 'claude-3-5-haiku@20241022')
            else:
                return os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-4@20250514')
        else:
            # Standard Anthropic API format - convert @ to - for API format
            if use_fast_model:
                model = os.environ.get('ANTHROPIC_SMALL_FAST_MODEL', 'claude-3-5-haiku-20241022')
            else:
                model = os.environ.get('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
            return model.replace('@', '-') if '@' in model else model
    
    def _build_agent_prompt(self, user_query: str, filename: str = None) -> str:
        """Build the prompt for the autonomous AI agent."""
        # Build the command that was used to run this agent
        agent_command = f"python main.py --query '{user_query}'"
        if filename:
            agent_command += f" --file '{filename}'"

        prompt_parts = [
            f"User Request: {user_query}",
            f"Agent Command: {agent_command}",
            "",
            "Available MCP Tools:"
        ]
        
        # List available MCP servers and their capabilities
        mcps = self.list_mcps()
        if mcps:
            for mcp in mcps:
                config = mcp['config']
                prompt_parts.append(f"- {mcp['name']}: {config.get('description', 'MCP server')}")
                prompt_parts.append(f"  Command: {config.get('command', 'N/A')}")
                prompt_parts.append(f"  Working Directory: {config.get('cwd', 'N/A')}")
        else:
            prompt_parts.append("- No MCP servers currently available")
        
        # Add file context if provided
        if filename:
            try:
                file_path = Path(filename)
                if file_path.exists():
                    with open(file_path, 'r') as f:
                        file_content = f.read()
                    prompt_parts.extend([
                        "",
                        f"Additional Context from {filename}:",
                        f"```\n{file_content}\n```"
                    ])
            except Exception as e:
                prompt_parts.extend([
                    "",
                    f"Note: Could not read file {filename}: {e}"
                ])
        
        return "\n".join(prompt_parts)
    
    def get_auth_info(self) -> Dict[str, Any]:
        """Get authentication information."""
        auth_manager = AnthropicAuthManager()
        return auth_manager.get_auth_info()


async def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="KubeVirt AI Agent using Anthropic Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --query "find the installed cluster and test passt"
  python main.py --query "create a VM and test basic connectivity"
  python main.py --query "test live migration functionality"
  python main.py --query "verify KubeVirt installation" --file cluster-info.yaml
  python main.py --list-mcps
  python main.py --auth-status
        """
    )
    
    parser.add_argument(
        "--query", "-q",
        help="Query or request for the AI agent (primary interface)"
    )
    
    parser.add_argument(
        "--file", "-f",
        help="Optional file to provide additional context"
    )
    
    parser.add_argument(
        "--auth-method",
        default="vertex_ai",
        choices=["auto", "api_key", "gcloud", "vertex_ai", "service_account", "claude_code"],
        help="Authentication method to use (default: vertex_ai)"
    )
    
    parser.add_argument(
        "--list-mcps",
        action="store_true",
        help="List all registered MCP servers"
    )
    
    parser.add_argument(
        "--auth-status",
        action="store_true",
        help="Check authentication status"
    )
    
    args = parser.parse_args()
    
    # Handle auth status check
    if args.auth_status:
        from login import check_auth_status
        check_auth_status()
        return
    
    try:
        # Initialize the AI agent
        console.print(Panel.fit(
            "[bold blue]KubeVirt AI Agent[/bold blue]\n"
            "Powered by Anthropic Claude with Vertex AI",
            border_style="blue"
        ))
        
        agent = KubeVirtAIAgent(auth_method=args.auth_method)
        
        # Handle MCP listing
        if args.list_mcps:
            mcps = agent.list_mcps()
            if mcps:
                console.print("\n[bold]Registered MCP Servers:[/bold]")
                for mcp in mcps:
                    config = mcp['config']
                    console.print(f"  - [bold cyan]{mcp['name']}[/bold cyan]")
                    console.print(f"    Command: {config.get('command', 'N/A')}")
                    console.print(f"    Args: {config.get('args', [])}")
                    console.print(f"    Working Dir: {config.get('cwd', 'N/A')}")
                    if 'description' in config:
                        console.print(f"    Description: {config['description']}")
                    console.print()
            else:
                console.print("\n[yellow]No MCP servers registered yet.[/yellow]")
                console.print("MCPs can be added in future versions for enhanced functionality.")
            return
        
        # Process query (primary interface)
        if args.query:
            console.print(f"\n[bold]Processing agent request[/bold]")
            
            try:
                response = await agent.process_query(args.query, args.file)
                
                console.print("\n[bold green]KubeVirt Agent Response:[/bold green]")
                # Escape Rich markup in response to prevent parsing errors
                safe_response = response.replace("[", "\\[").replace("]", "\\]")
                console.print(Panel(
                    safe_response,
                    border_style="green",
                    title="KubeVirt Agent",
                    title_align="left"
                ))
                
            except Exception as e:
                # Escape Rich markup in error messages
                safe_error = str(e).replace("[", "\\[").replace("]", "\\]")
                console.print(f"[red]Error processing query: {safe_error}[/red]")
                sys.exit(1)
            finally:
                # Disconnect MCP clients
                await agent.mcp_registry.disconnect_all()
        else:
            # Interactive mode or show help
            console.print("\n[yellow]No query specified. This is an autonomous KubeVirt agent.[/yellow]")
            console.print("\nExample usage:")
            console.print("  python main.py --query 'find the installed cluster and test passt'")
            console.print("  python main.py --query 'create a VM and test basic connectivity'")
            console.print("  python main.py --query 'test live migration functionality'")
            console.print("  python main.py --query 'verify KubeVirt installation' --file cluster-info.yaml")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        # Escape Rich markup in error messages
        safe_error = str(e).replace("[", "\\[").replace("]", "\\]")
        console.print(f"\n[red]Unexpected error: {safe_error}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
