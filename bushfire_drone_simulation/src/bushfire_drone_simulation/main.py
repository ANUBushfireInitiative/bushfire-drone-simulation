"""Main entry point for bushfire-drone-simulation."""

import csv
import logging
from pathlib import Path
from sys import stderr
from typing import List, Optional

import typer
from matplotlib import path

from bushfire_drone_simulation.gui.gui import GUI
from bushfire_drone_simulation.parameters import JSONParameters
from bushfire_drone_simulation.read_csv import read_lightning, read_locations
from bushfire_drone_simulation.simulator import Simulator, run_simulations

app = typer.Typer()


def main() -> None:
    """Entry point for bushfire_drone_simulation."""
    logging.basicConfig(stream=stderr, level=logging.WARNING)
    app()


@app.command()
def gui(
    parameters_filename: Optional[Path] = typer.Argument(None, help="Path to parameters file."),
    parallel: bool = typer.Option(True, help="Use multiple cores to parallelise scenarios"),
) -> None:
    """Start a GUI version of the drone simulation."""
    if parameters_filename is None:
        GUI(None)
    else:
        params = JSONParameters(parameters_filename)
        params.create_output_folder()
        simulator = run_simulations(params, parallel)[0]
        if simulator is not None:
            GUI(parameters_filename)


@app.command()
def gui_from_file(
    path: Path = typer.Argument(..., help="Path to gui json."),
) -> None:
    """Start a GUI version of the drone simulation."""
    GUI(path)


@app.command()
def run_simulation(
    parameters_filename: Optional[Path] = typer.Argument(
        "parameters.json", help="Path to parameters file."
    ),
    parallel: bool = typer.Option(True, help="Use multiple cores to parallelise scenarios"),
) -> List[Simulator]:
    """Run bushfire drone simulation."""
    if parameters_filename is None:
        parameters_filename = Path("parameters.json")
    params = JSONParameters(parameters_filename)
    params.create_output_folder()
    return run_simulations(params, parallel)


@app.command()
def process_lightning(
    lightning_filename: Optional[Path] = typer.Argument(
        "utc6190120_all.csv", help="Path to lightning file."
    )
) -> None:
    """Run bushfire drone simulation."""
    if lightning_filename is None:
        lightning_filename = Path("utc6190120_all.csv")
    lightning = read_lightning(lightning_filename, 0)
    polygon = read_locations("input_data/boundary_polygon.csv")
    polygon_points = [(loc.lat, loc.lon) for loc in polygon]
    boundary = path.Path(polygon_points)
    lightning_to_keep = []
    for strike in lightning:
        if boundary.contains_point([strike.lat, strike.lon]):
            lightning_to_keep.append(strike)

    with open(
        "refined_lightning.csv",
        "w",
        newline="",
        encoding="utf8",
    ) as outputfile:
        filewriter = csv.writer(outputfile)
        filewriter.writerow(
            [
                "latitude",
                "longitude",
                "time",
            ]
        )
        for strike in lightning_to_keep:
            filewriter.writerow([strike.lat, strike.lon, strike.spawn_time / 60])


if __name__ == "__main__":
    main()
