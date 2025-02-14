"""
Command-line interface for AgentOrchestrator.
"""

import typer
from rich import print
from rich.console import Console
from rich.panel import Panel

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
    reload: bool = typer.Option(False, help="Enable auto-reload on code changes")
):
    """Start the AgentOrchestrator server."""
    import uvicorn
    console.print("[bold green]Starting AgentOrchestrator server...[/]")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload
    )

if __name__ == "__main__":
    app() 