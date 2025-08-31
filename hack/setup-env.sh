#!/bin/bash
set -e

# Environment setup script for kubevirt-ai
# Generates deterministic environment variables to reduce agent load

ENV_FILE=".env"

# Function to update docs if repository is clean
update_docs_if_clean() {
    local docs_path="$1"

    # Expand ~ to home directory
    docs_path="${docs_path/#\~/$HOME}"

    if [ ! -d "$docs_path" ]; then
        echo "# Documentation path does not exist: $docs_path"
        return
    fi

    cd "$docs_path" || return

    # Check if git status is clean (no staged, unstaged, or untracked files)
    if ! git status --porcelain | grep -q .; then
        echo "# Repository is clean, updating documentation..."

        # Check if upstream remote exists
        if git remote | grep -q "^upstream$"; then
            echo "# Pulling from upstream main..."
            git pull upstream main 2>/dev/null && echo "# Documentation updated from upstream" || echo "# Failed to pull from upstream"
        else
            echo "# Pulling from origin main..."
            git pull origin main 2>/dev/null && echo "# Documentation updated from origin" || echo "# Failed to pull from origin"
        fi
    else
        echo "# Repository has uncommitted changes, skipping documentation update"
        git status --short
    fi

    cd - > /dev/null
}

echo "# Auto-generated environment variables for kubevirt-ai session" > "$ENV_FILE"
echo "# Generated at: $(date -Iseconds)" >> "$ENV_FILE"

# Generate unique session ID (5 chars for readability)
RANDOM_ID=$(date +%s%N | cut -b1-13 | tail -c 6)
echo "RANDOM_ID=$RANDOM_ID" >> "$ENV_FILE"

# Set workspace root
WORKSPACE_ROOT=$(pwd)
echo "WORKSPACE_ROOT=$WORKSPACE_ROOT" >> "$ENV_FILE"

# Session start timestamp
SESSION_START=$(date -Iseconds)
echo "SESSION_START=$SESSION_START" >> "$ENV_FILE"

# Detect cluster type and docs folder using MCP (with timeout)
echo "# Detecting cluster type and docs folder..."
MCP_RESULT=$(timeout 30s bash -c 'echo "{\"jsonrpc\": \"2.0\", \"id\": 1, \"method\": \"tools/call\", \"params\": {\"name\": \"detect_kubevirtci_cluster\", \"arguments\": {}}}" | ./bin/kubevirt-mcp' 2>/dev/null || echo "")

# Extract cluster info from MCP output
if echo "$MCP_RESULT" | grep -q "CLUSTER_TYPE="; then
    CLUSTER_TYPE=$(echo "$MCP_RESULT" | grep -o "CLUSTER_TYPE=[a-zA-Z]*" | cut -d= -f2)
    DOCS_FOLDER=$(echo "$MCP_RESULT" | grep -o "DOCS_FOLDER=[~/a-zA-Z0-9/_-]*" | cut -d= -f2)

    # Extract KUBECONFIG if present (not needed for in-cluster)
    if echo "$MCP_RESULT" | grep -q "export KUBECONFIG="; then
        KUBECONFIG_PATH=$(echo "$MCP_RESULT" | grep -o "export KUBECONFIG=[/a-zA-Z0-9._-]*" | cut -d= -f2)
        echo "KUBECONFIG=$KUBECONFIG_PATH" >> "$ENV_FILE"
    fi

    echo "CLUSTER_TYPE=$CLUSTER_TYPE" >> "$ENV_FILE"
    echo "DOCS_FOLDER=$DOCS_FOLDER" >> "$ENV_FILE"
    echo "# Cluster detection: SUCCESS ($CLUSTER_TYPE)"

    # Update documentation if clean
    echo "# Updating documentation..."
    update_docs_if_clean "$DOCS_FOLDER"
else
    echo "# Cluster detection: FAILED"
    echo "ERROR: Could not detect cluster type. MCP output:"
    echo "$MCP_RESULT"
    echo "# Setup cannot continue without cluster detection"
    exit 1
fi

echo "Environment setup complete:"
cat "$ENV_FILE"
