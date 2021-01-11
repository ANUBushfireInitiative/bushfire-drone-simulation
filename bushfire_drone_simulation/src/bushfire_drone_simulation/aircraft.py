"""Aircraft module for various aircraft classes."""

import logging
from abc import abstractmethod
from enum import Enum

from bushfire_drone_simulation.fire_utils import Base, Location, Time, WaterTank, minimum
from bushfire_drone_simulation.units import Distance, Duration, Speed, Volume

_LOG = logging.getLogger(__name__)


class Status(Enum):
    """Enum for Aircraft status."""

    HOVERING = 0
    GOING_TO_STRIKE = 1
    WAITING_AT_BASE = 2
    GOING_TO_BASE = 3
    WAITING_AT_WATER = 4
    GOING_TO_WATER = 5


class Updates(Location):  # pylint: disable=too-few-public-methods
    """Class keeping track of all updates to an Aircrafts position."""

    def __init__(self, latitude: float, longitude: float, time: Time, status: Status):
        """Initialize Updates class."""
        self.time = time
        self.status = status
        super().__init__(latitude, longitude)

    @classmethod
    def from_pos(cls, position: Location, time: Time, status: Status):
        """Initialize Updates class with position."""
        cls.latitude = position.lat
        cls.longitude = position.lon
        cls.time = time
        cls.status = status


class Aircraft(Location):
    """Generic aircraft class for flying vehicles."""

    current_fuel_capacity: float = 1.0
    status = Status.WAITING_AT_BASE

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
        self.time = Time("0000/00/00/00/00/00")
        self.id_no = id_no
        super().__init__(latitude, longitude)
        self.past_locations = [Updates(latitude, longitude, self.time, self.status)]

    def fuel_refill(self):
        """Update time and range of aircraft after fuel refill."""
        self.current_fuel_capacity = 1.0
        self.time.add_duration(self.fuel_refill_time)

    def update_location(self, position):
        """Hopefully not necessary."""
        self.lat = position.lat
        self.lon = position.lon

    @abstractmethod
    def get_range(self):
        """Return total range of Aircraft."""

    def get_water_refil_time(self):  # pylint: disable=no-self-use
        """Return water refil time of Aircraft."""
        return 0

    def update_position(self, position: Location, departure_time: Time, final_status: Status):
        """Update position, range and time of Water bomber."""
        if self.status == Status.HOVERING and self.time < departure_time:
            self.current_fuel_capacity -= (
                (self.time - departure_time).get("hr")
                * self.max_velocity.get("km", "hr")
                / self.get_range().get("km")
            )
        self.current_fuel_capacity -= super().distance(position).get() / self.get_range().get()
        if self.time < departure_time:
            self.time = departure_time.copy_time()
        if final_status == Status.WAITING_AT_BASE:
            self.past_locations.append(
                Updates(position.lat, position.lon, self.time.copy_time(), Status.GOING_TO_BASE)
            )
        elif final_status == Status.HOVERING:
            self.past_locations.append(
                Updates(position.lat, position.lon, self.time.copy_time(), Status.GOING_TO_STRIKE)
            )
        else:
            self.past_locations.append(
                Updates(position.lat, position.lon, self.time.copy_time(), Status.GOING_TO_WATER)
            )
        self.time.add_duration(
            Duration(super().distance(position).get("km") / self.max_velocity.get("km", "hr"), "hr")
        )
        if self.current_fuel_capacity < 0:
            _LOG.error("Aircraft ran out of fuel")
        self.status = final_status
        self.update_location(position)
        self.past_locations.append(
            Updates(position.lat, position.lon, self.time.copy_time(), self.status)
        )

    def consider_going_to_base(self, bases, departure_time: Time, fraction: int = 3):
        """Aircraft will return to base.

        if it takes more than 1/fraction of its fuel tank to return to the nearest base
        """
        if self.status == Status.HOVERING:
            index, value = minimum(bases, Distance(1000000), super().distance)
            if value.get() * fraction > self.current_fuel_capacity * self.get_range().get():
                self.update_position(bases[index], departure_time, Status.WAITING_AT_BASE)
                self.fuel_refill()

    def arrival_time(self, positions, time_of_event: Time):
        """Return arrival time of Aircraft to a given array of positions."""
        current_time = max(self.time, time_of_event).copy_time()
        for index, position in enumerate(positions):
            if index == 0:
                current_time.add_duration(
                    Duration(
                        super().distance(position, "km").get("km")
                        / self.max_velocity.get("km", "hr"),
                        "hr",
                    )
                    # FIXME(units not right, swap km for lat) # pylint: disable=fixme
                )
            else:
                current_time.add_duration(
                    Duration(
                        positions[index - 1].distance(position, "km").get("km")
                        / self.max_velocity.get("km", "hr"),
                        "hr",
                    )
                    # FIXME(units not right, swap km for lat) # pylint: disable=fixme
                )
            if isinstance(position, WaterTank):
                current_time.add_duration(self.get_water_refil_time())
            if isinstance(position, Base):
                current_time.add_duration(self.fuel_refill_time)
        return current_time

    def enough_fuel(self, positions, departure_time: Time):
        """Return whether an Aircraft has enough fuel to traverse a given array of positions."""
        current_fuel = self.current_fuel_capacity
        if self.status == Status.HOVERING and self.time < departure_time:
            # Update fuel loss from hovering
            current_fuel -= (
                (self.time - departure_time).get("hr")
                * self.max_velocity.get("km", "hr")
                / self.get_range().get("km")
            )
        for index, position in enumerate(positions):
            if index == 0:
                current_fuel -= super().distance(position).get() / self.get_range().get()
            else:
                current_fuel -= (
                    positions[index - 1].distance(position).get() / self.get_range().get()
                )
            if isinstance(position, Base):
                current_fuel = 1.0
            if current_fuel < 0:
                return False
        return True

    def go_to_base(self, base, time):
        """Go to and refill Aircraft at base."""
        self.update_position(base, time, Status.WAITING_AT_BASE)
        self.fuel_refill()

    def print_past_locations(self):
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


