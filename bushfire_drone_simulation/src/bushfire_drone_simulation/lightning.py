"""Module containing lightning class for bushfire_drone_simulation."""

import random
from copy import deepcopy
from typing import List, Union

from bushfire_drone_simulation.fire_utils import Location, Time


class Lightning(Location):
    """Class for individual lightning strikes."""

    inspected_time: Union[Time, None] = None
    suppressed_time: Union[Time, None] = None
    nearest_base: Union[int, None] = None

    def __init__(
        self,
        latitude: float,
        longitude: float,
        spawn_time: Time,
        ignition_probability: float,
        id_no: int,
    ):  # pylint: disable=too-many-arguments
        """Initialize lightning."""
        self.spawn_time = spawn_time
        self.ignition = random.random() < ignition_probability
        super().__init__(latitude, longitude)
        self.id_no = id_no

    def inspected(self, time: Time) -> None:
        """Lightning strike is updated when inspected.

        Args:
            time (Time): time of inspection
        """
        self.inspected_time = deepcopy(time)

    def suppressed(self, time: Time):
        """Lightning strike is updated when suppressed.

        Args:
            time (Time): time of supression
        """
        self.suppressed_time = deepcopy(time)

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
