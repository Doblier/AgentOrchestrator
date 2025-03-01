# Deployment Options

AgentOrchestrator is designed to be deployed in various environments, from local development to cloud-based production deployments. This guide will help you deploy your agents in different scenarios.

## Stateless Architecture

AgentOrchestrator follows a stateless architecture, making it ideal for cloud deployments:

- **No Shared Memory**: Agents don't rely on in-memory state between requests
- **Horizontally Scalable**: Deploy multiple instances for increased throughput
- **Resilient**: Instance failures don't affect overall system availability

## Local Development

For local development and testing, you can run:

```bash
python main.py
```

For a more production-like setup with Redis and other services:

```bash
docker-compose up -d
```

## Docker Deployment

### Building a Docker Image

```bash
# Build the Docker image
docker build -t agentorchestrator:latest .

# Run the container
docker run -p 8000:8000 --env-file .env agentorchestrator:latest
```

### Docker Compose

For a complete environment with Redis:

```yaml
# docker-compose.yml
version: '3'

services:
  agentorchestrator:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:latest
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  redis-data:
```

Run with:

```bash
docker-compose up -d
```

## Kubernetes Deployment

For production deployments on Kubernetes:

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentorchestrator
  labels:
    app: agentorchestrator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agentorchestrator
  template:
    metadata:
      labels:
        app: agentorchestrator
    spec:
      containers:
      - name: agentorchestrator
        image: agentorchestrator:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: agentorchestrator-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: agentorchestrator-service
spec:
  selector:
    app: agentorchestrator
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

Apply with:

```bash
kubectl apply -f kubernetes/deployment.yaml
```

## Serverless Deployment

### AWS Lambda with API Gateway

1. Package your application:

```bash
pip install --target ./package -r requirements.txt
cd package
zip -r ../lambda_function.zip .
cd ..
zip -g lambda_function.zip main.py agentorchestrator/
```

2. Create Lambda function using the AWS Console or CLI
3. Configure API Gateway as the trigger
4. Set environment variables in the Lambda configuration

### Google Cloud Run

1. Build the Docker image:

```bash
docker build -t gcr.io/your-project/agentorchestrator:latest .
```

2. Push to Google Container Registry:

```bash
docker push gcr.io/your-project/agentorchestrator:latest
```

3. Deploy to Cloud Run:

```bash
gcloud run deploy agentorchestrator \
  --image gcr.io/your-project/agentorchestrator:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## Scaling Considerations

For production deployments, consider:

1. **Redis Cluster**: For high-availability caching and rate limiting
2. **Prometheus/Grafana**: For monitoring and alerting
3. **Load Balancer**: For distributed traffic across multiple instances
4. **Rate Limiting**: To prevent abuse and control costs
5. **Backup Strategy**: For critical data and configuration

## CI/CD Pipeline

Example GitHub Actions workflow:

```yaml
# .github/workflows/deploy.yml
name: Deploy AgentOrchestrator

on:
  push:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install uv
        uv pip install -r requirements.txt
    
    - name: Run tests
      run: pytest
    
    - name: Build Docker image
      run: docker build -t agentorchestrator:${{ github.sha }} .
    
    - name: Push to Container Registry
      uses: docker/login-action@v1
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Tag and push image
      run: |
        docker tag agentorchestrator:${{ github.sha }} ghcr.io/${{ github.repository }}/agentorchestrator:latest
        docker push ghcr.io/${{ github.repository }}/agentorchestrator:latest
```

## Managed AgentOrchestrator Cloud (Coming Soon)

A fully managed AgentOrchestrator Cloud service is planned, which will offer:

- One-click deployment of agents
- Automatic scaling
- Built-in monitoring and observability
- Pay-as-you-go pricing model
- Enterprise support options

Stay tuned for updates! 