"""Aircraft module for various aircraft classes."""

import logging
from abc import abstractmethod
from enum import Enum
from typing import Any, List, Optional

import numpy as np

from bushfire_drone_simulation.fire_utils import Base, Location, Time, WaterTank
from bushfire_drone_simulation.units import Distance, Duration, Speed, Volume

# if TYPE_CHECKING:
#     from bushfire_drone_simulation.lightning import Lightning

_LOG = logging.getLogger(__name__)


class Status(Enum):
    """Enum for Aircraft status."""

    HOVERING = 0
    GOING_TO_STRIKE = 1
    WAITING_AT_BASE = 2
    GOING_TO_BASE = 3
    WAITING_AT_WATER = 4
    GOING_TO_WATER = 5


class UpdateEvent(Location):  # pylint: disable=too-few-public-methods
    """Class keeping track of all updates to an Aircrafts position."""

    def __init__(
        self,
        name: str,
        latitude: float,
        longitude: float,
        time: Time,
        status: Status,
        distance_travelled: Distance,
        current_fuel: float,
        current_range: Distance,
        distance_hovered: Distance,
        current_water: Optional[Volume] = None,
    ):  # pylint: disable=too-many-arguments
        """Initialize UpdateEvent class."""
        self.name = name
        self.distance_travelled = distance_travelled  # since previous update
        self.fuel = current_fuel
        self.current_range = current_range
        self.distance_hovered = distance_hovered
        self.water = current_water
        self.time = time
        self.status = status
        super().__init__(latitude, longitude)

    def __lt__(self, other: "UpdateEvent") -> bool:
        """Less than operator for Updates."""
        return self.time < other.time


class Aircraft(Location):
    """Generic aircraft class for flying vehicles."""

    def __init__(
        self,
        latitude: float,
        longitude: float,
        max_velocity: Speed,
        fuel_refill_time: Duration,
        id_no: int,
    ):  # pylint: disable=too-many-arguments
        """Initialize aircraft."""
        self.max_velocity = max_velocity
        self.fuel_refill_time = fuel_refill_time
        self.time = Time("0")
        self.id_no = id_no
        super().__init__(latitude, longitude)
        self.current_fuel_capacity: float = 1.0
        self.status = Status.WAITING_AT_BASE
        self.past_locations: List[UpdateEvent] = []

    def fuel_refill(self, base: Base) -> None:  # pylint: disable=unused-argument
        """Update time and range of aircraft after fuel refill."""
        # base.empty()
        self.current_fuel_capacity = 1.0
        self.time.add_duration(self.fuel_refill_time)

    def update_location(self, position: Location) -> None:
        """Hopefully not necessary."""
        self.lat = position.lat
        self.lon = position.lon

    @abstractmethod
    def get_range(self) -> Distance:
        """Return total range of Aircraft."""

    def get_water_refill_time(self) -> Duration:
        """Return water refil time of Aircraft."""
        assert isinstance(self, WaterBomber), "A UAV is trying to visit a water tank"
        return Duration(0)

    def update_position(
        self, position: Location, departure_time: Time, final_status: Status
    ) -> None:
        """Update position, range and time of Water bomber."""
        if self.time < departure_time:
            self.time = departure_time.copy_time()
        if final_status == Status.WAITING_AT_BASE:
            self.add_update(Status.GOING_TO_BASE)
        elif final_status == Status.HOVERING:
            self.add_update(Status.GOING_TO_STRIKE)
        else:
            self.add_update(Status.GOING_TO_WATER)

        if self.status == Status.HOVERING and self.time < departure_time:
            self.current_fuel_capacity -= (self.time - departure_time).mul_by_speed(
                self.max_velocity
            ) / self.get_range()
        self.current_fuel_capacity -= self.distance(position) / self.get_range()

        self.time.add_duration(self.distance(position).div_by_speed(self.max_velocity))
        if self.current_fuel_capacity < 0:
            _LOG.error("Aircraft %s ran out of fuel", self.id_no)
        self.status = final_status
        self.update_location(position)
        self.add_update(self.status)

    def consider_going_to_base(
        self, bases: List[Base], departure_time: Time, fraction: float = 3
    ) -> None:
        """Aircraft will return to base.

        if it takes more than 1/fraction of its fuel tank to return to the nearest base
        """
        if self.status == Status.HOVERING:
            index = np.argmin(map(self.distance, bases))
            if (
                self.distance(bases[index]) * fraction
                > self.get_range() * self.current_fuel_capacity
            ):
                self.update_position(bases[index], departure_time, Status.WAITING_AT_BASE)
                self.fuel_refill(bases[index])

    def arrival_time(self, positions: List[Location], time_of_event: Time):
        """Return arrival time of Aircraft to a given array of positions."""
        current_time = max(self.time, time_of_event).copy_time()
        for index, position in enumerate(positions):
            if index == 0:
                current_time.add_duration(self.distance(position).div_by_speed(self.max_velocity))
            else:
                current_time.add_duration(
                    positions[index - 1].distance(position).div_by_speed(self.max_velocity)
                )
            if isinstance(position, WaterTank):
                current_time.add_duration(self.get_water_refill_time())
            elif isinstance(position, Base):
                current_time.add_duration(self.fuel_refill_time)
        return current_time

    def enough_fuel(self, positions: List[Location], departure_time: Time):
        """Return whether an Aircraft has enough fuel to traverse a given array of positions."""
        current_fuel = self.current_fuel_capacity
        if self.status == Status.HOVERING and self.time < departure_time:
            # Update fuel loss from hovering
            current_fuel -= (self.time - departure_time).mul_by_speed(
                self.max_velocity
            ) / self.get_range()
        for index, position in enumerate(positions):
            if index == 0:
                current_fuel -= self.distance(position) / self.get_range()
            else:
                current_fuel -= positions[index - 1].distance(position) / self.get_range()
            if current_fuel < 0:
                return False
            if isinstance(position, Base):
                current_fuel = 1.0
        return True

    def go_to_base(self, base: Base, time: Time) -> None:
        """Go to and refill Aircraft at base."""
        self.update_position(base, time, Status.WAITING_AT_BASE)
        self.fuel_refill(base)

    def print_past_locations(self) -> None:
        """Print the past locations of the aircraft."""
        _LOG.debug("Locations of aircraft %s:", self.id_no)
        for update in self.past_locations:
            _LOG.debug(
                "position: %s, %s, time: %s, status: %s",
                update.lat,
                update.lon,
                update.time.get(),
                update.status,
            )

    @abstractmethod
    def add_update(self, new_status: Status) -> None:
        """Add update to past locations."""


