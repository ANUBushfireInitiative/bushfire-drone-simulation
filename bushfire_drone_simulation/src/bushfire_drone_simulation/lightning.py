"""Module containing lightning class for bushfire_drone_simulation."""

import random
from collections import namedtuple
from typing import List, Union

from bushfire_drone_simulation.fire_utils import Location


class Lightning(Location):
    """Class for individual lightning strikes."""

    def __init__(
        self,
        latitude: float,
        longitude: float,
        spawn_time: float,
        ignition_probability: float,
        risk_rating: float,
        id_no: int,
    ):  # pylint: disable=too-many-arguments
        """Initialize lightning."""
        self.spawn_time = spawn_time
        self.ignition = random.random() < ignition_probability
        self.risk_rating = risk_rating
        super().__init__(latitude, longitude)
        self.id_no = id_no
        self.inspected_time: Union[float, None] = None
        self.suppressed_time: Union[float, None] = None
        self.nearest_base: Union[int, None] = None

    def copy_from_lightning(self, other: "Lightning") -> None:
        """Copy parameters from another lightning strike.

        Args:
            other ("Lightning"): other
        """
        self.__dict__.update(other.__dict__)

    def inspected(self, time: float) -> None:
        """Lightning strike is updated when inspected.

        Args:
            time (Time): time of inspection
        """
        self.inspected_time = time

    def suppressed(self, time: float) -> None:
        """Lightning strike is updated when suppressed.

        Args:
            time (Time): time of suppression
        """
        self.suppressed_time = time

    def __lt__(self, other: "Lightning") -> bool:
        """Less than operator for Lightning."""
        return self.spawn_time < other.spawn_time


def reduce_lightning_to_ignitions(lightning_strikes: List[Lightning]) -> List[Lightning]:
    """Given an array of inspected lightning_strikes, return an array of those that ignited."""
    ignitions = []
    for strike in lightning_strikes:
        if strike.ignition:
            if strike.inspected_time is not None:  # Lightning was not inspected
                ignitions.append(strike)
    return ignitions


AllocatedLightning = namedtuple("AllocatedLightning", "lightning time")
