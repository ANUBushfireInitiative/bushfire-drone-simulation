"""Main entry point for bushfire-drone-simulation."""

import logging
from sys import stderr
from typing import List

import typer

from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.coordinator import Coordinator
from bushfire_drone_simulation.fire_utils import Base, WaterTank
from bushfire_drone_simulation.gui.gui import start_gui
from bushfire_drone_simulation.lightning import Lightning, reduce_lightning_to_ignitions
from bushfire_drone_simulation.read_csv import (
    CSVParameters,
    read_lightning,
    read_locations,
    read_locations_with_capacity,
)
from bushfire_drone_simulation.units import Distance, Duration, Speed, Volume

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
    "csv_data/parameters.csv", help="Path to parameters file."
)

SCENARIO_NUM_ARGUMENT = typer.Option(1, help="Scenario number to run.")


@app.command()
def run_simulation(
    parameters_filename: str = PARAMETERS_FILENAME_ARGUMENT, scenario: int = SCENARIO_NUM_ARGUMENT
):
    """Run bushfire drone simulation."""
    # Read parameters
    params = CSVParameters(parameters_filename, scenario)

    # Read and initialise data
    uav_bases = read_locations_with_capacity(params.get_uav_bases_filename(), Base)
    water_bomber_bases = read_locations_with_capacity(
        params.get_water_bomber_bases_filename(), Base
    )
    water_tanks = read_locations_with_capacity(params.get_water_tanks_filename(), WaterTank)
    # FIXME(water tank capacity) # pylint: disable=fixme
    uav_spawn_locs = read_locations(params.get_uav_spawn_locations_filename())
    wb_spawn_locs = read_locations(params.get_water_bomber_spawn_locations_filename())

    uavs = []
    for idx, base_location in enumerate(uav_spawn_locs):
        uavs.append(
            UAV(
                id_no=idx,
                position=base_location,
                max_velocity=Speed(int(params.get_max_velocity("UAV")), "km", "hr"),
                fuel_refill_time=Duration(int(params.get_fuel_refill_time("UAV")), "min"),
                total_range=Distance(int(params.get_range("UAV")), "km"),
                # TODO(Inspection time) Incorporate inspection time
            )
        )

    water_bombers = []
    for idx, base in wb_spawn_locs:
        water_bombers.append(
            WaterBomber(
                id_no=idx,
                position=base,
                max_velocity=Speed(int(params.get_max_velocity("WB")), "km", "hr"),
                range_under_load=Distance(int(params.get_range("WB")), "km"),
                range_empty=Distance(int(params.get_range("WBE")), "km"),
                water_refill_time=Duration(int(params.get_water_refill_time()), "min"),
                fuel_refill_time=Duration(int(params.get_fuel_refill_time("WB")), "min"),
                bombing_time=Duration(int(params.get_bombing_time()), "min"),
                water_capacity=Volume(int(params.get_water_capacity()), "L"),
                water_per_delivery=Volume(int(params.get_water_per_delivery()), "L"),
            )
        )

    # lightning_strikes = read_lightning(
    #     params.get_lightning_filename(), float(params.get_ignition_probability())
    # )
    lightning_strikes = read_lightning(
        "csv_data/lightning.csv", float(params.get_ignition_probability())
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
