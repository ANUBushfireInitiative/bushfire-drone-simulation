"""Module containing lightning class for bushfire_drone_simulation."""

import random

from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.fire_utils import Location, Time


class Lightning:
    """Class for individual lightning strikes."""

    ignition: bool
    inspected_time: Time = None
    supressed_time: Time = None
    inspected_by: UAV = None
    supressed_by: WaterBomber = None
    nearest_base: int = None

    def __init__(self, position: Location, spawn_time: Time, ignition_probability: float):
        """Initialize lightning."""
        self.position = position
        self.spawn_time = spawn_time
        self.ignition = random.random() < ignition_probability

    def inspected(self, uav: UAV, time: Time):
        """Lightning strike is updated when inspected."""
        self.inspected_by = uav
        self.inspected_time = time

    def supressed(self, water_bomber: WaterBomber, time: Time):
        """Lightning strike is updated when supressed."""
        self.supressed_by = water_bomber
        self.supressed_time = time

    def __le__(self, other):
        """Less than operator for Lightning."""
        return self.spawn_time < other.spawn_time


def reduce_lightning_to_ignitions(lightning_strikes):
    """Given an array of inspected lightning_strikes, return an array of those that ignited."""
    ignitions = []
    for strike in lightning_strikes:
        if strike.ignition:
            ignitions.append(strike)
