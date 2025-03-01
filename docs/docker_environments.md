# Docker Environments Guide

This document explains how to use the various Docker environments in the AgentOrchestrator project.

## Available Environments

AgentOrchestrator comes with four Docker-based environments:

1. **Development**: For active development with hot reloading and debugging
2. **Testing**: For running automated tests
3. **UAT (User Acceptance Testing)**: Pre-production environment for validation
4. **Production**: Optimized for performance and security

## Docker Images

All environments are available as Docker images on Docker Hub:

```
ameenalam/agentorchestrator-dev:latest    # Development
ameenalam/agentorchestrator-test:latest   # Testing
ameenalam/agentorchestrator-uat:latest    # UAT
ameenalam/agentorchestrator:latest        # Production
```

## Quick Start

### Using the Helper Scripts

We've provided helper scripts to make running environments easier:

#### Windows (PowerShell)

```powershell
# Start development environment
.\scripts\run_environments.ps1 -Environment dev

# Start with rebuilding the image
.\scripts\run_environments.ps1 -Environment dev -Build

# Stop the environment
.\scripts\run_environments.ps1 -Environment dev -Down

# Run production environment
.\scripts\run_environments.ps1 -Environment prod

# Run all environments (note: port conflicts possible)
.\scripts\run_environments.ps1 -Environment all
```

#### Linux/macOS (Bash)

```bash
# Start development environment
./scripts/run_environments.sh dev

# Start with rebuilding the image
./scripts/run_environments.sh dev --build

# Stop the environment
./scripts/run_environments.sh dev --down

# Run production environment
./scripts/run_environments.sh prod

# Run all environments (note: port conflicts possible)
./scripts/run_environments.sh all
```

### Using Docker Compose Directly

You can also use Docker Compose profiles directly:

```bash
# Development environment
docker-compose --profile dev up

# Testing environment
docker-compose --profile test up

# UAT environment
docker-compose --profile uat up

# Production environment
docker-compose --profile prod up
```

Add the `-d` flag to run in detached mode (background).

## Environment Details

### Development Environment

```
Image: ameenalam/agentorchestrator-dev:latest
Port: 8000
Configuration: .env.dev
```

The development environment includes:
- Hot reloading of code changes
- Full set of dependencies for development
- Mounted volumes for live editing

### Testing Environment

```
Image: ameenalam/agentorchestrator-test:latest
Configuration: .env.test
```

The testing environment includes:
- Test frameworks and tools (pytest, pytest-cov)
- Test-specific dependencies
- Preconfigured for running test suites

### UAT Environment

```
Image: ameenalam/agentorchestrator-uat:latest
Port: 8001
Configuration: .env.uat
```

The UAT environment includes:
- Production-like setup
- Isolated from development configurations
- Suitable for pre-deployment validation

### Production Environment

```
Image: ameenalam/agentorchestrator:latest
Port: 8000
Configuration: .env
```

The production environment includes:
- Optimized settings for performance
- Minimal dependencies
- Security-focused configuration

## Port Configuration

The container ports are mapped to host ports as follows:

| Environment | Container Port | Host Port | URL |
|-------------|----------------|-----------|-----|
| Development | 8000 | 8000 | http://localhost:8000 |
| UAT | 8000 | 8001 | http://localhost:8001 |
| Production | 8000 | 8000 | http://localhost:8000 |

**Note:** Development and Production environments share the same host port (8000). You cannot run both environments simultaneously without modifying the port mappings in `docker-compose.yml`.

## Pushing Images to Docker Hub

After making changes, you can build and push the images to Docker Hub:

### Windows (PowerShell)

```powershell
# Build all images
docker-compose build

# Push to Docker Hub (requires Docker Hub login)
.\scripts\push_images.ps1

# Alternative: build and push in one command
.\scripts\build_and_push_images.ps1
```

### Linux/macOS (Bash)

```bash
# Build all images
docker-compose build

# Push to Docker Hub (requires Docker Hub login)
./scripts/build_and_push_images.sh
```

## Managing Multiple Environments

When working with multiple environments, follow these best practices:

1. **Avoid port conflicts**: Stop one environment before starting another that uses the same port
   ```powershell
   .\scripts\run_environments.ps1 -Environment dev -Down
   .\scripts\run_environments.ps1 -Environment prod -Build
   ```

2. **Check running containers**: Use Docker commands to see what's currently running
   ```bash
   docker ps
   ```

3. **View container logs**: Check logs for troubleshooting
   ```bash
   docker logs agentorchestrator-agentorchestrator-uat-1
   docker-compose --profile uat logs -f
   ```

## Customizing Environments

### Environment Variables

Each environment uses its own .env file:
- `.env.dev` - Development
- `.env.test` - Testing
- `.env.uat` - UAT
- `.env` - Production

### Docker Configuration

The Docker setup is defined in multiple files:
- `docker-compose.yml` - Main configuration
- `Dockerfile.dev` - Development image
- `Dockerfile.test` - Testing image
- `Dockerfile` - Production/UAT image

## Troubleshooting

### Common Issues

1. **Redis Connection Errors**
   - Make sure the Redis host is set to `redis` in your .env files
   - Ensure the Redis container is running

2. **Permission Issues**
   - If you encounter permission errors on Linux, you may need to run commands with `sudo`

3. **Port Conflicts**
   - If ports are already in use, modify the port mappings in `docker-compose.yml`
   - Alternatively, stop the conflicting container first:
     ```
     docker stop <container_name>
     ```

4. **Container Name Conflicts**
   - If you see errors about duplicate container names, remove the existing containers:
     ```
     docker rm <container_name>
     ```

### Viewing Logs

```bash
# View logs for a specific environment
docker-compose --profile dev logs -f

# View logs for a specific container
docker logs agentorchestrator-agentorchestrator-dev-1
```

## Additional Resources

- [Environment Management Strategy](environment_management.md)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Docker Hub Repository](https://hub.docker.com/r/ameenalam/agentorchestrator) 