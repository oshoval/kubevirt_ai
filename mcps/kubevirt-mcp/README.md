# KubeVirt MCP Server

A Model Context Protocol (MCP) server for KubeVirt development workflows that validates cluster connectivity using configurable kubeconfig sources.

## Features

### 🔍 `detect_kubevirtci_cluster`
- **Configurable sources** - checks multiple kubeconfig locations in priority order
- **Environment variables** - KUBECONFIG, GLOBAL_KUBECONFIG, etc.
- **File paths** - ~/.kube/config and custom paths
- **Connectivity testing** - validates cluster access using kubectl
- **Smart fallbacks** - tries next source if current one fails

## Prerequisites

- **Go 1.21+** for building
- **kubectl** installed and accessible
- **Cursor IDE** with MCP support
- **Kubeconfig** available via environment variables or file paths (see Configuration section)

## Configuration

The MCP server uses a `config.yaml` file to define kubeconfig sources and their priority order. If no config file exists, it uses sensible defaults.

### Default Configuration

By default, the server checks sources in this order:
1. **KUBECONFIG** environment variable (standard kubectl)
2. **GLOBAL_KUBECONFIG** environment variable (development environments)  
3. **~/.kube/config** file (default kubectl location)

### Custom Configuration

Create a `config.yaml` file in the MCP directory:

```yaml
kubeconfig:
  sources:
    - type: "env_var"
      name: "KUBECONFIG"
      description: "Standard kubectl environment variable"
    
    - type: "env_var" 
      name: "GLOBAL_KUBECONFIG"
      description: "Global kubeconfig for development environments"
    
    - type: "file"
      path: "~/.kube/config"
      description: "Default kubectl config location"
    
    - type: "file"
      path: "/custom/path/kubeconfig"
      description: "Custom kubeconfig location"

connectivity_test:
  timeout: 10
  command: ["kubectl", "get", "nodes"]

logging:
  level: "info"  # debug, info, warn, error
```

### Configuration Options

- **kubeconfig.sources**: Array of sources to check in priority order
  - **type**: Either "env_var" (environment variable) or "file" (file path)
  - **name**: Environment variable name (for env_var type)
  - **path**: File path (for file type), supports tilde expansion (~)
  - **description**: Human-readable description
- **connectivity_test.timeout**: Seconds to wait for kubectl test (default: 10)
- **connectivity_test.command**: Command to test connectivity (default: kubectl get nodes)
- **logging.level**: Log verbosity level (default: info)

## Installation

### 1. Build the Server
```bash
cd path/to/kubevirt-mcp
go build -o kubevirt-mcp .
```

### 2. Configure MCP in Cursor

Add the following to your `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "kubevirt-mcp": {
      "command": "./mcps/kubevirt-mcp/kubevirt-mcp",
      "args": [],
      "cwd": "~/project/kubevirt"
    }
  }
}
```

### 3. Restart Cursor
- Close Cursor completely
- Reopen Cursor
- Verify the server appears in MCP settings

## Usage

### Via Cursor AI Chat

```
Detect kubevirtci cluster using MCP
```

### Expected Output

When a kubeconfig source is found and cluster is accessible:
```
✅ Cluster Available via Standard kubectl environment variable

🔧 Setup Commands:
   export KUBECONFIG=/path/to/your/.kubeconfig

📝 Verification:
   kubectl get nodes
   kubectl get kubevirt -n kubevirt

✨ Ready to use cluster!
```

When no accessible cluster is found:
```
❌ No accessible cluster found using any configured kubeconfig source
```

The server tries each configured source in order and reports the first successful connection.



## Development

### Project Structure
```
kubevirt-mcp/
├── main.go       # MCP server implementation
├── detector.go   # Cluster detection logic
├── go.mod        # Go module definition
└── README.md     # This file
```

### Testing Locally
```bash
# Test the tool directly
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "detect_kubevirtci_cluster", "arguments": {}}}' | ./kubevirt-mcp
```

### Debugging
- Logs go to stderr (visible in terminal)
- JSON-RPC communication uses stdout
- Check Cursor's MCP debug panel for connection issues

## Cluster Validation Logic

The server validates cluster connectivity by:

1. **Configuration loading**: Reads config.yaml or uses built-in defaults
2. **Source iteration**: Tries each kubeconfig source in priority order
3. **Source validation**: Checks if environment variables are set or files exist
4. **Connectivity test**: Runs configurable kubectl command to test cluster access
5. **Smart fallbacks**: Continues to next source if current one fails
6. **Result reporting**: Returns success with source info or failure message

## Integration with KubeVirt Workflow

This MCP server is designed to integrate seamlessly with any Kubernetes development:

- **Environment-based** configuration using GLOBAL_KUBECONFIG
- **Connectivity validation** ensures cluster is accessible before use
- **Clear error reporting** helps diagnose configuration issues
- **Simple setup** requiring only the GLOBAL_KUBECONFIG environment variable

## Troubleshooting

### Server Not Connecting
1. Check the binary path in `mcp.json` is correct
2. Ensure the binary is executable: `chmod +x kubevirt-mcp`
3. Restart Cursor after configuration changes

### No Cluster Detected
1. Verify kubevirtci is actually running: `docker ps` or `podman ps`
2. Check container naming patterns match expected kubevirtci conventions
3. Ensure container runtime is accessible (not requiring sudo)

### Permission Issues
- Docker: Add user to `docker` group or use rootless Docker
- Podman: Ensure rootless Podman is properly configured

## Future Enhancements

Planned features for future versions:
- **Start/stop cluster** commands
- **Cluster status** monitoring  
- **Log access** from kubevirtci containers
- **Port forwarding** management
- **Test execution** helpers

---

**Ready to streamline your KubeVirt development with MCP! 🚀**