"""Water bomber class."""

from math import inf
from typing import List, Optional, Union

import numpy as np
from pydantic.main import BaseModel

from bushfire_drone_simulation.aircraft import Aircraft, AircraftType, Event, UpdateEvent
from bushfire_drone_simulation.fire_utils import Base, Location, WaterTank
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.units import Distance, Duration, Speed, Volume


class WBAttributes(BaseModel):
    """Water Bomber attributes."""

    id_no: int
    latitude: float
    longitude: float
    flight_speed: float
    fuel_refill_time: float
    suppression_time: float
    water_refill_time: float
    water_per_suppression: float
    range_empty: float
    range_under_load: float
    water_capacity: float
    pct_fuel_cutoff: float
    bomber_type: str


class WaterBomber(Aircraft):
    """Class for aircraft that contain water for dropping on potential fires."""

    def __init__(
        self,
        attributes: WBAttributes,
        starting_at_base: bool,
        initial_fuel: float,
    ):
        """Initialize water bombing aircraft.

        Args:
            id_no (int): id number of water bomber
            latitude (float): latitude of water bomber
            longitude (float): longitude of water bomber
            attributes (): dictionary of attributes of water bomber
            bomber_type (str): type of water bomber
        """
        super().__init__(
            attributes.latitude,
            attributes.longitude,
            Speed(int(attributes.flight_speed), "km", "hr").get(),
            Duration(int(attributes.fuel_refill_time), "min").get(),
            attributes.id_no,
            starting_at_base,
            initial_fuel,
            attributes.pct_fuel_cutoff,
        )
        self.range_empty: float = Distance(int(attributes.range_empty), "km").get()
        self.range_under_load: float = Distance(int(attributes.range_under_load), "km").get()
        self.water_refill_time: float = Duration(int(attributes.water_refill_time), "min").get()
        self.suppression_time: float = Duration(int(attributes.suppression_time), "min").get()
        self.water_per_suppression: float = Volume(int(attributes.water_per_suppression), "L").get()
        self.water_capacity: float = Volume(int(attributes.water_capacity), "L").get()
        self.water_on_board: float = Volume(int(attributes.water_capacity), "L").get()
        self.type: str = attributes.bomber_type
        self.name: str = f"{attributes.bomber_type} {attributes.id_no+1}"
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
                [],
            )
        ]

    @classmethod
    def aircraft_type(cls) -> AircraftType:
        """Typesting of water bomber aircraft."""
        return AircraftType.WB

    def copy_from_wb(self, other: "WaterBomber") -> None:
        """Copy parameters from another water bomber.

        Args:
            other ("WaterBomber"): other
        """
        self.__dict__.update(other.__dict__)

    def get_range(self) -> float:
        """Return range of Water bomber."""
        return (self.range_under_load - self.range_empty) * (
            self.water_on_board / self.water_capacity
        ) + self.range_empty

    def _get_time_at_strike(self) -> float:
        """Return suppression time of water bomber."""
        return self.suppression_time

    def get_name(self) -> str:
        """Return name of Water Bomber."""
        return str(self.name)

    def get_type(self) -> str:
        """Return type of Water Bomber."""
        return self.type

    def check_water_tank(self, water_tank: WaterTank) -> bool:
        """Return whether a given water tank has enough capacity to refill the water bomber.

        Returns:
            bool: Returns false if water tank has enough to extinguish a single fire
            but not completely refill
        """
        return (
            water_tank.get_water_capacity(not self.use_current_status)
            >= self.water_capacity - self._get_future_water()
        )

    def enough_water(
        self, positions: List[Location], state: Optional[Union[Event, str]] = None
    ) -> bool:
        """Return whether the water bomber has enough water.

        To traverse given list of positions from a given state.
        """
        if state is None:
            water = self._get_future_water()
        elif isinstance(state, str):
            water = self.water_on_board
        else:
            water = state.water
        for position in positions:
            if isinstance(position, Lightning):
                water -= self.water_per_suppression
            if water < 0:
                return False
            if isinstance(position, WaterTank):
                water = self.water_capacity
        return True

    def _get_water_refill_time(self) -> float:
        """Return water refill time of Aircraft. Should be 0 if does not exist."""
        return self.water_refill_time

    def _get_water_on_board(self) -> float:
        """Return water refill time of Aircraft. Should be 0 if does not exist."""
        return self.water_on_board

    def _get_water_per_suppression(self) -> float:
        """Return water per delivery time of Aircraft."""
        return self.water_per_suppression

    def _get_water_capacity(self) -> float:
        """Return water capacity of Aircraft."""
        return self.water_capacity

    def _set_water_on_board(self, water: float) -> None:
        """Set water on board of Aircraft."""
        self.water_on_board = water

    def go_to_water_if_necessary(self, water_tanks: List[WaterTank], bases: List[Base]) -> None:
        """Aircraft will fill up water if it does not have enough to suppress another strike.

        Args:
            water_tanks (List[WaterTank]): list of water tanks
            bases (List[Base]): list of avaliable bases
        """
        if self._get_future_water() < self.water_per_suppression:
            min_dist = inf
            best_tank = None
            for tank in water_tanks:
                if self.check_water_tank(tank):
                    base_index = int(np.argmin(list(map(tank.distance, bases))))
                    if self.enough_fuel([tank, bases[base_index]]) is not None:
                        dist_to_tank = self._get_future_position().distance(tank)
                        if dist_to_tank < min_dist:
                            min_dist = dist_to_tank
                            best_tank = tank
            if best_tank is None:
                # If we can't get to water and fuel go staight to fule - no point hovering anymore
                base_index = int(np.argmin(list(map(self._get_future_position().distance, bases))))
                self.add_location_to_queue(bases[base_index])
            else:
                self.add_location_to_queue(best_tank)
