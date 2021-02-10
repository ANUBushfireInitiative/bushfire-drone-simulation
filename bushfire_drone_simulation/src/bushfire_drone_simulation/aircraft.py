"""Aircraft module for various aircraft classes."""

import logging
import math
from abc import abstractmethod
from copy import deepcopy
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from bushfire_drone_simulation.fire_utils import Base, Location, WaterTank
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.linked_list import LinkedList
from bushfire_drone_simulation.precomupted import PreComputedDistances
from bushfire_drone_simulation.units import (
    DEFAULT_DISTANCE_UNITS,
    DEFAULT_DURATION_UNITS,
    DEFAULT_VOLUME_UNITS,
    Distance,
    Duration,
    Speed,
    Volume,
)

_LOG = logging.getLogger(__name__)

EPSILON: float = 0.001


class Status(Enum):
    """Enum for Aircraft status."""

    HOVERING = 0
    GOING_TO_STRIKE = 1
    WAITING_AT_BASE = 2
    GOING_TO_BASE = 3
    WAITING_AT_WATER = 4
    GOING_TO_WATER = 5


class StatusWithId:  # pylint: disable=too-few-public-methods
    """Class for storing status and id number of the location in that status."""

    def __init__(self, status: Status, id_no: Optional[int] = None):
        """Initialize StatusID."""
        self.status = status
        self.id_no = id_no

    def __str__(self):
        """To strike method for StatusId."""
        if self.id_no is None:
            return self.status
        return f"{self.status} {self.id_no}"


