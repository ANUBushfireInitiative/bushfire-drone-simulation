"""Class for dealing with inputting and outputting parameters to and from the simulation."""

import copy
import csv
import json
import logging
import shutil
import sys
import warnings
from functools import reduce
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
from matplotlib.figure import Figure

from bushfire_drone_simulation.aircraft import AircraftType, UpdateEvent
from bushfire_drone_simulation.cluster import LightningCluster
from bushfire_drone_simulation.fire_utils import (
    Base,
    Location,
    Target,
    Time,
    WaterTank,
    assert_bool,
    assert_number,
)
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.plots import (
    inspection_time_histogram,
    risk_rating_plot,
    risk_rating_plot_over_time,
    suppression_time_histogram,
    suppressions_per_bomber_plot,
    water_tank_plot,
)
from bushfire_drone_simulation.read_csv import (
    CSVFile,
    read_bases,
    read_lightning,
    read_locations,
    read_targets,
    read_water_tanks,
)
from bushfire_drone_simulation.uav import UAV, UAVAttributes
from bushfire_drone_simulation.units import Distance, Duration, Volume
from bushfire_drone_simulation.water_bomber import WaterBomber, WBAttributes

_LOG = logging.getLogger(__name__)
matplotlib.use("Agg")


def _get_from_dict(data_dict: Dict[str, Any], key_list: Union[str, Sequence[str]]) -> Optional[Any]:
    """Get value corresponding to a list of keys in nested dictionaries."""
    if isinstance(key_list, str):
        return data_dict[key_list]
    to_return = reduce(
        lambda d, key: d.get(key) if key in d else None, key_list, data_dict  # type: ignore
    )
    return to_return


def _set_in_dict(
    data_dict: Dict[str, Any],
    key_list: Union[str, Sequence[str]],
    value: Union[Dict[str, Any], str],
) -> None:
    """Set value corresponding to a list of keys in nested dictionaries."""
    if isinstance(key_list, str):
        data_dict[key_list] = value
    else:
        _get_from_dict(data_dict, key_list[:-1])[key_list[-1]] = value  # type: ignore


def commandline_confirm(message: str) -> bool:
    """Confirm message using command line.

    Args:
        message (str): message

    Returns:
        bool: User response
    """
    cont = input(f"{message}\nEnter 'Y' if yes and 'N' if no \n")
    return cont.lower().strip() == "y"


def time_prioritisation(time: float, _: Any) -> float:
    """Prioritisation function based purely on time.

    Args:
        time (float): time
        _ (Any): _

    Returns:
        float:
    """
    return time


def time_risk_product_prioritisation(time: float, risk: float) -> float:
    """Prioritisation function based on product of time and risk.

    Args:
        time (float): time
        risk (float): risk

    Returns:
        float:
    """
    return time * risk


def time_risk_squared_prioritisation(time: float, risk: float) -> float:
    """Prioritisation function based on product of time and risk.

    Args:
        time (float): time
        risk (float): risk

    Returns:
        float:
    """
    return time * risk * risk


def time_risk_cubed_prioritisation(time: float, risk: float) -> float:
    """Prioritisation function based on product of time and risk.

    Args:
        time (float): time
        risk (float): risk

    Returns:
        float:
    """
    return time * risk * risk * risk


def time_risk_threshold_prioritisation(time: float, risk: float) -> float:
    """Prioritisation function based on product of time and risk.

    Args:
        time (float): time
        risk (float): risk

    Returns:
        float:
    """
    if risk > 0.8:
        return time * 100
    return time


