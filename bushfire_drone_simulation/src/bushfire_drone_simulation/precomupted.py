"""File for storing precomputed values."""

from typing import Dict, List

import numpy as np

from bushfire_drone_simulation.fire_utils import Base, WaterTank
from bushfire_drone_simulation.lightning import Lightning


def create_distance_array(list1, list2):
    """Given 2 lists of locations, return a 2D distance array.

    The ith jth should contain the distance between the ith element from list1
    and the jth element from list2.
    """
    ret_array = np.empty((len(list1), len(list2)), float)
    for i, element1 in enumerate(list1):
        for j, element2 in enumerate(list2):
            ret_array[i][j] = element1.distance(element2)
    return ret_array


class PreComputedDistances:
    """Class for storing precomputed distances."""

    def __init__(
        self,
        lightning: List[Lightning],
        uav_bases: List[Base],
        water_bomber_bases_dict: Dict[str, Base],
        water_tanks: List[WaterTank],
    ):
        """Initialize precomputed distances."""
        self.to_ignition_id: Dict[int, int] = {}
        self.strike_to_strike_array = np.empty((len(lightning), len(lightning)), float)
        ignitions = np.array([])
        ignition_id = 0
        for i, strike in enumerate(lightning):
            if strike.ignition:
                ignitions = np.append(ignitions, strike)
                self.to_ignition_id[i] = ignition_id
                ignition_id += 1

        self.strike_to_base_array = create_distance_array(lightning, uav_bases)
        self.closest_uav_base_array = np.empty(len(lightning), int)
        for idx, strike in enumerate(lightning):
            self.closest_uav_base_array[idx] = np.argmin(self.strike_to_base_array[strike.id_no])

        self.closest_wb_base_array = np.empty(len(ignitions), int)
        for idx, strike in enumerate(ignitions):
            self.closest_uav_base_array[idx] = np.argmin(self.strike_to_base_array[strike.id_no])

        self.closest_wb_base_dict: Dict[str, np.ndarray] = {}
        self.ignition_to_base_dict: Dict[str, np.ndarray] = {}
        self.water_to_base_dict: Dict[str, np.ndarray] = {}
        for water_bomber_name in water_bomber_bases_dict:
            self.ignition_to_base_dict[water_bomber_name] = create_distance_array(
                ignitions, water_bomber_bases_dict[water_bomber_name]
            )
            self.water_to_base_dict[water_bomber_name] = create_distance_array(
                water_tanks, water_bomber_bases_dict[water_bomber_name]
            )
            self.closest_wb_base_dict[water_bomber_name] = np.empty(len(ignitions), int)
            for idx, strike in enumerate(ignitions):
                self.closest_wb_base_dict[water_bomber_name][idx] = np.argmin(
                    self.ignition_to_base_dict[water_bomber_name][self.to_ignition_id[strike.id_no]]
                )

        self.ignition_to_water_array = create_distance_array(ignitions, water_tanks)

    def closest_uav_base(self, lightning: Lightning) -> int:
        """Return the index of the closest UAV base to a given lightning strike."""
        return self.closest_uav_base_array[lightning.id_no]

    def closest_wb_base(self, ignition: Lightning, bomber_name: str) -> int:
        """Return the index of the closest water bomber base to a given ignition."""
        return self.closest_wb_base_dict[bomber_name][self.to_ignition_id[ignition.id_no]]

    def uav_dist(self, strike: Lightning, base: Base) -> float:
        """Return distance between a strike and uav base."""
        return self.strike_to_base_array[strike.id_no][base.id_no]

    def ignition_to_water(self, strike: Lightning, water_tank: WaterTank) -> float:
        """Return distance in km from given ignition to water tank."""
        return self.ignition_to_water_array[self.to_ignition_id[strike.id_no]][water_tank.id_no]

    def ignition_to_base(self, strike: Lightning, base: Base, bomber_name: str) -> float:
        """Return distance in km from given ignition to water bomber base."""
        return self.ignition_to_base_dict[bomber_name][self.to_ignition_id[strike.id_no]][
            base.id_no
        ]

    def water_to_base(self, water_tank: WaterTank, base: Base, bomber_name: str) -> float:
        """Return distance in km from given water tank to water bomber base."""
        return self.water_to_base_dict[bomber_name][water_tank.id_no][base.id_no]
