"""Various classes and functions useful to the bushfire_drone_simulation application."""

from math import atan2, cos, inf, radians, sin, sqrt

from bushfire_drone_simulation.units import DEFAULT_DURATION_UNITS, Distance, Duration, Volume

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

    def to_coordinates(self):
        """Return pixel coordinates of location."""
        # FIXME(not converting lat lon to coordinates)  # pylint: disable=fixme
        return (self.lat + 39) * 130, (self.lon - 142) * 60

    def distance(self, other, units: str = "km"):
        """Find Euclidian distance."""
        temp = (
            sin(radians(other.lat - self.lat) / 2) ** 2
            + cos(radians(self.lat))
            * cos(radians(other.lat))
            * sin(radians(other.lon - self.lon) / 2) ** 2
        )
        return Distance(6371 * 2 * atan2(sqrt(temp), sqrt(1 - temp)), units)

    def copy_loc(self):
        """Create a new instance of Location."""
        return Location(self.lat, self.lon)


class WaterTank(Location):
    """Class containing a water tank's location and capacity."""

    def __init__(self, latitude: float, longitude: float, capacity: Volume):
        """Initialise watertank from location and capacity."""
        super().__init__(latitude, longitude)
        self.capacity = capacity

    def empty(self, volume: Volume):
        """Remove a given volume from the water tank."""
        self.capacity -= volume


class Base(Location):
    """Class containing a base's location and fuel capacity."""

    def __init__(self, latitude: float, longitude: float, capacity: Volume = None):
        """Initialise aircraft base from location and fuel capacity."""
        super().__init__(latitude, longitude)
        self.capacity = capacity


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
        Alternatively enter "inf" for an 'infnite time' (i.e. all times occur before it)
        """
        if time_in == "inf":
            self.time = Duration(inf)
        else:
            self.time = (
                # Duration(int(time_in[:4]), "year")
                Duration(month_to_days(int(time_in[5:7])) + int(time_in[8:10]) - 1, "day")
                + Duration(int(time_in[11:13]), "hr")
                + Duration(int(time_in[14:16]), "min")
                + Duration(int(time_in[17:19]), "s")
            )

    def copy_time(self):
        """Create new Time."""
        copy = Time("0000/00/00/00/00/00")
        copy.time = self.time
        return copy

    def get(self, units: str = DEFAULT_DURATION_UNITS):
        """Return time."""
        return self.time.get(units)

    def __eq__(self, other):
        """Equality for Time."""
        return self.get() == other.get()

    def __lt__(self, other):
        """Less than operator for Time."""
        return self.get() < other.get()

    def __sub__(self, other):
        """Subtraction operator for Time, returns a Duration."""
        return Duration(self.get() - other.get())

    def add_duration(self, duration: Duration):
        """Add a given duration to time."""
        self.time += duration


def minimum(array, min_value, operator=id):
    """Return the minimum value of a list and the index of that value."""
    index = None
    for (i, val) in enumerate(array):
        if operator(val) < min_value:
            index = i
            min_value = operator(val)
    return index, min_value