class UAV(Aircraft):
    """UAV class for unmanned aircraft searching lightning strikes."""

    def __init__(self, id_no: int, latitude: float, longitude: float, attributes):
        """Initialize UAV."""
        super().__init__(
            latitude,
            longitude,
            Speed(int(attributes["flight_speed"]), "km", "hr"),
            Duration(int(attributes["fuel_refill_time"]), "min"),
            id_no,
        )
        self.total_range = Distance(int(attributes["range"]), "km")
        self.past_locations = [
            UpdateEvent(
                "uav " + str(self.id_no),
                self.lat,
                self.lon,
                self.time.copy_time(),
                self.status,
                Distance(0),
                self.current_fuel_capacity,
                self.get_range(),
                Distance(0),
            )
        ]

    def go_to_strike(self, lightning, departure_time, arrival_time):
        """UAV go to and inspect strike."""
        self.update_position(lightning, departure_time, Status.HOVERING)
        lightning.inspected(self, arrival_time)  # change location of this in future

    def complete_update(self):
        """For future developments."""

    def get_range(self):
        """Return total range of UAV."""
        return self.total_range

    def add_update(self, new_status: Status):
        """Add update to UAV past locations."""
        previous_update = self.past_locations[-1]
        distance_hovered = Distance(0)
        if previous_update.status == Status.HOVERING:
            distance_hovered = (previous_update.time - self.time).mul_by_speed(self.max_velocity)
        self.past_locations.append(
            UpdateEvent(
                "uav " + str(self.id_no),
                self.lat,
                self.lon,
                self.time.copy_time(),
                new_status,
                self.distance(previous_update),
                self.current_fuel_capacity,
                self.get_range() * self.current_fuel_capacity,
                distance_hovered,
            )
        )


