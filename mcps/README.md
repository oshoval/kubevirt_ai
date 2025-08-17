# Vendored MCP Servers

This directory contains vendored Model Context Protocol (MCP) servers used by the KubeVirt AI Agent.

## Purpose

Vendoring MCPs ensures:
- **Consistent versions**: All team members use the same MCP version
- **Self-contained**: Project doesn't depend on external MCP installations
- **Reliability**: MCPs are available even if original sources change
- **Version control**: MCP changes are tracked with the project

## Structure

```
mcps/
├── README.md                 # This file
└── kubevirt-mcp/            # KubeVirt MCP server
    ├── kubevirt-mcp         # Binary executable
    ├── README.md            # MCP documentation
    └── go.mod               # Version information
```

## Included MCPs

### kubevirt-mcp
- **Description**: KubeVirt MCP server for cluster operations
- **Source**: `/home/oshoval/work/kubevirt-mcp`
- **Version**: vendored
- **Binary**: `kubevirt-mcp/kubevirt-mcp`

## Usage

MCPs are automatically loaded from the configuration in `config/mcps.json`. The configuration references the vendored binaries using relative paths:

```json
{
  "mcpServers": {
    "kubevirt-mcp": {
      "command": "./mcps/kubevirt-mcp/kubevirt-mcp",
      "args": [],
      "cwd": "/home/oshoval/project/kubevirt",
      "description": "KubeVirt MCP server for cluster operations (vendored)"
    }
  }
}
```

## Updating Vendored MCPs

To update a vendored MCP:

1. Copy the new binary and files:
   ```bash
   cp /path/to/new/mcp-binary mcps/mcp-name/
   chmod +x mcps/mcp-name/mcp-binary
   ```

2. Update documentation if needed:
   ```bash
   cp /path/to/new/README.md mcps/mcp-name/
   ```

3. Test the updated MCP:
   ```bash
   python main.py --list-mcps
   python main.py --query "test MCP functionality"
   ```

4. Commit the changes:
   ```bash
   git add mcps/
   git commit -m "Update vendored MCP: mcp-name"
   ```

## Adding New MCPs

To vendor a new MCP:

1. Create a directory for the MCP:
   ```bash
   mkdir mcps/new-mcp-name
   ```

2. Copy the MCP files:
   ```bash
   cp /path/to/mcp-binary mcps/new-mcp-name/
   cp /path/to/mcp-docs mcps/new-mcp-name/
   chmod +x mcps/new-mcp-name/mcp-binary
   ```

3. Add configuration to `config/mcps.json`:
   ```json
   {
     "mcpServers": {
       "new-mcp-name": {
         "command": "./mcps/new-mcp-name/mcp-binary",
         "args": [],
         "cwd": "/working/directory",
         "description": "Description of the new MCP",
         "version": "vendored",
         "source": "/original/source/path"
       }
     }
   }
   ```

4. Update this README to document the new MCP.

## Best Practices

- **Keep binaries updated**: Regularly sync with upstream sources
- **Document versions**: Include version information and source paths
- **Test after updates**: Always test MCPs after updating
- **Commit atomically**: Include binary, docs, and config changes in single commits
- **Security**: Only vendor MCPs from trusted sources
