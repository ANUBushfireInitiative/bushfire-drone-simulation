"""Aircraft module for various aircraft classes."""

import logging
from abc import abstractmethod
from copy import deepcopy
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from bushfire_drone_simulation.fire_utils import Base, Location, Time, WaterTank
from bushfire_drone_simulation.lightning import Lightning
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
        """Initialize UpdateEvent class.

        Args:
            name (str): name of aircraft
            latitude (float): latitude of aircraft
            longitude (float): logitude of aircraft
            time (Time): time of event
            status (Status): status of aircraft
            distance_travelled (Distance): distance travelled by aircraft since last event update
            current_fuel (float): percentage of current fuel remaining
            current_range (Distance): current range of aircraft
            distance_hovered (Distance): distance hovered by aircraft since last event update
            current_water (Optional[Volume], optional): Current water on board aircraft.
        """
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
        flight_speed: Speed,
        fuel_refill_time: Duration,
        id_no: int,
    ):  # pylint: disable=too-many-arguments
        """Initialize aircraft."""
        self.flight_speed = flight_speed
        self.fuel_refill_time = fuel_refill_time
        self.time = Time("0")
        self.id_no = id_no
        super().__init__(latitude, longitude)
        self.current_fuel_capacity: float = 1.0
        self.status = Status.WAITING_AT_BASE
        self.past_locations: List[UpdateEvent] = []
        self.strikes_visited: List[Tuple[Lightning, Time]] = []

    def fuel_refill(self, base: Base) -> None:  # pylint: disable=unused-argument
        """Update time and range of aircraft after fuel refill.

        Args:
            base (Base): base to be refilled from
        """
        # base.empty()
        self.current_fuel_capacity = 1.0
        self.time.add_duration(self.fuel_refill_time)

    def update_location(self, position: Location) -> None:
        """Update location of aircraft."""
        self.lat = position.lat
        self.lon = position.lon

    def reduce_current_fuel(self, proportion: float) -> None:
        """Reduce current fuel of aircraft by proportion and throw an error if less than 0."""
        self.current_fuel_capacity -= proportion
        if self.current_fuel_capacity < 0:
            _LOG.error("%s ran out of fuel", self.get_name())

    @abstractmethod
    def get_range(self) -> Distance:
        """Return total range of Aircraft."""

    @abstractmethod
    def get_time_at_strike(self) -> Duration:
        """Return duration an aircraft spends inspecting or supressing a strike."""

    @abstractmethod
    def get_name(self) -> str:
        """Return name of aircraft."""

    def get_water_refill_time(self) -> Duration:
        """Return water refil time of Aircraft."""
        assert isinstance(self, WaterBomber), "A UAV is trying to visit a water tank"
        return Duration(0)

    def update_position(
        self, position: Location, departure_time: Time, final_status: Status
    ) -> None:
        """Update position, range and time of Water bomber.

        Args:
            position (Location): new aircraft position
            departure_time (Time): time of triggering event of update position
            final_status (Status): status of aircraft after position update
        """
        if self.status == Status.HOVERING and self.time < departure_time:
            self.reduce_current_fuel(
                (departure_time - self.time).mul_by_speed(self.flight_speed) / self.get_range()
            )

        if self.time < departure_time:
            self.time = departure_time.copy_time()
        if final_status == Status.WAITING_AT_BASE:
            self.add_update(Status.GOING_TO_BASE)
        elif final_status == Status.HOVERING:
            self.add_update(Status.GOING_TO_STRIKE)
        else:
            self.add_update(Status.GOING_TO_WATER)
        self.reduce_current_fuel(self.distance(position) / self.get_range())
        self.time.add_duration(self.distance(position).div_by_speed(self.flight_speed))
        self.status = final_status
        self.update_location(position)
        self.add_update(self.status)

    def consider_going_to_base(
        self, bases: List[Base], departure_time: Time, fraction: float = 3
    ) -> None:
        """Aircraft will return to base.

        if it takes more than 1/fraction of its fuel tank to return to the nearest base

        Args:
            bases (List[Base]): list of avaliable bases
            departure_time (Time): time of triggering event of consider going to base
            fraction (float, optional): fraction of fuel tank. Defaults to 3.
        """
        if self.status == Status.HOVERING:
            index = np.argmin(list(map(self.distance, bases)))
            if (
                self.distance(bases[index]) * fraction
                > self.get_range() * self.current_fuel_capacity
            ):
                self.update_position(bases[index], departure_time, Status.WAITING_AT_BASE)
                self.fuel_refill(bases[index])

    def arrival_time(self, positions: List[Location], time_of_event: Time) -> Time:
        """Return arrival time of Aircraft to a given array of positions.

        Args:
            positions (List[Location]): array of locations for the aircraft to traverse
            time_of_event (Time): Time of departure

        Returns:
            Time: Arrival time of aircraft
        """
        current_time = max(self.time, time_of_event).copy_time()
        for index, position in enumerate(positions):
            if index == 0:
                current_time.add_duration(self.distance(position).div_by_speed(self.flight_speed))
            else:
                current_time.add_duration(
                    positions[index - 1].distance(position).div_by_speed(self.flight_speed)
                )
            if isinstance(position, WaterTank):
                current_time.add_duration(self.get_water_refill_time())
            elif isinstance(position, Base):
                current_time.add_duration(self.fuel_refill_time)
            elif isinstance(position, Lightning):
                current_time.add_duration(self.get_time_at_strike())
        return current_time

    def enough_fuel(self, positions: List[Location], departure_time: Time) -> bool:
        """Return whether an Aircraft has enough fuel to traverse a given array of positions.

        Args:
            positions (List[Location]): array of locations for the aircraft to traverse
            departure_time (Time): Time of departure

        Returns:
            bool: whether the aircraft has enough fuel to traverse positions
        """
        current_fuel = self.current_fuel_capacity
        if self.status == Status.HOVERING and self.time < departure_time:
            current_fuel -= (departure_time - self.time).mul_by_speed(
                self.flight_speed
            ) / self.get_range()
        for index, position in enumerate(positions):
            if index == 0:
                current_fuel -= self.distance(position) / self.get_range()
            else:
                current_fuel -= positions[index - 1].distance(position) / self.get_range()
            if isinstance(position, Lightning):
                current_fuel -= (
                    self.get_time_at_strike().mul_by_speed(self.flight_speed) / self.get_range()
                )
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

    def num_strikes_visited(self) -> int:
        """Return number of ignitions this aircraft has visited."""
        return len(self.strikes_visited)


