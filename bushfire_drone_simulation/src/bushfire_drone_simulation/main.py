"""Main entry point for bushfire-drone-simulation."""

import logging
from sys import stderr
from typing import List

import typer
from tqdm import tqdm

from bushfire_drone_simulation.coordinator import Coordinator
from bushfire_drone_simulation.fire_utils import Base, WaterTank
from bushfire_drone_simulation.gui.gui import start_gui, start_map_gui
from bushfire_drone_simulation.lightning import Lightning, reduce_lightning_to_ignitions
from bushfire_drone_simulation.parameters import JSONParameters
from bushfire_drone_simulation.read_csv import read_lightning, read_locations_with_capacity

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
    coordinator, lightning_strikes = run_simulation(parameters_filename)[0]
    if coordinator is not None:
        start_gui(coordinator, lightning_strikes)


@app.command()
def map_gui():
    """Start a GUI version of the drone simulation."""
    start_map_gui()


@app.command()
def run_simulation(
    parameters_filename: str = PARAMETERS_FILENAME_ARGUMENT,
):
    """Run bushfire drone simulation."""
    # Read parameters
    params = JSONParameters(parameters_filename)

    to_return = []

    for scenario_idx in tqdm(range(0, len(params.scenarios)), unit="scenario"):
        # Read and initialise data
        uav_bases = read_locations_with_capacity(
            params.get_relative_filepath("uav_bases_filename", scenario_idx), Base
        )
        water_bomber_bases = read_locations_with_capacity(
            params.get_relative_filepath("water_bomber_bases_filename", scenario_idx), Base
        )
        water_tanks = read_locations_with_capacity(
            params.get_relative_filepath("water_tanks_filename", scenario_idx), WaterTank
        )

        uavs = params.process_uavs(scenario_idx)
        water_bombers, water_bomber_bases = params.process_water_bombers(
            water_bomber_bases, scenario_idx
        )

        lightning_strikes = read_lightning(
            params.get_relative_filepath("lightning_filename", scenario_idx),
            params.get_attribute("ignition_probability", scenario_idx),
        )

        lightning_strikes.sort()  # By strike time

        coordinator = Coordinator(uavs, uav_bases, water_bombers, water_bomber_bases, water_tanks)

        _LOG.info("Processing lightning strikes")
        process_lightning(lightning_strikes, coordinator)
        _LOG.info("Completed processing lightning strikes")

        ignitions = reduce_lightning_to_ignitions(lightning_strikes)
        ignitions.sort()  # By time of inspection

        _LOG.info("Processing ignitions")
        process_ignitions(ignitions, coordinator)
        _LOG.info("Completed processing ignitions")

        params.write_to_output_folder(lightning_strikes, coordinator, scenario_idx)

        to_return.append((coordinator, lightning_strikes))

    return to_return


def process_lightning(lightning_strikes: List[Lightning], coordinator: Coordinator):
    """Process lightning strikes by feeding to coordinator."""
    for lightning in lightning_strikes:
        # while (
        #     coordinator.get_next_event_time() is not None
        #     and coordinator.get_next_event_time() < lightning.spawn_time
        # ):
        #     coordinator.lightning_update()
        coordinator.lightning_update(lightning)


def process_ignitions(ignitions, coordinator):
    """Process ignitions by feeding to coordinator."""
    for ignition in ignitions:
        # while (
        #     coordinator.get_next_event_time() is not None
        #     and coordinator.get_next_event_time() < ignition.spawn_time
        # ):
        #     coordinator.ignition_update()
        coordinator.ignition_update(ignition)