class UAV(Aircraft):  # pylint: disable=too-few-public-methods
    """UAV class for unmanned aircraft searching lightning strikes."""

    def __init__(
        self,
        id_no: int,
        latitude: float,
        longitude: float,
        max_velocity: Speed,
        fuel_refill_time: Duration,
        total_range: Distance,
    ):  # pylint: disable=too-many-arguments
        """Initialize UAV."""
        super().__init__(latitude, longitude, max_velocity, fuel_refill_time, id_no)
        self.total_range = total_range

    def go_to_strike(self, lightning, departure_time, arrival_time):
        """UAV go to and inspect strike."""
        self.update_position(lightning, departure_time, Status.HOVERING)
        lightning.inspected(self, arrival_time)  # change location of this in future

    def complete_update(self):
        """For future devlopments."""

    def get_range(self):
        """Return total range of UAV."""
        return self.total_range


class WaterBomber(Aircraft):
    """Class for aircraft that contain water for dropping on potential fires."""

    water_on_board: Volume

    def __init__(
        self,
        id_no: int,
        latitude: float,
        longitude: float,
        max_velocity: Speed,
        range_under_load: Distance,
        range_empty: Distance,
        water_refill_time: Duration,
        fuel_refill_time: Duration,
        bombing_time: Duration,
        water_capacity: Volume,
        water_per_delivery: Volume,
        bomber_type: str,
        bomber_name: str,
    ):  # pylint: disable=too-many-arguments
        """Initialize water bombing aircraft."""
        super().__init__(latitude, longitude, max_velocity, fuel_refill_time, id_no)
        self.range_empty = range_empty
        self.range_under_load = range_under_load
        self.water_refill_time = water_refill_time
        self.bombing_time = bombing_time
        self.water_per_delivery = water_per_delivery
        self.water_capacity = water_capacity
        self.water_on_board = water_capacity
        self.type = bomber_type
        self.name = bomber_name
        self.ignitions_suppressed = []

    def get_range(self):
        """Return range of Water bomber."""
        # TODO(Override other method) #pylint: disable=fixme
        return self.range_empty

    def go_to_strike(self, ignition, departure_time, arrival_time):
        """UAV go to and inspect strike."""
        self.update_position(ignition, departure_time, Status.HOVERING)
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
        water_tank.empty(self.water_capacity - self.water_on_board)
        if water_tank.capacity.get() < 0:
            _LOG.error("Water tank ran out of water")
        self.water_on_board = self.water_capacity
        self.time.add_duration(self.water_refill_time)

    def enough_water(self, no_of_fires: int = 1):
        """Return whether the water bomber has enough water to extinguish desired fires."""
        return self.water_on_board.get() >= self.water_per_delivery.get() * no_of_fires

    def get_water_refil_time(self):
        """Return water refil time of Aircraft. Should be 0 if does not exist."""
        return self.water_refill_time
