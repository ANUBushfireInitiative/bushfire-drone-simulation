"""Aircraft module for various aircraft classes."""

from enum import Enum

from bushfire_drone_simulation.fire_utils import Location
from bushfire_drone_simulation.units import Distance, Duration, Speed, Volume


class UAVStatus(Enum):
    """Enum for UAV status."""

    WAITING = 0
    TRAVEL_TO_STRIKE = 1
    GOING_TO_BASE = 2
    WAITING_AT_BASE = 3


class Aircraft:  # pylint: disable=too-few-public-methods
    """Generic aircraft class for flying vehicles."""

    current_fuel_capacity: float = 1.0

    def __init__(self, position: Location, max_velocity: Speed, fuel_refill_time: Duration):
        """Initialize aircraft."""
        self.position = position
        self.max_velocity = max_velocity
        self.fuel_refill_time = fuel_refill_time


class UAV(Aircraft):  # pylint: disable=too-few-public-methods
    """UAV class for unmanned aircraft searching lightning strikes."""

    status = UAVStatus.WAITING

    def __init__(
        self,
        position: Location,
        max_velocity: Speed,
        fuel_refill_time: Duration,
        uav_range: Distance,
    ):
        """Initialize UAV."""
        super().__init__(position, max_velocity, fuel_refill_time)
        self.uav_range = uav_range


class WaterBomber(Aircraft):  # pylint: disable=too-few-public-methods
    """Class for aircraft that contain water for dropping on potential fires."""

    water_on_board: Volume

    def __init__(  # pylint: disable=too-many-arguments
        self,
        position: Location,
        max_velocity: Speed,
        range_under_load: Distance,
        range_empty: Distance,
        water_refill_time: Duration,
        fuel_refill_time: Duration,
        bombing_time: Duration,
        water_capacity: Volume,
        water_per_delivery: Volume,
    ):
        """Initialize water bombing aircraft."""
        super().__init__(position, max_velocity, fuel_refill_time)
        self.range_under_load = range_under_load
        self.range_empty = range_empty
        self.water_refill_time = water_refill_time
        self.bombing_time = bombing_time
        self.water_per_delivery = water_per_delivery
        self.water_capacity = water_capacity
        self.water_on_board = water_capacity
