# KubeVirt AI Agent

AI-powered tools for KubeVirt operations using Anthropic Claude with Vertex AI authentication and Model Context Protocol (MCP) support.

## Features

- **Anthropic Claude Integration**: Uses native Anthropic SDK with Vertex AI authentication
- **File-based AI Analysis**: Process KubeVirt configuration files and get expert insights
- **MCP Support**: Extensible Model Context Protocol server integration
- **Multiple Authentication Methods**: Supports Vertex AI, API keys, gcloud, and more
- **Rich Console Interface**: Beautiful terminal output with colored formatting
- **Configurable**: MCP servers loaded from JSON configuration
- **Well Tested**: Comprehensive unit test coverage

## Prerequisites

- Python 3.7+
- Google Cloud SDK (`gcloud`) for Vertex AI authentication
- Required Python packages:
  - `anthropic`
  - `rich`

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd kubevirt_ai
```

2. Install dependencies:
```bash
# Install core dependencies
pip install -r requirements.txt

# Or install manually
pip install anthropic rich
```

For development work, install additional tools:
```bash
pip install -r requirements-dev.txt
```

3. Set up authentication (choose one):

### Vertex AI Authentication (Recommended)
```bash
# Set environment variables
export CLAUDE_CODE_USE_VERTEX=1
export ANTHROPIC_VERTEX_PROJECT_ID=your-project-id
export CLOUD_ML_REGION=us-east5

# Authenticate with Google Cloud
gcloud auth login
gcloud auth application-default login
```

### API Key Authentication
```bash
export ANTHROPIC_API_KEY=your-api-key
```

### Model Configuration
Configure which models to use via environment variables:
```bash
# Primary model for complex reasoning tasks
export ANTHROPIC_MODEL='claude-sonnet-4@20250514'

# Fast model for simple operations
export ANTHROPIC_SMALL_FAST_MODEL='claude-3-5-haiku@20241022'
```

## Configuration

### MCP Servers

MCP servers are configured in `config/mcps.json` and vendored in the `mcps/` directory for consistency and reliability.

#### Configuration

Example configuration:

```json
{
  "mcpServers": {
    "kubevirt-mcp": {
      "command": "./mcps/kubevirt-mcp/kubevirt-mcp",
      "args": [],
      "cwd": "/home/oshoval/project/kubevirt",
      "description": "KubeVirt MCP server for cluster operations"
    }
  }
}
```

#### Vendored MCPs

MCPs are vendored in the `mcps/` directory to ensure:
- **Consistent versions** across all environments
- **Self-contained** deployment without external dependencies
- **Version control** of MCP changes with the project
- **Reliability** independent of external MCP sources

The project includes:
- **kubevirt-mcp**: KubeVirt cluster operations and testing

For detailed information about vendored MCPs, see `mcps/README.md`.

#### Building MCPs

To build all MCP servers from source:

```bash
python build_mcps.py
```

This script will:
- Check for required build dependencies (Go)
- Build all Go-based MCPs in the `mcps/` directory
- Make binaries executable
- Report build status

### Agent Prompt

The AI agent behavior is defined in `agents/kubevirt-ai-agent-prompt.txt`. This file contains the system prompt that guides the AI's responses and expertise.

## Usage

### Basic Commands

```bash
# Process a file with the AI agent
python main.py --file vm-config.yaml

# Ask specific questions about a file
python main.py --file deployment.yaml --query "How can I optimize this configuration?"

# Check authentication status
python main.py --auth-status

# List registered MCP servers
python main.py --list-mcps

# Use different authentication method
python main.py --auth-method api_key --file vm.yaml
```

### Examples

1. **Analyze a VM configuration**:
```bash
python main.py --file my-vm.yaml
```

2. **Get optimization suggestions**:
```bash
python main.py --file vm-deployment.yaml --query "What are the best practices for this configuration?"
```

3. **Check system status**:
```bash
python main.py --auth-status
python main.py --list-mcps
```

## Command Line Options

- `--file`, `-f`: File to process with the AI agent
- `--query`, `-q`: Specific question about the file
- `--auth-method`: Authentication method (`auto`, `api_key`, `gcloud`, `vertex_ai`, `service_account`, `claude_code`)
- `--list-mcps`: List all registered MCP servers
- `--auth-status`: Check authentication status and available methods
- `--help`: Show help message

## Authentication Methods

The application supports multiple authentication methods (tried in order when using `auto`):

1. **Claude Code**: Uses Claude Code's built-in authentication
2. **Vertex AI**: Google Cloud Vertex AI integration (recommended for enterprise)
3. **API Key**: Direct Anthropic API key
4. **gcloud**: Google Cloud SDK authentication
5. **Service Account**: Service account key file

## Testing

```bash
# Run unit tests
make test

# Run e2e tests (requires: sudo dnf install bats)
make e2e-test

# Code quality
make tox
```

## Project Structure

```
kubevirt_ai/
├── main.py              # Main application
├── login.py             # Authentication utilities
├── build_mcps.py        # MCP build script
├── run_tests.py         # Test runner
├── requirements.txt     # Core dependencies
├── requirements-dev.txt # Development dependencies
├── agents/
│   └── kubevirt-ai-agent-prompt.txt  # AI agent system prompt
├── config/
│   └── mcps.json        # MCP server configuration
├── mcps/                # Vendored MCP servers
│   ├── README.md        # MCP documentation
│   └── kubevirt-mcp/    # KubeVirt MCP server
│       ├── kubevirt-mcp # MCP binary
│       ├── main.go      # Go source code
│       ├── detector.go  # Cluster detection logic
│       ├── go.mod       # Go module definition
│       └── README.md    # MCP-specific docs
├── tests/
│   ├── __init__.py      # Tests package
│   └── test_main.py     # Unit tests
└── README.md           # This file
```

## Development

### Adding New MCP Servers

1. Add the server configuration to `config/mcps.json`:
```json
{
  "mcpServers": {
    "my-new-server": {
      "command": "/path/to/server",
      "args": ["--option", "value"],
      "cwd": "/working/directory",
      "description": "Server description"
    }
  }
}
```

2. Restart the application - MCPs are loaded automatically

### Modifying AI Behavior

Edit `agents/kubevirt-ai-agent-prompt.txt` to customize how the AI agent responds and what expertise it provides.

### Running Development Tests

```bash
# Run tests during development
python run_tests.py

# Check for linting issues
python -m flake8 main.py test_main.py
```

## Troubleshooting

### Authentication Issues

1. Check authentication status:
```bash
python main.py --auth-status
```

2. Verify environment variables:
```bash
echo $CLAUDE_CODE_USE_VERTEX
echo $ANTHROPIC_VERTEX_PROJECT_ID
echo $CLOUD_ML_REGION
```

3. Test gcloud authentication:
```bash
gcloud auth list
gcloud auth application-default login
```

### MCP Issues

1. Check MCP configuration:
```bash
python main.py --list-mcps
```

2. Verify MCP server executable exists and is executable:
```bash
ls -la /path/to/mcp/server
```

### File Processing Issues

1. Ensure the file exists and is readable
2. Check file encoding (should be UTF-8)
3. Verify the file contains valid content for analysis

## License

See LICENSE file for details.
