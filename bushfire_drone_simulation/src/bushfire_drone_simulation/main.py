"""Main entry point for bushfire-drone-simulation."""

import logging
from sys import stderr
from typing import List

import typer

from bushfire_drone_simulation.coordinator import Coordinator
from bushfire_drone_simulation.fire_utils import Base, WaterTank
from bushfire_drone_simulation.gui.gui import start_gui
from bushfire_drone_simulation.lightning import Lightning, reduce_lightning_to_ignitions
from bushfire_drone_simulation.read_csv import (
    JSONParameters,
    read_lightning,
    read_locations_with_capacity,
)

_LOG = logging.getLogger(__name__)
app = typer.Typer()


def main():
    """Entry point for bushfire_drone_simulation."""
    logging.basicConfig(stream=stderr, level=logging.DEBUG)
    app()


@app.command()
def gui():
    """Start a GUI version of the drone simulation."""
    start_gui()


PARAMETERS_FILENAME_ARGUMENT = typer.Option(
    "csv_data/parameters.json", help="Path to parameters file."
)

# SCENARIO_NUM_ARGUMENT = typer.Option(1, help="Scenario number to run.")


@app.command()
def run_simulation(parameters_filename: str = PARAMETERS_FILENAME_ARGUMENT):
    """Run bushfire drone simulation."""
    # Read parameters
    # params = CSVParameters(parameters_filename, scenario)
    params = JSONParameters(parameters_filename)

    # Read and initialise data
    uav_bases = read_locations_with_capacity(params.get_attribute("uav_bases_filename"), Base)
    water_bomber_bases = read_locations_with_capacity(
        params.get_attribute("water_bomber_bases_filename"), Base
    )
    water_tanks = read_locations_with_capacity(
        params.get_attribute("water_tanks_filename"), WaterTank
    )
    # FIXME(water tank capacity) # pylint: disable=fixme

    uavs = params.process_uavs()
    water_bombers, water_bomber_bases = params.process_water_bombers(water_bomber_bases)

    # lightning_strikes = read_lightning(
    #     params.get_attribute("lightning_filename"), params.get_attribute("ignition_probability")
    # )
    lightning_strikes = read_lightning(
        "csv_data/lightning.csv", params.get_attribute("ignition_probability")
    )
    lightning_strikes.sort()  # By strike time

    coordinator = Coordinator(uavs, uav_bases, water_bombers, water_bomber_bases, water_tanks)

    process_lightning(lightning_strikes, coordinator)
    _LOG.info("Completed processing lightning strikes")

    ignitions = reduce_lightning_to_ignitions(lightning_strikes)
    ignitions.sort()  # By time of inspection

    process_ignitions(ignitions, coordinator)
    _LOG.info("Completed processing ignitions")


def process_lightning(lightning_strikes: List[Lightning], coordinator: Coordinator):
    """Process lightning strikes by feeding to coordinator."""
    for lightning in lightning_strikes:
        while (
            coordinator.get_next_event_time() is not None
            and coordinator.get_next_event_time() < lightning.spawn_time
        ):
            coordinator.lightning_update()
        coordinator.lightning_update(lightning)


def process_ignitions(ignitions, coordinator):
    """Process ignitions by feeding to coordinator."""
    for ignition in ignitions:
        while (
            coordinator.get_next_event_time() is not None
            and coordinator.get_next_event_time() < ignition.spawn_time
        ):
            coordinator.ignition_update()
        coordinator.ignition_update(ignition)
