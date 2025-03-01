"""
Command-line interface for AgentOrchestrator.
"""

import os
import sys
import shutil
from pathlib import Path
import subprocess
import typer
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import List, Optional

app = typer.Typer(
    name="agentorchestrator",
    help="A powerful agent orchestration framework",
    add_completion=False,
)

console = Console()

@app.command()
def version():
    """Display the current version of AgentOrchestrator."""
    from agentorchestrator import __version__
    console.print(
        Panel.fit(
            f"[bold blue]AgentOrchestrator[/] version: [bold green]{__version__}[/]",
            title="Version Info"
        )
    )

@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind the server to"),
    port: int = typer.Option(8000, help="Port to bind the server to"),
    reload: bool = typer.Option(False, help="Enable auto-reload on code changes"),
    env: str = typer.Option("prod", help="Environment to use (dev, test, uat, prod)")
):
    """Start the AgentOrchestrator server."""
    if env == "dev":
        console.print("[yellow]⚠️  Running in DEVELOPMENT mode with HOT RELOADING[/]")
        reload = True
    elif env == "prod":
        console.print("[green]🚀 Running in PRODUCTION mode with optimized settings[/]")
        reload = False
    
    # Load the appropriate .env file
    env_file = f".env.{env}" if env != "prod" else ".env"
    if not os.path.exists(env_file):
        console.print(f"[bold red]Error:[/] Environment file {env_file} not found")
        if env != "prod":
            create_env = typer.confirm("Do you want to create it from .env.example?")
            if create_env:
                shutil.copy(".env.example", env_file)
                console.print(f"[green]Created {env_file} from .env.example[/]")
            else:
                return
    
    console.print(f"[bold green]Starting AgentOrchestrator server ({env} environment)...[/]")
    
    import uvicorn
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        reload_dirs=["src"] if reload else None,
        workers=1 if reload else min(os.cpu_count() or 1, 4),
        log_level="info" if env == "prod" else "debug"
    )

@app.command()
def dev(
    host: str = typer.Option("0.0.0.0", help="Host to bind the server to"),
    port: int = typer.Option(8000, help="Port to bind the server to")
):
    """Start the development server with hot reloading."""
    console.print("[bold blue]Starting development server with hot reloading...[/]")
    serve(host=host, port=port, reload=True, env="dev")

@app.command()
def test(
    args: List[str] = typer.Argument(None, help="Arguments to pass to pytest"),
    coverage: bool = typer.Option(False, help="Run with coverage report"),
    path: str = typer.Option("", help="Specific test path to run (e.g., tests/test_main.py)")
):
    """Run tests with pytest."""
    try:
        import pytest
    except ImportError:
        console.print("[bold red]Error:[/] pytest not found. Install with 'uv add pytest --dev'")
        return
    
    console.print("[bold blue]Running tests...[/]")
    
    cmd = ["pytest"]
    if coverage:
        cmd.extend(["--cov=agentorchestrator", "--cov-report=term", "--cov-report=html"])
    
    # Add specific path if provided
    if path:
        cmd.append(path)
    elif not args:  # If no args and no path, default to main tests
        cmd.append("tests/test_main.py")
        
    if args:
        cmd.extend(args)
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        console.print("[bold green]✅ All tests passed![/]")
    else:
        console.print("[bold red]❌ Tests failed[/]")

