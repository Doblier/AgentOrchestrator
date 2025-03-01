#!/bin/bash

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored text
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Build and push Docker images for AgentOrchestrator"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --build-only    Only build images, don't push to Docker Hub"
    echo "  --push-only     Only push images to Docker Hub, don't build"
    echo "  --help          Show this help message"
    echo
    echo "Examples:"
    echo "  $0              # Build and push all images"
    echo "  $0 --build-only # Only build all images"
    echo "  $0 --push-only  # Only push all images"
}

# Parse arguments
BUILD=true
PUSH=true

for arg in "$@"; do
    case $arg in
        --build-only)
            PUSH=false
            ;;
        --push-only)
            BUILD=false
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $arg"
            show_usage
            exit 1
            ;;
    esac
done

# Build images if requested
if [ "$BUILD" = true ]; then
    print_info "Building all Docker images..."
    docker-compose build
    
    if [ $? -ne 0 ]; then
        print_error "Failed to build Docker images"
        exit 1
    else
        print_success "Successfully built all Docker images"
    fi
fi

# Push images if requested
if [ "$PUSH" = true ]; then
    print_info "Logging into Docker Hub..."
    echo "Please enter your Docker Hub credentials:"
    docker login
    
    if [ $? -ne 0 ]; then
        print_error "Failed to log into Docker Hub"
        exit 1
    fi
    
    print_info "Pushing development image..."
    docker push ameenalam/agentorchestrator-dev:latest
    
    if [ $? -ne 0 ]; then
        print_error "Failed to push development image"
        exit 1
    else
        print_success "Successfully pushed development image"
    fi
    
    print_info "Pushing test image..."
    docker push ameenalam/agentorchestrator-test:latest
    
    if [ $? -ne 0 ]; then
        print_error "Failed to push test image"
        exit 1
    else
        print_success "Successfully pushed test image"
    fi
    
    print_info "Pushing UAT image..."
    docker push ameenalam/agentorchestrator-uat:latest
    
    if [ $? -ne 0 ]; then
        print_error "Failed to push UAT image"
        exit 1
    else
        print_success "Successfully pushed UAT image"
    fi
    
    print_info "Pushing production image..."
    docker push ameenalam/agentorchestrator:latest
    
    if [ $? -ne 0 ]; then
        print_error "Failed to push production image"
        exit 1
    else
        print_success "Successfully pushed production image"
    fi
    
    print_success "All images have been pushed to Docker Hub"
fi

print_info "Script completed successfully" 