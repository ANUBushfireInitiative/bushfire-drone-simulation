"""Main entry point for bushfire-drone-simulation."""

import logging
from pathlib import Path
from sys import stderr
from typing import List, Optional

import typer

from bushfire_drone_simulation.gui.gui import start_gui, start_gui_from_file
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
        start_gui()
    else:
        params = JSONParameters(parameters_filename)
        simulator = run_simulations(params)[0]
        if simulator is not None:
            start_gui(simulation=simulator)


@app.command()
def gui_from_file(
    scenario_name: str = typer.Argument(..., help="Name of scenario to display in GUI"),
    path: Path = typer.Option("", help="Path to output data folder."),
) -> None:
    """Start a GUI version of the drone simulation."""
    start_gui_from_file(path, scenario_name)


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
    return run_simulations(params)


if __name__ == "__main__":
    main()
