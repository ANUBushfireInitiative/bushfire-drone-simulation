"""Class for dealing with inputting and outputting parameters to and from the simulation."""

import copy
import csv
import json
import logging
import os
import shutil
import sys
from functools import reduce
from math import isinf
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from bushfire_drone_simulation.aircraft import UAV, UpdateEvent, WaterBomber
from bushfire_drone_simulation.fire_utils import Base, Time, WaterTank, assert_bool, assert_number
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.read_csv import CSVFile, read_lightning, read_locations_with_capacity
from bushfire_drone_simulation.units import Distance, Volume

_LOG = logging.getLogger(__name__)
matplotlib.use("Agg")


def _get_from_dict(
    data_dict: Dict[str, Any], key_list: List[str]
) -> Union[Dict[str, Any], str, int, float]:
    """Get value corresponding to a list of keys in nested dictionaries."""
    to_return = reduce(dict.__getitem__, key_list, data_dict)
    return to_return


def _set_in_dict(
    data_dict: Dict[str, Any], key_list: List[str], value: Union[Dict[str, Any], str]
) -> None:
    """Set value corresponding to a list of keys in nested dictionaries."""
    _get_from_dict(data_dict, key_list[:-1])[key_list[-1]] = value  # type: ignore


class JSONParameters:
    """Class for reading parameters from a csv file."""

    def __init__(self, parameters_file: Path):
        """Read collection of variables stored in filename.

        Args:
            filename (str): filepath to json parameters file from current working directory
        """
        self.folder = parameters_file.parent
        self.filepath = parameters_file
        with open(parameters_file) as file:
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

        self.output_folder = self.folder / self.scenarios[0]["output_folder_name"]

        # All scenarios output to same folder
        if self.output_folder.exists():
            if any(self.output_folder.iterdir()):
                cont = input(
                    "Output folder already exists and is not empty, "
                    + "do you want to overwrite its contents? \nEnter 'Y' if yes and 'N' if no \n"
                )
                if cont.lower() != "y":
                    _LOG.info("Aborting")
                    sys.exit()
        else:
            self.output_folder.mkdir(parents=True)

    def get_uav_bases(self, scenario_idx: int) -> List[Base]:
        """Return list of UAV bases."""
        return read_locations_with_capacity(
            self.get_relative_filepath("uav_bases_filename", scenario_idx), Base
        )

    def get_water_bomber_bases_all(self, scenario_idx: int) -> List[Base]:
        """Return list of all water bomber bases (regardless of which bombers can visit)."""
        return read_locations_with_capacity(
            self.get_relative_filepath("water_bomber_bases_filename", scenario_idx), Base
        )

    def get_water_tanks(self, scenario_idx: int) -> List[WaterTank]:
        """Return list of water tanks."""
        return read_locations_with_capacity(
            self.get_relative_filepath("water_tanks_filename", scenario_idx), WaterTank
        )

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
            attributes = water_bomber["attributes"]
            for attribute in [
                "flight_speed",
                "fuel_refill_time",
                "range_empty",
                "range_under_load",
                "water_refill_time",
                "bombing_time",
                "water_per_delivery",
                "water_capacity",
            ]:
                if attribute not in attributes:
                    raise Exception(
                        f"Error: Parameter '{attribute}' is missing in '{self.filepath}'.\n"
                        f"Please add '{attribute}' to 'water_bombers/attributes' in "
                        f"'{self.filepath}' and run the simulation again"
                    )
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
                water_bombers.append(
                    WaterBomber(
                        id_no=i,
                        latitude=lat,
                        longitude=lon,
                        attributes=attributes,
                        bomber_type=water_bomber_type,
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
        attributes = uav_data["attributes"]
        for attribute in ["flight_speed", "fuel_refill_time", "range", "inspection_time"]:
            if attribute not in attributes:
                raise Exception(
                    f"Error: Parameter '{attribute}' is missing in '{self.filepath}'.\n"
                    f"Please add '{attribute}' to 'uavs/attributes' in '{self.filepath}' "
                    f"and run the simulation again"
                )
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
            uavs.append(
                UAV(
                    id_no=i,
                    latitude=lat,
                    longitude=lon,
                    attributes=attributes,
                    starting_at_base=starting_at_base,
                    initial_fuel=initial_fuel,
                ),
            )
        return uavs

    def get_attribute(self, attribute: str, scenario_idx: int) -> Any:
        """Return attribute of JSON file."""
        if attribute not in self.scenarios[scenario_idx]:
            raise Exception(
                f"Error: Parameter '{attribute}' is missing in '{self.filepath}'.\n"
                f"Please add '{attribute}' to '{self.filepath}' "
                f"and run the simulation again"
            )
        return self.scenarios[scenario_idx][attribute]

    def get_relative_filepath(self, key: str, scenario_idx: int) -> Path:
        """Return relative file path to given key."""
        filename = self.get_attribute(key, scenario_idx)
        assert isinstance(filename, str)
        return self.folder / filename

    def create_plots(  # pylint: disable=too-many-arguments
        self,
        inspection_times: List[float],
        suppression_times: List[float],
        water_bombers: List[WaterBomber],
        water_tanks: List[WaterTank],
        prefix: str,
    ) -> Dict[str, List[Union[float, str]]]:
        """Create plots and write to output."""
        title = ""
        summary_results: Dict[str, List[Union[float, str]]] = {}
        if len(inspection_times) != 0:
            mean_inspection_time = sum(inspection_times) / len(inspection_times)
            title = f"Mean inspection time of {mean_inspection_time} hrs"
            summary_results["uavs"] = [
                mean_inspection_time,
                np.max(inspection_times),
                np.percentile(inspection_times, 99),
                np.percentile(inspection_times, 90),
                np.percentile(inspection_times, 50),
            ]
        if len(suppression_times) != 0:
            mean_suppression_time = sum(suppression_times) / len(suppression_times)
            title += f"\nMean suppression time of {mean_suppression_time} hrs"
            summary_results["wbs"] = [
                mean_suppression_time,
                np.max(suppression_times),
                np.percentile(suppression_times, 99),
                np.percentile(suppression_times, 90),
                np.percentile(suppression_times, 50),
            ]

        fig, axs = plt.subplots(2, 2, figsize=(12, 8), dpi=300)

        fig.suptitle(title)

        axs[0, 0].hist(inspection_times, bins=20)
        axs[0, 0].set_title("Histogram of UAV inspection times")
        axs[0, 0].set(xlabel="Inspection time (Hours)", ylabel="Frequency")
        axs[0, 0].set_xlim(left=0)
        axs[0, 0].set_ylim(bottom=0)

        axs[0, 1].hist(suppression_times, bins=20)
        axs[0, 1].set_title("Histogram of suppression times")
        axs[0, 1].set(xlabel="Suppression time (Hours)", ylabel="Frequency")
        axs[0, 1].set_xlim(left=0)
        axs[0, 1].set_ylim(bottom=0)

        water_bomber_names = [wb.name for wb in water_bombers]
        num_suppressed = [len(wb.strikes_visited) for wb in water_bombers]
        axs[1, 0].set_title("Lightning strikes suppressed per water bomber")
        axs[1, 0].bar(water_bomber_names, num_suppressed)
        axs[1, 0].tick_params(labelrotation=90)

        water_tank_ids = [i for i, _ in enumerate(water_tanks)]
        axs[1, 1].set_title("Water tank levels after suppression")
        axs[1, 1].bar(
            water_tank_ids,
            [
                Volume(wt.initial_capacity).get(units="kL")
                for wt in water_tanks
                if not isinf(wt.initial_capacity)
            ],
            label="Full Capacity",
            color="orange",
        )
        axs[1, 1].bar(
            water_tank_ids,
            [Volume(wt.capacity).get(units="kL") for wt in water_tanks],
            label="Final Level",
            color="blue",
        )
        axs[1, 1].legend()
        axs[1, 1].set(ylabel="kL")

        fig.tight_layout()
        plt.savefig(
            os.path.join(
                self.output_folder,
                prefix + "inspection_times_plot.png",
            )
        )
        return summary_results

    def write_to_simulation_output_file(
        self, lightning_strikes: List[Lightning], prefix: str
    ) -> Tuple[List[float], List[float]]:
        """Write simulation data to output file."""
        with open(
            self.output_folder / (prefix + "simulation_output.csv"),
            "w",
            newline="",
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
                spawn_times.append(Time.from_time(strike.spawn_time).get("hr"))
                if strike.inspected_time is not None:
                    inspection_times.append(
                        Time.from_time(strike.inspected_time - strike.spawn_time).get("hr"),
                    )
                    inspection_times_to_return.append(
                        Time.from_time(strike.inspected_time - strike.spawn_time).get("hr"),
                    )
                else:
                    _LOG.error("strike %s was not inspected", str(strike.id_no))
                    inspection_times.append("N/A")
                if strike.suppressed_time is not None:
                    suppression_times.append(
                        Time.from_time(strike.suppressed_time - strike.spawn_time).get("hr"),
                    )
                    suppression_times_to_return.append(
                        Time.from_time(strike.suppressed_time - strike.spawn_time).get("hr"),
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

    def write_to_uav_updates_file(self, uavs: List[UAV], prefix: str) -> None:
        """Write UAV event update data to output file."""
        with open(
            self.output_folder / (prefix + "uav_event_updates.csv"),
            "w",
            newline="",
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
                        Time.from_time(uav_update.time).get("min"),
                        Distance(uav_update.distance_travelled).get("km"),
                        Distance(uav_update.distance_hovered).get("km"),
                        uav_update.fuel * 100,
                        Distance(uav_update.current_range).get("km"),
                        uav_update.status_str,
                        uav_update.list_of_next_events,
                    ]
                )

    def write_to_wb_updates_file(self, water_bombers: List[WaterBomber], prefix: str) -> None:
        """Write water bomber event update data to output file."""
        # water_bombers: List[WaterBomber] = coordinator.water_bombers
        with open(
            os.path.join(
                self.output_folder,
                prefix + "water_bomber_event_updates.csv",
            ),
            "w",
            newline="",
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
                        Time.from_time(wb_update.time).get("min"),
                        Distance(wb_update.distance_travelled).get("km"),
                        Distance(wb_update.distance_hovered).get("km"),
                        wb_update.fuel * 100,
                        Distance(wb_update.current_range).get("km"),
                        Volume(wb_update.water).get("L"),
                        str(wb_update.status),
                        wb_update.list_of_next_events,
                    ]
                )

    def write_to_input_parameters_folder(self, scenario_idx: int) -> None:
        """Copy input parameters to input parameters folder to be output."""
        input_folder = os.path.join(self.output_folder, "simulation_input")
        if not os.path.exists(input_folder):
            os.mkdir(input_folder)

        shutil.copy2(self.filepath, str(input_folder))
        shutil.copy2(
            str(self.get_relative_filepath("water_bomber_bases_filename", scenario_idx)),
            str(input_folder),
        )
        shutil.copy2(
            str(self.get_relative_filepath("uav_bases_filename", scenario_idx)), str(input_folder)
        )
        shutil.copy2(
            str(self.get_relative_filepath("water_tanks_filename", scenario_idx)), str(input_folder)
        )
        shutil.copy2(
            str(self.get_relative_filepath("lightning_filename", scenario_idx)), str(input_folder)
        )
        shutil.copy2(
            str(self.get_relative_filepath("scenario_parameters_filename", scenario_idx)),
            str(input_folder),
        )
        shutil.copy2(
            str(os.path.join(self.folder, self.scenarios[scenario_idx]["uavs"]["spawn_loc_file"])),
            str(input_folder),
        )
        for water_bomber_type in self.get_attribute("water_bombers", scenario_idx):
            shutil.copy2(
                str(
                    os.path.join(
                        self.folder,
                        self.scenarios[scenario_idx]["water_bombers"][water_bomber_type][
                            "spawn_loc_file"
                        ],
                    )
                ),
                str(input_folder),
            )
