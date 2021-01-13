"""Various unit classes useful to the bushfire_drone_simulation."""

DEFAULT_DISTANCE_UNITS = "km"
DISTANCE_FACTORS = {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000}

DEFAULT_DURATION_UNITS = "s"
DURATION_FACTORS = {"ms": 0.001, "s": 1.0, "min": 60, "hr": 3600, "day": 86400, "year": 31536000}

DEFAULT_SPEED_DISTANCE_UNITS = "km"
DEFAULT_SPEED_TIME_UNITS = "hr"

DEFAULT_VOLUME_UNITS = "L"
VOLUME_FACTORS = {"mL": 0.001, "L": 1.0, "kL": 1000, "ML": 1000000}


class Units:
    """Units class for easy unit conversion."""

    def __init__(self, value: float):
        """hold."""
        self.value = value

    def __lt__(self, other):
        """Less than operator of Distance."""
        assert isinstance(self, type(other)), "Units in inequaility are not the same"
        return self.value < other.value

    def __sub__(self, other):
        """Subtraction operator for Distance."""
        assert isinstance(self, type(other)), "Units in subtraction are not the same"
        return type(self)(self.value - other.value)

    def __mul__(self, other: float):
        """Scalar multiplication operator for Distance."""
        return type(self)(self.value * other)

    def __add__(self, other):
        """Addition operator of Duration."""
        assert isinstance(self, type(other)), "Units in addition are not the same"
        return type(self)(self.value + other.value)

    def __ge__(self, other):
        """Greater than or equal to operator for Volume."""
        assert isinstance(self, type(other)), "Units in inequaility are not the same"
        return self.value >= other.value

    def __truediv__(self, other):
        """Division operator for Volume."""
        assert isinstance(self, type(other)), "Units in division are not the same"
        return self.value / other.value


class Distance(Units):  # pylint: disable=too-few-public-methods
    """Distance class for easy unit conversion. Distance stored internally as metres."""

    def __init__(self, distance: float, units: str = DEFAULT_DISTANCE_UNITS):
        """Initialise distance specifying units.

        Defaults to DEFAULT_DISTANCE_UNITS if units not specified.
        """
        super().__init__(distance * DISTANCE_FACTORS[units])

    def get(self, units: str = DEFAULT_DISTANCE_UNITS):
        """Get distance specifying units.

        Defaults to DEFAULT_DISTANCE_UNITS if units not specified.
        """
        return self.value / DISTANCE_FACTORS[units]


class Duration(Units):  # pylint: disable=too-few-public-methods
    """Duration class for easy unit conversion. Duration stored internally as seconds."""

    def __init__(self, duration: float, units: str = DEFAULT_DURATION_UNITS):
        """Initialise duration specifying units.

        Defaults to DEFAULT_DURATION_UNITS if units not specified.
        """
        super().__init__(duration * DURATION_FACTORS[units])

    def get(self, units: str = DEFAULT_DURATION_UNITS):
        """Get duration specifying units.

        Defaults to DEFAULT_DURATION_UNITS if units not specified.
        """
        return self.value / DURATION_FACTORS[units]


class Speed(Units):  # pylint: disable=too-few-public-methods
    """Speed class for easy unit conversion. Speed stored internally as metres/second."""

    def __init__(
        self,
        speed: float,
        distance_units: str = DEFAULT_SPEED_DISTANCE_UNITS,
        time_units: str = DEFAULT_SPEED_TIME_UNITS,
    ):
        """Initialise speed specifying both distance and time units.

        Defaults to DEFAULT_SPEED_DISTANCE_UNITS and DEFAULT_SPEED_TIME_UNITS if units not
        specified.
        """
        super().__init__(speed * DISTANCE_FACTORS[distance_units] / DURATION_FACTORS[time_units])

    def get(
        self,
        distance_units: str = DEFAULT_SPEED_DISTANCE_UNITS,
        time_units: str = DEFAULT_SPEED_TIME_UNITS,
    ):
        """Get speed specifying both distance and time units.

        Defaults to DEFAULT_SPEED_DISTANCE_UNITS and DEFAULT_SPEED_TIME_UNITS if units not
        specified.
        """
        return self.value * DURATION_FACTORS[time_units] / DISTANCE_FACTORS[distance_units]


class Volume(Units):  # pylint: disable=too-few-public-methods
    """Volume class for easy unit conversion. Volume stored internally as litres."""

    def __init__(self, volume: float, units: str = DEFAULT_VOLUME_UNITS):
        """Initialise distance specifying units.

        Defaults to DEFAULT_VOLUME_UNITS if units not specified.
        """
        super().__init__(volume * VOLUME_FACTORS[units])

    def get(self, units: str = DEFAULT_VOLUME_UNITS):
        """Get distance specifying units.

        Defaults to DEFAULT_VOLUME_UNITS if units not specified.
        """
        return self.value / VOLUME_FACTORS[units]
