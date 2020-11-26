"""Main entry point for bushfire-drone-simulation."""

import logging
from sys import stderr

import typer

_LOG = logging.getLogger(__name__)
app = typer.Typer()


def main():
    """Entry point for bushfire_drone_simulation."""
    logging.basicConfig(stream=stderr, level=logging.INFO)
    app()


@app.command()
def func1(x: int = typer.Argument(..., help="Help stuff"), y: int = typer.Option(7, help="Help 2")):
    """Test function 1."""
    _LOG.info("Hello world from func1")
    print(x, y)


@app.command()
def func2():
    """Test function 2."""
    _LOG.info("Hello world from func2")
