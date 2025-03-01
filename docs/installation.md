# Installation & Environment Management

This guide covers all the ways you can install and configure AgentOrchestrator for different environments.

## Quick Start (5 minutes)

```bash
# Clone the repository
git clone https://github.com/your-username/AgentOrchestrator.git
cd AgentOrchestrator

# Set up development environment with UV
ao setup-env dev

# Activate the environment
source .venv-dev/bin/activate  # On Windows: .venv-dev\Scripts\activate

# Start the development server
ao dev
```

Your server is now running at http://localhost:8000 with hot reloading enabled! 🎉

## Installation Options

AgentOrchestrator offers multiple installation approaches depending on your needs:

### Option 1: Using Built-in CLI Tools (Recommended)

Our built-in CLI tools make environment setup simple:

```bash
# Set up a development environment
ao setup-env dev

# Set up a testing environment
ao setup-env test

# Set up a UAT environment
ao setup-env uat

# Set up a production environment
ao setup-env prod
```

### Option 2: Using Docker Compose

For containerized development and deployment:

```bash
# Development environment with hot reloading
docker-compose --profile dev up

# Testing environment to run tests
docker-compose --profile test up -d
docker-compose --profile test exec agentorchestrator-test ao test

# UAT environment
docker-compose --profile uat up

# Production environment
docker-compose --profile prod up
```

### Option 3: Using Advanced Environment Management Script

For more fine-grained control, use our advanced environment management script:

```bash
# Create environments
python scripts/manage_envs.py create dev
python scripts/manage_envs.py create test
python scripts/manage_envs.py create uat
python scripts/manage_envs.py create prod

# Update specific environment dependencies
python scripts/manage_envs.py update dev

# Generate locked requirements for production
python scripts/manage_envs.py lock

# Update all environments at once
python scripts/manage_envs.py sync-all
```

### Option 4: Manual Environment Setup with UV

For those who prefer direct control:

```bash
# Development environment
uv venv .venv-dev
source .venv-dev/bin/activate  # On Windows: .venv-dev\Scripts\activate
uv pip install -e ".[dev]"

# Testing environment
uv venv .venv-test
source .venv-test/bin/activate  # On Windows: .venv-test\Scripts\activate
uv pip install -e ".[test]"

# UAT environment
uv venv .venv-uat
source .venv-uat/bin/activate  # On Windows: .venv-uat\Scripts\activate
uv pip install -e .

# Production environment
uv venv .venv-prod
source .venv-prod/bin/activate  # On Windows: .venv-prod\Scripts\activate
uv pip install -e .
uv pip compile pyproject.toml --python-version=3.12 --no-dev --output-file=requirements.lock
```

## Environment Configuration

### Environment-specific .env Files

Each environment can have its own configuration:

- `.env.dev` - Development settings
- `.env.test` - Testing settings
- `.env.uat` - UAT settings
- `.env` - Production settings

You can create them all at once:

```bash
ao create-env-files
```

### Required Configuration

At minimum, you need to configure:

1. **API Keys**: At least one LLM provider API key (Google AI, OpenAI, etc.)
2. **Redis**: For production deployments with caching, rate limiting, etc.

Example `.env` file:

```
# Core settings
DEBUG=false
PORT=8000

# API Keys (at least one is required)
GOOGLE_API_KEY=your_google_api_key_here

# Redis (required for production features)
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Running the Server

### Development Mode

```bash
# Using the CLI (with hot reloading)
ao dev

# Or with more options
ao serve --env dev --host 0.0.0.0 --port 8000 --reload
```

### Testing

```bash
# Run all tests
ao test

# Run with coverage
ao test --coverage

# Run specific tests
ao test tests/api/
```

### Production Mode

```bash
# Using the CLI
ao serve --env prod

# With specific host/port
ao serve --env prod --host 0.0.0.0 --port 8080
```

## Building for Production

```bash
# Build distribution packages
ao build

# Create locked requirements
python scripts/manage_envs.py lock
```

## Docker Production Deployment

Our multi-stage Docker build creates optimized production images:

```bash
# Build the production image
docker build -t agentorchestrator:latest .

# Run the container
docker run -p 8000:8000 --env-file .env agentorchestrator:latest
```

## Continuous Integration

Our GitHub Actions workflow automatically:

1. Runs tests with coverage
2. Runs integration tests (UAT)
3. Builds distribution packages
4. Creates Docker images
5. Deploys to production (when configured)

You can run the same checks locally:

```bash
# Setup test environment
ao setup-env test

# Run linting and tests
source .venv-test/bin/activate
ruff check .
ao test --coverage
```

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   - Use `uv pip install -e ".[dev]"` to install all dependencies

2. **Environment Activation Problems**
   - Ensure you're using the correct activation command for your OS
   - Windows: `.venv-dev\Scripts\activate`
   - Unix/macOS: `source .venv-dev/bin/activate`

3. **Redis Connection Issues**
   - Ensure Redis is running: `docker run -p 6379:6379 redis:latest`

### Getting Help

If you encounter issues, please:

1. Check the [FAQ](./faq.md)
2. Search existing GitHub issues
3. Create a new issue with detailed information about your problem 