class UpdateEvent(Location):  # pylint: disable=too-few-public-methods
    """Class keeping track of all updates to an Aircrafts position."""

    def __init__(
        self,
        name: str,
        latitude: float,
        longitude: float,
        time: float,
        status: Status,
        distance_travelled: float,
        current_fuel: float,
        current_range: float,
        distance_hovered: float,
        current_water: float,
    ):  # pylint: disable=too-many-arguments
        """Initialize UpdateEvent class.

        Args:
            name (str): name of aircraft
            latitude (float): latitude of aircraft
            longitude (float): logitude of aircraft
            time (float): time of event
            status (Status): status of aircraft
            distance_travelled (float): distance travelled by aircraft since last event update
            current_fuel (float): percentage of current fuel remaining
            current_range (float): current range of aircraft
            distance_hovered (float): distance hovered by aircraft since last event update
            current_water (float): Current water on board aircraft.
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
        """Less than operator for UpdateEvent."""
        return self.time < other.time


class Event:  # pylint: disable=too-few-public-methods
    """Class containing events."""

    def __init__(
        self,
        position: Location,
        departure_time: float,
        arrival_time: float,
        arrival_fuel: float,
        completion_fuel: float,
        water: float,
        arrival_status: Status,
        completion_status: Status,
        completion_time: float,
    ):  # pylint: disable = too-many-arguments
        """Initialize event."""
        self.position = position
        self.position_description: str = "base"
        self.departure_time = departure_time
        self.arrival_time = arrival_time
        self.completion_time = completion_time
        self.arrival_fuel = arrival_fuel
        self.completion_fuel = completion_fuel
        self.water = water
        self.arrival_status = arrival_status
        self.completion_status = completion_status

    def __lt__(self, other: "Event") -> bool:
        """Less than operator for Event."""
        return self.departure_time < other.departure_time


class Aircraft(Location):  # pylint: disable=too-many-public-methods
    """Generic aircraft class for flying vehicles."""

    def __init__(
        self,
        latitude: float,
        longitude: float,
        flight_speed: float,
        fuel_refill_time: float,
        id_no: int,
        starting_at_base: bool,
        initial_fuel: float,
    ):  # pylint: disable=too-many-arguments
        """Initialize aircraft."""
        self.flight_speed = flight_speed
        self.fuel_refill_time = fuel_refill_time
        self.time: float = 0.0
        self.id_no: int = id_no
        super().__init__(latitude, longitude)
        self.current_fuel_capacity: float = initial_fuel
        if starting_at_base:
            self.status = Status.WAITING_AT_BASE
        else:
            self.status = Status.HOVERING
        self.past_locations: List[UpdateEvent] = []
        self.strikes_visited: List[Tuple[Lightning, float]] = []
        self.event_queue: LinkedList = LinkedList()
        self.use_current_status: bool = False
        self.closest_base: Optional[Base] = None
        self.required_departure_time: Optional[float] = None
        self.precomputed: Optional[PreComputedDistances] = None

    def accept_precomputed_distances(self, precomputed: PreComputedDistances):
        """Accept precomputed distance class with distances already evaluated."""
        self.precomputed = precomputed

    def fuel_refill(self, base: Base) -> None:  # pylint: disable=unused-argument
        """Update time and range of aircraft after fuel refill.

        Args:
            base (Base): base to be refilled from
        """
        # base.empty()
        self.current_fuel_capacity = 1.0
        self.time += self.fuel_refill_time

    def _update_location(self, position: Location) -> None:
        """Update location of aircraft."""
        self.lat = position.lat
        self.lon = position.lon

    def _reduce_current_fuel(self, proportion: float) -> None:
        """Reduce current fuel of aircraft by proportion and throw an error if less than 0."""
        self.current_fuel_capacity -= proportion
        if self.current_fuel_capacity < 0:
            _LOG.error("%s ran out of fuel", self.get_name())

    @abstractmethod
    def get_range(self) -> float:
        """Return total range of Aircraft."""

    def _get_future_state(self) -> Tuple[float, float, Location]:
        """Return future time, fuel and position of aircraft.

        As if all elements of the event queue have been completed.
        """
        if self.event_queue.empty() or self.use_current_status:
            return self.time, self.current_fuel_capacity, Location(self.lat, self.lon)
        future_event = self.event_queue.peak_first()
        return future_event.completion_time, future_event.completion_fuel, future_event.position

    def _get_future_time(self) -> float:
        """Return time as if all elements of the event queue have been completed."""
        if self.event_queue.empty() or self.use_current_status:
            return self.time
        return self.event_queue.peak_first().completion_time

    def _get_future_position(self) -> Location:
        """Return position as if all elements of the event queue have been completed."""
        if self.event_queue.empty() or self.use_current_status:
            return Location(self.lat, self.lon)
        return self.event_queue.peak_first().position

    def _get_future_fuel(self) -> float:
        """Return fuel capacity as if all elements of the event queue have been completed."""
        if self.event_queue.empty() or self.use_current_status:
            return self.current_fuel_capacity
        return self.event_queue.peak_first().completion_fuel

    def _get_future_water(self) -> float:
        """Return water on board as if all elements of the event queue have been completed."""
        if self.event_queue.empty() or self.use_current_status:
            return self._get_water_on_board()
        return self.event_queue.peak_first().water

    def _get_future_status(self) -> Status:
        """Return water on board as if all elements of the event queue have been completed."""
        if self.event_queue.empty() or self.use_current_status:
            return self.status
        return self.event_queue.peak_first().completion_status

    def _get_water_per_delivery(self) -> float:
        """Return water per delivery time of Aircraft."""
        assert isinstance(
            self, WaterBomber
        ), f"{self.get_name()} is trying to measure water per delivery"
        return 0

    def _get_water_capacity(self) -> float:
        """Return water capcaity of Aircraft."""
        assert isinstance(
            self, WaterBomber
        ), f"{self.get_name()} is trying to measure it's water capacity"
        return 0

    def _get_water_refill_time(self) -> float:
        """Return water refill time of Aircraft."""
        assert isinstance(self, WaterBomber), f"{self.get_name()} is trying to visit a water tank"
        return 0

    # pylint: disable=R0201
    def _get_water_on_board(self) -> float:
        """Return water on board of Aircraft."""
        return 0

    def _set_water_on_board(self, water: float) -> None:  # pylint: disable=unused-argument
        """Set water on board of Aircraft."""
        assert isinstance(self, WaterBomber), f"{self.get_name()} is trying to set water on board"

    def get_type(self) -> str:
        """Return type of Aircraft."""
        assert isinstance(self, WaterBomber), f"{self.get_name()} is trying to access type"
        return ""

    @abstractmethod
    def _get_time_at_strike(self) -> float:
        """Return duration an aircraft spends inspecting or suppressing a strike."""

    @abstractmethod
    def get_name(self) -> str:
        """Return name of aircraft."""

    def _complete_event(self) -> Tuple[Optional[Lightning], Optional[Lightning]]:
        """Completes next event in queue and returns list of strikes inspected and suppressed."""
        assert not self.event_queue.empty(), "Complete event was called on empty queue"
        event = self.event_queue.get_last()
        inspection = None
        suppression = None
        assert isinstance(event, Event), "event_queue contained a non event"
        self.status = event.arrival_status
        self._add_update()
        self.status = event.completion_status
        self.current_fuel_capacity = event.arrival_fuel
        self.time = event.arrival_time
        self._update_location(event.position)
        self._add_update()
        self.current_fuel_capacity = event.completion_fuel
        self.time = event.completion_time
        if isinstance(event.position, WaterTank):
            assert isinstance(self, WaterBomber), f"{self.get_name()} was sent to a water tank"
            event.position.remove_water(self._get_water_capacity() - self._get_water_on_board())
        elif isinstance(event.position, Lightning):
            if isinstance(self, UAV):
                event.position.inspected(self.time)
                self.strikes_visited.append((event.position, self.time))
                inspection = event.position
            else:
                event.position.suppressed(self.time)
                self.strikes_visited.append((event.position, self.time))
                suppression = event.position
        # elif isinstance(event.position, Base):
        # base.empty()
        if isinstance(self, WaterBomber):
            self._set_water_on_board(event.water)
        return inspection, suppression

    def update_to_time(  # pylint: disable=too-many-branches
        self, update_time: float
    ) -> Tuple[List[Lightning], List[Lightning]]:
        """Update aircraft to given time and delete all updates beyond this time.

        Args:
            time (Time): Time to update to

        Returns:
            List[Lightning]: list of strikes inspected
            List[Lightning]]: list of ignitions suppressed
        """
        assert isinstance(update_time, float)
        strikes_inspected: List[Lightning] = []
        strikes_suppressed: List[Lightning] = []
        # If we can get to the next position then complete update, otherwise make it half way there
        while not self.event_queue.empty():
            next_event = self.event_queue.peak()
            if next_event.departure_time > self.time:
                if self.status == Status.HOVERING:
                    self._reduce_current_fuel(
                        (next_event.departure_time - self.time)
                        * self.flight_speed
                        / self.get_range()
                    )
                self.time = next_event.departure_time
            if next_event.arrival_time <= update_time:
                inspected, suppressed = self._complete_event()
                if inspected is not None:
                    strikes_inspected.append(inspected)
                if suppressed is not None:
                    strikes_suppressed.append(suppressed)
            else:
                if self.time < update_time:  # The uav time is still less than the time to update to
                    # add update and update status
                    if isinstance(next_event.position, Base):
                        self.status = Status.GOING_TO_BASE
                        self._add_update()
                    elif isinstance(next_event.position, Lightning):
                        self.status = Status.GOING_TO_STRIKE
                        self._add_update()
                    else:
                        self.status = Status.GOING_TO_WATER
                        self._add_update()
                    # update to midpoint
                    percentage = (
                        (update_time - self.time)
                        * self.flight_speed
                        / self.distance(next_event.position)
                    )
                    intermediate_point = self.intermediate_point(next_event.position, percentage)
                    self._reduce_current_fuel(self.distance(intermediate_point) / self.get_range())
                    self.time += self.distance(intermediate_point) / self.flight_speed
                    self._update_location(intermediate_point)
                break
        # Lose fuel if hovering and update self.time to update_time
        if (
            self.required_departure_time is not None
            and update_time - self.required_departure_time > -EPSILON
        ):
            assert self.closest_base is not None
            self.go_to_base(self.closest_base, self.required_departure_time)
        assert isinstance(update_time, float)
        if update_time > self.time and not math.isinf(update_time):
            if self.status == Status.HOVERING:
                self._reduce_current_fuel(
                    (update_time - self.time) * self.flight_speed / self.get_range()
                )
            self.time = update_time
        return strikes_inspected, strikes_suppressed

    def add_location_to_queue(self, position: Location, departure_time: float) -> None:
        """Add location to queue departing at the earliest at the given time.

        The arrival time, fuel level, water level and status are calculated and appended to the
        queue along with the location and departure time.

        Args:
            position (Location): position to target
            departure_time (Time): departure time
        """
        if self.use_current_status:
            # TODO(Add allocated water back to water tank!!) pylint: disable=fixme
            self.event_queue.clear()
            self.use_current_status = False
        fuel = self._get_future_fuel()
        assert self._get_future_time() >= departure_time
        departure_time = self._get_future_time()
        dist_to_position = self._get_future_position().distance(position)
        arrival_fuel = fuel - dist_to_position / self.get_range()

        event_arrival_time = departure_time + dist_to_position / (self.flight_speed)
        water = deepcopy(self._get_future_water())

        if isinstance(position, WaterTank):
            assert isinstance(self, WaterBomber), "A UAV was sent to a water tank"
            event_completion_time = event_arrival_time + self._get_water_refill_time()
            position.remove_unallocated_water(self._get_water_capacity() - self._get_future_water())
            water = self._get_water_capacity()
            self.event_queue.put(
                Event(
                    position=position,
                    departure_time=departure_time,
                    arrival_time=event_arrival_time,
                    arrival_fuel=arrival_fuel,
                    completion_fuel=arrival_fuel,
                    water=water,
                    arrival_status=Status.GOING_TO_WATER,
                    completion_status=Status.WAITING_AT_WATER,
                    completion_time=event_completion_time,
                )
            )

        elif isinstance(position, Base):
            event_completion_time = event_arrival_time + self.fuel_refill_time
            completion_fuel = 1.0
            self.event_queue.put(
                Event(
                    position=position,
                    departure_time=departure_time,
                    arrival_time=event_arrival_time,
                    arrival_fuel=arrival_fuel,
                    completion_fuel=completion_fuel,
                    water=water,
                    arrival_status=Status.GOING_TO_BASE,
                    completion_status=Status.WAITING_AT_BASE,
                    completion_time=event_completion_time,
                )
            )

        elif isinstance(position, Lightning):
            event_completion_time = event_arrival_time + self._get_time_at_strike()
            completion_fuel = (
                arrival_fuel - self._get_time_at_strike() * self.flight_speed / self.get_range()
            )
            if isinstance(self, WaterBomber):
                water -= self._get_water_per_delivery()
            self.event_queue.put(
                Event(
                    position=position,
                    departure_time=departure_time,
                    arrival_time=event_arrival_time,
                    arrival_fuel=arrival_fuel,
                    completion_fuel=completion_fuel,
                    water=water,
                    arrival_status=Status.GOING_TO_STRIKE,
                    completion_status=Status.HOVERING,
                    completion_time=event_completion_time,
                )
            )
        else:
            _LOG.error("Input to accept update should be a base, strike or water tank")

    def _update_position(self, position: Location, departure_time: float) -> None:
        """Update position, range and time of an aircraft.

        Args:
            position (Location): new aircraft position
            departure_time (Time): time of triggering event of update position
            final_status (Status): status of aircraft after position update
        """
        if departure_time - self.time > EPSILON:
            assert self.status == Status.HOVERING  # Must have been called from consider
            self._reduce_current_fuel(
                (departure_time - self.time) * (self.flight_speed) / self.get_range()
            )
            self.time = departure_time
        if isinstance(position, Base):
            self.status = Status.GOING_TO_BASE
            self._add_update()
            self.status = Status.WAITING_AT_BASE
        elif isinstance(position, Lightning):
            self.status = Status.GOING_TO_STRIKE
            self._add_update()
            self.status = Status.HOVERING
        else:
            assert isinstance(position, WaterTank) and isinstance(self, WaterBomber)
            self.status = Status.GOING_TO_WATER
            self._add_update()
            self.status = Status.WAITING_AT_WATER
        self._reduce_current_fuel(self.distance(position) / self.get_range())
        self.time += self.distance(position) / self.flight_speed
        self._update_location(position)
        self._add_update()

    @abstractmethod
    def go_to_strike(self, lightning: Lightning, departure_time: float) -> None:
        """Send aircraft to strike."""

    def go_to_water(
        self, water_tank: WaterTank, departure_time: float  # pylint: disable=unused-argument
    ) -> None:
        """Send water bomber to water."""
        assert False, f"{self.get_name()} is trying to visit a water tank"

    def go_to_base(self, base: Base, time: float) -> None:
        """Go to and refill Aircraft at base."""
        self._update_position(base, time)
        self.fuel_refill(base)

    def consider_going_to_base(
        self,
        bases: List[Base],
        departure_time: float,
        percentage: float = 0.3,
    ) -> None:
        """Aircraft will return to base.

        if it takes more than percentage of its fuel tank to return to the nearest base

        Args:
            bases (List[Base]): list of avaliable bases
            departure_time (Time): time of triggering event of consider going to base
            percentage (float, optional): percentage of fuel tank. Defaults to 0.3, must be <= 1.
        """
        if self._get_future_status() == Status.HOVERING:
            current_fuel = self._get_future_fuel()
            # Update fuel loss from hovering [necessary incase we're given a funcy departure time
            # but doesn't affect current implementation]
            if self._get_future_time() < departure_time:
                current_fuel -= (
                    (departure_time - self._get_future_time())
                    * self.flight_speed
                    / self.get_range()
                )
            # Calculate distance that if a base is within we can break
            required_distance = self.get_range() * current_fuel * percentage
            best_base = bases[0]
            min_dist = self._get_future_position().distance(best_base)
            for base in bases:
                dist_to_base = self._get_future_position().distance(base)
                if dist_to_base <= required_distance:
                    # There is a close enough base so we don't need to do anything
                    return
                if dist_to_base < min_dist:
                    best_base = base
                    min_dist = dist_to_base
            # Find nearest base and go to if necessary
            self.add_location_to_queue(best_base, departure_time)

    def go_to_base_when_necessary(
        self,
        bases: List[Base],
        departure_time: float,
        percentage: float = 0.3,
    ) -> None:
        """Aircraft will return to base.

        when it takes more than percentage of its fuel tank to return to the nearest base

        Args:
            bases (List[Base]): list of avaliable bases
            departure_time (Time): time of triggering event of consider going to base
            percentage (float, optional): fraction of fuel tank. Defaults to 0.3, must be <= 1.
        """
        if self._get_future_status() == Status.HOVERING:
            base_index = np.argmin(list(map(self._get_future_position().distance, bases)))
            dist_to_base = self._get_future_position().distance(bases[base_index])
            percentage_range = self._get_future_fuel() * self.get_range() * percentage
            time_to_base = (percentage_range - dist_to_base) / self.flight_speed
            # time to base could be negative becuase current range is a percentage of actual range
            # we want departure time to be the current time if this is the case or the current time
            # plus the time_to_base if not
            if time_to_base > 0:
                departure_time = self._get_future_time() + time_to_base
            else:
                departure_time = self._get_future_time()
            self.closest_base = bases[base_index]
            self.required_departure_time = departure_time
        else:
            self.closest_base = None
            self.required_departure_time = None

    def enough_fuel(  # pylint: disable=too-many-branches, too-many-arguments
        self, positions: List[Location]
    ) -> Optional[float]:
        """Return whether an Aircraft has enough fuel to traverse a given array of positions.

        The fuel is tested when the positions are added to the targets queue with the given
        departure time.

        If the aircraft does not have enough fuel, the function returns None.
        Otherwise the arrival time of the aircraft is returned.

        Args:
            positions (List[Location]): array of locations for the aircraft to traverse

        Returns:
            Optional[Time]: The arrival time of the aircraft after traversing the array of positions
            or None if not enough fuel
        """
        current_time, current_fuel, current_pos = self._get_future_state()
        for idx, position in enumerate(positions):
            if idx == 0:
                dist = current_pos.distance(position)
            else:
                departure_pos = positions[idx - 1]
                if self.precomputed is not None:
                    if isinstance(self, WaterBomber):
                        if isinstance(position, Base) and isinstance(departure_pos, Lightning):
                            dist = self.precomputed.ignition_to_base(
                                departure_pos, position, self.get_type()
                            )
                        elif isinstance(position, Lightning) and isinstance(departure_pos, Base):
                            dist = self.precomputed.ignition_to_base(
                                position, departure_pos, self.get_type()
                            )
                        elif isinstance(position, Base) and isinstance(departure_pos, WaterTank):
                            dist = self.precomputed.water_to_base(
                                departure_pos, position, self.get_type()
                            )
                        elif isinstance(position, WaterTank) and isinstance(departure_pos, Base):
                            dist = self.precomputed.water_to_base(
                                position, departure_pos, self.get_type()
                            )
                        elif isinstance(position, Lightning) and isinstance(
                            departure_pos, WaterTank
                        ):
                            dist = self.precomputed.ignition_to_water(position, departure_pos)
                        elif isinstance(position, WaterTank) and isinstance(
                            departure_pos, Lightning
                        ):
                            dist = self.precomputed.ignition_to_water(departure_pos, position)
                        else:
                            dist = departure_pos.distance(position)
                    else:
                        if isinstance(position, Base) and isinstance(departure_pos, Lightning):
                            dist = self.precomputed.uav_dist(departure_pos, position)
                        elif isinstance(position, Lightning) and isinstance(departure_pos, Base):
                            dist = self.precomputed.uav_dist(position, departure_pos)
                        else:
                            dist = departure_pos.distance(position)
                else:
                    dist = departure_pos.distance(position)
            current_fuel -= dist / self.get_range()
            current_time += dist / self.flight_speed

            if isinstance(position, Lightning):
                current_fuel -= self._get_time_at_strike() * self.flight_speed / self.get_range()
                current_time += self._get_time_at_strike()
            if current_fuel < 0:
                return None
            if isinstance(position, Base):
                current_time += self.fuel_refill_time
                current_fuel = 1.0
            elif isinstance(position, WaterTank):
                current_time += self._get_water_refill_time()

        return current_time

    def enough_fuel2(self, positions: List[Location]) -> Optional[float]:
        """Return whether an Aircraft has enough fuel to traverse a given array of positions.

        The fuel is tested when the positions are added to the targets queue with the given
        departure time.

        If the aircraft does not have enough fuel, the function returns None.
        Otherwise the arrival time of the aircraft is returned.

        Args:
            positions (List[Location]): array of locations for the aircraft to traverse

        Returns:
            Optional[Time]: The arrival time of the aircraft after traversing the array of positions
            or None if not enough fuel
        """
        current_fuel = self._get_future_fuel()
        current_time = self._get_future_time()
        departure_position = self._get_future_position()
        for position in positions:
            dist = departure_position.distance(position)
            current_fuel -= dist / self.get_range()
            current_time += dist / self.flight_speed
            if isinstance(position, Lightning):
                current_fuel -= self._get_time_at_strike() * self.flight_speed / self.get_range()
                current_time += self._get_time_at_strike()
            if current_fuel < 0:
                return None
            if isinstance(position, WaterTank):
                current_time += self._get_water_refill_time()
            if isinstance(position, Base):
                current_time += self.fuel_refill_time
                current_fuel = 1.0
            departure_position = position
        return current_time

    def _add_update(self) -> None:
        """Add update to past locations."""
        previous_update = self.past_locations[-1]
        distance_hovered = 0.0
        if previous_update.status == Status.HOVERING:
            distance_hovered = (self.time - previous_update.time) * self.flight_speed
        self.past_locations.append(
            UpdateEvent(
                self.get_name(),
                self.lat,
                self.lon,
                self.time,
                self.status,
                self.distance(previous_update),
                self.current_fuel_capacity,
                self.get_range() * self.current_fuel_capacity,
                distance_hovered,
                self._get_water_on_board(),
            )
        )


class UAV(Aircraft):
    """UAV class for unmanned aircraft searching lightning strikes."""

    def __init__(
        self,
        id_no: int,
        latitude: float,
        longitude: float,
        attributes: Dict[str, Any],
        starting_at_base: bool,
        initial_fuel: float,
    ):  # pylint: disable=too-many-arguments
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
            Speed(int(attributes["flight_speed"]), "km", "hr").get(
                DEFAULT_DISTANCE_UNITS, DEFAULT_DURATION_UNITS
            ),
            Duration(int(attributes["fuel_refill_time"]), "min").get(DEFAULT_DURATION_UNITS),
            id_no,
            starting_at_base,
            initial_fuel,
        )
        self.total_range: float = Distance(int(attributes["range"]), "km").get(
            DEFAULT_DISTANCE_UNITS
        )
        self.inspection_time: float = Duration(1.0, "min").get(DEFAULT_DURATION_UNITS)
        # TODO(read from csv) pylint: disable=fixme
        self.past_locations = [
            UpdateEvent(
                self.get_name(),
                self.lat,
                self.lon,
                self.time,
                self.status,
                0,
                self.current_fuel_capacity,
                self.get_range(),
                0,
                0,
            )
        ]

    def go_to_strike(self, lightning: Lightning, departure_time: float) -> None:
        """UAV go to and inspect strike.

        Args:
            lightning (Lightning): strike being inspected
            departure_time (Time): time of UAVs departure
            arrival_time (Time): time of UAVs arrival at strike
        """
        self._update_position(lightning, departure_time)
        self.time += self._get_time_at_strike()
        self._reduce_current_fuel(
            (self._get_time_at_strike() * self.flight_speed / self.get_range())
        )
        lightning.inspected(self.time)
        self.strikes_visited.append((lightning, self.time))

    def get_range(self):
        """Return total range of UAV."""
        return self.total_range

    def get_name(self) -> str:
        """Return name of UAV."""
        return f"uav {self.id_no}"

    def _get_time_at_strike(self) -> float:
        """Return inspection time of UAV."""
        return self.inspection_time


class WaterBomber(Aircraft):
    """Class for aircraft that contain water for dropping on potential fires."""

    def __init__(
        self,
        id_no: int,
        latitude: float,
        longitude: float,
        attributes,
        bomber_type: str,
        starting_at_base: bool,
        initial_fuel: float,
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
            Speed(int(attributes["flight_speed"]), "km", "hr").get(
                DEFAULT_DISTANCE_UNITS, DEFAULT_DURATION_UNITS
            ),
            Duration(int(attributes["fuel_refill_time"]), "min").get(DEFAULT_DURATION_UNITS),
            id_no,
            starting_at_base,
            initial_fuel,
        )
        self.range_empty: float = Distance(int(attributes["range_empty"]), "km").get(
            DEFAULT_DISTANCE_UNITS
        )
        self.range_under_load: float = Distance(int(attributes["range_under_load"]), "km").get(
            DEFAULT_DISTANCE_UNITS
        )
        self.water_refill_time: float = Duration(int(attributes["water_refill_time"]), "min").get(
            DEFAULT_DURATION_UNITS
        )
        self.bombing_time: float = Duration(int(attributes["bombing_time"]), "min").get(
            DEFAULT_DURATION_UNITS
        )
        self.water_per_delivery: float = Volume(int(attributes["water_per_delivery"]), "L").get(
            DEFAULT_VOLUME_UNITS
        )
        self.water_capacity: float = Volume(int(attributes["water_capacity"]), "L").get(
            DEFAULT_VOLUME_UNITS
        )
        self.water_on_board: float = Volume(int(attributes["water_capacity"]), "L").get(
            DEFAULT_VOLUME_UNITS
        )
        self.type: str = bomber_type
        self.name: str = f"{bomber_type} {id_no+1}"
        self.past_locations = [
            UpdateEvent(
                self.name,
                self.lat,
                self.lon,
                self.time,
                self.status,
                0,
                self.current_fuel_capacity,
                self.get_range(),
                0,
                self.water_on_board,
            )
        ]

    def get_range(self):
        """Return range of Water bomber."""
        return (self.range_under_load - self.range_empty) * (
            self.water_on_board / self.water_capacity
        ) + self.range_empty

    def _get_time_at_strike(self) -> float:
        """Return bombing time of water bomber."""
        return self.bombing_time

    def get_name(self) -> str:
        """Return name of Water Bomber."""
        return str(self.name)

    def get_type(self) -> str:
        """Return type of Water Bomber."""
        return self.type

    def go_to_strike(self, lightning: Lightning, departure_time: float) -> None:
        """Water Bomber go to and suppress strike.

        Args:
            lightning (Lightning): ignition being suppressed
            departure_time (Time): time of water bombers departure
        """
        self._update_position(lightning, departure_time)
        self.water_on_board -= self.water_per_delivery
        self.time += self._get_time_at_strike()
        self.current_fuel_capacity -= (
            self._get_time_at_strike() * self.flight_speed / self.get_range()
        )
        lightning.suppressed(self.time)
        self.strikes_visited.append((lightning, self.time))

    def go_to_water(self, water_tank: WaterTank, departure_time: float) -> None:
        """Water bomber goes and fills up water.

        Args:
            water_tank (WaterTank): water tank
            departure_time (Time): departure time of water bomber
        """
        self._update_position(water_tank, departure_time)
        self._water_refill(water_tank)

    def check_water_tank(self, water_tank: WaterTank) -> bool:
        """Return whether a given water tank has enough capacity to refill the water bomber.

        Args:
            water_tank (WaterTank): water tank

        Returns:
            bool: Returns false if water tank has enough to extinguish a single fire
            but not completely refill
        """
        return (
            water_tank.get_water_capacity(not self.use_current_status)
            >= self.water_capacity - self._get_future_water()
        )

    def _water_refill(self, water_tank: WaterTank) -> None:
        """Update time and range of water bomber after water refill."""
        water_tank.remove_water(self.water_capacity - self.water_on_board)
        self.water_on_board = self.water_capacity
        self.time += self.water_refill_time

    def enough_water(self, no_of_fires: int = 1) -> bool:
        """Return whether the water bomber has enough water to extinguish desired fires."""
        return self._get_future_water() >= self.water_per_delivery * no_of_fires

    def _get_water_refill_time(self) -> float:
        """Return water refill time of Aircraft. Should be 0 if does not exist."""
        return self.water_refill_time

    def _get_water_on_board(self) -> float:
        """Return water refill time of Aircraft. Should be 0 if does not exist."""
        return self.water_on_board

    def _get_water_per_delivery(self) -> float:
        """Return water per delivery time of Aircraft."""
        return self.water_per_delivery

    def _get_water_capacity(self) -> float:
        """Return water capcaity of Aircraft."""
        return self.water_capacity

    def _set_water_on_board(self, water: float) -> None:
        """Set water on board of Aircraft."""
        self.water_on_board = water
