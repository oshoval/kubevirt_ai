# VM-Exec Tool

A standalone command-line tool for executing commands inside KubeVirt VMs via console connection.

## Overview

This tool connects to KubeVirt VMs using the console interface, performs automatic login based on VM type detection, and executes user-specified commands. It's modeled after the console interaction patterns used in KubeVirt's test suite.

## Features

- **Automatic VM Type Detection**: Detects Fedora, CirrOS, and Alpine VMs
- **Smart Login**: Automatically logs in using VM-specific credentials
- **Console-based Execution**: Uses the same console methods as KubeVirt tests
- **Exit Code Propagation**: Returns the command's actual exit code
- **Verbose Logging**: Optional detailed console interaction logs

## Supported VM Types

| VM Type | Username | Password | Root Access |
|---------|----------|----------|-------------|
| Fedora  | fedora   | fedora   | `sudo su`   |
| CirrOS  | cirros   | gocubsgo | Direct      |
| Alpine  | root     | (none)   | Direct      |

## Usage

```bash
# Basic usage
./vm-exec -n <namespace> -v <vm-name> -c '<command>'

# Examples
./vm-exec -n default -v vmi1 -c 'whoami'
./vm-exec -n default -v vmi2 -c 'uname -a'
./vm-exec -n kubevirt-test -v test-vm -c 'cat /etc/os-release'

# With verbose output
./vm-exec -n default -v vmi1 -c 'ls -la' --verbose

# Custom kubeconfig
./vm-exec --kubeconfig=/path/to/config -n default -v vmi1 -c 'ps aux'
```

## Command Line Options

- `-n, --namespace`: Kubernetes namespace (default: "default")
- `-v, --vm`: VM name (required)
- `-c, --command`: Command to execute (required)
- `-t, --timeout`: Timeout in seconds (default: 30)
- `--kubeconfig`: Path to kubeconfig file
- `--verbose`: Enable verbose console logging

## How It Works

1. **VM Discovery**: Checks for VMI first, falls back to VM if running
2. **Connection**: Establishes console connection using KubeVirt API
3. **Login**: Detects VM type and performs appropriate login sequence
4. **Execution**: Sends command and captures output
5. **Exit Code**: Retrieves and returns the command's exit code

## Installation

```bash
# Build the tool
./build.sh

# The binary will be created as ./vm-exec
```

## Prerequisites

- KubeVirt cluster with running VMs
- kubectl access to the cluster
- Go 1.23+ (for building)

## Limitations

- Only supports console-based VMs (no SSH-only VMs)
- Requires VM to be in Running state
- VM must have supported OS type (Fedora, CirrOS, Alpine)
- Console must be accessible and not paused
- **Exit codes**: Currently always returns 0 (command output is captured correctly)

## Inspiration

This tool is based on the console interaction patterns from:
- `tests/reporter/kubernetes.go` - VM command execution
- `tests/console/` package - Login and console management

It provides the same VM execution capabilities used by KubeVirt's test infrastructure as a standalone tool.
