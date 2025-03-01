#!/bin/bash
# AgentOrchestrator Environment Runner
# This script provides easy commands to run different environments

# Set colors for better visibility
COLOR_INFO="\033[0;36m"     # Cyan
COLOR_SUCCESS="\033[0;32m"  # Green
COLOR_WARNING="\033[0;33m"  # Yellow
COLOR_ERROR="\033[0;31m"    # Red
COLOR_RESET="\033[0m"       # Reset color

# Function to display usage information
show_usage() {
    echo -e "${COLOR_INFO}AgentOrchestrator Environment Runner${COLOR_RESET}"
    echo -e "Usage: ./run_environments.sh [dev|test|uat|prod|all] [--build] [--down]"
    echo ""
    echo "Parameters:"
    echo "  Environment    Environment to run (dev, test, uat, prod, or all)"
    echo "  --build        Build the Docker images before running"
    echo "  --down         Stop and remove the containers"
    echo ""
    echo "Examples:"
    echo "  ./run_environments.sh dev"
    echo "  ./run_environments.sh prod --build"
    echo "  ./run_environments.sh all --down"
    exit 1
}

# Function to run a specific environment
run_environment() {
    local env=$1
    local build=$2
    local down=$3
    
    if [ "$down" = true ]; then
        echo -e "${COLOR_WARNING}Stopping the $env environment...${COLOR_RESET}"
        docker-compose --profile $env down
        return
    fi
    
    if [ "$build" = true ]; then
        echo -e "${COLOR_INFO}Building the $env environment...${COLOR_RESET}"
        docker-compose --profile $env build
    fi
    
    echo -e "${COLOR_SUCCESS}Starting the $env environment...${COLOR_RESET}"
    docker-compose --profile $env up -d
    
    if [ "$env" = "dev" ]; then
        echo -e "${COLOR_SUCCESS}Development environment is running at http://localhost:8000${COLOR_RESET}"
    elif [ "$env" = "uat" ]; then
        echo -e "${COLOR_SUCCESS}UAT environment is running at http://localhost:8001${COLOR_RESET}"
    elif [ "$env" = "prod" ]; then
        echo -e "${COLOR_SUCCESS}Production environment is running at http://localhost:8000${COLOR_RESET}"
    fi
}

# Parse command line arguments
if [ $# -lt 1 ]; then
    show_usage
fi

ENVIRONMENT=$1
BUILD=false
DOWN=false

shift
while [ $# -gt 0 ]; do
    case "$1" in
        --build) BUILD=true ;;
        --down) DOWN=true ;;
        *) echo -e "${COLOR_ERROR}Unknown option: $1${COLOR_RESET}"; show_usage ;;
    esac
    shift
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|test|uat|prod|all)$ ]]; then
    echo -e "${COLOR_ERROR}Invalid environment: $ENVIRONMENT${COLOR_RESET}"
    show_usage
fi

# Main script logic
if [ "$ENVIRONMENT" = "all" ]; then
    if [ "$DOWN" = true ]; then
        echo -e "${COLOR_WARNING}Stopping all environments...${COLOR_RESET}"
        docker-compose down
    else
        if [ "$BUILD" = true ]; then
            echo -e "${COLOR_INFO}Building all environments...${COLOR_RESET}"
            docker-compose build
        fi
        
        echo -e "${COLOR_SUCCESS}Starting all environments...${COLOR_RESET}"
        docker-compose up -d
        
        echo -e "${COLOR_SUCCESS}All environments are running:${COLOR_RESET}"
        echo "  Development: http://localhost:8000"
        echo "  UAT: http://localhost:8001"
        echo -e "${COLOR_WARNING}  Production: http://localhost:8000 (warning: port conflict with dev)${COLOR_RESET}"
    fi
else
    run_environment "$ENVIRONMENT" "$BUILD" "$DOWN"
fi

# Display helpful commands
if [ "$DOWN" = false ]; then
    echo ""
    echo -e "${COLOR_INFO}Helpful commands:${COLOR_RESET}"
    echo "  View logs: docker-compose --profile $ENVIRONMENT logs -f"
    echo "  Stop containers: ./run_environments.sh $ENVIRONMENT --down"
    echo "  View running containers: docker ps"
fi 