"""Main entry point for bushfire-drone-simulation."""

import logging
from sys import stderr
from typing import List

import typer
from tqdm import tqdm

from bushfire_drone_simulation.gui.gui import start_gui, start_map_gui
from bushfire_drone_simulation.parameters import JSONParameters
from bushfire_drone_simulation.simple_coordinator import SimpleUAVCoordinator, SimpleWBCoordinator
from bushfire_drone_simulation.simulator import Simulator

_LOG = logging.getLogger(__name__)
app = typer.Typer()

PARAMETERS_FILENAME_ARGUMENT = typer.Option("parameters.json", help="Path to parameters file.")


def main():
    """Entry point for bushfire_drone_simulation."""
    logging.basicConfig(stream=stderr, level=logging.WARNING)
    app()


@app.command()
def gui(
    parameters_filename: str = PARAMETERS_FILENAME_ARGUMENT,
):
    """Start a GUI version of the drone simulation."""
    simulator = run_simulation(parameters_filename)[0]
    if simulator is not None:
        start_gui(simulator)


@app.command()
def map_gui():
    """Start a GUI version of the drone simulation."""
    start_map_gui()


@app.command()
def run_simulation(parameters_filename: str = PARAMETERS_FILENAME_ARGUMENT) -> List[Simulator]:
    """Run bushfire drone simulation."""
    params = JSONParameters(parameters_filename)
    to_return = []
    for scenario_idx in tqdm(range(0, len(params.scenarios)), unit="scenario"):
        simulator = Simulator(params, scenario_idx)
        uav_coordinator = SimpleUAVCoordinator(simulator.uavs, simulator.uav_bases)
        wb_coordinator = SimpleWBCoordinator(
            simulator.water_bombers, simulator.water_bomber_bases_dict, simulator.water_tanks
        )
        simulator.run_simulation(uav_coordinator, wb_coordinator)

        simulator.output_results(params, scenario_idx)
        to_return.append(simulator)
    return to_return
