"""Functions for reading and writing data to a csv."""

import math
from typing import List, Union

import pandas as pd

from bushfire_drone_simulation.fire_utils import Time, assert_bool, assert_number
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.units import Volume


class ColumnNotFoundException(Exception):
    """ColumnNotFoundException."""


class CSVFile:
    """CSVFile class to provide wrapper for csv files (with useful errors)."""

    def __init__(self, filename: str):
        """__init__.

        Args:
            filename (str): filename
        """
        self.filename: str = filename
        self.csv_dataframe: pd.DataFrame = pd.DataFrame(pd.read_csv(filename))

    def get_column(self, column: Union[str, int]) -> pd.Series:
        """get_column.

        Args:
            column_name (str): column_name
        """
        if isinstance(column, int):
            column_to_return = pd.Series(self.csv_dataframe.iloc[:, column])
        elif column not in self.csv_dataframe:
            raise ColumnNotFoundException(
                f"Error: No column labelled '{column}' in '{self.filename}'"
            )
        else:
            column_to_return = pd.Series(self.csv_dataframe[column])
        return column_to_return

    def get_cell(self, column: Union[str, int], cell_idx: int):
        """get_cell.

        Args:
            column_name (str): column_name
            cell_idx (int): cell_idx
        """
        return self.get_column(column)[cell_idx]

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
        assert isinstance(
            cap, (float, int)
        ), f"Error: The capacity on row {i+1} of '{filename}' ('{cap}') is not a number"
        to_return.append(
            constructor(location_data["latitude"][i], location_data["longitude"][i], Volume(cap))
        )
    return to_return


def read_lightning(filename: str, ignition_probability: float) -> List[Lightning]:
    """Return a list of Locations contained in the first two columns of a given a csv file."""
    lightning = []
    lightning_data = CSVFile(filename)
    lats = lightning_data["latitude"]
    lons = lightning_data["longitude"]
    times = lightning_data["time"]
    try:
        ignitions = lightning_data["ignited"]
        for i, lat in enumerate(lats):
            lat = assert_number(
                lat, f"Error: The latitude on row {i+1} of '{filename}' ('{lat}') is not a number."
            )
            lon = assert_number(
                lons[i],
                f"Error: The longitude on row {i+1} of '{filename}' ('{lons[i]}') is not a number.",
            )
            ignited = assert_bool(
                ignitions[i],
                f"Error: The ignition on row {i+1} of '{filename}'\
('{ignitions[i]}') is not a boolean.",
            )
            lightning.append(Lightning(lat, lon, Time(str(times[i])), 1 if ignited else 0))
    except ColumnNotFoundException:
        for i, lat in enumerate(lats):
            lat = assert_number(
                lat, f"Error: The latitude on row {i+1} of '{filename}' ('{lat}') is not a number."
            )
            lon = assert_number(
                lons[i],
                f"Error: The longitude on row {i+1} of '{filename}' ('{lons[i]}') is not a number.",
            )
            lightning.append(Lightning(lat, lon, Time(str(times[i])), ignition_probability))
    return lightning
