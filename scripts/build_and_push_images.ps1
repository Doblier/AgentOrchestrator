# Build and push Docker images for all environments

# Build all images
Write-Host "Building all Docker images..." -ForegroundColor Green
docker-compose build

# Tag and push each image
Write-Host "Pushing dev image..." -ForegroundColor Green
docker push ameenalam/agentorchestrator-dev:latest

Write-Host "Pushing test image..." -ForegroundColor Green
docker push ameenalam/agentorchestrator-test:latest

Write-Host "Pushing UAT image..." -ForegroundColor Green
docker push ameenalam/agentorchestrator-uat:latest

Write-Host "Pushing production image..." -ForegroundColor Green
docker push ameenalam/agentorchestrator:latest

Write-Host "All images have been successfully pushed to Docker Hub!" -ForegroundColor Green 