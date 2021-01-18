"""Module containing lightning class for bushfire_drone_simulation."""

import random
from typing import List, Union

from bushfire_drone_simulation.fire_utils import Location, Time


class Lightning(Location):
    """Class for individual lightning strikes."""

    inspected_time: Union[Time, None] = None
    suppressed_time: Union[Time, None] = None
    nearest_base: Union[int, None] = None

    def __init__(
        self, latitude: float, longitude: float, spawn_time: Time, ignition_probability: float
    ):
        """Initialize lightning."""
        self.spawn_time = spawn_time
        self.ignition = random.random() < ignition_probability
        super().__init__(latitude, longitude)

    def inspected(self, time: Time) -> None:
        """Lightning strike is updated when inspected."""
        self.inspected_time = time

    def suppressed(self, time: Time):
        """Lightning strike is updated when suppressed."""
        self.suppressed_time = time

    def __lt__(self, other) -> bool:
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
