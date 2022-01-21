"""UAV Class."""

from pydantic.main import BaseModel

from bushfire_drone_simulation.aircraft import Aircraft, AircraftType, UpdateEvent
from bushfire_drone_simulation.units import Distance, Duration, Speed


class UAVAttributes(BaseModel):
    """UAV attributes."""

    id_no: int
    latitude: float
    longitude: float
    flight_speed: float
    fuel_refill_time: float
    range: float
    inspection_time: float
    pct_fuel_cutoff: float


class UAV(Aircraft):
    """UAV class for unmanned aircraft searching lightning strikes."""

    def __init__(
        self,
        attributes: UAVAttributes,
        starting_at_base: bool,
        initial_fuel: float,
    ):  # pylint: disable=too-many-arguments
        """Initialize UAV.

        Args:
            id_no (int): id number of UAV
            latitude (float): latitude of UAV
            longitude (float): longitude of UAV
            attributes (UAVAttributes): attributes of UAV
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
        self.total_range: float = Distance(int(attributes.range), "km").get()
        self.inspection_time: float = Duration(attributes.inspection_time, "min").get()
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
                [],
            )
        ]

    @classmethod
    def aircraft_type(cls) -> AircraftType:
        """Typestring of UAV aircraft."""
        return AircraftType.UAV

    def copy_from_uav(self, other: "UAV") -> None:
        """Copy parameters from another UAV.

        Args:
            other ("UAV"): other
        """
        super().copy_from_aircraft(other)
        self.total_range = other.total_range
        self.inspection_time = other.inspection_time
        self.past_locations = other.past_locations

    def get_range(self) -> float:
        """Return total range of UAV."""
        return self.total_range

    def get_name(self) -> str:
        """Return name of UAV."""
        return f"uav {self.id_no}"

    def _get_time_at_strike(self) -> float:
        """Return inspection time of UAV."""
        return self.inspection_time