class WaterBomber(Aircraft):
    """Class for aircraft that contain water for dropping on potential fires."""

    water_on_board: Volume

    def __init__(
        self,
        id_no: int,
        latitude: float,
        longitude: float,
        attributes,
        bomber_type: str,
    ):  # pylint: disable=too-many-arguments
        """Initialize water bombing aircraft."""
        super().__init__(
            latitude,
            longitude,
            Speed(int(attributes["flight_speed"]), "km", "hr"),
            Duration(int(attributes["fuel_refill_time"]), "min"),
            id_no,
        )
        self.range_empty = Distance(int(attributes["range_empty"]), "km")
        self.range_under_load = Distance(int(attributes["range_under_load"]), "km")
        self.water_refill_time = Duration(int(attributes["water_refill_time"]), "min")
        self.bombing_time = Duration(int(attributes["bombing_time"]), "min")
        self.water_per_delivery = Volume(int(attributes["water_per_delivery"]), "L")
        self.water_capacity = Volume(int(attributes["water_capacity"]), "L")
        self.water_on_board = Volume(int(attributes["water_capacity"]), "L")
        self.type = bomber_type
        self.name = f"{bomber_type} {id_no+1}"
        self.ignitions_suppressed: List[Any] = []  # TODO(fix types) #pylint: disable=fixme
        self.past_locations = [
            UpdateEvent(
                self.name,
                self.lat,
                self.lon,
                self.time.copy_time(),
                self.status,
                Distance(0),
                self.current_fuel_capacity,
                self.get_range(),
                Distance(0),
                self.water_on_board,
            )
        ]

    def get_range(self):
        """Return range of Water bomber."""
        return (self.range_under_load - self.range_empty) * (
            self.water_on_board / self.water_capacity
        ) + self.range_empty

    def go_to_strike(self, ignition, departure_time, arrival_time):
        """UAV go to and inspect strike."""
        self.update_position(ignition, departure_time, Status.HOVERING)
        self.water_on_board -= self.water_per_delivery
        ignition.suppressed(self, arrival_time)  # change location of this in future
        self.ignitions_suppressed.append((ignition, arrival_time))

    def num_ignitions_suppressed(self):
        """Return number of ignitions this water bomber has suppressed."""
        return len(self.ignitions_suppressed)

    def go_to_water(self, water_tank, departure_time):
        """UAV go to and inspect strike."""
        self.update_position(water_tank, departure_time, Status.WAITING_AT_WATER)
        self.water_refill(water_tank)

    def check_water_tank(self, water_tank: WaterTank):
        """Return whether a given water tank has enough capacity to refill the water bomber."""
        # Returns false if water tank has enough to extinguish a single fire
        # but not completely refill
        return water_tank.capacity >= self.water_capacity - self.water_on_board

    def water_refill(self, water_tank: WaterTank):
        """Update time and range of water bomber after water refill."""
        water_tank.remove_water(self.water_capacity - self.water_on_board)
        if water_tank.capacity < Volume(0):
            _LOG.error("Water tank ran out of water")
        self.water_on_board = self.water_capacity
        self.time.add_duration(self.water_refill_time)

    def enough_water(self, no_of_fires: int = 1):
        """Return whether the water bomber has enough water to extinguish desired fires."""
        return self.water_on_board >= self.water_per_delivery * no_of_fires

    def get_water_refill_time(self):
        """Return water refill time of Aircraft. Should be 0 if does not exist."""
        return self.water_refill_time

    def add_update(self, new_status: Status):
        """Add update to Water Bomber past locations."""
        previous_update = self.past_locations[-1]
        distance_hovered = Distance(0)
        if previous_update.status == Status.HOVERING:
            distance_hovered = (previous_update.time - self.time).mul_by_speed(self.max_velocity)
        self.past_locations.append(
            UpdateEvent(
                self.name,
                self.lat,
                self.lon,
                self.time.copy_time(),
                new_status,
                self.distance(previous_update),
                self.current_fuel_capacity,
                self.get_range() * self.current_fuel_capacity,
                distance_hovered,
                self.water_on_board,
            )
        )
