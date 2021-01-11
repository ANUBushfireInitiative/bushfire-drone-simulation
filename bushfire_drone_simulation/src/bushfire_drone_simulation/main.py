"""Main entry point for bushfire-drone-simulation."""

import logging
from sys import stderr
from typing import List

import typer

from bushfire_drone_simulation.coordinator import Coordinator
from bushfire_drone_simulation.fire_utils import Base, WaterTank
from bushfire_drone_simulation.gui.gui import start_gui, start_map_gui
from bushfire_drone_simulation.lightning import Lightning, reduce_lightning_to_ignitions
from bushfire_drone_simulation.read_csv import JSONParameters, read_lightning, read_locations

_LOG = logging.getLogger(__name__)
app = typer.Typer()

PARAMETERS_FILENAME_ARGUMENT = typer.Option(
    "csv_data/parameters.json", help="Path to parameters file."
)


def main():
    """Entry point for bushfire_drone_simulation."""
    logging.basicConfig(stream=stderr, level=logging.INFO)
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


# SCENARIO_NUM_ARGUMENT = typer.Option(1, help="Scenario number to run.")


@app.command()
def run_simulation(
    parameters_filename: str = PARAMETERS_FILENAME_ARGUMENT,
):
    """Run bushfire drone simulation."""
    # Read parameters
    params = JSONParameters(parameters_filename)

    if params.abort:
        return None, None

    ret = []

    for scenario_idx in params.scenarios_to_run:
        # Read and initialise data
        uav_bases = read_locations(
            params.get_relative_filepath("uav_bases_filename", scenario_idx), Base
        )
        water_bomber_bases = read_locations(
            params.get_relative_filepath("water_bomber_bases_filename", scenario_idx), Base
        )
        water_tanks = read_locations(
            params.get_relative_filepath("water_tanks_filename", scenario_idx), WaterTank
        )
        # FIXME(water tank capacity) # pylint: disable=fixme

        uavs = params.process_uavs(scenario_idx)
        water_bombers, water_bomber_bases = params.process_water_bombers(
            water_bomber_bases, scenario_idx
        )

        lightning_strikes = read_lightning(
            params.get_relative_filepath("lightning_filename", scenario_idx),
            params.get_attribute("ignition_probability", scenario_idx),
        )
        # lightning_strikes = read_lightning(
        # lightning_filename, params.get_attribute("ignition_probability")
        # )
        lightning_strikes.sort()  # By strike time

        coordinator = Coordinator(uavs, uav_bases, water_bombers, water_bomber_bases, water_tanks)

        process_lightning(lightning_strikes, coordinator)
        _LOG.info("Completed processing lightning strikes")

        ignitions = reduce_lightning_to_ignitions(lightning_strikes)
        ignitions.sort()  # By time of inspection

        process_ignitions(ignitions, coordinator)
        _LOG.info("Completed processing ignitions")

        params.write_to_output_folder(lightning_strikes, water_bombers, water_tanks, scenario_idx)

        ret.append((coordinator, lightning_strikes))

    return ret


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
