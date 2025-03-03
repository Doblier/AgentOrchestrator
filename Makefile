.PHONY: install dev-install test lint format clean docs build publish help

# Default target
help:
	@echo "AORBIT - Enterprise Agent Orchestration Framework"
	@echo ""
	@echo "Usage:"
	@echo "  make install         Install production dependencies and package"
	@echo "  make dev-install     Install development dependencies and package in editable mode"
	@echo "  make test            Run tests"
	@echo "  make lint            Run linters (ruff, mypy, black --check)"
	@echo "  make format          Format code (black, isort)"
	@echo "  make clean           Clean build artifacts"
	@echo "  make docs            Build documentation"
	@echo "  make build           Build distribution packages"
	@echo "  make publish         Publish to PyPI"
	@echo ""

# Install production dependencies
install:
	@echo "Installing AORBIT..."
	python -m pip install -U uv
	uv pip install .
	@echo "Installation complete. Type 'aorbit --help' to get started."

# Install development dependencies
dev-install:
	@echo "Installing AORBIT in development mode..."
	python -m pip install -U uv
	uv pip install -e ".[dev,docs]"
	@echo "Development installation complete. Type 'aorbit --help' to get started."

# Run tests
test:
	@echo "Running tests..."
	pytest

# Run with coverage
coverage:
	@echo "Running tests with coverage..."
	pytest --cov=agentorchestrator --cov-report=term-missing --cov-report=html

# Run linters
lint:
	@echo "Running linters..."
	ruff check .
	mypy agentorchestrator
	black --check .
	isort --check .

# Format code
format:
	@echo "Formatting code..."
	black .
	isort .

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} +

# Build documentation
docs:
	@echo "Building documentation..."
	mkdocs build

# Serve documentation locally
docs-serve:
	@echo "Serving documentation at http://localhost:8000"
	mkdocs serve

# Build distribution packages
build: clean
	@echo "Building distribution packages..."
	python -m build

# Publish to PyPI
publish: build
	@echo "Publishing to PyPI..."
	twine upload dist/*

# Generate a new encryption key and save to .env
generate-key:
	@echo "Generating new encryption key..."
	@python -c "import base64; import secrets; key = base64.b64encode(secrets.token_bytes(32)).decode('utf-8'); print(f'ENCRYPTION_KEY={key}')" >> .env
	@echo "Key added to .env file."

# Run the development server
run:
	@echo "Starting AORBIT development server..."
	python main.py

# Initialize security with default roles/permissions
init-security:
	@echo "Initializing security framework..."
	@python -c "from agentorchestrator.security.rbac import RBACManager; import redis.asyncio as redis; import asyncio; async def init(): r = redis.from_url('redis://localhost:6379/0'); rbac = RBACManager(r); await rbac.create_role('admin'); await rbac.assign_permission('admin', '*:*'); await rbac.create_role('user'); await rbac.assign_permission('user', 'read:*'); print('Default roles created: admin, user'); redis_client = await r.close(); asyncio.run(init())" 