"""Main entry point for bushfire-drone-simulation."""

import logging

import typer

_LOG = logging.getLogger(__name__)
app = typer.Typer()


def main():
    """Entry point for bushfire_drone_simulation."""
    app()


@app.command()
def func1():
    """Test function 1."""
    _LOG.info("Hello world from func1")


@app.command()
def func2():
    """Test function 2."""
    _LOG.info("Hello world from func2")
