"""Main entry point for bushfire-drone-simulation."""

import logging
from sys import stderr

import typer

from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.coordinator import Coordinator
from bushfire_drone_simulation.fire_utils import Base, WaterTank
from bushfire_drone_simulation.gui.gui import start_gui
from bushfire_drone_simulation.lightning import reduce_lightning_to_ignitions
from bushfire_drone_simulation.read_csv import CSVParameters, read_lightning, read_locations
from bushfire_drone_simulation.units import Distance, Duration, Speed, Volume

_LOG = logging.getLogger(__name__)
_LOG.setLevel(logging.DEBUG)
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
    loc = WaterTank(3, 2, 3)
    print(loc.lat)
    print(isinstance(loc, WaterBomber))
    _LOG.info("Hello world from func2")


@app.command()
def gui():
    """Start a GUI version of the drone simulation."""
    start_gui()


@app.command()
def run_simulation():
    """Run bushfire drone simulation."""
    # Read parameters
    filename = "csv_data/parameters.csv"
    params = CSVParameters(filename)

    # Read and initalize data
    uav_bases = read_locations(params.get_uav_bases_filename(), Base, 0)
    water_bomber_bases = read_locations(params.get_water_bomber_bases_filename(), Base, 0)
    water_tanks = read_locations(params.get_water_tanks_filename(), WaterTank, 1)
    # FIXME(water tank capacity) # pylint: disable=fixme
    uav_spawn_locs = read_locations(params.get_uav_spawn_locations_filename())
    wb_spawn_locs = read_locations(params.get_water_bomber_spawn_locations_filename())
    uavs = []
    id_no = 1
    for base in uav_spawn_locs:
        uavs.append(
            UAV(
                id_no,
                base,
                Speed(int(params.get_max_velocity("UAV")), "km", "hr"),
                Duration(int(params.get_fuel_refill_time("UAV")), "min"),
                Distance(int(params.get_range("UAV")), "km"),
            )
        )
        id_no += 1
    water_bombers = []
    id_no = 1
    for base in wb_spawn_locs:
        water_bombers.append(
            WaterBomber(
                id_no,
                base,
                Speed(int(params.get_max_velocity("WB")), "km", "hr"),
                Distance(int(params.get_range("WB")), "km"),
                Distance(int(params.get_range("WBE")), "km"),
                Duration(int(params.get_water_refill_time()), "min"),
                Duration(int(params.get_fuel_refill_time("WB")), "min"),
                Duration(int(params.get_bombing_time()), "min"),
                Volume(int(params.get_water_capacity()), "L"),
                Volume(int(params.get_water_per_delivery()), "L"),
            )
        )
        id_no += 1
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


def process_lightning(lightning_strikes, coordinator):
    """Process lightning strikes by feeding to coordinator."""
    for lightning in lightning_strikes:
        while can_proceed(coordinator, lightning):
            #     coordinator.get_next_event_time() is not None
            #     or coordinator.get_next_event_time() < lightning.spawn_time
            # ):
            coordinator.lightning_update()
        coordinator.lightning_update(lightning)


def process_ignitions(ignitions, coordinator):
    """Process ignitions by feeding to coordinator."""
    for ignition in ignitions:
        while can_proceed(coordinator, ignition):
            #     coordinator.get_next_event_time() is not None
            #     or coordinator.get_next_event_time() < lightning.spawn_time
            # ):
            coordinator.ignition_update()
        coordinator.ignition_update(ignition)


def can_proceed(coordinator, lightning):
    """Check whether lightning is next event."""
    if coordinator.get_next_event_time() is not None:
        if coordinator.get_next_event_time() < lightning.spawn_time:
            return True
    return False