class UAV(Aircraft):
    """UAV class for unmanned aircraft searching lightning strikes."""

    def __init__(self, id_no: int, latitude: float, longitude: float, attributes: Dict[str, Any]):
        """Initialize UAV.

        Args:
            id_no (int): id number of UAV
            latitude (float): latitude of UAV
            longitude (float): longitude of UAV
            attributes (Dict[Any]): dictionary of attributes of UAV
        """
        super().__init__(
            latitude,
            longitude,
            Speed(int(attributes["flight_speed"]), "km", "hr"),
            Duration(int(attributes["fuel_refill_time"]), "min"),
            id_no,
        )
        self.total_range: Distance = Distance(int(attributes["range"]), "km")
        self.inspection_time: Duration = Duration(
            1, "min"
        )  # TODO(read from csv) pylint: disable=fixme
        self.past_locations = [
            UpdateEvent(
                self.get_name(),
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

    def go_to_strike(self, lightning: Lightning, departure_time: Time) -> None:
        """UAV go to and inspect strike.

        Args:
            lightning (Lightning): strike being inspected
            departure_time (Time): time of UAVs departure
            arrival_time (Time): time of UAVs arrival at strike
        """
        self.update_position(lightning, departure_time, Status.HOVERING)
        self.time.add_duration(self.get_time_at_strike())
        self.reduce_current_fuel(
            (self.get_time_at_strike().mul_by_speed(self.flight_speed) / self.get_range())
        )
        lightning.inspected(deepcopy(self.time))
        self.strikes_visited.append((lightning, deepcopy(self.time)))

    def complete_update(self):
        """For future developments."""

    def get_range(self):
        """Return total range of UAV."""
        return self.total_range

    def get_name(self) -> str:
        """Return name of UAV."""
        return f"uav {self.id_no}"

    def get_time_at_strike(self) -> Duration:
        """Return inspection time of UAV."""
        return self.inspection_time

    def add_update(self, new_status: Status):
        """Add update to UAV past locations."""
        previous_update = self.past_locations[-1]
        distance_hovered = Distance(0)
        if previous_update.status == Status.HOVERING:
            distance_hovered = (self.time - previous_update.time).mul_by_speed(self.flight_speed)
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
        """Initialize water bombing aircraft.

        Args:
            id_no (int): id number of water bomber
            latitude (float): latitude of water bomber
            longitude (float): longitude of water bomber
            attributes ([type]): dictionary of attributes of water bomber
            bomber_type (str): type of water bomber
        """
        super().__init__(
            latitude,
            longitude,
            Speed(int(attributes["flight_speed"]), "km", "hr"),
            Duration(int(attributes["fuel_refill_time"]), "min"),
            id_no,
        )
        self.range_empty: Distance = Distance(int(attributes["range_empty"]), "km")
        self.range_under_load: Distance = Distance(int(attributes["range_under_load"]), "km")
        self.water_refill_time: Duration = Duration(int(attributes["water_refill_time"]), "min")
        self.bombing_time: Duration = Duration(int(attributes["bombing_time"]), "min")
        self.water_per_delivery: Volume = Volume(int(attributes["water_per_delivery"]), "L")
        self.water_capacity: Volume = Volume(int(attributes["water_capacity"]), "L")
        self.water_on_board: Volume = Volume(int(attributes["water_capacity"]), "L")
        self.type: str = bomber_type
        self.name: str = f"{bomber_type} {id_no+1}"
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

    def get_time_at_strike(self) -> Duration:
        """Return bombing time of water bomber."""
        return self.bombing_time

    def get_name(self) -> str:
        """Return name of Water bomber."""
        return str(self.name)

    def go_to_strike(self, ignition: Lightning, departure_time: Time) -> None:
        """Water Bomber go to and supress strike.

        Args:
            ignition (Lightning): strike being supressed
            departure_time (Time): time of water bombers departure
        """
        self.update_position(ignition, departure_time, Status.HOVERING)
        self.water_on_board -= self.water_per_delivery
        self.time.add_duration(self.get_time_at_strike())
        self.current_fuel_capacity -= (
            self.get_time_at_strike().mul_by_speed(self.flight_speed) / self.get_range()
        )
        ignition.suppressed(deepcopy(self.time))
        self.strikes_visited.append((ignition, deepcopy(self.time)))

    def go_to_water(self, water_tank: WaterTank, departure_time: Time) -> None:
        """Water bomber goes and fills up water.

        Args:
            water_tank (WaterTank): water tank
            departure_time (Time): departure time of water bomber
        """
        self.update_position(water_tank, departure_time, Status.WAITING_AT_WATER)
        self.water_refill(water_tank)

    def check_water_tank(self, water_tank: WaterTank) -> bool:
        """Return whether a given water tank has enough capacity to refill the water bomber.

        Args:
            water_tank (WaterTank): water tank

        Returns:
            bool: Returns false if water tank has enough to extinguish a single fire
            but not completely refill
        """
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
            distance_hovered = (self.time - previous_update.time).mul_by_speed(self.flight_speed)
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
