"""Various classes and functions useful to the bushfire_drone_simulation application."""

import logging
from math import atan2, cos, degrees, inf, radians, sin, sqrt
from typing import Any, Tuple

from bushfire_drone_simulation.units import DEFAULT_DURATION_UNITS, Duration

_LOG = logging.getLogger(__name__)

EARTH_RADIUS = 6371  # in km


class Coordinate:
    """Coordinate."""

    def __init__(self, x: int, y: int):
        """Initialise coordinate."""
        self.x = x
        self.y = y


class Location:
    """Position in worldwide latitude and longitude coordinates."""

    def __init__(self, latitude: float, longitude: float):
        """Initialise from latitude and longitude coordinates."""
        self.lat = latitude
        self.lon = longitude

    def distance(self, other: "Location") -> float:
        """Find Euclidian distance in km between two locations."""
        temp = (
            sin(radians(other.lat - self.lat) / 2) ** 2
            + cos(radians(self.lat))
            * cos(radians(other.lat))
            * sin(radians(other.lon - self.lon) / 2) ** 2
        )
        return EARTH_RADIUS * 2 * atan2(sqrt(temp), sqrt(1 - temp))

    def plane_distance_sq(self, other: "Location") -> float:
        """Find planar distance squared in degrees between two locations."""
        return (self.lat - other.lat) ** 2 + (self.lon - other.lon) ** 2

    def __str__(self) -> str:
        """To string method for location."""
        return f"{self.lat} {self.lon}"

    def equals(self, other: "Location") -> bool:
        """Equality for Location."""
        return self.lat == other.lat and self.lon == other.lon

    def intermediate_point(self, other: "Location", percentage: float) -> "Location":
        """Find intermediate point a proportion of the way between self and other."""
        angular_distance = self.distance(other) / EARTH_RADIUS
        if angular_distance == 0:
            return self.copy_loc()
        h_1 = sin(radians((1 - percentage) * angular_distance)) / sin(radians(angular_distance))
        h_2 = sin(radians(percentage * angular_distance)) / sin(radians(angular_distance))
        x = h_1 * cos(radians(self.lat)) * cos(radians(self.lon)) + h_2 * cos(
            radians(other.lat)
        ) * cos(radians(other.lon))
        y = h_1 * cos(radians(self.lat)) * sin(radians(self.lon)) + h_2 * cos(
            radians(other.lat)
        ) * sin(radians(other.lon))
        z = h_1 * sin(radians(self.lat)) + h_2 * sin(radians(other.lat))
        lon = degrees(atan2(y, x)) % 360
        lat = degrees(atan2(z, sqrt(x * x + y * y)))
        return Location(lat, lon)

    def plane_intermediate_point(self, other: "Location", percentage: float) -> "Location":
        """Find intermediate point a proportion of the way between self and other.

        As if the locations were on a plane.
        """
        new_lat = (1 - percentage) * self.lat + percentage * other.lat
        new_lon = (1 - percentage) * self.lon + percentage * other.lon
        return Location(new_lat, new_lon)

    def copy_loc(self) -> "Location":
        """Create a new instance of Location with same lat and lon."""
        return Location(self.lat, self.lon)

    def closest_point_on_line(self, start: "Location", end: "Location") -> "Location":
        """Return the closest point to self on line given start and end points."""
        dot_prod = (start.lat - self.lat) * (start.lat - end.lat) + (start.lon - self.lon) * (
            start.lon - end.lon
        )
        prop = dot_prod / start.plane_distance_sq(end)

        if prop < 0:
            return start.copy_loc()
        if prop > 1:
            return end.copy_loc()
        return start.plane_intermediate_point(end, prop)


class Target(Location):
    """Location and time frame for UAV target (level of attraction defined in parameters file)."""

    def __init__(self, latitude: float, longitude: float, start_time: float, end_time: float):
        """Initialize target."""
        super().__init__(latitude, longitude)
        self.start_time = start_time
        self.end_time = end_time

    def currently_active(self, time: float) -> bool:
        """Return whether or not a given time falls between the start and finish time."""
        return self.start_time <= time <= self.end_time


class Base(Location):
    """Base's location and id_no."""

    def __init__(self, latitude: float, longitude: float, id_no: int):
        """Initialise aircraft base from location and id_no."""
        super().__init__(latitude, longitude)
        self.id_no: int = id_no


class WaterTank(Location):
    """Water tank's location and capacity."""

    def __init__(self, latitude: float, longitude: float, capacity: float, id_no: int):
        """Initialise watertank from location and capacity."""
        super().__init__(latitude, longitude)
        self.capacity: float = capacity
        self.unallocated_capacity: float = capacity
        self.initial_capacity: float = capacity
        self.id_no = id_no

    def copy_from_water_tank(self, other: "WaterTank") -> None:
        """Copy parameters from another water tank.

        Args:
            other ("WaterTank"): other
        """
        self.__dict__.update(other.__dict__)

    def remove_water(self, volume: float) -> None:
        """Remove a given volume from the water tank."""
        self.capacity -= volume
        if self.capacity < 0:
            _LOG.error("Water tank ran out of water")

    def remove_unallocated_water(self, volume: float) -> None:
        """Remove a given volume from unallocated water in the water tank."""
        self.unallocated_capacity -= volume

    def return_allocated_water(self, volume: float) -> None:
        """Return a given volume to the unallocated water tank in the water tank."""
        self.unallocated_capacity += volume

    def get_water_capacity(self, future_capacity: bool = False) -> float:
        """Return water capacity of tank.

        The actual capacity (self.capacity) or the unallocated capacity if future_capacity
        is True

        Args:
            future_capacity (bool): Select whether to return current or future capacity.
            Default: False

        Returns:
            Volume: Water capacity
        """
        if future_capacity:
            return self.unallocated_capacity
        return self.capacity


