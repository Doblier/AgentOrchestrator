# Push Docker images to Docker Hub
# Run this script after building the images with docker-compose build

# First, login to Docker Hub
Write-Host "Logging into Docker Hub..." -ForegroundColor Cyan
Write-Host "Please enter your Docker Hub credentials when prompted." -ForegroundColor Yellow
docker login

# Push each image
Write-Host "Pushing dev image..." -ForegroundColor Green
docker push ameenalam/agentorchestrator-dev:latest

Write-Host "Pushing test image..." -ForegroundColor Green
docker push ameenalam/agentorchestrator-test:latest

Write-Host "Pushing UAT image..." -ForegroundColor Green
docker push ameenalam/agentorchestrator-uat:latest

Write-Host "Pushing production image..." -ForegroundColor Green
docker push ameenalam/agentorchestrator:latest

Write-Host "All images have been successfully pushed to Docker Hub!" -ForegroundColor Cyan
Write-Host "You can now use these images with: docker pull ameenalam/agentorchestrator-[dev|test|uat]:latest" -ForegroundColor White 