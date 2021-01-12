"""Functions for reading and writing data to a csv."""

import logging
import math

import pandas as pd

from bushfire_drone_simulation.fire_utils import Time
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.units import Volume

_LOG = logging.getLogger(__name__)


def read_locations(filename: str, constructor, offset: int = 0):
    """Return a list of Locations contained in the first two columns of a given a csv file."""
    location_data = pd.read_csv(filename)
    x = location_data[location_data.columns[0 + offset]].values.tolist()
    y = location_data[location_data.columns[1 + offset]].values.tolist()
    capacity = location_data[location_data.columns[2 + offset]].values.tolist()
    ret = []
    for i, _ in enumerate(x):
        if str(capacity[i]) == "inf":
            capacity[i] = math.inf
        ret.append(constructor(x[i], y[i], Volume(capacity[i])))
    return ret


def read_lightning(filename: str, ignition_probability: float):
    """Return a list of Locations contained in the first two columns of a given a csv file."""
    lightning = []
    ligtning_data = pd.read_csv(filename)
    x = ligtning_data[ligtning_data.columns[0]].values.tolist()
    y = ligtning_data[ligtning_data.columns[1]].values.tolist()
    time = ligtning_data[ligtning_data.columns[2]].values.tolist()
    try:
        ignition = ligtning_data[ligtning_data.columns[3]].values.tolist()
        for i, _ in enumerate(x):
            lightning.append(Lightning(x[i], y[i], Time(time[i]), ignition[i]))
    except IndexError:
        for i, _ in enumerate(x):
            lightning.append(Lightning(x[i], y[i], Time(time[i]), ignition_probability))
    return lightning
