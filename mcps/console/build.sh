#!/bin/bash

set -e

echo "Building vm-exec tool..."

# Change to mcp directory
cd "$(dirname "$0")"

# Initialize go mod if go.sum doesn't exist
if [ ! -f go.sum ]; then
    echo "Initializing go modules..."
    go mod tidy
fi

# Build the binary
echo "Compiling vm-exec..."
go build -o vm-exec vm-exec.go

echo "Build complete! Binary: $(pwd)/vm-exec"
echo ""
echo "Usage examples:"
echo "  ./vm-exec -n default -v vmi1 -c 'uname -a'"
echo "  ./vm-exec -n default -v vmi2 -c 'ls -la' --method ssh"
echo "  ./vm-exec -n default -v vmi1 -c 'whoami' --verbose"
