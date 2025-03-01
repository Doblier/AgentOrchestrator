# Environment Management Strategy

This document outlines AgentOrchestrator's standardized approach to managing dependencies across development, testing, UAT, and production environments.

## Environment Types

### Development Environment
- **Purpose**: Active development with all development tools
- **Features**: Full debugging, hot reloading, development servers
- **Dependencies**: All production and development dependencies
- **Usage**: Day-to-day development work

### Testing Environment
- **Purpose**: Running automated tests
- **Features**: Test frameworks, mocking libraries, code coverage tools
- **Dependencies**: Production dependencies + test-specific dependencies
- **Usage**: CI pipelines, local testing

### UAT (User Acceptance Testing) Environment
- **Purpose**: Pre-production validation
- **Features**: Production-like setup with monitoring capabilities
- **Dependencies**: Production dependencies only (no development tools)
- **Usage**: Manual testing before releases, staging deployments

### Production Environment
- **Purpose**: Live deployment
- **Features**: Optimized for performance, security-hardened
- **Dependencies**: Locked, pinned production dependencies only
- **Usage**: Live customer-facing deployments

## CLI Commands for Environment Management

AgentOrchestrator includes built-in CLI commands for managing environments:

```bash
# Display version information
ao version

# Set up a specific environment
ao setup-env dev
ao setup-env test
ao setup-env uat
ao setup-env prod

# Create environment-specific .env files
ao create-env-files

# Run development server with hot reloading
ao dev

# Run tests with or without coverage
ao test
ao test --coverage

# Build distribution packages for production
ao build

# Start server in specific environment
ao serve --env dev
ao serve --env test
ao serve --env uat
ao serve --env prod
```

## Helper Scripts for Docker Environments

For easier management of Docker environments, we provide helper scripts in both PowerShell and Bash:

### Windows (PowerShell)

```powershell
# Start development environment
.\scripts\run_environments.ps1 -Environment dev

# Start with rebuilding the image
.\scripts\run_environments.ps1 -Environment dev -Build

# Stop the environment
.\scripts\run_environments.ps1 -Environment dev -Down

# Run all environments (warning: potential port conflicts)
.\scripts\run_environments.ps1 -Environment all -Build
```

### Linux/macOS (Bash)

```bash
# Start development environment
./scripts/run_environments.sh dev

# Start with rebuilding the image
./scripts/run_environments.sh dev --build

# Stop the environment
./scripts/run_environments.sh dev --down

# Run all environments (warning: potential port conflicts)
./scripts/run_environments.sh all --build
```

## Docker Compose Profiles

For containerized environments, we provide Docker Compose profiles:

```bash
# Development environment with hot reloading
docker-compose --profile dev up

# Testing environment for running tests
docker-compose --profile test up

# UAT environment for testing production build
docker-compose --profile uat up

# Production environment
docker-compose --profile prod up
```

## Port Mapping for Docker Environments

Each environment has a specific port mapping:

| Environment | Container Port | Host Port | Access URL |
|-------------|----------------|-----------|------------|
| Development | 8000 | 8000 | http://localhost:8000 |
| UAT | 8000 | 8001 | http://localhost:8001 |
| Production | 8000 | 8000 | http://localhost:8000 |

**Note:** You cannot run both Development and Production environments simultaneously due to port conflicts unless you modify the port mappings in the `docker-compose.yml` file.

## Distribution & Deployment

### Building Production Packages

AgentOrchestrator can be built into optimized Python packages:

```bash
# Build both wheel and source distribution
ao build

# Build only wheel package
ao build --wheel --no-sdist

# Specify output directory
ao build --output-dir ./dist
```

### Docker Image Management

We maintain Docker images on Docker Hub for all environments:

```
ameenalam/agentorchestrator-dev:latest   # Development
ameenalam/agentorchestrator-test:latest  # Testing
ameenalam/agentorchestrator-uat:latest   # UAT
ameenalam/agentorchestrator:latest       # Production
```

To build and push images to Docker Hub:

```powershell
# Build all images
docker-compose build

# Push to Docker Hub (requires Docker Hub login)
.\scripts\push_images.ps1
```

Or on Linux/macOS:

```bash
# Build and push in one command
./scripts/build_and_push_images.sh
```

### Production Deployment

For production, our Docker image uses a multi-stage build process:

1. **Build Stage**: Creates a wheel package from the source code
2. **Run Stage**: Installs only the wheel package and locked dependencies

This ensures:
- Smaller image size
- Faster startup
- No source code in the production container
- Predictable dependencies

## Environment-specific .env Files

- `.env.dev`: Development environment settings
- `.env.test`: Test environment settings
- `.env.uat`: UAT environment settings
- `.env`: Production environment settings

## Dependency Management

### Using UV for Dependencies

We use [UV](https://github.com/astral-sh/uv) for faster, more reliable dependency management:

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Install test dependencies
uv pip install -e ".[test]"

# Install production dependencies
uv pip install -e .
```

### Locking Dependencies for Production

For production deployments, we generate a locked requirements file:

```bash
# Generate locked requirements
uv pip compile pyproject.toml --python-version=3.12 --no-dev --output-file=requirements.lock
```

## CI/CD Pipeline Strategy

Our CI/CD pipeline is designed to test, validate, and deploy code through all environments:

1. **Test Stage**:
   - Runs linting and unit tests
   - Uses test environment with test dependencies

2. **UAT Stage**:
   - Runs integration tests
   - Uses UAT environment with production-only dependencies
   - Only runs for main branch and release branches

3. **Build Stage**:
   - Builds distribution packages
   - Generates locked requirements
   - Builds Docker image with multi-stage process
   - Only runs for main branch

4. **Production Stage**:
   - Deploys Docker image to production
   - Requires deployment environment approval
   - Only runs for main branch

## Best Practices

1. **Use the built-in CLI tools**
   - The `ao` CLI command provides everything needed for environment management

2. **Keep environments isolated**
   - Each environment has its own virtual environment and .env file
   - Use the appropriate profile for Docker Compose

3. **For Docker operations**
   - Use the helper scripts (`run_environments.ps1`/`run_environments.sh`) for ease of use
   - Be aware of port conflicts between environments
   - Check container logs for troubleshooting with `docker logs <container_name>`

4. **For production deployments**
   - Always build a proper package with `ao build`
   - Use the multi-stage Dockerfile
   - Only expose necessary volumes (src/routes)

5. **CI/CD Pipeline Integration**
   - Our GitHub Actions workflow uses the same environment management strategy
   - Each stage uses the appropriate environment

6. **Update dependencies strategically**
   - Schedule regular dependency updates
   - Test thoroughly after updates 