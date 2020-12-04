"""Functions for reading and writing data to a csv."""

import logging

import pandas

from bushfire_drone_simulation.fire_utils import Location, Time
from bushfire_drone_simulation.lightning import Lightning

_LOG = logging.getLogger(__name__)


def read_locations(filename: str, offset: int = 0):
    """Return a list of Locations contained in the first two columns of a given a csv file."""
    data = pandas.read_csv(filename)
    x = data[data.columns[0 + offset]].values.tolist()
    y = data[data.columns[1 + offset]].values.tolist()
    locations = []
    for i, _ in enumerate(x):
        locations.append(Location(x[i], y[i]))
    return locations


def read_lightning(filename: str, ignition_probability: float, offset: int = 0):
    """Return a list of Locations contained in the first two columns of a given a csv file."""
    data = pandas.read_csv(filename)
    x = data[data.columns[0 + offset]].values.tolist()
    y = data[data.columns[1 + offset]].values.tolist()
    time = data[data.columns[2 + offset]].values.tolist()
    lightning = []
    for i, _ in enumerate(x):
        lightning.append(Lightning(Location(x[i], y[i]), Time(time[i]), ignition_probability))
    return lightning


class CSVParameters:
    """Class for reading parameters from a csv file."""

    parameters = None

    def __init__(self, filename: str):
        """Read collection of variables stored in filename."""
        data = pandas.read_csv(filename)
        self.parameters = data[data.columns[2]].values.tolist()

    def get_uav_bases_filename(self):
        """Return uav bases filename."""
        return self.parameters[47]

    def get_uav_spawn_locations_filename(self):
        """Return uav spawn locations filename."""
        return self.parameters[44]

    def get_water_bomber_bases_filename(self):
        """Return water bomber bases filename."""
        return self.parameters[43]

    def get_water_bomber_spawn_locations_filename(self):
        """Return water bomber spawn locations filename."""
        return self.parameters[46]

    def get_water_tanks_filename(self):
        """Return water tanks filename."""
        return self.parameters[45]

    def get_lightning_filename(self):
        """Return lightning filename."""
        return self.parameters[0]

    def get_max_velocity(self, aircraft: str):
        """Return the maximum velocity of a given aircraft."""
        if aircraft == "UAV":
            return self.parameters[10]
        if aircraft == "WB":
            return self.parameters[16]
        _LOG.error("Incorrent aircraft input for get_max_velocity")
        return None

    def get_fuel_refill_time(self, aircraft: str):
        """Return the fuel refill time of a given aircraft."""
        if aircraft == "UAV":
            return self.parameters[11]
        if aircraft == "WB":
            return self.parameters[16]
        _LOG.error("Incorrent aircraft input for get_fuel_refill_time")
        return None

    def get_range(self, aircraft: str):
        """Return the range of a given aircraft."""
        if aircraft == "UAV":
            return self.parameters[12]
        if aircraft == "WB":
            return self.parameters[22]
        if aircraft == "WBE":
            return self.parameters[21]
        _LOG.error("Incorrent aircraft input for get_range")
        return None

    def get_water_refill_time(self):
        """Return the range of an aircraft."""
        return self.parameters[18]

    def get_bombing_time(self):
        """Return the bombing time of an aircraft."""
        return self.parameters[17]

    def get_water_capacity(self):
        """Return the water capacity of an aircraft."""
        return self.parameters[23]

    def get_water_per_delivery(self):
        """Return the water required for each delivery."""
        return self.parameters[20]

    def get_ignition_probability(self):
        """Return the ignition probability of an lightning strike."""
        return self.parameters[35]
