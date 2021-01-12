"""Functions for reading and writing data to a csv."""

import copy
import csv
import json
import logging
import math
import operator
import os
import shutil
from functools import reduce
from typing import List

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.fire_utils import Time, WaterTank
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.units import Volume

_LOG = logging.getLogger(__name__)
matplotlib.use("Agg")


def _get_from_dict(data_dict, key_list):
    """Get value corresponding to a list of keys in nested dictionaries."""
    return reduce(operator.getitem, key_list, data_dict)


def _set_in_dict(data_dict, key_list, value):
    """Set value corresponding to a list of keys in nested dictionaries."""
    _get_from_dict(data_dict, key_list[:-1])[key_list[-1]] = value


def read_locations(filename: str, constructor, offset: int = 0):
    """Return a list of Locations contained in the first two columns of a given a csv file."""
    data = pd.read_csv(filename)
    x = data[data.columns[0 + offset]].values.tolist()
    y = data[data.columns[1 + offset]].values.tolist()
    capacity = data[data.columns[2 + offset]].values.tolist()
    ret = []
    for i, _ in enumerate(x):
        if str(capacity[i]) == "inf":
            capacity[i] = math.inf
        ret.append(constructor(x[i], y[i], Volume(capacity[i])))
    return ret


def read_lightning(filename: str, ignition_probability: float):
    """Return a list of Locations contained in the first two columns of a given a csv file."""
    lightning = []
    data = pd.read_csv(filename)
    x = data[data.columns[0]].values.tolist()
    y = data[data.columns[1]].values.tolist()
    time = data[data.columns[2]].values.tolist()
    try:
        ignition = data[data.columns[3]].values.tolist()
        for i, _ in enumerate(x):
            lightning.append(Lightning(x[i], y[i], Time(time[i]), ignition[i]))
    except IndexError:
        for i, _ in enumerate(x):
            lightning.append(Lightning(x[i], y[i], Time(time[i]), ignition_probability))
    return lightning


class JSONParameters:
    """Class for reading parameters from a csv file."""

    def __init__(self, filename: str):
        """Read collection of variables stored in filename."""
        self.folder = os.path.dirname(filename)
        self.filepath = filename
        with open(filename) as file:
            self.parameters = json.load(file)

        self.scenarios = [self.parameters]
        if (
            "scenario_parameters_filename" in self.parameters.keys()
            and self.parameters["scenario_parameters_filename"] != "?"
        ):
            self.csv_scenarios = pd.read_csv(
                self.get_relative_filepath("scenario_parameters_filename", 0)
            )

            self.scenarios = [
                copy.deepcopy(self.parameters) for _ in range(len(self.csv_scenarios.axes[0]))
            ]

            for scenario_idx, scenario in enumerate(self.scenarios):
                scenario["scenario_name"] = self.csv_scenarios["scenario_name"][scenario_idx]

            def recurse_through_dictionaries(dictionary_path: List[str], dictionary):
                if isinstance(dictionary, str) and dictionary == "?":
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

        self.output_folder = os.path.join(self.folder, self.scenarios[0]["output_folder_name"])
        self.abort = False
        # All scenarios output to same folder
        if os.path.exists(self.output_folder):
            if os.listdir(self.output_folder):
                cont = input(
                    "Output folder already exists and is not empty, "
                    + "do you want to overwrite its contents? \nEnter 'Y' if yes and 'N' if no \n"
                )
                if cont.lower() != "y":
                    _LOG.info("Aborting")
                    self.abort = True

        else:
            os.mkdir(self.output_folder)

    def process_water_bombers(self, bases, scenario_idx):
        """Create water bombers from json file."""
        water_bombers = []
        water_bombers_bases_dict = {}
        for water_bomber_type in self.scenarios[scenario_idx]["water_bombers"]:
            water_bomber = self.scenarios[scenario_idx]["water_bombers"][water_bomber_type]
            water_bomber_spawn_locs = pd.read_csv(
                os.path.join(self.folder, water_bomber["spawn_loc_file"])
            )
            x = water_bomber_spawn_locs[water_bomber_spawn_locs.columns[0]].values.tolist()
            y = water_bomber_spawn_locs[water_bomber_spawn_locs.columns[1]].values.tolist()
            attributes = water_bomber["attributes"]
            for idx, _ in enumerate(x):
                water_bombers.append(
                    WaterBomber(
                        id_no=idx,
                        latitude=x[idx],
                        longitude=y[idx],
                        attributes=attributes,
                        bomber_type=water_bomber_type,
                    )
                )
            base_data = pd.read_csv(
                os.path.join(
                    self.folder, self.scenarios[scenario_idx]["water_bomber_bases_filename"]
                )
            )
            bases_specific = base_data[water_bomber_type]
            bases_all = base_data["all"]
            current_bases = []
            for (idx, base) in enumerate(bases):
                if bases_all[idx] == 1 or bases_specific[idx] == 1:
                    current_bases.append(base)
            water_bombers_bases_dict[water_bomber_type] = current_bases

        return water_bombers, water_bombers_bases_dict

    def process_uavs(self, scenario_idx):
        """Create uavs from json file."""
        uav_data = self.scenarios[scenario_idx]["uavs"]
        uav_spawn_locs = pd.read_csv(os.path.join(self.folder, uav_data["spawn_loc_file"]))
        x = uav_spawn_locs[uav_spawn_locs.columns[0]].values.tolist()
        y = uav_spawn_locs[uav_spawn_locs.columns[1]].values.tolist()
        uavs = []
        attributes = uav_data["attributes"]
        for idx, _ in enumerate(x):
            uavs.append(
                UAV(
                    id_no=idx,
                    latitude=x[idx],
                    longitude=y[idx],
                    attributes=attributes
                    # TODO(Inspection time) Incorporate inspection time #pylint: disable=fixme
                )
            )
        return uavs

    def get_attribute(self, attribute: str, scenario_idx):
        """Return attribute of JSON file."""
        return self.scenarios[scenario_idx][attribute]

    def get_relative_filepath(self, key: str, scenario_idx):
        """Return realtive file path to given key."""
        return os.path.join(self.folder, self.scenarios[scenario_idx][key])

    def write_to_output_folder(
        self,
        lightning_strikes: List[Lightning],
        water_bombers: List[WaterBomber],
        water_tanks: List[WaterTank],
        scenario_idx,
    ):
        """Write results of simulation to output folder."""
        prefix = ""
        if "scenario_name" in self.scenarios[scenario_idx]:
            prefix = str(self.scenarios[scenario_idx]["scenario_name"]) + "_"

        with open(
            os.path.join(
                self.output_folder,
                prefix + "simulation_output.csv",
            ),
            "w",
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
            num_suppressed = [wb.num_ignitions_suppressed() for wb in water_bombers]
            axs[1, 0].set_title("Ligntning strikes suppressed per helicopter")
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
                    str(self.scenarios[scenario_idx]["scenario_name"])
                    + "inspection_times_plot.png",
                )
            )
        self.write_to_input_parameters_folder(scenario_idx)

    def write_to_input_parameters_folder(self, scenario_idx):
        """Copy input parameters to input parameters folder to be outputed."""
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
        for water_bomber_type in self.scenarios[scenario_idx]["water_bombers"]:
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
