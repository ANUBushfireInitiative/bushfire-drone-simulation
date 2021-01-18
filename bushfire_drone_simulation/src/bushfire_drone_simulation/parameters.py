"""Class for dealing with inputting and outputting parameters to and from the simulation."""

import copy
import csv
import json
import logging
import os
import shutil
import sys
from functools import reduce
from typing import Any, Dict, List

import matplotlib
import matplotlib.pyplot as plt

from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.coordinator import Coordinator
from bushfire_drone_simulation.fire_utils import WaterTank, assert_bool, assert_number
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.read_csv import CSVFile

_LOG = logging.getLogger(__name__)
matplotlib.use("Agg")


def _get_from_dict(data_dict: Dict[str, Any], key_list: List[str]):
    """Get value corresponding to a list of keys in nested dictionaries."""
    return reduce(dict.__getitem__, key_list, data_dict)


def _set_in_dict(data_dict, key_list, value):
    """Set value corresponding to a list of keys in nested dictionaries."""
    _get_from_dict(data_dict, key_list[:-1])[key_list[-1]] = value


class JSONParameters:
    """Class for reading parameters from a csv file."""

    def __init__(self, filename: str):
        """Read collection of variables stored in filename.

        Args:
            filename (str): filepath to json parameters file from current working directory
        """
        self.folder = os.path.dirname(filename)
        self.filepath = filename
        with open(filename) as file:
            self.parameters = json.load(file)

        self.scenarios: List[Dict[str, Any]] = []

        if "scenario_parameters_filename" in self.parameters.keys():
            self.csv_scenarios = CSVFile(
                os.path.join(self.folder, self.parameters["scenario_parameters_filename"])
            )

            def recurse_through_dictionaries(dictionary_path: List[str], dictionary):
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
            self.scenarios[0]["scenario_name"] = ""

        self.output_folder = os.path.join(self.folder, self.scenarios[0]["output_folder_name"])

        # All scenarios output to same folder
        if os.path.exists(self.output_folder):
            if os.listdir(self.output_folder):
                cont = input(
                    "Output folder already exists and is not empty, "
                    + "do you want to overwrite its contents? \nEnter 'Y' if yes and 'N' if no \n"
                )
                if cont.lower() != "y":
                    _LOG.info("Aborting")
                    sys.exit()

        else:
            os.mkdir(self.output_folder)

    def process_water_bombers(self, bases, scenario_idx):
        """Create water bombers from json file."""
        water_bombers = []
        water_bombers_bases_dict = {}
        for water_bomber_type in self.scenarios[scenario_idx]["water_bombers"]:
            water_bomber = self.scenarios[scenario_idx]["water_bombers"][water_bomber_type]
            filename = os.path.join(self.folder, water_bomber["spawn_loc_file"])
            water_bomber_spawn_locs = CSVFile(filename)
            lats = water_bomber_spawn_locs["latitude"]
            lons = water_bomber_spawn_locs["longitude"]
            attributes = water_bomber["attributes"]
            for i, lat in enumerate(lats):
                lat = assert_number(
                    lat,
                    f"Error: The latitude on row {i+1} of '{filename}' ('{lat}') is not a number.",
                )
                lon = assert_number(
                    lons[i],
                    (
                        f"Error: The longitude on row {i+1} of '{filename}' "
                        "('{lons[i]}') is not a number."
                    ),
                )
                water_bombers.append(
                    WaterBomber(
                        id_no=i,
                        latitude=lat,
                        longitude=lon,
                        attributes=attributes,
                        bomber_type=water_bomber_type,
                    )
                )
            water_bombers_bases_dict[water_bomber_type] = self.get_water_bomber_bases(
                bases, water_bomber_type, scenario_idx
            )

        return water_bombers, water_bombers_bases_dict

    def get_water_bomber_bases(self, bases, water_bomber_type: str, scenario_idx: int):
        """get_water_bomber_bases.

        Args:
            bases:
            water_bomber_type (str): water_bomber_type
            scenario_idx (int): scenario_idx
        """
        filename = os.path.join(
            self.folder, self.get_attribute("water_bomber_bases_filename", scenario_idx)
        )
        base_data = CSVFile(filename)
        bases_specific = base_data[water_bomber_type]
        bases_all = base_data["all"]
        current_bases = []
        for (idx, base) in enumerate(bases):
            if assert_bool(
                bases_all[idx],
                (
                    f"Error: The value on row {idx+1} of column 'all' in '{filename}' "
                    "('{bases_all[idx]}') is not a boolean."
                ),
            ) or assert_bool(
                bases_specific[idx],
                (
                    f"Error: The value on row {idx+1} of column '{water_bomber_type}' in "
                    "'{filename}' ('{bases_all[idx]}') is not a boolean."
                ),
            ):
                current_bases.append(base)
        return current_bases

    def process_uavs(self, scenario_idx):
        """Create uavs from json file."""
        uav_data = self.get_attribute("uavs", scenario_idx)
        filename = os.path.join(self.folder, uav_data["spawn_loc_file"])
        uav_spawn_locs = CSVFile(filename)
        lats = uav_spawn_locs["latitude"]
        lons = uav_spawn_locs["longitude"]
        uavs = []
        attributes = uav_data["attributes"]
        for i, lat in enumerate(lats):
            lat = assert_number(
                lat,
                f"Error: The latitude on row {i+1} of '{filename}' ('{lat}') is not a number.",
            )
            lon = assert_number(
                lons[i],
                f"Error: The longitude on row {i+1} of '{filename}' ('{lons[i]}') is not a number",
            )
            uavs.append(
                UAV(
                    id_no=i,
                    latitude=lat,
                    longitude=lon,
                    attributes=attributes
                    # TODO(Inspection time) Incorporate inspection time #pylint: disable=fixme
                )
            )
        return uavs

    def get_attribute(self, attribute: str, scenario_idx):
        """Return attribute of JSON file."""
        if attribute not in self.scenarios[scenario_idx]:
            raise Exception(
                f"Error: Parameter '{attribute}' is missing in '{self.filepath}'.\n"
                "Please add '{attribute}' to '{self.filepath}' "
                "and run the simulation again"
            )
        return self.scenarios[scenario_idx][attribute]

    def get_relative_filepath(self, key: str, scenario_idx):
        """Return relative file path to given key."""
        return os.path.join(self.folder, self.get_attribute(key, scenario_idx))

    def write_to_output_folder(
        self,
        lightning_strikes: List[Lightning],
        coordinator: Coordinator,
        scenario_idx: int,
    ):
        """Write results of simulation to output folder."""
        prefix = ""
        if "scenario_name" in self.scenarios[scenario_idx]:
            prefix = str(self.get_attribute("scenario_name", scenario_idx)) + "_"

        inspection_times, supression_times_ignitions_only = self.write_to_simulation_output_file(
            lightning_strikes, prefix
        )
        self.write_to_uav_updates_file(coordinator, prefix)
        self.write_to_wb_updates_file(coordinator, prefix)
        self.write_to_input_parameters_folder(scenario_idx)
        self.create_plots(inspection_times, supression_times_ignitions_only, coordinator, prefix)

    def create_plots(self, inspection_times, supression_times_ignitions_only, coordinator, prefix):
        """Create plots and write to output."""
        water_tanks: List[WaterTank] = coordinator.water_tanks
        water_bombers: List[WaterBomber] = coordinator.water_bombers

        fig, axs = plt.subplots(2, 2, figsize=(12, 8), dpi=300)
        axs[0, 0].hist(inspection_times, bins=20)
        axs[0, 0].set_title("Histogram of UAV inspection times")
        axs[0, 0].set(xlabel="Inspection time (Hours)", ylabel="Frequency")
        axs[0, 0].set_xlim(left=0)
        axs[0, 0].set_ylim(bottom=0)

        axs[0, 1].hist(supression_times_ignitions_only, bins=20)
        axs[0, 1].set_title("Histogram of supression times")
        axs[0, 1].set(xlabel="Suppression time (Hours)", ylabel="Frequency")
        axs[0, 1].set_xlim(left=0)
        axs[0, 1].set_ylim(bottom=0)

        water_bomber_names = [wb.name for wb in water_bombers]
        num_suppressed = [wb.num_strikes_visited() for wb in water_bombers]
        axs[1, 0].set_title("Lightning strikes suppressed per helicopter")
        axs[1, 0].bar(water_bomber_names, num_suppressed)
        axs[1, 0].tick_params(labelrotation=90)

        water_tank_ids = [i for i, _ in enumerate(water_tanks)]
        axs[1, 1].set_title("Water tank levels after suppression")
        axs[1, 1].bar(
            water_tank_ids,
            [wt.initial_capacity.get(units="kL") for wt in water_tanks],
            label="Full Capacity",
            color="orange",
        )
        axs[1, 1].bar(
            water_tank_ids,
            [wt.capacity.get(units="kL") for wt in water_tanks],
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

    def write_to_simulation_output_file(self, lightning_strikes, prefix):
        """Write simulation data to output file."""
        with open(
            os.path.join(
                self.output_folder,
                prefix + "simulation_output.csv",
            ),
            "w",
            newline="",
        ) as outputfile:
            filewriter = csv.writer(outputfile)
            lats = []
            lons = []
            inspection_times = []
            supression_times = []
            supression_times_ignitions_only = []
            for strike in lightning_strikes:
                lats.append(strike.lat)
                lons.append(strike.lon)
                if strike.inspected_time is not None:
                    inspection_times.append((strike.inspected_time - strike.spawn_time).get("hr"))
                else:
                    inspection_times.append("N/A")
                if strike.suppressed_time is not None:
                    supression_times.append((strike.suppressed_time - strike.spawn_time).get("hr"))
                    supression_times_ignitions_only.append(
                        (strike.suppressed_time - strike.spawn_time).get("hr")
                    )
                else:
                    supression_times.append("N/A")
            filewriter.writerow(
                ["Latitude", "Longitude", "Inspection time (hr)", "Supression time (hr)"]
            )
            for row in zip(*[lats, lons, inspection_times, supression_times]):
                filewriter.writerow(row)
        return inspection_times, supression_times_ignitions_only

    def write_to_uav_updates_file(self, coordinator, prefix):
        """Write UAV event update data to output file."""
        uavs: List[UAV] = coordinator.uavs

        with open(
            os.path.join(
                self.output_folder,
                prefix + "uav_event_updates.csv",
            ),
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
                ]
            )
            all_uav_updates = []
            for uav in uavs:
                all_uav_updates = all_uav_updates + uav.past_locations

            all_uav_updates.sort()
            for uav_update in all_uav_updates:
                filewriter.writerow(
                    [
                        uav_update.name,
                        uav_update.lat,
                        uav_update.lon,
                        uav_update.time.get("min"),
                        uav_update.distance_travelled.get("km"),
                        uav_update.distance_hovered.get("km"),
                        uav_update.fuel * 100,
                        uav_update.current_range.get("km"),
                        str(uav_update.status),
                    ]
                )

    def write_to_wb_updates_file(self, coordinator, prefix):
        """Write water bomber event update data to output file."""
        water_bombers: List[WaterBomber] = coordinator.water_bombers
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
                ]
            )
            all_wb_updates = []
            for water_bomber in water_bombers:
                all_wb_updates = all_wb_updates + water_bomber.past_locations

            all_wb_updates.sort()
            for wb_update in all_wb_updates:
                filewriter.writerow(
                    [
                        wb_update.name,
                        wb_update.lat,
                        wb_update.lon,
                        wb_update.time.get(),
                        wb_update.distance_travelled.get("km"),
                        wb_update.distance_hovered.get("km"),
                        wb_update.fuel * 100,
                        wb_update.current_range.get("km"),
                        wb_update.water.get("L"),
                        str(wb_update.status),
                    ]
                )

    def write_to_input_parameters_folder(self, scenario_idx):
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
