"""Container class for GUI Data."""

import math
from pathlib import Path
from typing import List, Sequence

from bushfire_drone_simulation.aircraft import Aircraft
from bushfire_drone_simulation.fire_utils import Location
from bushfire_drone_simulation.gui.gui_objects import GUIAircraft, GUILightning, GUIPoint
from bushfire_drone_simulation.read_csv import CSVFile
from bushfire_drone_simulation.simulator import Simulator

HOURS_TO_SECONDS = 3600


class GUIData:
    """Object for holding GUI data."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        lightning: List[GUILightning],
        ignitions: List[GUILightning],
        uavs: List[GUIAircraft],
        water_bombers: List[GUIAircraft],
        uav_bases: List[GUIPoint],
        wb_bases: List[GUIPoint],
        watertanks: List[GUIPoint],
    ):
        """Initialize a GUI data object.

        Args:
            lightning (List[GUILightning]): lightning
            ignitions (List[GUILightning]): ignitions
            uavs (List[GUIAircraft]): uavs
            water_bombers (List[GUIAircraft]): wbs
            uav_bases (List[GUIPoint]): uav_bases
            wb_bases (List[GUIPoint]): wb_bases
            watertanks (List[GUIPoint]): watertanks
        """
        self.lightning = lightning
        self.ignitions = ignitions
        self.uavs = uavs
        self.uav_lines = [line for uav in uavs for line in uav.aircraft_lines]
        self.water_bombers = water_bombers
        self.wb_lines = [line for wb in water_bombers for line in wb.aircraft_lines]
        self.uav_bases = uav_bases
        self.wb_bases = wb_bases
        self.watertanks = watertanks
        if len(water_bombers) + len(uavs) == 0:
            self.max_time = 0.0
        else:
            self.max_time = max(event.time for a in water_bombers + uavs for event in a.events)

    @classmethod
    def from_simulator(cls, simulation: Simulator) -> "GUIData":
        """Create GUI data from a simulator object.

        Args:
            simulation (Simulator): simulation
        """
        lightning = extract_simulation_lightning(simulation, ignited=False)
        ignitions = extract_simulation_lightning(simulation, ignited=True)
        uavs = extract_simulation_aircraft(simulation, "uav")
        water_bombers = extract_simulation_aircraft(simulation, "wb")
        uav_bases = extract_simulation_uav_bases(simulation)
        wb_bases = extract_simulation_wb_bases(simulation)
        watertanks = extract_simulation_water_tanks(simulation)
        return cls(lightning, ignitions, uavs, water_bombers, uav_bases, wb_bases, watertanks)

    @classmethod
    def from_output(
        cls, path: Path, scenario_name: str  # pylint: disable=unused-argument
    ) -> "GUIData":
        """Generate GUI data from output of a prior simulation scenario.

        Args:
            path (Path): path
            scenario_name (str): scenario_name
        """
        lightning = extract_lightning_from_output(path, scenario_name, ignited=False)
        ignitions = extract_lightning_from_output(path, scenario_name, ignited=True)
        uavs: List[GUIAircraft] = []
        water_bombers: List[GUIAircraft] = []
        uav_bases: List[GUIPoint] = []
        wb_bases: List[GUIPoint] = []
        watertanks: List[GUIPoint] = []
        return cls(lightning, ignitions, uavs, water_bombers, uav_bases, wb_bases, watertanks)


def extract_simulation_lightning(simulation: Simulator, ignited: bool) -> List[GUILightning]:
    """extract_simulation_lightning.

    Args:
        simulation (Simulator): simulation

    Returns:
        List[GUILightning]:
    """
    to_return: List[GUILightning] = []
    for strike in simulation.lightning_strikes:
        if strike.ignition == ignited:
            to_return.append(
                GUILightning(
                    Location(strike.lat, strike.lon),
                    strike.id_no,
                    strike.spawn_time,
                    strike.inspected_time,
                    strike.suppressed_time,
                    strike.ignition,
                )
            )
    return to_return


def extract_simulation_aircraft(simulation: Simulator, aircraft_type: str) -> List[GUIAircraft]:
    """Extract uavs from simulator.

    Args:
        simulation (Simulator): simulation

    Returns:
        List[GUIAircraft]:
    """
    to_return: List[GUIAircraft] = []
    assert aircraft_type in ["uav", "wb"]
    aircraft_list: Sequence[Aircraft] = (
        simulation.water_bombers if aircraft_type == "wb" else simulation.uavs  # type: ignore
    )
    for aircraft in aircraft_list:
        to_return.append(
            GUIAircraft(aircraft.past_locations, "orange" if aircraft_type == "wb" else "green")
        )
    return to_return


def extract_simulation_uav_bases(simulation: Simulator) -> List[GUIPoint]:
    """Extract uav bases from simulator.

    Args:
        simulation (Simulator): simulation

    Returns:
        List[GUIPoint]:
    """
    to_return: List[GUIPoint] = []
    for uav_base in simulation.uav_bases:
        to_return.append(GUIPoint(Location(uav_base.lat, uav_base.lon), radius=2, colour="grey"))
    return to_return


def extract_simulation_wb_bases(simulation: Simulator) -> List[GUIPoint]:
    """Extract water bomber bases from simulator.

    Args:
        simulation (Simulator): simulation

    Returns:
        List[GUIPoint]:
    """
    to_return: List[GUIPoint] = []
    for wb_base in simulation.water_bomber_bases_list:
        to_return.append(GUIPoint(Location(wb_base.lat, wb_base.lon), radius=3, colour="black"))
    return to_return


def extract_simulation_water_tanks(simulation: Simulator) -> List[GUIPoint]:
    """Extract water tanks from simulator.

    Args:
        simulation (Simulator): simulation

    Returns:
        List[GUIPoint]:
    """
    to_return: List[GUIPoint] = []
    for water_tank in simulation.water_tanks:
        to_return.append(
            GUIPoint(Location(water_tank.lat, water_tank.lon), radius=2, colour="blue")
        )
    return to_return


def extract_lightning_from_output(
    path: Path, scenario_name: str, ignited: bool
) -> List[GUILightning]:
    """extract_lightning_from_output.

    Args:
        path (Path): path
        scenario_name (str): scenario_name
        ignited (bool): ignited

    Returns:
        List[GUILightning]:
    """
    to_return: List[GUILightning] = []
    lightning_csv = CSVFile(
        path / f"{scenario_name}{'_' if scenario_name else ''}simulation_output.csv"
    )
    for row in lightning_csv:
        if math.isnan(row[6]) != ignited:
            to_return.append(
                GUILightning(
                    Location(row[2], row[3]),
                    row[1],
                    row[4] * HOURS_TO_SECONDS,
                    row[5] * HOURS_TO_SECONDS,
                    row[6] * HOURS_TO_SECONDS if ignited else None,
                    ignited,
                )
            )
    return to_return
