"""Functions for reading and writing data to a csv."""

import copy
import csv
import json
import logging
import math
import operator
import os
from functools import reduce
from typing import List

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.fire_utils import Time, WaterTank
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.units import Distance, Duration, Speed, Volume

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


def read_lightning(filename: str, ignition_probability: float, offset: int = 0):
    """Return a list of Locations contained in the first two columns of a given a csv file."""
    data = pd.read_csv(filename)
    x = data[data.columns[0 + offset]].values.tolist()
    y = data[data.columns[1 + offset]].values.tolist()
    time = data[data.columns[2 + offset]].values.tolist()
    lightning = []
    for i, _ in enumerate(x):
        lightning.append(Lightning(x[i], y[i], Time(time[i]), ignition_probability))
    return lightning


class JSONParameters:
    """Class for reading parameters from a csv file."""

    def __init__(self, filename: str):
        """Read collection of variables stored in filename."""
        self.scenario_idx = 0  # FIXME(BLA) pylint: disable=w0511
        self.folder = os.path.dirname(filename)
        with open(filename) as file:
            self.parameters = json.load(file)

        self.scenarios = [self.parameters]
        if (
            "scenario_parameters_filename" in self.parameters.keys()
            and self.parameters["scenario_parameters_filename"] != "?"
        ):
            self.csv_scenarios = pd.read_csv(
                self.get_relative_filepath("scenario_parameters_filename")
            )

            self.scenarios = [
                copy.deepcopy(self.parameters) for _ in range(len(self.csv_scenarios.axes[0]))
            ]

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

        if (
            "scenarios_to_run" in self.parameters.keys()
            and self.parameters["scenarios_to_run"] != "all"
        ):
            self.scenarios_to_run = self.parameters["scenarios_to_run"]
        else:
            self.scenarios_to_run = range(0, len(self.scenarios))

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
                    print("Aborting")
                    self.abort = True

        else:
            print("creating output folder")
            os.mkdir(self.output_folder)

    def process_water_bombers(self, bases, scenario_idx=None):
        """Create water bombers from json file."""
        if scenario_idx is None:
            scenario_idx = self.scenario_idx
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
                        max_velocity=Speed(int(attributes["flight_speed"]), "km", "hr"),
                        range_under_load=Distance(int(attributes["range_under_load"]), "km"),
                        range_empty=Distance(int(attributes["range_empty"]), "km"),
                        water_refill_time=Duration(int(attributes["water_refill_time"]), "min"),
                        fuel_refill_time=Duration(int(attributes["fuel_refill_time"]), "min"),
                        bombing_time=Duration(int(attributes["bombing_time"]), "min"),
                        water_capacity=Volume(int(attributes["water_capacity"]), "L"),
                        water_per_delivery=Volume(int(attributes["water_per_delivery"]), "L"),
                        bomber_type=water_bomber_type,
                        bomber_name=f"{water_bomber_type} {idx+1}",
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

    def process_uavs(self, scenario_idx=None):
        """Create uavs from json file."""
        if scenario_idx is None:
            scenario_idx = self.scenario_idx
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
                    max_velocity=Speed(int(attributes["flight_speed"]), "km", "hr"),
                    total_range=Distance(int(attributes["range"]), "km"),
                    fuel_refill_time=Duration(int(attributes["fuel_refill_time"]), "min"),
                    # TODO(Inspection time) Incorporate inspection time #pylint: disable=fixme
                )
            )
        return uavs

    def get_attribute(self, attribute: str, scenario_idx=None):
        """Return attribute of JSON file."""
        if scenario_idx is None:
            scenario_idx = self.scenario_idx
        return self.scenarios[scenario_idx][attribute]

    def get_relative_filepath(self, key: str, scenario_idx=None):
        """Return realtive file path to given key."""
        if scenario_idx is None:
            scenario_idx = self.scenario_idx
        return os.path.join(self.folder, self.scenarios[scenario_idx][key])

    def write_to_output_folder(
        self,
        lightning_strikes: List[Lightning],
        water_bombers: List[WaterBomber],
        water_tanks: List[WaterTank],
        scenario_idx=None,
    ):
        """Write results of simulation to output folder."""
        with open(
            os.path.join(self.output_folder, "simulation_output_s" + str(scenario_idx) + ".csv"),
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
            axs[0, 0].set_xlim(left=0)
            axs[0, 0].set_ylim(bottom=0)
            axs[0, 0].hist(inspection_times, bins=20)
            axs[0, 0].set_title("Histogram of UAV inspection times")
            axs[0, 0].set(xlabel="Inspection time (Hours)", ylabel="Frequency")

            axs[0, 1].set_xlim(left=0)
            axs[0, 1].set_ylim(bottom=0)
            axs[0, 1].hist(supression_times_ignitions_only, bins=20)
            axs[0, 1].set_title("Histogram of supression times")
            axs[0, 1].set(xlabel="Suppression time (Hours)", ylabel="Frequency")

            water_bomber_names = [wb.name for wb in water_bombers]
            num_suppressed = [wb.num_ignitions_suppressed() for wb in water_bombers]
            axs[1, 0].set_title("Ligntning strikes suppressed per helicopter")
            axs[1, 0].bar(water_bomber_names, num_suppressed)
            axs[1, 0].tick_params(labelrotation=90)

            water_tank_ids = [i for i, _ in enumerate(water_tanks)]
            water_tank_levels = [wt.capacity.get(units="kL") for wt in water_tanks]
            axs[1, 1].set_title("Water tank levels after suppression")
            axs[1, 1].bar(
                water_tank_ids,
                [wt.initial_capacity.get(units="kL") for wt in water_tanks],
                label="Full Capacity",
                color="orange",
            )
            axs[1, 1].bar(water_tank_ids, water_tank_levels, label="Final Level", color="blue")
            axs[1, 1].legend()
            axs[1, 1].set(ylabel="kL")

            fig.tight_layout()
            plt.savefig(
                os.path.join(
                    self.output_folder, "inspection_times_plot_s" + str(scenario_idx) + ".png"
                )
            )