def month_to_days(month: int, leap_year: bool = False) -> int:
    """Convert month to the number of days since the beginning of the year to beginning of month.

    Usage:
        >>> from bushfire_drone_simulation.fire_utils import month_to_days
        >>> month_to_days(13)
        365

        >>> month_to_days(13, leap_year=True)
        366
    """
    month -= 1
    days = month * 31
    if month >= 2:
        days -= 3
        if leap_year:
            days += 1
    for i in [4, 6, 9, 11]:
        if month >= i:
            days -= 1
    return days


def days_to_month(days: int, leap_year: bool = False) -> Tuple[int, int]:
    """Convert number of days to a date since the beginning of the year.

    Usage:
        >>> from bushfire_drone_simulation.fire_utils import days_to_month
        >>> days_to_month(365)
        (12, 31)
    """
    month = 1
    for i in range(1, 12):
        sub = 31
        if i in (4, 6, 9, 11):
            sub = 30
        if i == 2:
            sub = 28
            if leap_year:
                sub += 1
        if days <= sub:
            break
        days -= sub
        month += 1
    return month, days


class Time:
    """Time in the form YYYY-MM-DD-HH-MM-SS."""

    def __init__(self, time_in: str):
        """Initialise time from string in the form YYYY*MM*DD*HH*MM*SS.

        "*" represents any character, e.g. 2033-11/03D12*00?12 would be accepted.
        Alternatively enter "inf" for an 'infinite time' (i.e. all times occur before it)
        or "0" for time 0.
        """
        if time_in == "inf":
            self.time: Duration = Duration(inf)
        elif time_in == "0":
            self.time = Duration(0)
        else:
            try:
                self.time = Duration(float(time_in), "min")
            except ValueError:
                self.time = (
                    # Duration(int(time_in[:4]), "year")
                    Duration(month_to_days(int(time_in[5:7])) + int(time_in[8:10]) - 1, "day")
                    + Duration(int(time_in[11:13]), "hr")
                    + Duration(int(time_in[14:16]), "min")
                    + Duration(int(time_in[17:19]), "s")
                )

    @classmethod
    def from_float(cls, time: float, units: str = DEFAULT_DURATION_UNITS) -> "Time":
        """Initialise Time from a float.

        Args:
            time (float): time as a float
            units (str): units [Default: DEFAULT_DURATION_UNITS]

        Returns:
            Time: Time object
        """
        ret_time = Time("0")
        ret_time.time = Duration(time, units)
        return ret_time

    def get(self, units: str = DEFAULT_DURATION_UNITS) -> float:
        """Return time as a float using specified units.

        Args:
            units (str): units (Default: DEFAULT_DURATION_UNITS)

        Returns:
            float: Time in specified units relative to time "0"
        """
        return self.time.get(units)

    def copy(self) -> "Time":
        """Create a new equivalent instance of Time."""
        ret_time = Time("inf")
        ret_time.time = self.time
        return ret_time

    def __eq__(self, other: object) -> bool:
        """Equality for Time."""
        if not isinstance(other, Time):
            return False
        return self.get() == other.get()

    def __lt__(self, other: "Time") -> bool:
        """Less than operator for Time."""
        return self.get() < other.get()

    def __ge__(self, other: "Time") -> bool:
        """Greater than or equal to operator for Time."""
        return self.get() >= other.get()

    def __sub__(self, other: "Time") -> Duration:
        """Subtraction operator for Time, returns a Duration."""
        return Duration(self.get() - other.get())

    def __add__(self, other: Duration) -> "Time":
        """Add a duration to a time.

        Args:
            other (Duration): Duration to add

        Returns:
            Time: New time instance
        """
        new_time = self.copy()
        new_time.add_duration(other)
        return new_time

    def add_duration(self, duration: Duration) -> None:
        """Add a given duration to time."""
        self.time += duration


def assert_number(value: Any, message: str) -> float:
    """Assert that a value can be converted to a float and return converted value.

    Args:
        value (Any): value to be converted to float
        message (str): message to be output in error if value cannot be converted to a float

    Returns:
        float: Value as a float.
    """
    if str(value) == "inf":
        return inf
    try:
        return float(value)
    except ValueError as err:
        raise ValueError(message) from err


def assert_bool(value: Any, message: str) -> bool:
    """Assert a value can be converted to a boolean and return the converted value.

    Args:
        value (Any): value to be converted to a boolean
        message (str): message to be output in error if value cannot be converted to a boolean

    Returns:
        bool: value converted to a boolean
    """
    value = str(value)
    if value.lower() in ["1", "1.0", "t", "true", "yes", "y"]:
        return True
    if value.lower() in ["0", "0.0", "f", "false", "no", "n", "", "nan"]:
        return False
    raise ValueError(message)
