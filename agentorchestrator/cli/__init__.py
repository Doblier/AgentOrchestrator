"""
AORBIT CLI tools

This package contains the command-line interface tools for AORBIT.
"""

import click

from agentorchestrator.cli.security_manager import security


@click.group()
def cli():
    """
    AORBIT Command Line Interface

    Use these tools to manage your AORBIT deployment, including security settings,
    agent deployment, and system configuration.
    """
    pass


# Add all command groups
cli.add_command(security)


if __name__ == "__main__":
    cli()
