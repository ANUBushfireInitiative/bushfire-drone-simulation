"""Functions for reading and writing data to a csv."""

from pathlib import Path
from typing import Any, Iterator, List, NamedTuple, Union

import pandas as pd

from bushfire_drone_simulation.fire_utils import (
    Base,
    Location,
    Target,
    Time,
    WaterTank,
    assert_bool,
    assert_number,
)
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.units import DEFAULT_DURATION_UNITS, Volume


class ColumnNotFoundException(Exception):
    """ColumnNotFoundException."""


class CSVFile:
    """CSVFile class to provide wrapper for csv files (with useful errors)."""

    def __init__(self, filename: Path):
        """Initialize CSVFile class.

        Args:
            filename (str): path to csv file from current working directory
        """
        self.filename = filename
        self.csv_dataframe: pd.DataFrame = pd.DataFrame(pd.read_csv(filename))  # type: ignore

    def get_column(self, column: Union[str, int]) -> pd.Series:  # type: ignore[no-any-unimported]
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
        """Get list of column headings.

        Returns:
            List[str]: List of column headings
        """
        return list(self.csv_dataframe.columns.values.tolist())

    def get_cell(self, column: Union[str, int], cell_idx: int) -> Any:
        """get_cell.

        Args:
            column_name (str): column_name
            cell_idx (int): cell_idx
        """
        return self.get_column(column)[cell_idx]

    def __len__(self) -> int:
        """__len__."""
        return len(self.csv_dataframe.axes[0])

    def __getitem__(self, i: Union[str, int]) -> pd.Series:  # type: ignore[no-any-unimported]
        """__getitem__.

        Args:
            i (Union[str, int]): i
        """
        return self.get_column(i)

    def __iter__(self) -> Iterator[NamedTuple]:
        """Iterate over rows in csv file.

        Returns:
            Iterable[NamedTuple]:
        """
        for row in self.csv_dataframe.itertuples():
            yield row


def read_bases(filename: Path) -> List[Base]:
    """Return a list of Bases from first two columns of the given csv file."""
    location_data = CSVFile(filename)
    to_return = []
    lats = location_data["latitude"]
    lons = location_data["longitude"]
    for i, lat in enumerate(lats):
        lat = assert_number(
            lat,
            f"Error: The latitude on row {i+1} of '{filename}' ('{lat}') is not a number",
        )
        lon = assert_number(
            lons[i],
            f"Error: The longitude on row {i+1} of '{filename}' ('{lons[i]}') is not a number",
        )
        to_return.append(Base(lat, lon, i))
    return to_return


def read_water_tanks(filename: Path, capacity_units: str = "L") -> List[WaterTank]:
    """Return a list of Water Tanks from first three columns of the given csv file."""
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
        to_return.append(WaterTank(lat, lon, Volume(cap, capacity_units).get(), i))
    return to_return


def read_locations(filename: Path) -> List[Location]:
    """Return a list of Locations contained in the first two columns of a given a csv file."""
    location_data = CSVFile(filename)
    to_return = []
    lats = location_data["latitude"]
    lons = location_data["longitude"]
    for i, lat in enumerate(lats):
        lat = assert_number(
            lat,
            f"Error: The latitude on row {i+1} of '{filename}' ('{lat}') is not a number",
        )
        lon = assert_number(
            lons[i],
            f"Error: The longitude on row {i+1} of '{filename}' ('{lons[i]}') is not a number",
        )
        to_return.append(Location(lat, lon))
    return to_return


def read_lightning(filename: Path, ignition_probability: float) -> List[Lightning]:
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
                ignition,
                (
                    f"Error: The ignition on row {i+1} of '{filename}' "
                    f"('{ignition}') is not a boolean."
                ),
            )
            else 0
            for i, ignition in enumerate(ignitions)
        ]
    else:
        ignition_probabilities = [ignition_probability for _ in enumerate(lats)]
    if "risk_rating" in lightning_data.get_column_headings():
        str_risk_ratings = lightning_data["risk_rating"]
        risk_ratings: List[float] = [
            assert_number(
                risk,
                (
                    f"Error: The risk_rating on row {i+1} of '{filename}' "
                    f"('{risk}') is not a number."
                ),
            )
            for i, risk in enumerate(str_risk_ratings)
        ]
    else:
        risk_ratings = [1 for _ in enumerate(lats)]

    for i, lat in enumerate(lats):
        lat = assert_number(
            lat, f"Error: The latitude on row {i+1} of '{filename}' ('{lat}') is not a number."
        )
        lon = assert_number(
            lons[i],
            f"Error: The longitude on row {i+1} of '{filename}' ('{lons[i]}') is not a number.",
        )
        lightning.append(
            Lightning(
                lat,
                lon,
                Time(str(times[i])).get(DEFAULT_DURATION_UNITS),
                ignition_probabilities[i],
                risk_ratings[i],
                i,
            ),
        )

    return lightning


def read_targets(filename: Path) -> List[Target]:
    """Return a list of targets from given file path."""
    targets: List[Target] = []
    target_data = CSVFile(filename)
    lats = target_data["latitude"]
    lons = target_data["longitude"]
    start_times = target_data["start time"]
    finish_times = target_data["finish time"]
    for i, lat in enumerate(lats):
        lat = assert_number(
            lat, f"Error: The latitude on row {i+1} of '{filename}' ('{lat}') is not a number."
        )
        lon = assert_number(
            lons[i],
            f"Error: The longitude on row {i+1} of '{filename}' ('{lons[i]}') is not a number.",
        )
        start_time = assert_number(
            start_times[i],
            f"Error: The longitude on row {i+1} of '{filename}' ('{start_times[i]}') "
            f"is not a number.",
        )
        finish_time = assert_number(
            finish_times[i],
            f"Error: The longitude on row {i+1} of '{filename}' ('{finish_times[i]}') "
            f"is not a number.",
        )
        targets.append(
            Target(
                lat,
                lon,
                start_time,
                finish_time,
            ),
        )
    return targets
