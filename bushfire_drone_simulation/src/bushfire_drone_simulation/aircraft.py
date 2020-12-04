"""Aircraft module for various aircraft classes."""

# import logging
from enum import Enum

from bushfire_drone_simulation.fire_utils import Location, Time, minimum_distance
from bushfire_drone_simulation.units import Distance, Duration, Speed, Volume

# _LOG = logging.getLogger(__name__)


class UAVStatus(Enum):
    """Enum for UAV status."""

    WAITING = 0
    TRAVEL_TO_STRIKE = 1
    GOING_TO_BASE = 2
    WAITING_AT_BASE = 3


class Aircraft:  # pylint: disable=too-few-public-methods
    """Generic aircraft class for flying vehicles."""

    current_fuel_capacity: float = 1.0

    def __init__(
        self, position: Location, max_velocity: Speed, fuel_refill_time: Duration, id_no: int
    ):
        """Initialize aircraft."""
        self.position = position
        self.max_velocity = max_velocity
        self.fuel_refill_time = fuel_refill_time
        self.time = Time("0000/00/00/00/00/00")
        self.id_no = id_no

    def fuel_refill(self):
        """Update time and range of aircraft after fuel refill."""
        self.current_fuel_capacity = 1.0
        self.time.add_duration(self.fuel_refill_time)


class UAV(Aircraft):  # pylint: disable=too-few-public-methods
    """UAV class for unmanned aircraft searching lightning strikes."""

    status = UAVStatus.WAITING_AT_BASE

    def __init__(
        self,
        id_no: int,
        position: Location,
        max_velocity: Speed,
        fuel_refill_time: Duration,
        uav_range: Distance,
    ):  # pylint: disable=too-many-arguments
        """Initialize UAV."""
        super().__init__(position, max_velocity, fuel_refill_time, id_no)
        self.uav_range = uav_range

    # Could be generic
    def update_position(self, position: Location, departure_time: Time, status: UAVStatus):
        """Update position, range and time of UAV."""
        if self.status == UAVStatus.WAITING and self.time < departure_time:
            self.current_fuel_capacity -= self.uav_range.get("km") / (
                (self.time - departure_time).get("hr") * self.max_velocity.get("km", "hr")
            )
        self.current_fuel_capacity -= self.position.distance(position).get() / self.uav_range.get()
        self.time.add_duration(
            Duration(
                self.position.distance(position, "km").get("km")
                / self.max_velocity.get("km", "hr"),
                "hr",
            )
            # FIXME(units not right, swap km for lat) # pylint: disable=fixme
        )
        if self.current_fuel_capacity < 0:
            # _LOG.error("UAV ran out of fuel")
            print("UAV ran out of fuel")
        self.status = status
        self.position = position

    # Could be generic
    def enough_fuel(self, positions, departure_time: Time):
        """Return whether a UAV has enough fuel to traverse a given array of positions."""
        current_fuel = self.current_fuel_capacity
        if self.status == UAVStatus.WAITING and self.time < departure_time:
            # Update fuel loss from hovering
            current_fuel -= (
                (self.time - departure_time).get("hr")
                * self.max_velocity.get("km", "hr")
                / self.uav_range.get("km")
            )
        for index, position in enumerate(positions):
            if index == 0:
                current_fuel -= self.position.distance(position).get() / self.uav_range.get()
            else:
                current_fuel -= positions[index - 1].distance(position).get() / self.uav_range.get()
            if current_fuel < 0:
                return False
        return True

    # Could be generic
    def arrival_time(self, positions, time_of_event: Time):
        """Return arrival time of UAV to a given position."""
        current_time = Time("0000/00/00/00/00/00")
        if self.time < time_of_event:
            current_time = time_of_event
            print(time_of_event.time.get())
            current_time.add_duration(Duration(1))
            print("adding duration")
            print(time_of_event.time.get())
        current_time = max(self.time, time_of_event)
        for index, position in enumerate(positions):
            if index == 0:
                current_time.add_duration(
                    Duration(
                        self.position.distance(position, "km").get("km")
                        / self.max_velocity.get("km", "hr"),
                        "hr",
                    )
                    # FIXME(units not right, swap km for lat) # pylint: disable=fixme
                )
            else:
                current_time.add_duration(
                    Duration(
                        self.position[index - 1].distance(position, "km").get("km")
                        / self.max_velocity.get("km", "hr"),
                        "hr",
                    )
                    # FIXME(units not right, swap km for lat) # pylint: disable=fixme
                )
        return current_time

    def consider_going_to_base(self, bases, departure_time: Time, fraction: int = 3):
        """UAV will return to base.

        if it takes more than 1/3 of its fuel tank to return to the nearest base
        """
        if self.status == UAVStatus.WAITING:
            index, value = minimum_distance(bases, self)
            self.update_position(self.position, departure_time, UAVStatus.WAITING)
            if value.get() * fraction > self.current_fuel_capacity * self.uav_range.get():
                self.update_position(bases[index], departure_time, UAVStatus.WAITING_AT_BASE)
                self.fuel_refill()

    def complete_update(self):
        """For future devlopments."""


class WaterBomber(Aircraft):  # pylint: disable=too-few-public-methods
    """Class for aircraft that contain water for dropping on potential fires."""

    water_on_board: Volume

    def __init__(  # pylint: disable=too-many-arguments
        self,
        id_no: int,
        position: Location,
        max_velocity: Speed,
        range_under_load: Distance,
        range_empty: Distance,
        water_refill_time: Duration,
        fuel_refill_time: Duration,
        bombing_time: Duration,
        water_capacity: Volume,
        water_per_delivery: Volume,
    ):  # pylint: disable=too-many-arguments
        """Initialize water bombing aircraft."""
        super().__init__(position, max_velocity, fuel_refill_time, id_no)
        self.range_under_load = range_under_load
        self.range_empty = range_empty
        self.water_refill_time = water_refill_time
        self.bombing_time = bombing_time
        self.water_per_delivery = water_per_delivery
        self.water_capacity = water_capacity
        self.water_on_board = water_capacity

    def water_refill(self):
        """Update time and range of water bomber after water refill."""
        self.water_on_board = self.water_capacity
        self.time.add_duration(self.water_refill_time)

    def enough_water(self, no_of_fires: int = 1):
        """Return whether the water bomber has enough water to extinguish desired fires."""
        return self.water_on_board >= self.water_per_delivery * no_of_fires
