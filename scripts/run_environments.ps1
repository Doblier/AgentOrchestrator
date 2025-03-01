# AgentOrchestrator Environment Runner
# This script provides easy commands to run different environments

param (
    [Parameter(Mandatory=$true)]
    [ValidateSet("dev", "test", "uat", "prod", "all")]
    [string]$Environment,
    
    [switch]$Build,
    
    [switch]$Down
)

# Set colors for better visibility
$colorInfo = "Cyan"
$colorSuccess = "Green"
$colorWarning = "Yellow"
$colorError = "Red"

# Function to display usage information
function Show-Usage {
    Write-Host "AgentOrchestrator Environment Runner" -ForegroundColor $colorInfo
    Write-Host "Usage: .\run_environments.ps1 -Environment [dev|test|uat|prod|all] [-Build] [-Down]" -ForegroundColor White
    Write-Host ""
    Write-Host "Parameters:" -ForegroundColor White
    Write-Host "  -Environment    Environment to run (dev, test, uat, prod, or all)" -ForegroundColor White
    Write-Host "  -Build          Build the Docker images before running" -ForegroundColor White
    Write-Host "  -Down           Stop and remove the containers" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor White
    Write-Host "  .\run_environments.ps1 -Environment dev" -ForegroundColor White
    Write-Host "  .\run_environments.ps1 -Environment prod -Build" -ForegroundColor White
    Write-Host "  .\run_environments.ps1 -Environment all -Down" -ForegroundColor White
}

# Function to run a specific environment
function Run-Environment {
    param (
        [string]$Env,
        [switch]$BuildFlag,
        [switch]$DownFlag
    )
    
    if ($DownFlag) {
        Write-Host "Stopping the $Env environment..." -ForegroundColor $colorWarning
        docker-compose --profile $Env down
        return
    }
    
    if ($BuildFlag) {
        Write-Host "Building the $Env environment..." -ForegroundColor $colorInfo
        docker-compose --profile $Env build
    }
    
    Write-Host "Starting the $Env environment..." -ForegroundColor $colorSuccess
    docker-compose --profile $Env up -d
    
    if ($Env -eq "dev") {
        Write-Host "Development environment is running at http://localhost:8000" -ForegroundColor $colorSuccess
    } elseif ($Env -eq "uat") {
        Write-Host "UAT environment is running at http://localhost:8001" -ForegroundColor $colorSuccess
    } elseif ($Env -eq "prod") {
        Write-Host "Production environment is running at http://localhost:8000" -ForegroundColor $colorSuccess
    }
}

# Main script logic
if ($Environment -eq "all") {
    if ($Down) {
        Write-Host "Stopping all environments..." -ForegroundColor $colorWarning
        docker-compose down
    } else {
        if ($Build) {
            Write-Host "Building all environments..." -ForegroundColor $colorInfo
            docker-compose build
        }
        
        Write-Host "Starting all environments..." -ForegroundColor $colorSuccess
        docker-compose up -d
        
        Write-Host "All environments are running:" -ForegroundColor $colorSuccess
        Write-Host "  Development: http://localhost:8000" -ForegroundColor White
        Write-Host "  UAT: http://localhost:8001" -ForegroundColor White
        Write-Host "  Production: http://localhost:8000 (warning: port conflict with dev)" -ForegroundColor $colorWarning
    }
} else {
    Run-Environment -Env $Environment -BuildFlag:$Build -DownFlag:$Down
}

# Display helpful commands
if (-not $Down) {
    Write-Host "" 
    Write-Host "Helpful commands:" -ForegroundColor $colorInfo
    Write-Host "  View logs: docker-compose --profile $Environment logs -f" -ForegroundColor White
    Write-Host "  Stop containers: .\run_environments.ps1 -Environment $Environment -Down" -ForegroundColor White
    Write-Host "  View running containers: docker ps" -ForegroundColor White
} 