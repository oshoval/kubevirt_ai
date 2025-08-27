.PHONY: help tox test format lint type-check quality clean e2e-test install-bats build build-mcp build-vm-exec build-agent cluster-up cluster-down deploy

# Default target
help:
	@echo "Available targets:"
	@echo "  build      - Build all required binaries (mcp + vm-exec)"
	@echo "  build-mcp  - Build kubevirt-mcp binary"
	@echo "  build-vm-exec - Build vm-exec binary"
	@echo "  build-agent - Build Docker image for AI agent"
	@echo "  deploy     - Load Docker image to kind and deploy to cluster"
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
	@echo "Checking required environment variables..."
	@test -n "$$GCLOUD_FOLDER" || (echo "Error: GCLOUD_FOLDER environment variable is not set, usually should be /home/$$USER/.config/gcloud" && exit 1)
	@test -n "$$ANTHROPIC_VERTEX_PROJECT_ID" || (echo "Error: ANTHROPIC_VERTEX_PROJECT_ID environment variable is not set" && exit 1)
	docker build --build-context gcloud-config=$$GCLOUD_FOLDER --build-arg ANTHROPIC_VERTEX_PROJECT_ID=$$ANTHROPIC_VERTEX_PROJECT_ID -t quay.io/user/claude:latest .

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

# Deploy Docker image to kind cluster
deploy:
	kind load docker-image quay.io/user/claude:latest
	kubectl delete --ignore-not-found=true -f manifests/claude-deployment.yaml
	kubectl create -f manifests/claude-deployment.yaml

# Clean tox environments
clean:
	tox --recreate
