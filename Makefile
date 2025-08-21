.PHONY: help tox test format lint type-check quality clean e2e-test install-bats

# Default target
help:
	@echo "Available targets:"
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

# Clean tox environments
clean:
	tox --recreate
