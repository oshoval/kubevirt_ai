#!/bin/bash
set -e

# Environment setup script for kubevirt-ai
# Generates deterministic environment variables to reduce agent load

ENV_FILE=".env"

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

echo "Environment setup complete:"
cat "$ENV_FILE"
