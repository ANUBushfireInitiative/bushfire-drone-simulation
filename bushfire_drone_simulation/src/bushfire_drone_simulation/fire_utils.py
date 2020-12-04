"""Various classes and functions useful to the bushfire_drone_simulation application."""

import math

from bushfire_drone_simulation.units import Distance, Duration

# class Point:  # pylint: disable=too-few-public-methods
#     """Point class holding a pair of x-y coordinates."""

#     def __init__(self, x: int, y: int):
#         """Initialise point coordinates."""
#         self.x = x
#         self.y = y


class Location:  # pylint: disable=too-few-public-methods
    """Location class storing postion in worldwide latitude and longitude coordinates."""

    def __init__(self, latitude: float, longitude: float):
        """Initialise location from latitude and longitude coordinates."""
        self.lat = latitude
        self.lon = longitude

    @classmethod
    def from_coordinates(cls, x: int, y: int):
        """Initialise location from pixel coordinates."""
        location = cls(x, y)
        # FIXME(not converting coordinates to lat lon)  # pylint: disable=fixme
        return location

    def distance(self, other, units: str = "km"):
        """Find Euclidian distance."""
        # FIXME(units not correct)  # pylint: disable=fixme
        return Distance(math.sqrt((self.lat - other.lat) ** 2 + (self.lon - other.lon) ** 2), units)


def month_to_days(month: int, leap_year: bool = False):
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


def days_to_month(days: int, leap_year: bool = False):
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


class Time:  # pylint: disable=too-few-public-methods
    """Time class storing time in the form YYYY-MM-DD-HH-MM-SS."""

    def __init__(self, time_in: str):
        """Initialise time from string in the form YYYY*MM*DD*HH*MM*SS.

        "*" represents any character, e.g. 2033-11/03D12*00?12 would be accepted
        """
        self.time = (
            Duration(int(time_in[:4]), "year")
            + Duration(month_to_days(int(time_in[5:7])) + int(time_in[8:10]) - 1, "day")
            + Duration(int(time_in[11:13]), "hr")
            + Duration(int(time_in[14:16]), "min")
            + Duration(int(time_in[17:19]), "s")
        )

    def copy_time(self):
        """Create new Time."""
        copy = Time("0000/00/00/00/00/00")
        copy.time = self.time
        return copy

    def __eq__(self, other):
        """Equality for Time."""
        return self.time.get() == other.time.get()

    def __lt__(self, other):
        """Less than operator for Time."""
        return self.time.get() < other.time.get()

    def __sub__(self, other):
        """Subtraction operator for Time, returns a Duration."""
        return Duration(self.time.get() - other.time.get())

    def add_duration(self, duration: Duration):
        """Add a given duration to time."""
        self.time += duration


def minimum(array, max_value, operator=id):
    """Return the minimum value of a list and the index of that value."""
    index = None
    for (i, val) in enumerate(array):
        if operator(val) < max_value:
            index = i
            max_value = operator(val)
    return index, max_value


def minimum_distance(array, location):
    """Return the minimum value of a list and the index of that value."""
    max_value = Distance(10000000000)
    index = None
    for (i, val) in enumerate(array):
        if location.position.distance(val).get() < max_value.get():
            index = i
            max_value = location.position.distance(val)
    return index, max_value
