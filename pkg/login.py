#!/usr/bin/env python3
"""
Authentication utilities for Anthropic API in enterprise environments.
Supports multiple authentication methods including Google Cloud ADC.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import anthropic
from rich.console import Console

console = Console()


class AnthropicAuthManager:
    """Manages authentication for Anthropic API in enterprise environments."""

    def __init__(self):
        self.client = None
        self._auth_method = None

    def get_client(self, auth_method: str = "auto") -> anthropic.Client:
        """
        Get an authenticated Anthropic client using various methods.

        Args:
            auth_method: Authentication method to use
                - "auto": Try all methods in order
                - "api_key": Use ANTHROPIC_API_KEY environment variable
                - "gcloud": Use gcloud authentication
                - "vertex_ai": Use Google Cloud Vertex AI
                - "service_account": Use service account key file
                - "claude_code": Use Claude Code's authentication
        """
        if self.client:
            return self.client

        if auth_method == "auto":
            self.client = self._try_auth_methods()
        elif auth_method == "api_key":
            self.client = self._auth_with_api_key()
        elif auth_method == "gcloud":
            self.client = self._auth_with_gcloud()
        elif auth_method == "vertex_ai":
            self.client = self._auth_with_vertex_ai()
        elif auth_method == "service_account":
            self.client = self._auth_with_service_account()
        elif auth_method == "claude_code":
            self.client = self._auth_with_claude_code()
        else:
            raise ValueError(f"Unknown auth method: {auth_method}")

        if not self.client:
            raise RuntimeError(f"Failed to authenticate with method: {auth_method}")

        return self.client

    def _try_auth_methods(self) -> Optional[anthropic.Client]:
        """Try authentication methods in order of preference."""
        methods = [
            ("claude_code", self._auth_with_claude_code),
            ("vertex_ai", self._auth_with_vertex_ai),
            ("api_key", self._auth_with_api_key),
            ("gcloud", self._auth_with_gcloud),
            ("service_account", self._auth_with_service_account),
        ]

        for method_name, method_func in methods:
            try:
                client = method_func()
                if client:
                    self._auth_method = method_name
                    console.print(f"[green]✅ Successfully authenticated using: {method_name}[/green]")
                    return client
            except Exception:
                # Silently continue to next method
                continue

        console.print("[red]❌ All authentication methods failed[/red]")
        return None

    def _auth_with_api_key(self) -> Optional[anthropic.Client]:
        """Authenticate using ANTHROPIC_API_KEY environment variable."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        return anthropic.Client(api_key=api_key)

    def _auth_with_gcloud(self) -> Optional[anthropic.Client]:
        """Authenticate using gcloud credentials."""
        try:
            # Check if gcloud is available and authenticated
            result = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                capture_output=True,
                text=True,
                check=True,
            )
            access_token = result.stdout.strip()

            if not access_token:
                raise ValueError("No access token from gcloud")

            # For Google Cloud integration with Anthropic API
            # This might require a different client configuration
            # depending on how your company has set up the integration

            # Check if there's a Google Cloud project configured for Anthropic
            project_result = subprocess.run(
                ["gcloud", "config", "get-value", "project"],
                capture_output=True,
                text=True,
            )
            project_id = project_result.stdout.strip()

            console.print(f"[blue]Using Google Cloud project: {project_id}[/blue]")
            console.print(f"[blue]Access token available: {'Yes' if access_token else 'No'}[/blue]")

            # This is a placeholder - the actual implementation depends on
            # how your company has configured Anthropic API access through Google Cloud
            # You may need to use a different endpoint or client configuration

            # Option 1: If Anthropic API is proxied through Google Cloud
            # return anthropic.Client(
            #     api_key=access_token,
            #     base_url="https://your-company-anthropic-proxy.googleapis.com"
            # )

            # Option 2: If using Vertex AI Anthropic integration
            # This would require the google-cloud-aiplatform library
            # and a different client setup

            # For now, return None to indicate this method needs configuration
            raise NotImplementedError(
                "Google Cloud authentication requires company-specific configuration. "
                "Please contact your IT team for the correct API endpoint and setup."
            )

        except subprocess.CalledProcessError as e:
            raise ValueError(f"gcloud authentication failed: {e}")
        except FileNotFoundError:
            raise ValueError("gcloud command not found. Please install Google Cloud SDK.")

    def _auth_with_vertex_ai(self) -> Optional[anthropic.Client]:
        """Authenticate using Google Cloud Vertex AI for Anthropic API."""
        try:
            # Check if Vertex AI environment variables are set
            vertex_enabled = os.environ.get("CLAUDE_CODE_USE_VERTEX")
            project_id = os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID")
            region = os.environ.get("CLOUD_ML_REGION")

            if not vertex_enabled or vertex_enabled != "1":
                raise ValueError("CLAUDE_CODE_USE_VERTEX not set to 1")

            if not project_id:
                raise ValueError("ANTHROPIC_VERTEX_PROJECT_ID environment variable not set")

            # Check if gcloud is authenticated
            try:
                result = subprocess.run(
                    ["gcloud", "auth", "print-access-token"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                access_token = result.stdout.strip()

                if not access_token:
                    raise ValueError("No access token from gcloud")

            except subprocess.CalledProcessError as e:
                raise ValueError(f"gcloud authentication failed: {e}")
            except FileNotFoundError:
                raise ValueError("gcloud command not found. Please install Google Cloud SDK.")

            console.print(f"[blue]Using Vertex AI project: {project_id}[/blue]")
            console.print(f"[blue]Using region: {region}[/blue]")

            # Create client with Vertex AI configuration
            client = anthropic.AnthropicVertex(project_id=project_id, region=region)

            console.print("[green]✅ Vertex AI client created successfully[/green]")
            return client

        except Exception as e:
            raise ValueError(f"Vertex AI authentication failed: {e}")

    def _auth_with_service_account(self) -> Optional[anthropic.Client]:
        """Authenticate using service account key file."""
        # Check for service account key file
        key_file_paths = [
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
            os.environ.get("ANTHROPIC_SERVICE_ACCOUNT_KEY"),
            str(Path.home() / ".config" / "anthropic" / "service-account.json"),
            str(Path.home() / ".anthropic" / "service-account.json"),
        ]

        for key_file in key_file_paths:
            if key_file and Path(key_file).exists():
                try:
                    with open(key_file) as f:
                        json.load(f)

                    # This would require company-specific implementation
                    # depending on how service accounts are configured for Anthropic API
                    console.print(f"[blue]Found service account key: {key_file}[/blue]")

                    raise NotImplementedError(
                        "Service account authentication requires company-specific configuration. "
                        "Please contact your IT team for the correct implementation."
                    )

                except Exception as e:
                    console.print(f"[yellow]Failed to load service account from {key_file}: {e}[/yellow]")
                    continue

        raise ValueError("No valid service account key file found")

    def _auth_with_claude_code(self) -> Optional[anthropic.Client]:
        """Try to use Claude Code's authentication if available."""
        try:
            # Check if we're running in a Claude Code environment
            # Claude Code might set specific environment variables or config files

            # Method 1: Check for Claude Code config
            claude_config_paths = [
                Path.home() / ".claude" / "config.json",
                Path.home() / ".config" / "claude" / "config.json",
                Path.home() / ".anthropic" / "config.json",
            ]

            for config_path in claude_config_paths:
                if config_path.exists():
                    try:
                        with open(config_path) as f:
                            config = json.load(f)

                        # Look for API key in config
                        api_key = config.get("api_key") or config.get("anthropic_api_key")
                        if api_key:
                            return anthropic.Client(api_key=api_key)

                    except Exception as e:
                        console.print(f"[yellow]Failed to load Claude config from {config_path}: {e}[/yellow]")
                        continue

            # Method 2: Check if running in Claude Code's environment
            # Look for environment variables that Claude Code might set
            claude_env_vars = [
                "CLAUDE_API_KEY",
                "ANTHROPIC_API_KEY",
                "_CLAUDE_API_KEY",  # Internal variable
            ]

            for env_var in claude_env_vars:
                api_key = os.environ.get(env_var)
                if api_key:
                    return anthropic.Client(api_key=api_key)

            raise ValueError("No Claude Code authentication found")

        except Exception as e:
            raise ValueError(f"Claude Code authentication failed: {e}")

    def get_auth_info(self) -> Dict[str, Any]:
        """Get information about the current authentication method."""
        return {
            "authenticated": self.client is not None,
            "auth_method": self._auth_method,
            "available_methods": self._check_available_methods(),
        }

    def _check_available_methods(self) -> Dict[str, bool]:
        """Check which authentication methods are available."""
        methods = {}

        # Check API key
        methods["api_key"] = bool(os.environ.get("ANTHROPIC_API_KEY"))

        # Check gcloud
        try:
            subprocess.run(["gcloud", "--version"], capture_output=True, check=True)
            methods["gcloud"] = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            methods["gcloud"] = False

        # Check Vertex AI
        vertex_enabled = os.environ.get("CLAUDE_CODE_USE_VERTEX") == "1"
        project_id = bool(os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID"))
        methods["vertex_ai"] = vertex_enabled and project_id and methods["gcloud"]

        # Check service account
        key_file_paths = [
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
            os.environ.get("ANTHROPIC_SERVICE_ACCOUNT_KEY"),
        ]
        methods["service_account"] = any(path and Path(path).exists() for path in key_file_paths)

        # Check Claude Code
        claude_config_paths = [
            Path.home() / ".claude" / "config.json",
            Path.home() / ".config" / "claude" / "config.json",
            Path.home() / ".anthropic" / "config.json",
        ]
        methods["claude_code"] = any(path.exists() for path in claude_config_paths)

        return methods


def get_anthropic_client(auth_method: str = "auto") -> anthropic.Client:
    """
    Convenience function to get an authenticated Anthropic client.

    Args:
        auth_method: Authentication method to use (auto, api_key, gcloud, service_account, claude_code)

    Returns:
        Authenticated Anthropic client
    """
    auth_manager = AnthropicAuthManager()
    return auth_manager.get_client(auth_method)


def check_auth_status() -> None:
    """Check and display authentication status."""
    auth_manager = AnthropicAuthManager()
    info = auth_manager.get_auth_info()

    console.print("\n[bold]Anthropic API Authentication Status[/bold]")
    console.print("=" * 50)

    available = info["available_methods"]

    for method, is_available in available.items():
        status = "✅ Available" if is_available else "❌ Not Available"
        console.print(f"{method:<15}: {status}")

    console.print("\nRecommended: Use 'auto' to try all methods in order")

    if not any(available.values()):
        console.print("\n[red]⚠️  No authentication methods available![/red]")
        console.print("Please ensure you have:")
        console.print("- ANTHROPIC_API_KEY environment variable, or")
        console.print("- Google Cloud Vertex AI configured (CLAUDE_CODE_USE_VERTEX=1), or")
        console.print("- Google Cloud SDK installed and authenticated, or")
        console.print("- Service account key file configured, or")
        console.print("- Claude Code authentication configured")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        check_auth_status()
    else:
        # Test authentication
        try:
            client = get_anthropic_client("auto")
            console.print("[green]✅ Authentication successful![/green]")

            # Test with a simple API call
            # Use the correct model name for Vertex AI
            model = "claude-3-5-haiku@20241022" if hasattr(client, "project_id") else "claude-3-haiku-20240307"
            response = client.messages.create(
                model=model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}],
            )
            console.print(f"[green]✅ API test successful: {response.content[0].text[:50]}...[/green]")

        except Exception as e:
            console.print(f"[red]❌ Authentication failed: {e}[/red]")
            check_auth_status()
