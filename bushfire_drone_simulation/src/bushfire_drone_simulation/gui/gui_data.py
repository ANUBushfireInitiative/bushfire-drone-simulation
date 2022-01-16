"""Container class for GUI Data."""

import math
from pathlib import Path
from typing import Dict, List, Sequence, Type, TypeVar, Union

from bushfire_drone_simulation.aircraft import Aircraft, Status, UpdateEvent
from bushfire_drone_simulation.fire_utils import Location, Time
from bushfire_drone_simulation.gui.gui_objects import (
    GUIAircraft,
    GUILightning,
    GUIObject,
    GUIPoint,
    GUIUav,
    GUIWaterBomber,
)
from bushfire_drone_simulation.parameters import JSONParameters
from bushfire_drone_simulation.read_csv import CSVFile
from bushfire_drone_simulation.simulator import Simulator

HOURS_TO_SECONDS = 3600
MINUTES_TO_SECONDS = 60


class GUIData:
    """Object for holding GUI data."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        lightning: Sequence[GUILightning],
        ignitions: Sequence[GUILightning],
        uavs: Sequence[GUIUav],
        water_bombers: Sequence[GUIWaterBomber],
        uav_bases: Sequence[GUIPoint],
        wb_bases: Sequence[GUIPoint],
        watertanks: Sequence[GUIPoint],
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
            aircraft: List[GUIAircraft] = list(water_bombers)
            aircraft += list(uavs)
            self.max_time = max(
                event.time
                for a in aircraft
                for event in a.events
                if event.status != Status.WAITING_AT_BASE
            )

    @property
    def all_lightning(self) -> Sequence[GUILightning]:
        """Get all lightning GUI objects.

        Returns:
            Sequence[GUILightning]:
        """
        return list(self.lightning) + list(self.ignitions)

    @property
    def dict(self) -> Dict[str, Sequence[GUIObject]]:
        """Get dictionary of contained GUIObjects by type.

        Returns:
            Dict[str, Sequence[GUIObject]]:
        """
        return {
            "water_tanks": self.watertanks,
            "uav_bases": self.uav_bases,
            "wb_bases": self.wb_bases,
            "uav_lines": self.uav_lines,
            "wb_lines": self.wb_lines,
            "lightning": self.lightning,
            "ignitions": self.ignitions,
            "uavs": self.uavs,
            "water_bombers": self.water_bombers,
        }

    def __getitem__(self, key: str) -> Sequence[GUIObject]:
        """Get object lists by name."""
        if key not in self.dict:
            raise KeyError(f"Key {key} is not in GUI data")
        return self.dict[key]

    @classmethod
    def from_simulator(cls, simulation: Simulator) -> "GUIData":
        """Create GUI data from a simulator object.

        Args:
            simulation (Simulator): simulation
        """
        lightning = extract_simulation_lightning(simulation, ignited=False)
        ignitions = extract_simulation_lightning(simulation, ignited=True)
        uavs = extract_simulation_aircraft(simulation, GUIUav)
        water_bombers = extract_simulation_aircraft(simulation, GUIWaterBomber)
        uav_bases = extract_simulation_uav_bases(simulation)
        wb_bases = extract_simulation_wb_bases(simulation)
        watertanks = extract_simulation_water_tanks(simulation)
        return cls(lightning, ignitions, uavs, water_bombers, uav_bases, wb_bases, watertanks)

    @classmethod
    def from_output(cls, parameters: JSONParameters, scenario: int) -> "GUIData":
        """Generate GUI data from output of a prior simulation scenario.

        Args:
            parameters_file (Path): path
            scenario_name (str): scenario_name
        """
        scenario_name = parameters.scenarios[scenario]["scenario_name"]
        output_folder = parameters.filepath.parent / parameters.get_attribute(
            "output_folder_name", scenario
        )
        lightning = extract_lightning_from_output(output_folder, scenario_name, ignited=False)
        ignitions = extract_lightning_from_output(output_folder, scenario_name, ignited=True)
        uavs = extract_aircraft_from_output(output_folder, scenario_name, GUIUav)
        water_bombers = extract_aircraft_from_output(output_folder, scenario_name, GUIWaterBomber)
        uav_bases: List[GUIPoint] = extract_bases_from_parameters(parameters, scenario, "uav")
        wb_bases: List[GUIPoint] = extract_bases_from_parameters(
            parameters, scenario, "water_bomber"
        )
        watertanks: List[GUIPoint] = extract_water_tanks_from_output(output_folder, scenario_name)
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


TAircraft = TypeVar("TAircraft", bound=Union[GUIUav, GUIWaterBomber])


def extract_simulation_aircraft(
    simulation: Simulator, aircraft_type: Type[TAircraft]
) -> List[TAircraft]:
    """Extract uavs from simulator.

    Args:
        simulation (Simulator): simulation

    Returns:
        List[GUIAircraft]:
    """
    to_return: List[TAircraft] = []
    aircraft_list: Sequence[Aircraft] = (
        simulation.water_bombers  # type: ignore
        if aircraft_type == GUIWaterBomber
        else simulation.uavs
    )
    for aircraft in aircraft_list:
        to_return.append(aircraft_type(aircraft.past_locations))  # type: ignore
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
                    Location(getattr(row, "Latitude"), getattr(row, "Longitude")),
                    row[1],
                    row[4] * HOURS_TO_SECONDS,
                    (row[4] + row[5]) * HOURS_TO_SECONDS,
                    (row[4] + row[6]) * HOURS_TO_SECONDS if ignited else None,
                    ignited,
                )
            )
    return to_return


def extract_water_tanks_from_output(path: Path, scenario_name: str) -> List[GUIPoint]:
    """Extract water tanks from output of previous simulation.

    Args:
        path (Path): path
        scenario_name (str): scenario_name

    Returns:
        List[GUILightning]:
    """
    to_return: List[GUIPoint] = []
    water_tank_csv = CSVFile(path / f"{scenario_name}{'_' if scenario_name else ''}water_tanks.csv")
    for row in water_tank_csv:
        to_return.append(
            GUIPoint(
                Location(getattr(row, "Latitude"), getattr(row, "Longitude")),
                radius=2,
                colour="blue",
            )
        )
    return to_return


def extract_bases_from_parameters(
    parameters: JSONParameters, scenario: int, aircraft_type: str
) -> List[GUIPoint]:
    """Extract bases from parameters of previous simulation.

    Args:
        parameters (JSONParameters): parameters
        scenario (int): scenario_idx

    Returns:
        List[GUIPoint]:
    """
    to_return: List[GUIPoint] = []
    base_csv = CSVFile(
        parameters.get_relative_filepath(aircraft_type + "_bases_filename", scenario)
    )
    for row in base_csv:
        to_return.append(
            GUIPoint(
                Location(getattr(row, "latitude"), getattr(row, "longitude")),
                radius=2 if aircraft_type == "uav" else 3,
                colour="grey" if aircraft_type == "uav" else "black",
            )
        )
    return to_return


def extract_aircraft_from_output(
    path: Path, scenario_name: str, aircraft_type: Type[TAircraft]
) -> List[TAircraft]:
    """extract_aircraft_from_output.

    Args:
        path (Path): path
        scenario_name (str): scenario_name
        aircraft_type (str): aircraft_type

    Returns:
        List[GUIAircraft]:
    """
    to_return: List[TAircraft] = []
    aircraft_csv = CSVFile(
        path / f"{scenario_name}{'_' if scenario_name else ''}{aircraft_type}_event_updates.csv"
    )
    aircraft_updates: Dict[str, List[UpdateEvent]] = {}
    for row in aircraft_csv:
        aircraft_id = row[1]
        status_str = row.Status  # type: ignore
        try:
            int(status_str.split()[-1])
            status = Status(" ".join(status_str.split()[:-1]))
        except ValueError:
            status = Status(status_str)
        update_event = UpdateEvent(
            aircraft_id,
            getattr(row, "Latitude"),
            getattr(row, "Longitude"),
            Time.from_float(row[4] * MINUTES_TO_SECONDS).get(),
            status,
            row[5],
            row[7],
            row[8],
            row[6],
            0 if aircraft_type == GUIUav else row[9],
            [],
            None,
        )
        if aircraft_id in aircraft_updates:
            aircraft_updates[aircraft_id].append(update_event)
        else:
            aircraft_updates[aircraft_id] = [update_event]

    for _, aircraft in aircraft_updates.items():
        to_return.append(aircraft_type(aircraft))  # type: ignore
    return to_return