class JSONParameters:
    """Class for reading parameters from a csv file."""

    def __init__(self, parameters_file: Path):
        """Read collection of variables stored in filename.

        Args:
            parameters_file (str): filepath to json parameters file from current working directory
        """
        self.folder = parameters_file.parent
        self.filepath = parameters_file
        with open(parameters_file, encoding="utf8") as file:
            self.parameters = json.load(file)

        self.scenarios: List[Dict[str, Any]] = []

        if "scenario_parameters_filename" in self.parameters.keys():
            self.csv_scenarios = CSVFile(
                self.folder / self.parameters["scenario_parameters_filename"]
            )

            def recurse_through_dictionaries(
                dictionary_path: List[str], dictionary: Union[Dict[str, Any], str]
            ) -> None:
                if isinstance(dictionary, str) and dictionary == "?":
                    if len(self.scenarios) == 0:
                        # Haven't yet deep copied self.scenarios
                        self.scenarios = [
                            copy.deepcopy(self.parameters) for _ in range(len(self.csv_scenarios))
                        ]
                    for scenario_idx, scenario in enumerate(self.scenarios):
                        _set_in_dict(
                            scenario,
                            dictionary_path,
                            self.csv_scenarios["/".join(dictionary_path)][scenario_idx],
                        )
                elif isinstance(dictionary, dict):
                    for element in dictionary:
                        recurse_through_dictionaries(
                            dictionary_path + [element], dictionary[element]
                        )

            recurse_through_dictionaries([], self.parameters)

            for scenario_idx, scenario in enumerate(self.scenarios):
                scenario["scenario_name"] = self.csv_scenarios["scenario_name"][scenario_idx]

        if len(self.scenarios) == 0:
            self.scenarios = [self.parameters]
        self.output_folder: Path = self.folder / self.scenarios[0]["output_folder_name"]

    def create_output_folder(
        self, confirmation: Callable[[str], bool] = commandline_confirm
    ) -> None:
        """Create output folder specified in parameters (and clear if non-empty).

        Args:
            confirmation (Callable[[str], bool]): confirmation method
        """
        print(self.output_folder)
        if self.output_folder.exists():
            if any(self.output_folder.iterdir()):
                if not confirmation(
                    "Output folder already exists and is not empty, "
                    + "do you want to overwrite its contents?\n"
                ):
                    _LOG.info("Aborting")
                    sys.exit()
            shutil.rmtree(self.output_folder)
        self.output_folder.mkdir(parents=True)

    def get_uav_bases(self, scenario_idx: int) -> List[Base]:
        """Return list of UAV bases."""
        return read_bases(self.get_relative_filepath("uav_bases_filename", scenario_idx))

    def get_water_bomber_bases_all(self, scenario_idx: int) -> List[Base]:
        """Return list of all water bomber bases (regardless of which bombers can visit)."""
        return read_bases(self.get_relative_filepath("water_bomber_bases_filename", scenario_idx))

    def get_water_tanks(self, scenario_idx: int) -> List[WaterTank]:
        """Return list of water tanks."""
        return read_water_tanks(self.get_relative_filepath("water_tanks_filename", scenario_idx))

    def get_lightning(self, scenario_idx: int) -> List[Lightning]:
        """Return list of lightning."""
        return read_lightning(
            self.get_relative_filepath("lightning_filename", scenario_idx),
            self.get_attribute("ignition_probability", scenario_idx),
        )

    def process_water_bombers(
        self, bases: List[Base], scenario_idx: int
    ) -> Tuple[List[WaterBomber], Dict[str, List[Base]]]:
        """Create water bombers from json file."""
        water_bombers: List[WaterBomber] = []
        water_bombers_bases_dict = {}
        for water_bomber_type in self.scenarios[scenario_idx]["water_bombers"]:
            water_bomber = self.scenarios[scenario_idx]["water_bombers"][water_bomber_type]
            filename = self.folder / water_bomber["spawn_loc_file"]
            water_bomber_spawn_locs = CSVFile(filename)
            lats = water_bomber_spawn_locs["latitude"]
            lons = water_bomber_spawn_locs["longitude"]
            start_locs = water_bomber_spawn_locs["starting at base"]
            fuel = water_bomber_spawn_locs["initial fuel"]
            for attribute in [
                "flight_speed",
                "fuel_refill_time",
                "range_empty",
                "range_under_load",
                "water_refill_time",
                "suppression_time",
                "water_per_suppression",
                "water_capacity",
                "pct_fuel_cutoff",
            ]:
                if attribute not in water_bomber:
                    raise Exception(
                        f"Error: Parameter '{attribute}' is missing in '{self.filepath}'.\n"
                        f"Please add '{attribute}' to 'water_bombers/{water_bomber_type}' in "
                        f"'{self.filepath}' and run the simulation again"
                    )
            assert (
                water_bomber["pct_fuel_cutoff"] <= 1 and water_bomber["pct_fuel_cutoff"] > 0
            ), "The percentage of remaining fuel required to return to base should be >0 and <=1"

            for i, lat in enumerate(lats):
                lat = assert_number(
                    lat,
                    f"Error: The latitude on row {i+1} of '{filename}' ('{lat}') is not a number.",
                )
                lon = assert_number(
                    lons[i],
                    (
                        f"Error: The longitude on row {i+1} of '{filename}' "
                        f"('{lons[i]}') isn't a number"
                    ),
                )
                starting_at_base = assert_bool(
                    start_locs[i],
                    f"Error: Row {i+1} of column 'starting at base' in '{filename}' "
                    f"('{start_locs[i]}') isn't a boolean.",
                )
                initial_fuel = assert_number(
                    fuel[i],
                    f"Error: The fuel on row {i+1} of '{filename}' ('{lons[i]}') isn't a number.",
                )
                wb_attributes = WBAttributes(
                    id_no=i,
                    latitude=lat,
                    longitude=lon,
                    flight_speed=water_bomber["flight_speed"],
                    fuel_refill_time=water_bomber["fuel_refill_time"],
                    suppression_time=water_bomber["suppression_time"],
                    water_refill_time=water_bomber["water_refill_time"],
                    water_per_suppression=water_bomber["water_per_suppression"],
                    range_empty=water_bomber["range_empty"],
                    range_under_load=water_bomber["range_under_load"],
                    water_capacity=water_bomber["water_capacity"],
                    pct_fuel_cutoff=water_bomber["pct_fuel_cutoff"],
                    bomber_type=water_bomber_type,
                )
                water_bombers.append(
                    WaterBomber(
                        attributes=wb_attributes,
                        starting_at_base=starting_at_base,
                        initial_fuel=initial_fuel,
                    ),
                )
            water_bombers_bases_dict[water_bomber_type] = self.get_water_bomber_bases(
                bases, water_bomber_type, scenario_idx
            )

        return water_bombers, water_bombers_bases_dict

    def get_water_bomber_bases(
        self, bases: List[Base], water_bomber_type: str, scenario_idx: int
    ) -> List[Base]:
        """get_water_bomber_bases.

        Args:
            bases:
            water_bomber_type (str): water_bomber_type
            scenario_idx (int): scenario_idx
        """
        filename = self.folder / str(
            self.get_attribute("water_bomber_bases_filename", scenario_idx)
        )
        base_data = CSVFile(filename)
        bases_specific = base_data[water_bomber_type]
        bases_all = base_data["all"]
        current_bases: List[Base] = []

        for (idx, base) in enumerate(bases):
            if assert_bool(
                bases_all[idx],
                (
                    f"Error: The value on row {idx+1} of column 'all' in '{filename}' "
                    f"('{bases_all[idx]}') is not a boolean."
                ),
            ) or assert_bool(
                bases_specific[idx],
                (
                    f"Error: The value on row {idx+1} of column '{water_bomber_type}' in "
                    f"'{filename}' ('{bases_all[idx]}') is not a boolean."
                ),
            ):
                current_bases.append(base)
        return current_bases

    def process_uavs(self, scenario_idx: int) -> List[UAV]:
        """Create uavs from json file."""
        uav_data = self.get_attribute("uavs", scenario_idx)
        assert isinstance(uav_data, dict)
        filename = self.folder / uav_data["spawn_loc_file"]
        uav_spawn_locs = CSVFile(filename)
        lats = uav_spawn_locs["latitude"]
        lons = uav_spawn_locs["longitude"]
        start_locs = uav_spawn_locs["starting at base"]
        fuel = uav_spawn_locs["initial fuel"]
        uavs: List[UAV] = []

        for attribute in [
            "flight_speed",
            "fuel_refill_time",
            "range",
            "inspection_time",
            "pct_fuel_cutoff",
        ]:
            if attribute not in uav_data:
                raise Exception(
                    f"Error: Parameter '{attribute}' is missing in '{self.filepath}'.\n"
                    f"Please add '{attribute}' to 'uavs' in '{self.filepath}' "
                    f"and run the simulation again"
                )
        assert (
            uav_data["pct_fuel_cutoff"] <= 1 and uav_data["pct_fuel_cutoff"] > 0
        ), "The percentage of remaining fuel required to return to base should be >0 and <=1"

        for i, lat in enumerate(lats):
            lat = assert_number(
                lat,
                f"Error: The latitude on row {i+1} of '{filename}' ('{lat}') is not a number.",
            )
            lon = assert_number(
                lons[i],
                f"Error: The longitude on row {i+1} of '{filename}' ('{lons[i]}') isn't a number.",
            )
            starting_at_base = assert_bool(
                start_locs[i],
                f"Error: Row {i+1} of column 'starting at base' in '{filename}' "
                f"('{start_locs[i]}') isn't a boolean.",
            )
            initial_fuel = assert_number(
                fuel[i],
                f"Error: The fuel on row {i+1} of '{filename}' ('{lons[i]}') isn't a number.",
            )
            uav_attributes = UAVAttributes(
                id_no=i,
                latitude=lat,
                longitude=lon,
                flight_speed=uav_data["flight_speed"],
                fuel_refill_time=uav_data["fuel_refill_time"],
                range=uav_data["range"],
                inspection_time=uav_data["inspection_time"],
                pct_fuel_cutoff=uav_data["pct_fuel_cutoff"],
            )
            uavs.append(
                UAV(
                    attributes=uav_attributes,
                    starting_at_base=starting_at_base,
                    initial_fuel=initial_fuel,
                ),
            )
        return uavs

    def process_unassigned_uavs(
        self, scenario_idx: int, lightning: List[Lightning]
    ) -> Tuple[Dict[str, Any], List[Target], List[Location], Path]:
        """Process targets, polygon and attributes associated with unassigned drone."""
        assert "unassigned_uavs" in self.parameters
        attribute_dict = self.get_attribute("unassigned_uavs", scenario_idx)
        assert isinstance(attribute_dict, dict)
        targets: List[Target] = []
        if "targets_filename" in attribute_dict and isinstance(
            attribute_dict["targets_filename"], str
        ):
            targets = read_targets(self.folder / attribute_dict["targets_filename"])
        if "boundary_polygon_filename" in attribute_dict:
            polygon = read_locations(self.folder / attribute_dict["boundary_polygon_filename"])
            if polygon[0].equals(polygon[-1]):
                del polygon[-1]
            if "forecasting" in attribute_dict:
                target_dict = attribute_dict["forecasting"]
                for attribute in [
                    "radius",
                    "min_in_target",
                    "target_resolution",
                    "look_ahead",
                    "attraction_const",
                    "attraction_pwr",
                ]:
                    if attribute not in target_dict:
                        raise Exception(
                            f"Error: Parameter '{attribute}' is missing in '{self.filepath}'.\n"
                            f"Please add '{attribute}' to 'unassigned_uavs/forecasting' in"
                            f" '{self.filepath}' and run the simulation again"
                        )
                cluster = LightningCluster(
                    lightning,
                    polygon,
                    Distance(target_dict["radius"], "km"),
                    target_dict["min_in_target"],
                    Duration(target_dict["target_resolution"], "min"),
                    Duration(target_dict["look_ahead"], "min"),
                    target_dict["attraction_const"],
                    target_dict["attraction_pwr"],
                )
                targets += cluster.generate_targets()
        else:
            raise Exception(
                f"Error: Parameter 'boundary_polygon_filename' is missing in '{self.filepath}'.\n"
                f"Please add 'boundary_polygon_filename' to 'unassigned_uavs' in "
                f"'{self.filepath}' and run the simulation again"
            )
        return attribute_dict, targets, polygon, self.output_folder

    def get_prioritisation_function(
        self, aircraft: str, scenario_idx: int
    ) -> Callable[[float, float], float]:
        """Return prioritisation function combining inspection/suppression time and risk rating."""
        aircraft_data = self.get_attribute(aircraft, scenario_idx)
        if "prioritisation_function" not in aircraft_data:
            return time_prioritisation
        function_name = aircraft_data["prioritisation_function"]
        if function_name == "time":
            return time_prioritisation
        if function_name == "product":
            return time_risk_product_prioritisation
        if function_name == "p_sq":
            return time_risk_squared_prioritisation
        if function_name == "p_cub":
            return time_risk_cubed_prioritisation
        if function_name == "thresh":
            return time_risk_threshold_prioritisation
        raise Exception(
            f"Error: Do not recognize value '{function_name}' "
            f"from attribute {aircraft}/prioritisation_function in '{self.filepath}'.\n"
            f"Please refer to the documentation for possible prioritisation functions."
        )

    def get_attribute(self, attribute: Union[str, Sequence[str]], scenario_idx: int) -> Any:
        """Return attribute of JSON file."""
        to_return = _get_from_dict(self.scenarios[scenario_idx], attribute)
        if to_return is None:
            raise Exception(
                f"Error: Parameter '{attribute}' is missing in '{self.filepath}'.\n"
                f"Please add '{attribute}' to '{self.filepath}' "
                f"and run the simulation again"
            )
        return to_return

    def scenario_name(self, scenario_idx: int) -> str:
        """Get name of scenario.

        Args:
            scenario_idx (int): scenario_idx

        Returns:
            str: Scenario name
        """
        if "scenario_name" in self.scenarios[scenario_idx]:
            return self.scenarios[scenario_idx]["scenario_name"]  # type: ignore
        return ""

    def get_relative_filepath(self, key: Union[str, Sequence[str]], scenario_idx: int) -> Path:
        """Return relative file path to given key."""
        filename = self.get_attribute(key, scenario_idx)
        assert isinstance(filename, str)
        return self.folder / filename

    def write_simulation_output(  # pylint: disable=too-many-arguments
        self,
        uavs: List[UAV],
        water_bombers: List[WaterBomber],
        water_tanks: List[WaterTank],
        lightning: List[Lightning],
        targets: List[Target],
        prefix: str,
    ) -> Dict[str, List[Union[float, str]]]:
        """Write simulation output to output folder.

        Args:
            simulator (Simulator): simulator
            prefix (str): scenario file prefix
        """
        inspection_times, suppression_times = self._write_to_simulation_output_file(
            lightning, prefix
        )
        self._write_to_uav_updates_file(uavs, prefix)
        self._write_to_water_tanks_file(water_tanks, prefix)
        self._write_to_wb_updates_file(water_bombers, prefix)
        self._write_to_targets_file(targets, prefix)
        summary_results = self._create_plots(
            inspection_times,
            suppression_times,
            water_bombers,
            water_tanks,
            lightning,
            prefix,
        )
        return summary_results

    def _create_plots(  # pylint: disable=too-many-arguments
        self,
        inspection_times: List[float],
        suppression_times: List[float],
        water_bombers: List[WaterBomber],
        water_tanks: List[WaterTank],
        lightning: List[Lightning],
        prefix: str,
    ) -> Dict[str, List[Union[float, str]]]:
        """Create plots and write to output."""
        title = ""
        summary_results: Dict[str, List[Union[float, str]]] = {}
        for times, name, aircraft_type in [
            (inspection_times, "inspection time", "uavs"),
            (suppression_times, "suppression time", "wbs"),
        ]:
            if len(times) != 0:
                times_np: npt.NDArray[np.float64] = np.array(times)
                mean_time = np.mean(times_np)
                title += f"Mean {name} of {mean_time} hrs\n"
                summary_results[aircraft_type] = [
                    float(mean_time),
                    float(np.amax(times_np)),
                    float(np.percentile(times_np, 99)),
                    float(np.percentile(times_np, 90)),
                    float(np.percentile(times_np, 50)),
                ]

        fig = Figure(figsize=(8, 6), dpi=300, tight_layout=True)
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", r"The value of the smallest subnormal for \<class .*\> type is zero."
            )
            axs = fig.subplots(2, 2)

        fig.suptitle(title)

        inspection_time_histogram(axs[0, 0], inspection_times)
        suppression_time_histogram(axs[0, 1], suppression_times)
        suppressions_per_bomber_plot(axs[1, 0], water_bombers)
        water_tank_plot(axs[1, 1], water_tanks)

        fig.tight_layout()
        fig.savefig(self.output_folder / (prefix + "inspection_times_plot.png"))
        plt.close(fig)

        fig = Figure(figsize=(8, 6), dpi=300, tight_layout=True)
        axs = fig.add_subplot(211)
        risk_rating_plot_over_time(fig, axs, lightning)
        axs = fig.add_subplot(212)
        risk_rating_plot(axs, lightning)
        fig.savefig(self.output_folder / (prefix + "risk_rating_plot.png"))
        plt.close(fig)
        return summary_results

    def _write_to_simulation_output_file(
        self, lightning_strikes: List[Lightning], prefix: str
    ) -> Tuple[List[float], List[float]]:
        """Write simulation data to output file."""
        with open(
            self.output_folder / (prefix + "simulation_output.csv"),
            "w",
            newline="",
            encoding="utf8",
        ) as outputfile:
            filewriter = csv.writer(outputfile)
            id_nos: List[int] = []
            lats: List[float] = []
            lons: List[float] = []
            spawn_times: List[float] = []
            inspection_times: List[Union[float, str]] = []
            suppression_times: List[Union[float, str]] = []
            inspection_times_to_return: List[float] = []
            suppression_times_to_return: List[float] = []
            for strike in lightning_strikes:
                id_nos.append(strike.id_no)
                lats.append(strike.lat)
                lons.append(strike.lon)
                spawn_times.append(Time.from_float(strike.spawn_time).get("hr"))
                if strike.inspected_time is not None:
                    inspection_times.append(
                        Time.from_float(strike.inspected_time - strike.spawn_time).get("hr"),
                    )
                    inspection_times_to_return.append(
                        Time.from_float(strike.inspected_time - strike.spawn_time).get("hr"),
                    )
                else:
                    _LOG.error("strike %s was not inspected", str(strike.id_no))
                    inspection_times.append("N/A")
                if strike.suppressed_time is not None:
                    suppression_times.append(
                        Time.from_float(strike.suppressed_time - strike.spawn_time).get("hr"),
                    )
                    suppression_times_to_return.append(
                        Time.from_float(strike.suppressed_time - strike.spawn_time).get("hr"),
                    )
                else:
                    suppression_times.append("N/A")
                    if strike.ignition:
                        _LOG.error("strike %s ignited but was not suppressed", str(strike.id_no))
            filewriter.writerow(
                [
                    "Strike ID",
                    "Latitude",
                    "Longitude",
                    "Spawn time (hr)",
                    "Inspection time (hr)",
                    "Suppression time (hr)",
                ]
            )
            for row in zip(id_nos, lats, lons, spawn_times, inspection_times, suppression_times):
                filewriter.writerow(row)
        return inspection_times_to_return, suppression_times_to_return

    def _write_to_water_tanks_file(self, water_tanks: List[WaterTank], prefix: str) -> None:
        """Write water tanks to output file."""
        with open(
            self.output_folder / (prefix + "water_tanks.csv"),
            "w",
            newline="",
            encoding="utf8",
        ) as outputfile:
            filewriter = csv.writer(outputfile)
            filewriter.writerow(
                ["Water Tank ID", "Latitude", "Longitude", "Initial Capacity", "Remaining Capacity"]
            )
            for water_tank in water_tanks:
                filewriter.writerow(
                    [
                        water_tank.id_no,
                        water_tank.lat,
                        water_tank.lon,
                        water_tank.initial_capacity,
                        water_tank.capacity,
                    ]
                )

    def _write_to_uav_updates_file(self, uavs: List[UAV], prefix: str) -> None:
        """Write UAV event update data to output file."""
        with open(
            self.output_folder / (f"{prefix}{AircraftType.UAV.value}_event_updates.csv"),
            "w",
            newline="",
            encoding="utf8",
        ) as outputfile:
            filewriter = csv.writer(outputfile)
            filewriter.writerow(
                [
                    "UAV ID",
                    "Latitude",
                    "Longitude",
                    "Time (min)",
                    "Distance travelled (km)",
                    "Distance hovered (km)",
                    "Fuel capacity (%)",
                    "Current range (km)",
                    "Status",
                    "Next updates",
                ]
            )
            all_uav_updates: List[UpdateEvent] = []
            for uav in uavs:
                all_uav_updates += uav.past_locations

            all_uav_updates.sort()
            for uav_update in all_uav_updates:
                filewriter.writerow(
                    [
                        uav_update.name,
                        uav_update.lat,
                        uav_update.lon,
                        Time.from_float(uav_update.time).get("min"),
                        Distance(uav_update.distance_travelled).get("km"),
                        Distance(uav_update.distance_hovered).get("km"),
                        uav_update.fuel * 100,
                        Distance(uav_update.current_range).get("km"),
                        uav_update.status_str,
                        uav_update.list_of_next_events,
                    ]
                )

    def _write_to_wb_updates_file(self, water_bombers: List[WaterBomber], prefix: str) -> None:
        """Write water bomber event update data to output file."""
        with open(
            self.output_folder / (f"{prefix}{AircraftType.WB.value}_event_updates.csv"),
            "w",
            newline="",
            encoding="utf8",
        ) as outputfile:
            filewriter = csv.writer(outputfile)
            filewriter.writerow(
                [
                    "Water Bomber ID",
                    "Latitude",
                    "Longitude",
                    "Time (min)",
                    "Distance travelled (km)",
                    "Distance hovered (km)",
                    "Fuel capacity (%)",
                    "Current range (km)",
                    "Water capacity (L)",
                    "Status",
                    "Next updates",
                ]
            )
            all_wb_updates: List[UpdateEvent] = []
            for water_bomber in water_bombers:
                all_wb_updates += water_bomber.past_locations

            all_wb_updates.sort()
            for wb_update in all_wb_updates:
                filewriter.writerow(
                    [
                        wb_update.name,
                        wb_update.lat,
                        wb_update.lon,
                        Time.from_float(wb_update.time).get("min"),
                        Distance(wb_update.distance_travelled).get("km"),
                        Distance(wb_update.distance_hovered).get("km"),
                        wb_update.fuel * 100,
                        Distance(wb_update.current_range).get("km"),
                        Volume(wb_update.water).get("L"),
                        wb_update.status_str,
                        wb_update.list_of_next_events,
                    ]
                )

    def _write_to_targets_file(self, targets: List[Target], prefix: str) -> None:
        """Write water bomber event update data to output file."""
        if "unassigned_uavs" in self.parameters:
            unassigned_uavs = self.parameters["unassigned_uavs"]
            if "targets_filename" in unassigned_uavs or "forecasting" in unassigned_uavs:
                with open(
                    self.output_folder / (f"{prefix}all_targets.csv"),
                    "w",
                    newline="",
                    encoding="utf8",
                ) as outputfile:
                    filewriter = csv.writer(outputfile)
                    filewriter.writerow(
                        [
                            "latitude",
                            "longitude",
                            "start time",
                            "finish time",
                            "attraction constant",
                            "attraction power",
                            "automatic",
                        ]
                    )
                    for target in targets:
                        filewriter.writerow(
                            [
                                target.lat,
                                target.lon,
                                Time.from_float(target.start_time).get("hr"),
                                Time.from_float(target.end_time).get("hr"),
                                target.attraction_const,
                                target.attraction_power,
                                target.automatic,
                            ]
                        )

    @property
    def gui_filename(self) -> Path:
        """Filename for gui parameters."""
        return self.output_folder / "gui.json"

    def write_to_input_parameters_folder(self) -> None:
        """Copy input parameters to input parameters folder to be output."""
        input_folder = self.output_folder / "simulation_input"
        if not input_folder.exists():
            input_folder.mkdir()
        gui_params = copy.deepcopy(self.parameters)
        gui_params["output_folder_name"] = "."

        copy_to_input(self.filepath, input_folder)

        scenario_parameters_csv = None
        if "scenario_parameters_filename" in self.parameters:
            copy_to_input(
                self.get_relative_filepath("scenario_parameters_filename", 0),
                input_folder,
            )
            path = copy_to_input(
                self.get_relative_filepath("scenario_parameters_filename", 0),
                input_folder,
                name="scenario_parameters_for_gui.csv",
            )
            gui_params["scenario_parameters_filename"] = str(path.relative_to(self.output_folder))
            scenario_parameters_csv = CSVFile(path)

        file_parameters = [
            "water_bomber_bases_filename",
            "uav_bases_filename",
            "water_tanks_filename",
            "lightning_filename",
            ["uavs", "spawn_loc_file"],
        ] + [
            ["water_bombers", water_bomber_type, "spawn_loc_file"]
            for water_bomber_type in self.get_attribute("water_bombers", 0)
        ]
        if "unassigned_uavs" in gui_params:
            file_parameters.append(["unassigned_uavs", "boundary_polygon_filename"])
            if _get_from_dict(gui_params, ["unassigned_uavs", "targets_filename"]) is not None:
                file_parameters.append(["unassigned_uavs", "targets_filename"])

        for file_parameter in file_parameters:
            if _get_from_dict(gui_params, file_parameter) != "?":
                path = copy_to_input(self.get_relative_filepath(file_parameter, 0), input_folder)
                _set_in_dict(gui_params, file_parameter, str(path.relative_to(self.output_folder)))
            else:
                assert scenario_parameters_csv is not None
                if isinstance(file_parameter, str):
                    heading = file_parameter
                else:
                    heading = "/".join(file_parameter)
                column = scenario_parameters_csv.get_column(heading)
                for i, cell in enumerate(column):
                    if not isinstance(cell, str):
                        continue
                    path = copy_to_input(
                        self.get_relative_filepath(file_parameter, i), input_folder
                    )
                    column[i] = path.relative_to(self.output_folder)

        with open(self.gui_filename, "w", encoding="utf8") as gui_file:
            json.dump(gui_params, gui_file)
        if scenario_parameters_csv is not None:
            scenario_parameters_csv.save(scenario_parameters_csv.filename)


def copy_to_input(file: Path, input_folder: Path, name: Optional[str] = None) -> Path:
    """Copy a file to the input folder ensuring unique naming.

    Args:
        file (Path): file
        input_folder (Path): input_folder

    Returns:
        Path: Destination
    """
    destination = input_folder / (name or file.name)
    i = 1
    while destination.exists():
        destination = destination.with_name(
            (name or file.name).split(".")[0] + "_" + str(i) + "." + destination.suffix
        )
    shutil.copy2(
        file,
        destination,
    )
    return destination
