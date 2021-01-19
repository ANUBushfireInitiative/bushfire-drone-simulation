"""Functions for reading and writing data to a csv."""

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
        """Initialize CSVFile class.

        Args:
            filename (str): path to csv file from current working directory
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

    def get_column_headings(self) -> List[str]:
        """Get headins of columns.

        Returns:
            List[str]: List of column headings
        """
        return self.csv_dataframe.columns.values.tolist()

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
    lats = location_data["latitude"]
    lons = location_data["longitude"]
    for i, cap in enumerate(location_data["capacity"]):
        cap = assert_number(
            cap, f"Error: The capacity on row {i+1} of '{filename}' ('{cap}') is not a number"
        )
        lat = assert_number(
            lats[i],
            f"Error: The latitude on row {i+1} of '{filename}' ('{lats[i]}') is not a number",
        )
        lon = assert_number(
            lons[i],
            f"Error: The longitude on row {i+1} of '{filename}' ('{lons[i]}') is not a number",
        )
        to_return.append(constructor(lat, lon, Volume(cap)))
    return to_return


def read_lightning(filename: str, ignition_probability: float) -> List[Lightning]:
    """Return a list of Locations contained in the first two columns of a given a csv file."""
    lightning = []
    lightning_data = CSVFile(filename)
    lats = lightning_data["latitude"]
    lons = lightning_data["longitude"]
    times = lightning_data["time"]
    if "ignited" in lightning_data.get_column_headings():
        ignitions = lightning_data["ignited"]
        ignition_probabilities: List[float] = [
            1
            if assert_bool(
                i,
                (
                    f"Error: The ignition on row {i+1} of '{filename}'"
                    "('{ignitions[i]}') is not a boolean."
                ),
            )
            else 0
            for i in ignitions
        ]
    else:
        ignition_probabilities = [ignition_probability for _ in enumerate(lats)]

    for i, lat in enumerate(lats):
        lat = assert_number(
            lat, f"Error: The latitude on row {i+1} of '{filename}' ('{lat}') is not a number."
        )
        lon = assert_number(
            lons[i],
            f"Error: The longitude on row {i+1} of '{filename}' ('{lons[i]}') is not a number.",
        )
        lightning.append(Lightning(lat, lon, Time(str(times[i])), ignition_probabilities[i]))

    return lightning
