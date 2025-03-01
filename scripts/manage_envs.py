#!/usr/bin/env python
"""
Advanced Environment Management Utility for AgentOrchestrator

This script extends the built-in 'ao' CLI with advanced environment management features.
It helps manage dependencies across different environments:
- development: For active development work with all dev tools
- testing: For running tests with test dependencies
- uat: For user acceptance testing with production-like setup
- production: For generating locked dependencies for production

Usage:
    python scripts/manage_envs.py create <env_name>
    python scripts/manage_envs.py update <env_name>
    python scripts/manage_envs.py lock
    python scripts/manage_envs.py sync-all

Examples:
    python scripts/manage_envs.py create dev
    python scripts/manage_envs.py update test
    python scripts/manage_envs.py lock
    python scripts/manage_envs.py sync-all
"""

import argparse
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
import shutil


ENV_CONFIGS = {
    "dev": {"venv_name": ".venv-dev", "install_args": ["--dev"], "extras": ["dev"]},
    "test": {"venv_name": ".venv-test", "install_args": [], "extras": ["test"]},
    "uat": {"venv_name": ".venv-uat", "install_args": ["--no-dev"], "extras": []},
    "prod": {
        "venv_name": ".venv-prod",
        "install_args": ["--no-dev", "--python-version=3.12"],
        "extras": ["prod"],
    },
}


def run_command(cmd, env=None, shell=False):
    """Run a shell command and print output."""
    print(f"Running: {' '.join(cmd) if not shell else cmd}")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, shell=shell)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result


def get_activate_script(venv_path):
    """Get the path to the activate script based on the OS."""
    if platform.system() == "Windows":
        return venv_path / "Scripts" / "activate.bat"
    return venv_path / "bin" / "activate"


def create_env(env_name, force=False):
    """Create a virtual environment for the specified environment."""
    if env_name not in ENV_CONFIGS:
        print(f"Unknown environment: {env_name}")
        print(f"Available environments: {', '.join(ENV_CONFIGS.keys())}")
        sys.exit(1)

    config = ENV_CONFIGS[env_name]
    venv_path = Path(config["venv_name"])

    if venv_path.exists():
        if force:
            print(f"Removing existing environment: {venv_path}")
            shutil.rmtree(venv_path)
        else:
            print(f"Environment {env_name} already exists at {venv_path}")
            update = input("Do you want to update it? [y/N] ").lower()
            if update != "y":
                return

            # If updating, just run update_env
            update_env(env_name)
            return

    # Create the virtual environment
    print(f"Creating {env_name} environment at {venv_path}")
    run_command(["uv", "venv", str(venv_path)])

    # Install dependencies
    update_env(env_name)

    # Create environment-specific .env file if it doesn't exist
    env_file = f".env{'' if env_name == 'prod' else '.' + env_name}"
    if not os.path.exists(env_file) and os.path.exists(".env.example"):
        print(f"Creating {env_file} from .env.example")
        shutil.copy(".env.example", env_file)

    # Print activation instructions
    activate_script = get_activate_script(venv_path)
    if platform.system() == "Windows":
        print(f"\nTo activate, run: {activate_script}")
    else:
        print(f"\nTo activate, run: source {activate_script}")

    print("\nQuick start with built-in CLI:")
    if env_name == "dev":
        print("  ao dev")
    elif env_name == "test":
        print("  ao test")
    else:
        print(f"  ao serve --env {env_name}")


def update_env(env_name):
    """Update dependencies for the specified environment."""
    if env_name not in ENV_CONFIGS:
        print(f"Unknown environment: {env_name}")
        sys.exit(1)

    config = ENV_CONFIGS[env_name]
    venv_path = Path(config["venv_name"])

    if not venv_path.exists():
        print(f"Environment {env_name} does not exist.")
        create = input("Do you want to create it? [y/N] ").lower()
        if create == "y":
            create_env(env_name)
            return
        else:
            sys.exit(1)

    # Determine install command based on extras
    extras = config["extras"]
    if extras:
        extras_str = ",".join(extras)
        install_cmd = ["uv", "pip", "install", "-e", f".[{extras_str}]"]
    else:
        install_cmd = ["uv", "pip", "install", "-e", "."]

    # Run the command with the virtual environment's Python
    print(f"Updating dependencies for {env_name} environment")

    if platform.system() == "Windows":
        # Windows needs a different approach
        activate_cmd = str(venv_path / "Scripts" / "activate.bat")
        full_cmd = f"{activate_cmd} && {' '.join(install_cmd)}"
        subprocess.run(full_cmd, shell=True)
    else:
        # Unix-like systems
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(venv_path)
        env["PATH"] = f"{venv_path}/bin:{env['PATH']}"
        run_command(install_cmd, env=env)

    print(f"Dependencies updated for {env_name}")


