"""Water bomber class."""

from typing import List, Optional, Union

from pydantic.main import BaseModel

from bushfire_drone_simulation.aircraft import Aircraft, AircraftType, Event, UpdateEvent
from bushfire_drone_simulation.fire_utils import Location, WaterTank
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
        super().copy_from_aircraft(other)
        self.range_empty = other.range_empty
        self.range_under_load = other.range_under_load
        self.water_refill_time = other.water_refill_time
        self.suppression_time = other.suppression_time
        self.water_per_suppression = other.water_per_suppression
        self.water_capacity = other.water_capacity
        self.water_on_board = other.water_on_board
        self.type = other.type
        self.name = other.name
        self.past_locations = other.past_locations

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
