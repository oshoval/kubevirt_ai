#!/usr/bin/env python3
"""
Unit tests for the KubeVirt AI agent main functionality.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from main import MCPRegistry, KubeVirtAIAgent


class TestMCPRegistry(unittest.TestCase):
    """Test cases for MCPRegistry class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = MCPRegistry()
    
    def test_empty_registry(self):
        """Test empty registry initialization."""
        self.assertEqual(len(self.registry.list_mcps()), 0)
        self.assertIsNone(self.registry.get_mcp("nonexistent"))
    
    def test_add_mcp(self):
        """Test adding MCP servers."""
        config = {
            "command": "/path/to/server",
            "args": ["--port", "8080"],
            "cwd": "/working/dir"
        }
        
        self.registry.add_mcp("test-server", config)
        
        # Check that MCP was added
        mcps = self.registry.list_mcps()
        self.assertEqual(len(mcps), 1)
        self.assertEqual(mcps[0]["name"], "test-server")
        self.assertEqual(mcps[0]["config"], config)
    
    def test_get_mcp(self):
        """Test retrieving specific MCP server."""
        config = {"command": "/path/to/server"}
        self.registry.add_mcp("test-server", config)
        
        # Get existing MCP
        mcp = self.registry.get_mcp("test-server")
        self.assertIsNotNone(mcp)
        self.assertEqual(mcp["name"], "test-server")
        self.assertEqual(mcp["config"], config)
        
        # Get non-existent MCP
        self.assertIsNone(self.registry.get_mcp("nonexistent"))
    
    def test_multiple_mcps(self):
        """Test handling multiple MCP servers."""
        config1 = {"command": "/path/to/server1"}
        config2 = {"command": "/path/to/server2"}
        
        self.registry.add_mcp("server1", config1)
        self.registry.add_mcp("server2", config2)
        
        mcps = self.registry.list_mcps()
        self.assertEqual(len(mcps), 2)
        
        # Verify both servers are present
        names = [mcp["name"] for mcp in mcps]
        self.assertIn("server1", names)
        self.assertIn("server2", names)


