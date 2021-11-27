"""Main entry point for bushfire-drone-simulation."""

import logging
from pathlib import Path
from sys import stderr
from typing import List, Optional

import typer

from bushfire_drone_simulation.gui.gui import start_gui_from_file
from bushfire_drone_simulation.parameters import JSONParameters
from bushfire_drone_simulation.simulator import Simulator, run_simulations

app = typer.Typer()


def main() -> None:
    """Entry point for bushfire_drone_simulation."""
    logging.basicConfig(stream=stderr, level=logging.WARNING)
    app()


@app.command()
def gui(
    parameters_filename: Optional[Path] = typer.Argument(None, help="Path to parameters file.")
) -> None:
    """Start a GUI version of the drone simulation."""
    if parameters_filename is None:
        start_gui_from_file(None)
    else:
        params = JSONParameters(parameters_filename)
        params.create_output_folder()
        simulator = run_simulations(params)[0]
        if simulator is not None:
            start_gui_from_file(parameters_filename)


@app.command()
def gui_from_file(
    path: Path = typer.Option("", help="Path to gui json."),
) -> None:
    """Start a GUI version of the drone simulation."""
    start_gui_from_file(path)


@app.command()
def run_simulation(
    parameters_filename: Optional[Path] = typer.Argument(
        "parameters.json", help="Path to parameters file."
    )
) -> List[Simulator]:
    """Run bushfire drone simulation."""
    if parameters_filename is None:
        parameters_filename = Path("parameters.json")
    params = JSONParameters(parameters_filename)
    params.create_output_folder()
    return run_simulations(params)


if __name__ == "__main__":
    main()
