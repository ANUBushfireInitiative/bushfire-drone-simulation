"""Various classes and functions useful to the bushfire_drone_simulation application."""

from math import atan2, cos, degrees, inf, radians, sin, sqrt
from typing import Any, Tuple

from bushfire_drone_simulation.units import DEFAULT_DURATION_UNITS, Distance, Duration, Volume


class Location:
    """Location class storing postion in worldwide latitude and longitude coordinates."""

    def __init__(self, latitude: float, longitude: float):
        """Initialise location from latitude and longitude coordinates."""
        self.lat = latitude
        self.lon = longitude

    def distance(self, other: "Location", units: str = "km") -> Distance:
        """Find Euclidian distance between two locations."""
        temp = (
            sin(radians(other.lat - self.lat) / 2) ** 2
            + cos(radians(self.lat))
            * cos(radians(other.lat))
            * sin(radians(other.lon - self.lon) / 2) ** 2
        )
        return Distance(6371 * 2 * atan2(sqrt(temp), sqrt(1 - temp)), units)

    def intermediate_point(self, other: "Location", percentage: float) -> "Location":
        """Find intermediate point percentage of the way between self and other."""
        angular = self.distance(other) / Distance(6371)
        h_1 = sin(radians((1 - percentage) * angular)) / sin(radians(angular))
        h_2 = sin(radians(percentage * angular)) / sin(radians(angular))
        x = h_1 * cos(radians(self.lat)) * cos(radians(self.lon)) + h_2 * cos(
            radians(other.lat)
        ) * cos(radians(other.lon))
        y = h_1 * cos(radians(self.lat)) * sin(radians(self.lon)) + h_2 * cos(
            radians(other.lat)
        ) * sin(radians(other.lon))
        z = h_1 * sin(radians(self.lat)) + h_2 * sin(radians(other.lat))
        return Location(degrees(atan2(z, sqrt(x * x + y * y))), degrees(atan2(y, x)))

    def to_coordinates(self) -> Tuple[float, float]:
        """Return pixel coordinates of location."""
        # FIXME(not converting lat lon to coordinates)  # pylint: disable=fixme
        return (self.lon - 144) * 100, (-34 - self.lat) * 100

    def copy_loc(self) -> "Location":
        """Create a new instance of Location."""
        return Location(self.lat, self.lon)


class WaterTank(Location):
    """Class containing a water tank's location and capacity."""

    def __init__(self, latitude: float, longitude: float, capacity: Volume):
        """Initialise watertank from location and capacity."""
        super().__init__(latitude, longitude)
        self.capacity: Volume = capacity
        self.initial_capacity: Volume = self.capacity

    def remove_water(self, volume: Volume) -> None:
        """Remove a given volume from the water tank."""
        self.capacity -= volume


class Base(Location):
    """Class containing a base's location and fuel capacity."""

    def __init__(self, latitude: float, longitude: float, capacity: Volume):
        """Initialise aircraft base from location and fuel capacity."""
        super().__init__(latitude, longitude)
        self.capacity = capacity

    def remove_fuel(self, volume: Volume) -> None:
        """Remove a given volume of fuel from the base."""
        self.capacity -= volume


def month_to_days(month: int, leap_year: bool = False) -> int:
    """Month is coverted to the number of days since the beginning of the year."""
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
    """Time class storing time in the form YYYY-MM-DD-HH-MM-SS."""

    def __init__(self, time_in: str):
        """Initialise time from string in the form YYYY*MM*DD*HH*MM*SS.

        "*" represents any character, e.g. 2033-11/03D12*00?12 would be accepted
        Alternatively enter "inf" for an 'infnite time' (i.e. all times occur before it)
        Or "0" for time 0.
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

    def get(self, units: str = DEFAULT_DURATION_UNITS) -> float:
        """Return time."""
        return self.time.get(units)

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

    def add_duration(self, duration: Duration) -> None:
        """Add a given duration to time."""
        self.time += duration


def assert_number(value: Any, message: str) -> float:
    """assert_number.

    Args:
        value (Any): value
        message (str): message

    Returns:
        float:
    """
    if str(value) == "inf":
        return inf
    try:
        int(value)
        return float(value)
    except ValueError:
        assert False, message


def assert_bool(value: Any, message: str) -> bool:
    """assert_bool.

    Args:
        value (Any): value
        message (str): message

    Returns:
        bool:
    """
    value = str(value)
    if value.lower() in ["1", "1.0", "t", "true", "yes", "y"]:
        return True
    assert value.lower() in ["0", "0.0", "f", "false", "no", "n", "", "nan"], message
    return False
