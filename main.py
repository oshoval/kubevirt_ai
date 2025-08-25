#!/usr/bin/env python3
"""
Main application for KubeVirt AI agent using Anthropic SDK with Vertex AI authentication.
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from rich.console import Console
from rich.panel import Panel

from pkg.login import AnthropicAuthManager, get_anthropic_client
from pkg.mcp import MCPRegistry
from pkg.tee_logger import TeeLogger

console = Console()


class KubeVirtAIAgent:
    """Main AI agent for KubeVirt operations using Anthropic Claude."""

    def __init__(self, auth_method: str = "vertex_ai"):
        self.auth_method = auth_method
        self.client = None
        self.mcp_registry = MCPRegistry()
        self.config = self._load_config()
        self.agent_prompt = self._load_agent_prompt()

        # Initialize authentication
        self._authenticate()

        # Initialize MCP servers
        self._initialize_mcps()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config/config.json."""
        config_path = Path(__file__).parent / "config" / "config.json"

        try:
            if not config_path.exists():
                console.print(f"[yellow]Warning: config/config.json not found at {config_path}[/yellow]")
                return {}

            with open(config_path, "r") as f:
                config = json.load(f)

            console.print("[green]Loaded configuration from config.json[/green]")
            return config

        except json.JSONDecodeError as e:
            console.print(f"[red]Error parsing config.json: {e}[/red]")
            return {}
        except Exception as e:
            console.print(f"[red]Error loading config.json: {e}[/red]")
            return {}

    def _initialize_mcps(self):
        """Initialize MCP servers from the loaded configuration."""
        mcp_servers = self.config.get("mcpServers", {})
        if not mcp_servers:
            console.print("[yellow]No MCP servers found in config.json[/yellow]")
            return

        for name, config in mcp_servers.items():
            self.add_mcp(name, config)

        console.print(f"[green]Loaded {len(mcp_servers)} MCP server(s) from config.json[/green]")

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
        """Load the agent prompt from the configured path."""
        agent_path = self.config.get("agent")
        if not agent_path:
            console.print("[red]No agent path configured in config.json[/red]")
            raise ValueError("Agent path must be configured in config.json")

        prompt_path = Path(__file__).parent / agent_path

        try:
            with open(prompt_path, "r") as f:
                prompt = f.read()
            console.print(f"[green]Loaded agent prompt from: {prompt_path}[/green]")
            return prompt
        except Exception as e:
            console.print(f"[red]Failed to load agent prompt from {prompt_path}: {e}[/red]")
            raise

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

            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                console.print("[green]✓ Command executed successfully[/green]")
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
                    tools=available_tools if available_tools else None,
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
                        # Sanitize tool result to prevent XML/HTML tag parsing issues
                        sanitized_result = self._sanitize_tool_result(tool_result)
                        messages.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": tool_call.id,
                                        "content": sanitized_result,
                                    }
                                ],
                            }
                        )

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
            if hasattr(content_block, "type") and content_block.type == "tool_use":
                tool_calls.append(content_block)
        return tool_calls

    def _extract_text_content(self, response):
        """Extract text content from response."""
        text_content = ""
        for content_block in response.content:
            if hasattr(content_block, "type") and content_block.type == "text":
                text_content += content_block.text
        return text_content

    def _sanitize_tool_result(self, content: str) -> str:
        """Sanitize tool result content to prevent XML/HTML tag parsing issues."""
        if not isinstance(content, str):
            content = str(content)

        # Replace characters that could be misinterpreted as XML/HTML tags
        # Focus on the specific pattern that caused the error: [/opt/cni/bin\]
        content = content.replace('[/', '[_/')  # Prevent [/path] from being seen as closing tag
        content = content.replace('\\]', '_]')  # Prevent escaped brackets
        content = content.replace('<', '&lt;')  # Escape actual HTML/XML brackets
        content = content.replace('>', '&gt;')

        return content

    async def _execute_tool_call(self, tool_call):
        """Execute a single tool call and return the result."""
        tool_name = tool_call.name
        tool_input = tool_call.input

        if tool_name == "vm_exec" and tool_input:
            namespace = tool_input.get("namespace", "")
            vm_name = tool_input.get("vm_name", "")
            command = tool_input.get("command", "")
            console.print(f"[blue]Executing tool: {tool_name}[/blue]")
            console.print(f"[dim]  → Running '{command}' on VM '{vm_name}' in namespace '{namespace}'[/dim]")
        else:
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

        # Success message for non-MCP tools only (MCP tools print their own success messages)
        if tool_name == "execute_shell_command":
            console.print(f"[green]✓ Tool {tool_name} executed successfully[/green]")
        return tool_result

    def _get_model_name(self, use_fast_model: bool = False) -> str:
        """Get the appropriate model name based on client type and environment variables."""
        # Check if we're using Vertex AI (AnthropicVertex client)
        if hasattr(self.client, "project_id"):
            # Vertex AI format - use company suggested models
            if use_fast_model:
                return os.environ.get("ANTHROPIC_SMALL_FAST_MODEL", "claude-3-5-haiku@20241022")
            else:
                return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4@20250514")
        else:
            # Standard Anthropic API format - convert @ to - for API format
            if use_fast_model:
                model = os.environ.get("ANTHROPIC_SMALL_FAST_MODEL", "claude-3-5-haiku-20241022")
            else:
                model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
            return model.replace("@", "-") if "@" in model else model

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
            "Available MCP Tools:",
        ]

        # List available MCP servers and their capabilities
        mcps = self.list_mcps()
        if mcps:
            for mcp in mcps:
                config = mcp["config"]
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
                    with open(file_path, "r") as f:
                        file_content = f.read()
                    prompt_parts.extend(
                        [
                            "",
                            f"Additional Context from {filename}:",
                            f"```\n{file_content}\n```",
                        ]
                    )
            except Exception as e:
                prompt_parts.extend(["", f"Note: Could not read file {filename}: {e}"])

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
        """,
    )

    parser.add_argument("--query", "-q", help="Query or request for the AI agent (primary interface)")

    parser.add_argument("--file", "-f", help="Optional file to provide additional context")

    parser.add_argument(
        "--auth-method",
        default="vertex_ai",
        choices=[
            "auto",
            "api_key",
            "gcloud",
            "vertex_ai",
            "service_account",
            "claude_code",
        ],
        help="Authentication method to use (default: vertex_ai)",
    )

    parser.add_argument("--list-mcps", action="store_true", help="List all registered MCP servers")

    parser.add_argument("--auth-status", action="store_true", help="Check authentication status")

    args = parser.parse_args()

    # Handle auth status check
    if args.auth_status:
        from login import check_auth_status

        check_auth_status()
        return

    try:
        # Initialize the AI agent
        console.print(
            Panel.fit(
                "[bold blue]KubeVirt AI Agent[/bold blue]\n" "Powered by Anthropic Claude with Vertex AI",
                border_style="blue",
            )
        )

        agent = KubeVirtAIAgent(auth_method=args.auth_method)

        # Handle MCP listing
        if args.list_mcps:
            mcps = agent.list_mcps()
            if mcps:
                console.print("\n[bold]Registered MCP Servers:[/bold]")
                for mcp in mcps:
                    config = mcp["config"]
                    console.print(f"  - [bold cyan]{mcp['name']}[/bold cyan]")
                    console.print(f"    Command: {config.get('command', 'N/A')}")
                    console.print(f"    Args: {config.get('args', [])}")
                    console.print(f"    Working Dir: {config.get('cwd', 'N/A')}")
                    if "description" in config:
                        console.print(f"    Description: {config['description']}")
                    console.print()
            else:
                console.print("\n[yellow]No MCP servers registered yet.[/yellow]")
                console.print("MCPs can be added in future versions for enhanced functionality.")
            return

        # Process query (primary interface)
        if args.query:
            console.print("\n[bold]Processing agent request[/bold]")

            try:
                response = await agent.process_query(args.query, args.file)

                console.print("\n[bold green]KubeVirt Agent Response:[/bold green]")
                # Escape Rich markup in response to prevent parsing errors
                safe_response = response.replace("[", "\\[").replace("]", "\\]")
                console.print(
                    Panel(
                        safe_response,
                        border_style="green",
                        title="KubeVirt Agent",
                        title_align="left",
                    )
                )

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
    # Create a unique log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = f"logs/kubevirt_ai_session_{timestamp}.log"

    # Use TeeLogger to capture all output to both console and log file
    with TeeLogger(log_file_path):
        print(f"Session logging started: {log_file_path}")
        asyncio.run(main())