@app.command()
def build(
    output_dir: str = typer.Option("dist", help="Output directory for built packages"),
    clean: bool = typer.Option(True, help="Clean output directory before building"),
    wheel: bool = typer.Option(True, help="Build wheel package"),
    sdist: bool = typer.Option(True, help="Build source distribution")
):
    """Build production-ready distribution packages."""
    try:
        import build as python_build
    except ImportError:
        console.print("[bold red]Error:[/] build package not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "build"])
    
    console.print("[bold blue]Building production packages...[/]")
    
    # Prepare the output directory
    output_path = Path(output_dir)
    if clean and output_path.exists():
        console.print(f"Cleaning {output_dir}...")
        shutil.rmtree(output_path)
    output_path.mkdir(exist_ok=True, parents=True)
    
    # Build the packages
    build_args = [sys.executable, "-m", "build", "--outdir", output_dir]
    if wheel and not sdist:
        build_args.append("--wheel")
    elif sdist and not wheel:
        build_args.append("--sdist")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Building packages...", total=1)
        result = subprocess.run(build_args, capture_output=True, text=True)
        progress.update(task, advance=1)
    
    if result.returncode == 0:
        built_files = list(output_path.glob("*"))
        console.print(f"[bold green]✅ Build successful! {len(built_files)} package(s) created:[/]")
        for file in built_files:
            console.print(f"  - {file.name}")
        console.print("\n[bold]To install the built package:[/]")
        console.print(f"  uv pip install {output_path / built_files[0].name}")
    else:
        console.print("[bold red]❌ Build failed[/]")
        console.print(result.stderr)
        sys.exit(result.returncode)

@app.command()
def setup_env(
    env_type: str = typer.Argument(..., help="Environment type (dev, test, uat, prod)"),
    force: bool = typer.Option(False, help="Force recreation of the environment")
):
    """Set up a virtual environment for the specified environment type."""
    valid_envs = ["dev", "test", "uat", "prod"]
    if env_type not in valid_envs:
        console.print(f"[bold red]Error:[/] Invalid environment type. Choose from: {', '.join(valid_envs)}")
        sys.exit(1)
    
    venv_dir = f".venv-{env_type}"
    if os.path.exists(venv_dir) and not force:
        console.print(f"[yellow]Environment {venv_dir} already exists.[/]")
        if not typer.confirm("Do you want to recreate it?"):
            console.print("Aborted.")
            return
    
    console.print(f"[bold blue]Setting up {env_type} environment...[/]")
    
    # Create virtual environment
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "uv"], check=True)
    except subprocess.CalledProcessError:
        console.print("[bold red]Failed to install uv. Please install it manually.[/]")
        sys.exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # Create venv
        task = progress.add_task("Creating virtual environment...", total=1)
        try:
            subprocess.run(["uv", "venv", venv_dir], check=True)
            progress.update(task, advance=1)
        except subprocess.CalledProcessError:
            progress.update(task, completed=True)
            console.print("[bold red]Failed to create virtual environment.[/]")
            sys.exit(1)
        
        # Install dependencies
        task = progress.add_task("Installing dependencies...", total=1)
        try:
            extras = []
            if env_type == "dev":
                extras.append("dev")
            elif env_type == "test":
                extras.append("test")
            
            if extras:
                extras_str = ",".join(extras)
                install_cmd = ["uv", "pip", "install", "-e", f".[{extras_str}]"]
            else:
                install_cmd = ["uv", "pip", "install", "-e", "."]
            
            # Use the appropriate Python from the venv
            if os.name == "nt":  # Windows
                python_path = os.path.join(venv_dir, "Scripts", "python")
            else:  # Unix-like
                python_path = os.path.join(venv_dir, "bin", "python")
            
            env = os.environ.copy()
            env["VIRTUAL_ENV"] = os.path.abspath(venv_dir)
            
            subprocess.run(install_cmd, check=True, env=env)
            progress.update(task, advance=1)
        except subprocess.CalledProcessError:
            progress.update(task, completed=True)
            console.print("[bold red]Failed to install dependencies.[/]")
            sys.exit(1)
    
    console.print(f"[bold green]✅ {env_type.upper()} environment setup complete![/]")
    if os.name == "nt":  # Windows
        console.print(f"[bold]To activate:[/] {venv_dir}\\Scripts\\activate")
    else:  # Unix-like
        console.print(f"[bold]To activate:[/] source {venv_dir}/bin/activate")

@app.command()
def create_env_files():
    """Create environment-specific .env files from .env.example."""
    if not os.path.exists(".env.example"):
        console.print("[bold red]Error:[/] .env.example not found")
        return
    
    for env in ["dev", "test", "uat", "prod"]:
        target = ".env" if env == "prod" else f".env.{env}"
        if not os.path.exists(target):
            shutil.copy(".env.example", target)
            console.print(f"[green]Created {target} from .env.example[/]")
        else:
            console.print(f"[yellow]{target} already exists, skipping[/]")
    
    console.print("[bold green]✅ Environment files created.[/]")
    console.print("[bold]Remember to update each file with environment-specific values.[/]")

# Command function exports for entry points
def serve_command():
    """Entry point for ao-serve command."""
    app(["serve"])

def build_command():
    """Entry point for ao-build command."""
    app(["build"])

def dev_command():
    """Entry point for ao-dev command."""
    app(["dev"])

def test_command():
    """Entry point for ao-test command."""
    app(["test"])

if __name__ == "__main__":
    app() 