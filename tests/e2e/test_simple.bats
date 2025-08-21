#!/usr/bin/env bats

# Simple e2e test

setup() {
    export PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    export MAIN_PY="$PROJECT_ROOT/main.py"
    cd "$PROJECT_ROOT"
}

@test "list mcps command works" {
    run python "$MAIN_PY" --list-mcps
    [ "$status" -eq 0 ]
    [[ "$output" =~ "MCP" ]] || [[ "$output" =~ "server" ]] || [[ "$output" =~ "kubevirt" ]]
}
