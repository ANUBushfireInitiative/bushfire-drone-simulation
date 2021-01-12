"""Functions for reading and writing data to a csv."""

import logging
import math
from typing import Union

import pandas as pd

from bushfire_drone_simulation.fire_utils import Time
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.units import Volume

_LOG = logging.getLogger(__name__)


class ColumnNotFoundException(Exception):
    """ColumnNotFoundException."""


class CSVFile:
    """CSVFile class to provide wrapper for csv files (with useful errors)."""

    def __init__(self, filename: str):
        """__init__.

        Args:
            filename (str): filename
        """
        self.filename = filename
        self.csv_dataframe = pd.read_csv(filename)

    def get_column(self, column: Union[str, int]):
        """get_column.

        Args:
            column_name (str): column_name
        """
        if isinstance(column, int):
            return self.csv_dataframe.iloc[:, column]
        if column not in self.csv_dataframe:
            raise ColumnNotFoundException(
                f"Error: No column labelled '{column}' in '{self.filename}'"
            )
        return self.csv_dataframe[column]

    def get_cell(self, column_name: str, cell_idx: int):
        """get_cell.

        Args:
            column_name (str): column_name
            cell_idx (int): cell_idx
        """
        return self.get_column(column_name)[cell_idx]

    def __len__(self):
        """__len__."""
        return len(self.csv_dataframe.axes[0])

    def __getitem__(self, i: Union[str, int]):
        """__getitem__.

        Args:
            i (Union[str, int]): i
        """
        return self.get_column(i)


def read_locations_with_capacity(filename: str, constructor):
    """Return a list of Locations contained in the first two columns of a given a csv file."""
    location_data = CSVFile(filename)
    to_return = []
    for i, cap in enumerate(location_data["capacity"]):
        if str(cap) == "inf":
            cap = math.inf
        to_return.append(
            constructor(location_data["latitude"][i], location_data["longitude"][i], Volume(cap))
        )
    return to_return


def read_lightning(filename: str, ignition_probability: float):
    """Return a list of Locations contained in the first two columns of a given a csv file."""
    lightning = []
    lightning_data = CSVFile(filename)
    lats = lightning_data[0]
    lons = lightning_data[1]
    times = lightning_data[2]
    try:
        ignitions = lightning_data[3]
        for i, lat in enumerate(lats):
            lightning.append(Lightning(lat, lons[i], Time(times[i]), ignitions[i]))
    except (ColumnNotFoundException, IndexError):
        for i, lat in enumerate(lats):
            lightning.append(Lightning(lat, lons[i], Time(times[i]), ignition_probability))
    return lightning