class TestKubeVirtAIAgent(unittest.TestCase):
    """Test cases for KubeVirtAIAgent class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        # Create config directory structure
        (Path(self.test_dir) / "config").mkdir(exist_ok=True)
        self.test_mcps_file = Path(self.test_dir) / "config" / "mcps.json"
        self.test_agent_prompt = Path(self.test_dir) / "agents" / "kubevirt-ai-agent-prompt.txt"
        
        # Create test directories
        (Path(self.test_dir) / "agents").mkdir(exist_ok=True)
        
        # Create test agent prompt file
        with open(self.test_agent_prompt, 'w') as f:
            f.write("You are a test KubeVirt assistant.")
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.test_dir)
    
    @patch('main.get_anthropic_client')
    def test_agent_initialization_no_mcps(self, mock_get_client):
        """Test agent initialization when no mcps.json exists."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        with patch('main.Path') as mock_path:
            # Mock the Path to point to our test directory
            mock_path.return_value.parent = Path(self.test_dir)
            
            with patch('main.console'):  # Suppress console output
                agent = KubeVirtAIAgent()
                
                # Verify basic initialization
                self.assertIsNotNone(agent.client)
                self.assertIsNotNone(agent.mcp_registry)
                self.assertEqual(len(agent.list_mcps()), 0)
    
    @patch('main.get_anthropic_client')
    def test_agent_initialization_with_mcps(self, mock_get_client):
        """Test agent initialization with valid mcps.json."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Create test mcps.json
        test_mcps = {
            "mcpServers": {
                "test-server": {
                    "command": "/test/command",
                    "args": [],
                    "cwd": "/test/dir",
                    "description": "Test server"
                }
            }
        }
        
        with open(self.test_mcps_file, 'w') as f:
            json.dump(test_mcps, f)
        
        with patch('main.Path') as mock_path:
            # Mock the Path to point to our test directory
            mock_path.return_value.parent = Path(self.test_dir)
            
            with patch('main.console'):  # Suppress console output
                agent = KubeVirtAIAgent()
                
                # Verify MCP was loaded
                mcps = agent.list_mcps()
                self.assertEqual(len(mcps), 1)
                self.assertEqual(mcps[0]["name"], "test-server")
                self.assertEqual(mcps[0]["config"]["command"], "/test/command")
    
    @patch('main.get_anthropic_client')
    def test_agent_initialization_invalid_json(self, mock_get_client):
        """Test agent initialization with invalid mcps.json."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Create invalid JSON file
        with open(self.test_mcps_file, 'w') as f:
            f.write('{"invalid": json content}')
        
        with patch('main.Path') as mock_path:
            # Mock the Path to point to our test directory
            mock_path.return_value.parent = Path(self.test_dir)
            
            with patch('main.console'):  # Suppress console output
                agent = KubeVirtAIAgent()
                
                # Verify no MCPs were loaded due to invalid JSON
                self.assertEqual(len(agent.list_mcps()), 0)
    
    @patch('main.get_anthropic_client')
    def test_load_agent_prompt(self, mock_get_client):
        """Test loading agent prompt from file."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        with patch('main.Path') as mock_path:
            # Mock the Path to point to our test directory
            mock_path.return_value.parent = Path(self.test_dir)
            
            with patch('main.console'):  # Suppress console output
                agent = KubeVirtAIAgent()
                
                # Verify prompt was loaded
                self.assertEqual(agent.agent_prompt, "You are a test KubeVirt assistant.")
    
    @patch('main.get_anthropic_client')
    def test_load_agent_prompt_missing_file(self, mock_get_client):
        """Test loading agent prompt when file is missing."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Remove the agent prompt file
        os.remove(self.test_agent_prompt)
        
        with patch('main.Path') as mock_path:
            # Mock the Path to point to our test directory
            mock_path.return_value.parent = Path(self.test_dir)
            
            with patch('main.console'):  # Suppress console output
                agent = KubeVirtAIAgent()
                
                # Verify default prompt is used
                self.assertEqual(agent.agent_prompt, "You are a helpful KubeVirt assistant.")
    
    @patch('main.get_anthropic_client')
    def test_get_model_name_vertex_ai(self, mock_get_client):
        """Test model name selection for Vertex AI client."""
        mock_client = Mock()
        mock_client.project_id = "test-project"  # Vertex AI client has project_id
        mock_get_client.return_value = mock_client
        
        with patch('main.Path') as mock_path:
            mock_path.return_value.parent = Path(self.test_dir)
            
            with patch('main.console'):  # Suppress console output
                agent = KubeVirtAIAgent()
                
                # Test regular model (use_fast_model=False)
                model_name = agent._get_model_name(use_fast_model=False)
                self.assertEqual(model_name, "claude-sonnet-4@20250514")
                
                # Test fast model (use_fast_model=True)
                fast_model_name = agent._get_model_name(use_fast_model=True)
                self.assertEqual(fast_model_name, "claude-3-5-haiku@20241022")
    
    @patch('main.get_anthropic_client')
    def test_get_model_name_with_env_vars(self, mock_get_client):
        """Test that environment variables are properly inherited in tox."""
        mock_client = Mock()
        mock_client.project_id = "test-project"  # Vertex AI client
        mock_get_client.return_value = mock_client
        
        with patch('main.Path') as mock_path:
            mock_path.return_value.parent = Path(self.test_dir)
            
            with patch('main.console'):  # Suppress console output
                # Test with custom environment variables
                with patch.dict(os.environ, {
                    'ANTHROPIC_MODEL': 'custom-main-model@123',
                    'ANTHROPIC_SMALL_FAST_MODEL': 'custom-fast-model@456'
                }):
                    agent = KubeVirtAIAgent()
                    
                    # Should use environment variable for main model
                    main_model = agent._get_model_name(use_fast_model=False)
                    self.assertEqual(main_model, "custom-main-model@123")
                    
                    # Should use environment variable for fast model
                    fast_model = agent._get_model_name(use_fast_model=True)
                    self.assertEqual(fast_model, "custom-fast-model@456")
    
    @patch('main.get_anthropic_client')
    def test_get_model_name_standard(self, mock_get_client):
        """Test model name selection for standard Anthropic client."""
        mock_client = Mock()
        # Standard client doesn't have project_id attribute
        if hasattr(mock_client, 'project_id'):
            delattr(mock_client, 'project_id')
        mock_get_client.return_value = mock_client
        
        with patch('main.Path') as mock_path:
            mock_path.return_value.parent = Path(self.test_dir)
            
            with patch('main.console'):  # Suppress console output
                # Clear environment variables to test defaults
                with patch.dict(os.environ, {}, clear=True):
                    agent = KubeVirtAIAgent()
                    
                    # Verify standard model name is used (should be the hardcoded default)
                    model_name = agent._get_model_name()
                    self.assertEqual(model_name, "claude-3-5-sonnet-20241022")


class TestMCPConfigurationLoading(unittest.TestCase):
    """Test cases for MCP configuration loading functionality."""
    
    def test_valid_mcps_config(self):
        """Test loading valid MCP configuration."""
        config = {
            "mcpServers": {
                "server1": {
                    "command": "/path/to/server1",
                    "args": ["--port", "8080"],
                    "cwd": "/work/dir1"
                },
                "server2": {
                    "command": "/path/to/server2",
                    "args": [],
                    "cwd": "/work/dir2",
                    "description": "Test server 2"
                }
            }
        }
        
        registry = MCPRegistry()
        
        # Simulate loading from config
        for name, server_config in config["mcpServers"].items():
            registry.add_mcp(name, server_config)
        
        # Verify all servers were loaded
        mcps = registry.list_mcps()
        self.assertEqual(len(mcps), 2)
        
        # Verify server details
        server1 = registry.get_mcp("server1")
        self.assertEqual(server1["config"]["command"], "/path/to/server1")
        self.assertEqual(server1["config"]["args"], ["--port", "8080"])
        
        server2 = registry.get_mcp("server2")
        self.assertEqual(server2["config"]["description"], "Test server 2")
    
    def test_empty_mcps_config(self):
        """Test handling empty MCP configuration."""
        config = {"mcpServers": {}}
        
        registry = MCPRegistry()
        
        # Simulate loading from empty config
        for name, server_config in config["mcpServers"].items():
            registry.add_mcp(name, server_config)
        
        # Verify no servers were loaded
        self.assertEqual(len(registry.list_mcps()), 0)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
