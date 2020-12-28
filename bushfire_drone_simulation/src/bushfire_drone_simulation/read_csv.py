"""Functions for reading and writing data to a csv."""

import json
import logging
import math
import os

import pandas

from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.fire_utils import Time
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.units import Distance, Duration, Speed, Volume

_LOG = logging.getLogger(__name__)


def read_locations(filename: str, constructor, offset: int = 0):
    """Return a list of Locations contained in the first two columns of a given a csv file."""
    data = pandas.read_csv(filename)
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
    data = pandas.read_csv(filename)
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
        self.folder = os.path.dirname(filename)
        with open(filename) as file:
            self.data = json.load(file)

    def process_water_bombers(self, bases):
        """Create water bombers from json file."""
        water_bombers_dict = {}
        water_bombers_bases_dict = {}
        for water_bomber in self.data["water_bombers"]:
            water_bomber_spawn_locs = pandas.read_csv(
                os.path.join(self.folder, water_bomber["spawn_loc_file"])
            )
            x = water_bomber_spawn_locs[water_bomber_spawn_locs.columns[0]].values.tolist()
            y = water_bomber_spawn_locs[water_bomber_spawn_locs.columns[1]].values.tolist()
            water_bombers = []
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
                    )
                )
            water_bombers_dict[water_bomber["name"]] = water_bombers
            base_data = pandas.read_csv(
                os.path.join(self.folder, self.data["water_bomber_bases_filename"])
            )
            bases_specific = base_data[water_bomber["name"]]
            bases_all = base_data["all"]
            current_bases = []
            for (idx, base) in enumerate(bases):
                if bases_all[idx] == 1 or bases_specific[idx] == 1:
                    current_bases.append(base)
            water_bombers_bases_dict[water_bomber["name"]] = current_bases

        return water_bombers_dict, water_bombers_bases_dict

    def process_uavs(self):
        """Create uavs from json file."""
        uav_data = self.data["uavs"]
        uav_spawn_locs = pandas.read_csv(os.path.join(self.folder, uav_data["spawn_loc_file"]))
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

    def get_attribute(self, attribute: str):
        """Return attribute of JSON file."""
        return self.data[attribute]

    def get_relative_filepath(self, key: str):
        """Return realtive file path to given key."""
        return os.path.join(self.folder, self.data[key])