def lock_dependencies(output_file="requirements.lock"):
    """Generate a locked requirements file for production use."""
    print("Generating locked dependencies for production...")

    # Create a production environment if it doesn't exist
    prod_config = ENV_CONFIGS["prod"]
    prod_venv = Path(prod_config["venv_name"])

    if not prod_venv.exists():
        print("Creating production environment for locking dependencies...")
        run_command(["uv", "venv", str(prod_venv)])

        # Install the package in the production environment
        if platform.system() == "Windows":
            activate_cmd = str(prod_venv / "Scripts" / "activate.bat")
            install_cmd = f"{activate_cmd} && uv pip install -e ."
            subprocess.run(install_cmd, shell=True)
        else:
            env = os.environ.copy()
            env["VIRTUAL_ENV"] = str(prod_venv)
            env["PATH"] = f"{prod_venv}/bin:{env['PATH']}"
            run_command(["uv", "pip", "install", "-e", "."], env=env)

    # Generate locked requirements
    cmd = [
        "uv",
        "pip",
        "compile",
        "pyproject.toml",
        "--python-version=3.12",
        "--no-dev",
        "--output-file",
        output_file,
    ]

    if platform.system() == "Windows":
        activate_cmd = str(prod_venv / "Scripts" / "activate.bat")
        full_cmd = f"{activate_cmd} && {' '.join(cmd)}"
        subprocess.run(full_cmd, shell=True)
    else:
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(prod_venv)
        env["PATH"] = f"{prod_venv}/bin:{env['PATH']}"
        run_command(cmd, env=env)

    print(f"Dependencies locked to {output_file}")

    # Also update the lock file for Docker builds
    docker_lock = "requirements.lock"
    if output_file != docker_lock:
        shutil.copy(output_file, docker_lock)
        print(f"Also copied to {docker_lock} for Docker builds")


def sync_all_environments():
    """Update all environments with latest dependencies."""
    print("Syncing all environments with latest dependencies...")

    for env_name in ENV_CONFIGS.keys():
        venv_path = Path(ENV_CONFIGS[env_name]["venv_name"])
        if venv_path.exists():
            print(f"\n=== Updating {env_name} environment ===")
            update_env(env_name)
            time.sleep(1)  # Small delay for readability
        else:
            print(f"\n=== Environment {env_name} does not exist, skipping ===")

    # After updating all envs, regenerate lock file
    print("\n=== Regenerating lock file ===")
    lock_dependencies()

    print("\nAll environments updated successfully!")


def create_integration_test_dir():
    """Create integration test directory structure if it doesn't exist."""
    integration_test_dir = Path("tests/integration")
    if not integration_test_dir.exists():
        integration_test_dir.mkdir(parents=True, exist_ok=True)
        init_file = integration_test_dir / "__init__.py"
        init_file.touch()

        # Create a sample integration test file
        test_file = integration_test_dir / "test_integration.py"
        with open(test_file, "w") as f:
            f.write(
                """
\"\"\"
Integration tests for AgentOrchestrator
\"\"\"

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_endpoint():
    \"\"\"Test the health endpoint.\"\"\"
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "status" in response.json()
"""
            )
        print(f"Created integration test directory at {integration_test_dir}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Advanced Environment Management for AgentOrchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new environment")
    create_parser.add_argument(
        "env", choices=ENV_CONFIGS.keys(), help="Environment to create"
    )
    create_parser.add_argument(
        "--force", action="store_true", help="Force recreation if exists"
    )

    # Update command
    update_parser = subparsers.add_parser(
        "update", help="Update an existing environment"
    )
    update_parser.add_argument(
        "env", choices=ENV_CONFIGS.keys(), help="Environment to update"
    )

    # Lock command
    lock_parser = subparsers.add_parser(
        "lock", help="Generate locked requirements for production"
    )
    lock_parser.add_argument(
        "--output", default="requirements.lock", help="Output file path"
    )

    # Sync-all command
    subparsers.add_parser(
        "sync-all", help="Update all environments and regenerate lock file"
    )

    # Setup-integration command
    subparsers.add_parser(
        "setup-integration", help="Create integration test directory structure"
    )

    args = parser.parse_args()

    # Create scripts directory if it doesn't exist
    Path("scripts").mkdir(exist_ok=True)

    if args.command == "create":
        create_env(args.env, args.force)
    elif args.command == "update":
        update_env(args.env)
    elif args.command == "lock":
        lock_dependencies(args.output)
    elif args.command == "sync-all":
        sync_all_environments()
    elif args.command == "setup-integration":
        create_integration_test_dir()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
