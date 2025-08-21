# End-to-End Testing

Simple BATS test for the KubeVirt AI Agent.

## Install BATS

```bash
sudo dnf install bats  # Fedora/RHEL
```

## Run Tests

```bash
# Run the test
make e2e-test

# Or directly
bats tests/e2e/test_simple.bats
```

## What's Tested

- `test_simple.bats` - Verifies MCP server listing works

That's it!