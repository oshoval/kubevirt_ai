.PHONY: help tox test format lint type-check quality clean e2e-test install-bats build build-mcp build-vm-exec build-agent cluster-up cluster-down

# Default target
help:
	@echo "Available targets:"
	@echo "  build      - Build all required binaries (mcp + vm-exec)"
	@echo "  build-mcp  - Build kubevirt-mcp binary"
	@echo "  build-vm-exec - Build vm-exec binary"
	@echo "  build-agent - Build Docker image for AI agent"
	@echo "  cluster-up - Setup Kind cluster with KubeVirt"
	@echo "  cluster-down - Teardown Kind cluster"
	@echo "  tox        - Run default tox environments (format + lint)"
	@echo "  test       - Run unit tests using tox"
	@echo "  e2e-test   - Run end-to-end tests with BATS"
	@echo "  format     - Format code (black, isort, autoflake)"
	@echo "  lint       - Run linting checks (flake8)"
	@echo "  type-check - Run type checking (mypy)"
	@echo "  quality    - Run all quality checks (format + lint)"
	@echo "  install-bats - Show BATS installation instructions"
	@echo "  clean      - Clean tox environments"

# Run default tox environments (format + lint)
tox:
	tox

# Run tests
test:
	tox -e test

# Format code
format:
	tox -e format

# Run linting
lint:
	tox -e lint

# Run type checking
type-check:
	tox -e type-check

# Run all quality checks
quality:
	tox -e quality

# Run end-to-end tests
e2e-test:
	bats tests/e2e/test_simple.bats

# Show BATS installation instructions
install-bats:
	@echo "Install BATS: sudo dnf install bats"

# Build all required binaries
build: build-mcp build-vm-exec
	@echo "All binaries built successfully in bin/"

# Build kubevirt-mcp binary
build-mcp:
	@echo "Building kubevirt-mcp..."
	cd mcps/kubevirt-mcp && go build -o ../../bin/kubevirt-mcp .
	@echo "✓ kubevirt-mcp built: bin/kubevirt-mcp"

# Build vm-exec binary
build-vm-exec:
	@echo "Building vm-exec..."
	cd mcps/console && go build -o ../../bin/vm-exec .
	@echo "✓ vm-exec built: bin/vm-exec"

# Build Docker image for AI agent
build-agent:
	@echo "Building Docker image for AI agent..."
	docker build -t agent .
	@echo "✓ Docker image built: agent"

# Setup Kind cluster with KubeVirt
cluster-up:
	@echo "Setting up Kind cluster with KubeVirt..."
	@bash -c "source tests/e2e/setup_suite.bash && setup_suite"
	@echo "✓ Cluster setup complete"

# Teardown Kind cluster
cluster-down:
	@echo "Tearing down Kind cluster..."
	@kind delete cluster --name kind || echo "Cluster may not exist"
	@rm -f kind-kubeconfig || true
	@echo "✓ Cluster teardown complete"

# Clean tox environments
clean:
	tox --recreate
