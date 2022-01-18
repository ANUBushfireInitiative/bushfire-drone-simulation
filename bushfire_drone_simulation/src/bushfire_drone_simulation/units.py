"""Various unit classes useful to the bushfire_drone_simulation."""

import abc
from copy import deepcopy
from typing import TypeVar, Union

DEFAULT_DISTANCE_UNITS = "km"
DISTANCE_FACTORS = {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000}

DEFAULT_DURATION_UNITS = "s"
DURATION_FACTORS = {"ms": 0.001, "s": 1.0, "min": 60, "hr": 3600, "day": 86400, "year": 31536000}

DEFAULT_VOLUME_UNITS = "L"
VOLUME_FACTORS = {"mL": 0.001, "L": 1.0, "kL": 1000, "ML": 1000000}

UnitsType = TypeVar("UnitsType", bound="Units")


class Units:
    """Units class for easy unit conversion."""

    @abc.abstractmethod
    def __init__(self, value: float):
        """Initialize units."""
        self.value = value

    def __lt__(self, other: "Units") -> bool:
        """Less than operator of Distance."""
        if isinstance(other, (float, int)):
            return self.value < other
        assert isinstance(self, type(other)), "Units in inequality are not the same"
        return self.value < other.value

    def __sub__(self: UnitsType, other: UnitsType) -> UnitsType:
        """Subtraction operator for Distance."""
        to_return = deepcopy(self)
        assert isinstance(self, type(other)), "Units in subtraction are not the same"
        to_return.value -= other.value
        return to_return

    def __mul__(self: UnitsType, other: Union[int, float]) -> UnitsType:
        """Scalar multiplication operator for Distance."""
        to_return = deepcopy(self)
        assert isinstance(other, (float, int)), (
            "Multiplication of "
            + str(type(self))
            + " and "
            + str(type(other))
            + " is not supported. To multiply a speed and time to return a distance, "
            "use time.mul_by_speed(speed) or speed.mul_by_time(time) respectively."
        )
        to_return.value *= other
        return to_return

    def __add__(self: UnitsType, other: UnitsType) -> UnitsType:
        """Addition operator of Duration."""
        to_return = deepcopy(self)
        assert isinstance(self, type(other)), "Units in addition are not the same"
        to_return.value += other.value
        return to_return

    def __ge__(self: UnitsType, other: UnitsType) -> bool:
        """Greater than or equal to operator for Units."""
        assert isinstance(self, type(other)), "Units in inequality are not the same"
        return self.value >= other.value

    def __truediv__(self: UnitsType, other: UnitsType) -> float:
        """Division operator for Units."""
        assert isinstance(self, type(other)), (
            "Units in division are not the same. To divide a distance by speed or time, "
            "use distance.div_by_speed(speed) or distance.div_by_time(time) respectively."
        )
        return self.value / other.value


class Distance(Units):
    """Distance class for easy unit conversion. Distance stored internally as metres."""

    def __init__(self, distance: float, units: str = DEFAULT_DISTANCE_UNITS):
        """Initialize distance specifying units.

        Defaults to DEFAULT_DISTANCE_UNITS if units not specified.
        """
        super().__init__(distance * DISTANCE_FACTORS[units])

    def get(self, units: str = DEFAULT_DISTANCE_UNITS) -> float:
        """Get distance specifying units.

        Defaults to DEFAULT_DISTANCE_UNITS if units not specified.
        """
        return self.value / DISTANCE_FACTORS[units]

    def div_by_time(self, time: "Duration") -> "Speed":
        """Divide distance by time to get speed.

        Args:
            time ("Duration"): time

        Returns:
            "Speed": Speed
        """
        return Speed(self.get(DEFAULT_DISTANCE_UNITS) / time.get(DEFAULT_DURATION_UNITS))

    def div_by_speed(self, speed: "Speed") -> "Duration":
        """Divide distance by speed to get time.

        Args:
            time ("Duration"): time

        Returns:
            "Speed": Speed
        """
        return Duration(self.get("km") / speed.get("km", DEFAULT_DURATION_UNITS))


class Duration(Units):
    """Duration class for easy unit conversion. Duration stored internally as seconds."""

    def __init__(self, duration: float, units: str = DEFAULT_DURATION_UNITS):
        """Initialize duration specifying units.

        Defaults to DEFAULT_DURATION_UNITS if units not specified.
        """
        super().__init__(duration * DURATION_FACTORS[units])

    def get(self, units: str = DEFAULT_DURATION_UNITS) -> float:
        """Get duration specifying units.

        Defaults to DEFAULT_DURATION_UNITS if units not specified.
        """
        return self.value / DURATION_FACTORS[units]

    def mul_by_speed(self, speed: "Speed") -> Distance:
        """mul_by_speed.

        Args:
            speed ("Speed"): speed

        Returns:
            Distance:
        """
        return Distance(self.get("hr") * speed.get(DEFAULT_DISTANCE_UNITS, "hr"))


class Speed(Units):
    """Speed class for easy unit conversion. Speed stored internally as metres/second."""

    def __init__(
        self,
        speed: float,
        distance_units: str = DEFAULT_DISTANCE_UNITS,
        time_units: str = DEFAULT_DURATION_UNITS,
    ):
        """Initialize speed specifying both distance and time units.

        Defaults to DEFAULT_SPEED_DISTANCE_UNITS and DEFAULT_SPEED_TIME_UNITS if units not
        specified.
        """
        super().__init__(speed * DISTANCE_FACTORS[distance_units] / DURATION_FACTORS[time_units])

    def get(
        self,
        distance_units: str = DEFAULT_DISTANCE_UNITS,
        time_units: str = DEFAULT_DURATION_UNITS,
    ) -> float:
        """Get speed specifying both distance and time units.

        Defaults to DEFAULT_SPEED_DISTANCE_UNITS and DEFAULT_SPEED_TIME_UNITS if units not
        specified.
        """
        return self.value * DURATION_FACTORS[time_units] / DISTANCE_FACTORS[distance_units]

    def mul_by_duration(self, duration: "Duration") -> Distance:
        """Multiply speed by duration to get distance.

        Args:
            duration ("Duration"): duration

        Returns:
            Distance: distance
        """
        return Distance(self.get(DEFAULT_DISTANCE_UNITS, "s") * duration.get("s"))


class Volume(Units):  # pylint: disable=too-few-public-methods
    """Volume class for easy unit conversion. Volume stored internally as litres."""

    def __init__(self, volume: float, units: str = DEFAULT_VOLUME_UNITS):
        """Initialize distance specifying units.

        Defaults to DEFAULT_VOLUME_UNITS if units not specified.
        """
        super().__init__(volume * VOLUME_FACTORS[units])

    def get(self, units: str = DEFAULT_VOLUME_UNITS) -> float:
        """Get distance specifying units.

        Defaults to DEFAULT_VOLUME_UNITS if units not specified.
        """
        return self.value / VOLUME_FACTORS[units]
