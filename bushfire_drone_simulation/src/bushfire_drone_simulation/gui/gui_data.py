"""Container class for GUI Data."""

import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Type, TypeVar

from bushfire_drone_simulation.aircraft import Aircraft, Status, UpdateEvent
from bushfire_drone_simulation.fire_utils import Location, Time
from bushfire_drone_simulation.gui.gui_objects import (
    GUIAircraft,
    GUILightning,
    GUIObject,
    GUIPoint,
    GUITarget,
    GUIUav,
    GUIWaterBomber,
    GUIWaterTank,
)
from bushfire_drone_simulation.parameters import JSONParameters
from bushfire_drone_simulation.read_csv import CSVFile, read_targets
from bushfire_drone_simulation.simulator import Simulator
from bushfire_drone_simulation.uav import UAV
from bushfire_drone_simulation.units import Volume
from bushfire_drone_simulation.water_bomber import WaterBomber

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
        watertanks: Sequence[GUIWaterTank],
        targets: Sequence[GUITarget],
    ):
        """Initialize a GUI data object.

        Args:
            lightning (Sequence[GUILightning]): lightning
            ignitions (Sequence[GUILightning]): ignitions
            uavs (Sequence[GUIAircraft]): uavs
            water_bombers (Sequence[GUIAircraft]): wbs
            uav_bases (Sequence[GUIPoint]): uav_bases
            wb_bases (Sequence[GUIPoint]): wb_bases
            watertanks (Sequence[GUIPoint]): watertanks
            targets (Sequence[GUITarget]): targets
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
        self.targets = targets
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
            Dict[str, Sequence[GUIObject]]: GUIObject dictionary
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
            "targets": self.targets,
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
        targets = extract_simulation_targets(simulation)
        return cls(
            lightning, ignitions, uavs, water_bombers, uav_bases, wb_bases, watertanks, targets
        )

    @classmethod
    def from_output(cls, parameters: JSONParameters, scenario_idx: int) -> "GUIData":
        """Generate GUI data from output of a prior simulation scenario.

        Args:
            parameters_file (Path): path
            scenario_name (str): scenario_name
        """
        output_folder = parameters.filepath.parent / parameters.get_attribute(
            "output_folder_name", scenario_idx
        )
        lightning = extract_lightning_from_output(parameters, scenario_idx, ignited=False)
        ignitions = extract_lightning_from_output(parameters, scenario_idx, ignited=True)
        uavs = extract_aircraft_from_output(parameters, output_folder, scenario_idx, GUIUav)
        water_bombers = extract_aircraft_from_output(
            parameters, output_folder, scenario_idx, GUIWaterBomber
        )
        uav_bases: List[GUIPoint] = extract_bases_from_parameters(parameters, scenario_idx, "uav")
        wb_bases: List[GUIPoint] = extract_bases_from_parameters(
            parameters, scenario_idx, "water_bomber"
        )
        watertanks = extract_water_tanks_from_output(parameters, scenario_idx)
        targets = extract_targets_from_output(parameters, scenario_idx)
        return cls(
            lightning, ignitions, uavs, water_bombers, uav_bases, wb_bases, watertanks, targets
        )


def extract_simulation_lightning(simulation: Simulator, ignited: bool) -> List[GUILightning]:
    """extract_simulation_lightning.

    Args:
        simulation (Simulator): simulation

    Returns:
        List[GUILightning]:
    """
    to_return: List[GUILightning] = []
    for strike in simulation.lightning_strikes:
        if not ignited or strike.ignition:
            to_return.append(GUILightning(strike))
    return to_return


def extract_simulation_targets(simulation: Simulator) -> List[GUITarget]:
    """Extract simulation targets.

    Args:
        simulation (Simulator): simulation

    Returns:
        List[GUITarget]:
    """
    to_return: List[GUITarget] = []
    for target in simulation.targets:
        to_return.append(GUITarget(target))
    return to_return


TAircraft = TypeVar("TAircraft", GUIUav, GUIWaterBomber)


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
    aircraft_list: Sequence[Aircraft] = []
    if aircraft_type == GUIWaterBomber:
        aircraft_list = simulation.water_bombers
    else:
        aircraft_list = simulation.uavs
    for aircraft in aircraft_list:
        to_return.append(aircraft_type(aircraft.past_locations))
        new_aircraft = to_return[-1]
        if isinstance(new_aircraft, GUIUav):
            assert isinstance(aircraft, UAV)
            new_aircraft.copy_from_uav(aircraft)
        if isinstance(new_aircraft, GUIWaterBomber):
            assert isinstance(aircraft, WaterBomber)
            new_aircraft.copy_from_wb(aircraft)
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


def extract_simulation_water_tanks(simulation: Simulator) -> List[GUIWaterTank]:
    """Extract water tanks from simulator.

    Args:
        simulation (Simulator): simulation

    Returns:
        List[GUIWaterTank]:
    """
    to_return: List[GUIWaterTank] = []
    for water_tank in simulation.water_tanks:
        to_return.append(GUIWaterTank(water_tank))
    return to_return


def extract_lightning_from_output(
    parameters: JSONParameters, scenario_idx: int, ignited: bool
) -> List[GUILightning]:
    """extract_lightning_from_output.

    Args:

    Returns:
        List[GUILightning]:
    """
    scenario_name = parameters.scenario_name(scenario_idx)
    output_folder = parameters.filepath.parent / parameters.get_attribute(
        "output_folder_name", scenario_idx
    )
    input_lightning = parameters.get_lightning(scenario_idx)
    to_return: List[GUILightning] = []
    lightning_csv = CSVFile(
        output_folder / f"{scenario_name}{'_' if scenario_name else ''}simulation_output.csv"
    )
    for row in lightning_csv:
        if not ignited or not math.isnan(row[6]):
            lightning = input_lightning[row[1]]
            lightning.inspected_time = (row[4] + row[5]) * HOURS_TO_SECONDS
            lightning.suppressed_time = (row[4] + row[6]) * HOURS_TO_SECONDS if ignited else None
            lightning.ignition = ignited
            to_return.append(GUILightning(lightning))
    return to_return


def extract_targets_from_output(parameters: JSONParameters, scenario_idx: int) -> List[GUITarget]:
    """Extract targets from output.

    Args:
        parameters (JSONParameters): parameters
        scenario_idx (int): scenario index

    Returns:
        List[GUITarget]: GUI targets
    """
    if "unassigned_uavs" in parameters.parameters:
        unassigned_uavs = parameters.parameters["unassigned_uavs"]
        if "targets_filename" in unassigned_uavs or "automatic_targets" in unassigned_uavs:
            scenario_name = parameters.scenario_name(scenario_idx)
            output_folder = parameters.filepath.parent / parameters.get_attribute(
                "output_folder_name", scenario_idx
            )
            targets = read_targets(
                output_folder / f"{scenario_name}{'_' if scenario_name else ''}all_targets.csv"
            )
            gui_targets = [GUITarget(target) for target in targets]
            return gui_targets
    return []


def extract_water_tanks_from_output(
    parameters: JSONParameters, scenario_idx: int
) -> List[GUIWaterTank]:
    """Extract water tanks from output of previous simulation.

    Args:
        path (Path): path
        scenario_name (str): scenario_name

    Returns:
        List[GUIWaterTank]:
    """
    to_return: List[GUIWaterTank] = []
    output_folder = parameters.filepath.parent / parameters.get_attribute(
        "output_folder_name", scenario_idx
    )
    scenario_name = parameters.scenario_name(scenario_idx)
    water_tank_csv = CSVFile(
        output_folder / f"{scenario_name}{'_' if scenario_name else ''}water_tanks.csv"
    )
    water_tanks = parameters.get_water_tanks(scenario_idx)

    for row in water_tank_csv:
        to_return.append(GUIWaterTank(water_tanks[int(row[1])]))
        to_return[-1].capacity = Volume(float(row[5])).get()
    return to_return


def extract_bases_from_parameters(
    parameters: JSONParameters, scenario_idx: int, aircraft_type: str
) -> List[GUIPoint]:
    """Extract bases from parameters of previous simulation.

    Args:
        parameters (JSONParameters): parameters
        scenario_idx (int): scenario_idx

    Returns:
        List[GUIPoint]:
    """
    to_return: List[GUIPoint] = []
    base_csv = CSVFile(
        parameters.get_relative_filepath(aircraft_type + "_bases_filename", scenario_idx)
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
    parameters: JSONParameters, path: Path, scenario_idx: int, aircraft_type: Type[TAircraft]
) -> List[TAircraft]:
    """extract_aircraft_from_output.

    Args:
        path (Path): path
        scenario_name (str): scenario_name
        aircraft_type (TAircraft): aircraft_type

    Returns:
        List[GUIAircraft]:
    """
    to_return: List[TAircraft] = []
    scenario_name = parameters.scenario_name(scenario_idx)
    aircraft_csv = CSVFile(
        path
        / (
            f"{scenario_name}{'_' if scenario_name else ''}"
            + f"{aircraft_type.aircraft_type().value}_event_updates.csv"
        )
    )
    aircraft_updates: Dict[str, List[UpdateEvent]] = {}
    for row in aircraft_csv:
        aircraft_id = row[1]
        status_str = row.Status  # type: ignore
        loc_id: Optional[int] = None
        try:
            loc_id = int(status_str.split()[-1])
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
            [],  # TODO(ryan) provide future events pylint: disable=fixme
            loc_id,
        )
        if aircraft_id in aircraft_updates:
            aircraft_updates[aircraft_id].append(update_event)
        else:
            aircraft_updates[aircraft_id] = [update_event]

    uavs = parameters.process_uavs(scenario_idx)
    wbs, _ = parameters.process_water_bombers(
        parameters.get_water_bomber_bases_all(scenario_idx), scenario_idx
    )
    lightning = parameters.get_lightning(scenario_idx)
    for aircraft_id, updates in aircraft_updates.items():
        to_return.append(aircraft_type(updates))
        aircraft = to_return[-1]
        if isinstance(aircraft, GUIUav):
            aircraft.copy_from_uav(uavs[int(aircraft_id.split()[1])])
        if isinstance(aircraft, GUIWaterBomber):
            for water_bomber in wbs:
                if aircraft_id == water_bomber.name:
                    aircraft.copy_from_wb(water_bomber)
        aircraft.past_locations = updates
        for update in updates:
            if update.status == Status.INSPECTING_STRIKE:
                assert update.loc_id_no is not None, "Lightning loc id should be int, not None"
                aircraft.strikes_visited.append((lightning[update.loc_id_no], update.time))
    return to_return
