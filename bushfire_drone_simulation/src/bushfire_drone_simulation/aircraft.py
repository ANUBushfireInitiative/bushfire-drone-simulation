"""Aircraft module for various aircraft classes."""

import logging
from abc import abstractmethod
from copy import deepcopy
from enum import Enum
from queue import Queue
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
        self.time = deepcopy(time)
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
        departure_time: Time,
        current_fuel_capacity: float,
        water_on_board: Volume,
        status: Status,
        arrival_time: Time,
    ):  # pylint: disable = too-many-arguments
        """Initalise event."""
        self.position = position
        self.time = departure_time
        # Theoretically after arrival:
        self.arrival_time = arrival_time  # Travel and event completed
        self.fuel = current_fuel_capacity
        self.water_on_board = water_on_board
        self.status = status

    def __lt__(self, other: "Event") -> bool:
        """Less than operator for Event."""
        return self.time < other.time


class Aircraft(Location):  # pylint: disable=too-many-public-methods
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
        self.event_queue: "Queue[Event]" = Queue()
        self.use_current_status: bool = False

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

    def use_event_queue(self) -> None:
        """For each aircraft, use queue to return status."""
        self.use_current_status = False

    def use_current_state(self) -> None:
        """For each aircraft, use current state to return current status."""
        self.use_current_status = True

    def get_future_assigned_time(self) -> Time:
        """Return time as if all elements of the event queue have been completed."""
        if self.event_queue.empty() or self.use_current_status:
            return self.time
        return self.event_queue.queue[-1].arrival_time

    def get_future_assigned_position(self) -> Location:
        """Return position as if all elements of the event queue have been completed."""
        if self.event_queue.empty() or self.use_current_status:
            return Location(self.lat, self.lon)
        return self.event_queue.queue[-1].position

    def get_future_fuel(self) -> float:
        """Return fuel capacity as if all elements of the event queue have been completed."""
        if self.event_queue.empty() or self.use_current_status:
            return self.current_fuel_capacity
        return self.event_queue.queue[-1].fuel

    def get_future_water(self) -> Volume:
        """Return water on board as if all elements of the event queue have been completed."""
        if self.event_queue.empty() or self.use_current_status:
            return self.get_water_on_board()
        return self.event_queue.queue[-1].water_on_board

    def get_future_status(self) -> Status:
        """Return water on board as if all elements of the event queue have been completed."""
        if self.event_queue.empty() or self.use_current_status:
            return self.status
        return self.event_queue.queue[-1].status

    @abstractmethod
    def get_time_at_strike(self) -> Duration:
        """Return duration an aircraft spends inspecting or suppressing a strike."""

    @abstractmethod
    def get_name(self) -> str:
        """Return name of aircraft."""

    @abstractmethod
    def go_to_strike(self, lightning: Lightning, departure_time: Time) -> None:
        """Send aircraft to strike."""

    def go_to_water(
        self, water_tank: WaterTank, departure_time: Time  # pylint: disable=unused-argument
    ) -> None:
        """Send water bomber to water."""
        assert False, f"THIS IS BAD. {self.get_name()} is trying to visit a water tank"

    def arrival_time(self, positions: List[Location], time_of_event: Time) -> Time:
        """Return arrival time of Aircraft to a given array of positions.

        Args:
            positions (List[Location]): array of locations for the aircraft to traverse
            time_of_event (Time): Time of departure

        Returns:
            Time: Arrival time of aircraft
        """
        current_time = deepcopy(max(self.get_future_assigned_time(), time_of_event))
        for index, position in enumerate(positions):
            if index == 0:
                current_time.add_duration(
                    position.distance(self.get_future_assigned_position()).div_by_speed(
                        self.flight_speed
                    )
                )
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

    def complete_event(self) -> Tuple[List[Lightning], List[Lightning]]:
        """Completes next event in queue and returns list of strikes inspected and suppressed."""
        assert not self.event_queue.empty(), "Complete event was called on empty queue"
        event = self.event_queue.get()
        inspections = []
        suppressions = []
        assert isinstance(event, Event), "event_queue contained a non event"
        if isinstance(event.position, WaterTank):
            assert isinstance(self, WaterBomber), "A UAV was sent to a water tank"
            self.go_to_water(event.position, event.time)
        elif isinstance(event.position, Base):
            self.go_to_base(event.position, event.time)
        elif isinstance(event.position, Lightning):
            self.go_to_strike(event.position, event.time)
            if isinstance(self, UAV):
                inspections.append(event.position)
            else:
                suppressions.append(event.position)
        return inspections, suppressions  # TODO This should not be a list

    def update_to_time(self, update_time: Time) -> Tuple[List[Lightning], List[Lightning]]:
        """Update aircraft to given time and delete all updates beyond this time.

        Args:
            time (Time): Time to update to

        Returns:
            List[Lightning]: list of strikes inspected
            List[Lightning]]: list of ignitions suppressed
        """
        strikes_inspected: List[Lightning] = []
        strikes_suppressed: List[Lightning] = []
        # If we can get to the next position then complete update, otherwise make it half way there
        while not self.event_queue.empty():
            next_event = self.event_queue.queue[0]
            self.time = deepcopy(next_event.time)  # TODO Lose fuel if hovering???
            arrival_time = deepcopy(self.time)
            arrival_time.add_duration(
                self.distance(next_event.position).div_by_speed(
                    self.flight_speed
                )  # TODO REMOVE THIS
            )
            if arrival_time <= update_time:
                inspected, suppressed = self.complete_event()
                strikes_inspected += inspected
                strikes_suppressed += suppressed
            else:
                if self.time < update_time:  # The uav time is still less than the time to update to
                    # add update and update status
                    if isinstance(next_event.position, Base):
                        self.add_update(Status.GOING_TO_BASE)
                        self.status = Status.GOING_TO_BASE
                    elif isinstance(next_event.position, Lightning):
                        self.add_update(Status.GOING_TO_STRIKE)
                        self.status = Status.GOING_TO_STRIKE
                    else:
                        self.add_update(Status.GOING_TO_WATER)
                        self.status = Status.GOING_TO_WATER
                    # update to midpoint
                    percentage = (update_time - self.time) / self.distance(
                        next_event.position
                    ).div_by_speed(self.flight_speed)
                    intermediate_point = self.intermediate_point(next_event.position, percentage)
                    self.reduce_current_fuel(self.distance(intermediate_point) / self.get_range())
                    self.time.add_duration(
                        self.distance(intermediate_point).div_by_speed(self.flight_speed)
                    )
                    self.update_location(intermediate_point)
                return strikes_inspected, strikes_suppressed
        return strikes_inspected, strikes_suppressed

    def add_location_to_queue(self, position: Location, earliest_departure_time: Time) -> None:
        """Add location to queue departing at the earliest at the given time.

        The arrival time, fuel level, water level and status are calculated and appended to the
        queue along with the location and departure time.

        Args:
            position (Location): position to target
            departure_time (Time): departure time
        """
        if self.use_current_status:
            self.event_queue.queue.clear()
            self.use_event_queue()
        fuel = self.get_future_fuel()
        if (
            self.get_future_status() == Status.HOVERING
            and self.get_future_assigned_time() < earliest_departure_time
        ):
            fuel -= (earliest_departure_time - self.get_future_assigned_time()).mul_by_speed(
                self.flight_speed
            ) / self.get_range()
        event_departure_time = deepcopy(
            max(self.get_future_assigned_time(), earliest_departure_time)
        )
        fuel -= self.get_future_assigned_position().distance(position) / self.get_range()

        event_arrival_time = event_departure_time + self.get_future_assigned_position().distance(
            position
        ).div_by_speed(self.flight_speed)
        water = deepcopy(self.get_future_water())

        if isinstance(position, WaterTank):
            assert isinstance(self, WaterBomber), "A UAV was sent to a water tank"
            event_completion_time = event_arrival_time + self.get_water_refill_time()
            water = self.get_water_capacity()
            self.event_queue.put(
                Event(
                    position,
                    event_departure_time,
                    fuel,
                    water,
                    Status.WAITING_AT_WATER,
                    event_completion_time,
                )
            )

        elif isinstance(position, Base):
            event_completion_time = event_arrival_time + self.fuel_refill_time
            fuel = 1
            self.event_queue.put(
                Event(
                    position,
                    event_departure_time,
                    fuel,
                    water,
                    Status.WAITING_AT_BASE,
                    event_completion_time,
                )
            )

        elif isinstance(position, Lightning):
            event_completion_time = event_arrival_time + self.get_time_at_strike()
            fuel -= self.get_time_at_strike().mul_by_speed(self.flight_speed) / self.get_range()
            if isinstance(self, WaterBomber):
                water -= self.get_water_per_delivery()
            self.event_queue.put(
                Event(
                    position,
                    event_departure_time,
                    fuel,
                    water,
                    Status.HOVERING,
                    event_completion_time,
                )
            )
        else:
            _LOG.error("Input to accept update should be a base, strike or water tank")

    def get_water_per_delivery(self) -> Volume:
        """Return water per delivery time of Aircraft."""
        assert isinstance(
            self, WaterBomber
        ), f"{self.get_name()} is trying to measure water per delivery"
        return Volume(0)

    def get_water_capacity(self) -> Volume:
        """Return water capcaity of Aircraft."""
        assert isinstance(
            self, WaterBomber
        ), f"{self.get_name()} is trying to measure it's water capacity"
        return Volume(0)

    def get_water_refill_time(self) -> Duration:
        """Return water refill time of Aircraft."""
        assert isinstance(self, WaterBomber), f"{self.get_name()} is trying to visit a water tank"
        return Duration(0)

    def get_water_on_board(self) -> Volume:
        """Return water on board of Aircraft."""
        assert isinstance(
            self, WaterBomber
        ), f"{self.get_name()} is trying to measure water on board"
        return Volume(0)

    def update_position(
        self, position: Location, departure_time: Time, final_status: Status
    ) -> None:
        """Update position, range and time of an aircraft.

        Args:
            position (Location): new aircraft position
            departure_time (Time): time of triggering event of update position
            final_status (Status): status of aircraft after position update
        """
        if self.time < departure_time:
            assert self.status == Status.HOVERING
            self.reduce_current_fuel(
                (departure_time - self.time).mul_by_speed(self.flight_speed) / self.get_range()
            )
            self.time = deepcopy(departure_time)
        if (
            final_status == Status.WAITING_AT_BASE
        ):  # TODO(WTF) why are we working out status based on final status
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
        self,
        bases: List[Base],
        departure_time: Time,
        fraction: float = 3,  # TODO percentage_fuel = 0.333333 instead???
    ) -> None:
        """Aircraft will return to base.

        if it takes more than 1/fraction of its fuel tank to return to the nearest base

        Args:
            bases (List[Base]): list of avaliable bases
            departure_time (Time): time of triggering event of consider going to base
            fraction (float, optional): fraction of fuel tank. Defaults to 3, must be >= 1.
        """
        if self.get_future_status() == Status.HOVERING:  # TODO why are we still using future status
            current_fuel = self.get_future_fuel()
            # Update fuel loss from hovering
            if self.get_future_assigned_time() < departure_time:
                current_fuel -= (departure_time - self.get_future_assigned_time()).mul_by_speed(
                    self.flight_speed
                ) / self.get_range()
            # Find nearest base and go to if necessary
            index = np.argmin(list(map(self.get_future_assigned_position().distance, bases)))
            if (
                self.get_future_assigned_position().distance(bases[index]) * fraction
                > self.get_range() * current_fuel
            ):
                self.add_location_to_queue(bases[index], departure_time)

    def go_to_base_when_necessary(
        self,
        bases: List[Base],
        departure_time: Time,
        fraction: float = 3,  # TODO and again 0.3, move default to parameters.json. Also see if it is faster if we only check if fuel is below a certain threshold.
    ) -> None:
        """Aircraft will return to base.

        when it takes more than 1/fraction of its fuel tank to return to the nearest base

        Args:
            bases (List[Base]): list of avaliable bases
            departure_time (Time): time of triggering event of consider going to base
            fraction (float, optional): fraction of fuel tank. Defaults to 3, must be >= 1.
        """
        if self.get_future_status() == Status.HOVERING:
            base_index = np.argmin(list(map(self.get_future_assigned_position().distance, bases)))
            # FIXME iterate over bases and break if any are close enough
            dist_to_base = (
                self.get_future_assigned_position().distance(bases[base_index]) * fraction
            )
            current_range = self.get_future_fuel() * self.get_range()
            time_to_base = (current_range - dist_to_base).div_by_speed(self.flight_speed)
            departure_time = deepcopy(self.get_future_assigned_time())
            departure_time.add_duration(time_to_base)
            departure_time = max(self.get_future_assigned_time(), departure_time)
            self.add_location_to_queue(bases[base_index], departure_time)

    def enough_fuel(self, positions: List[Location], departure_time: Time) -> bool:
        """Return whether an Aircraft has enough fuel to traverse a given array of positions.

        The fuel is tested when the positions are added to the targets queue with the given
        departure time.

        Args:
            positions (List[Location]): array of locations for the aircraft to traverse
            departure_time (Time): Time of departure

        Returns:
            bool: whether the aircraft has enough fuel to traverse positions
        """
        current_fuel = self.get_future_fuel()
        if (
            self.get_future_status() == Status.HOVERING
            and self.get_future_assigned_time() < departure_time
        ):
            current_fuel -= (departure_time - self.get_future_assigned_time()).mul_by_speed(
                self.flight_speed
            ) / self.get_range()
        for index, position in enumerate(positions):
            if index == 0:
                current_fuel -= (
                    self.get_future_assigned_position().distance(position) / self.get_range()
                )
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
        """Return number of lightning strikes this aircraft has visited."""
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
                self.time,
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
        lightning.inspected(self.time)
        self.strikes_visited.append((lightning, deepcopy(self.time)))

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
                self.time,
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
                self.time,
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

    def go_to_strike(self, lightning: Lightning, departure_time: Time) -> None:
        """Water Bomber go to and suppress strike.

        Args:
            lightning (Lightning): ignition being suppressed
            departure_time (Time): time of water bombers departure
        """
        self.update_position(lightning, departure_time, Status.HOVERING)
        self.water_on_board -= self.water_per_delivery
        self.time.add_duration(self.get_time_at_strike())
        self.current_fuel_capacity -= (
            self.get_time_at_strike().mul_by_speed(self.flight_speed) / self.get_range()
        )
        lightning.suppressed(self.time)
        self.strikes_visited.append((lightning, deepcopy(self.time)))

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

    def water_refill(self, water_tank: WaterTank) -> None:
        """Update time and range of water bomber after water refill."""
        water_tank.remove_water(self.water_capacity - self.water_on_board)
        if water_tank.capacity < Volume(0):
            _LOG.error("Water tank ran out of water")
        self.water_on_board = self.water_capacity
        self.time.add_duration(self.water_refill_time)

    def enough_water(self, no_of_fires: int = 1) -> bool:
        """Return whether the water bomber has enough water to extinguish desired fires."""
        return self.get_future_water() >= self.water_per_delivery * no_of_fires

    def get_water_refill_time(self) -> Duration:
        """Return water refill time of Aircraft. Should be 0 if does not exist."""
        return self.water_refill_time

    def get_water_on_board(self) -> Volume:
        """Return water refill time of Aircraft. Should be 0 if does not exist."""
        return self.water_on_board

    def get_water_per_delivery(self) -> Volume:
        """Return water per delivery time of Aircraft."""
        return self.water_per_delivery

    def get_water_capacity(self) -> Volume:
        """Return water capcaity of Aircraft."""
        return self.water_capacity

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
                self.time,
                new_status,
                self.distance(previous_update),
                self.current_fuel_capacity,
                self.get_range() * self.current_fuel_capacity,
                distance_hovered,
                self.water_on_board,
            )
        )
