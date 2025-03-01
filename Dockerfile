# Build stage
FROM python:3.12-slim as builder

WORKDIR /build

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build tools
RUN pip install build uv wheel hatchling

# Copy project files
COPY pyproject.toml .
COPY README.md .
COPY agentorchestrator ./agentorchestrator
COPY src ./src
COPY main.py .

# Build wheel package
RUN python -m build --wheel --no-isolation

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install curl for healthchecks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install production dependencies
COPY requirements.docker.txt /tmp/requirements.docker.txt
RUN pip install uv && uv pip install --system -r /tmp/requirements.docker.txt

# Copy built wheel from builder stage
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install /tmp/*.whl

# Copy main.py to the container - this ensures the main module is available
COPY main.py .

# Create directory for user agents
RUN mkdir -p /app/src/routes
VOLUME /app/src/routes

# Expose the port
EXPOSE 8000

# Command to run the application
CMD ["python", "main.py"] 