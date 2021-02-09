"""File for storing precomputed values."""

from typing import List

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
        water_bomber_bases: List[Base],
        water_tanks: List[WaterTank],
    ):
        """Initalise precomputed distances."""
        # Can delete, just for precommit
        self.water_bomber_bases = water_bomber_bases
        self.water_tanks = water_tanks
        # self.to_ignition_id: Dict[int, int] = {}
        # self.strike_to_strike_array = np.empty((len(lightning),len(lightning)), float)
        # ignition_id = 0
        # for i, strike in enumerate(lightning):
        #     if strike.ignition:
        #         ignitions = np.append(ignitions, strike)
        #         self.to_ignition_id[i] = ignition_id
        #         ignition_id += 1
        # for j in range(i + 1, len(lightning)):
        #     dist = strike.distance(lightning[j])
        #     self.strike_to_strike_array[i][j] = dist
        #     self.strike_to_strike_array[j][i] = dist

        self.strike_to_base_array = create_distance_array(lightning, uav_bases)
        self.closest_uav_base_array = np.empty(len(lightning), int)
        for idx, strike in enumerate(lightning):
            self.closest_uav_base_array[idx] = np.argmin(self.strike_to_base_array[strike.id_no])

        # self.ignition_to_base_array = create_distance_array(ignitions, water_bomber_bases)
        # self.ignition_to_water_array = create_distance_array(ignitions, water_tanks)
        # self.water_to_base_array = create_distance_array(water_tanks, water_bomber_bases)

    def uav_dist(self, loc1, loc2):
        """Return distance between two locations for a uav.

        If loc1 is instance of a Aircraft then if it is at a base or strike this can be specified
        if loc1_description as follows:
            "base" if the aircraft is at a uav Base
            "strike" if the aircraft is at Lightning
        """
        if isinstance(loc1, Base):
            assert isinstance(loc2, Lightning)
            return self.strike_to_base_array[loc2.id_no][loc1.id_no]
        assert isinstance(loc2, Base) and isinstance(loc1, Lightning)
        return self.strike_to_base_array[loc1.id_no][loc2.id_no]

    def closest_uav_base(self, lightning: Lightning) -> int:
        """Return the index of the closest UAV base to a given lightning strike."""
        return self.closest_uav_base_array[lightning.id_no]

    # def closest_wb_base(self, ignition: Lightning) -> int:
    #     """Return the index of the closest UAV base to a given ignition strike."""
    #     return np.argmin(self.ignition_to_base_array[ignition.id_no])

    # def wb_dist(self, loc1, loc2):
    #     """Return distance between two locations for a uav.

    #     If loc1 is instance of a Aircraft then if it is at a base or strike this can be specified
    #     if loc1_description as follows:
    #         "base" if the aircraft is at a uav Base
    #         "strike" if the aircraft is at Lightning
    #     """
    #     if isinstance(loc2, Base):
    #         if isinstance(loc1, Lightning):
    #             return self.ignition_to_base_array[self.to_ignition_id[loc1.id_no]][loc2.id_no]
    #         assert isinstance(loc1, WaterTank)
    #         return self.water_to_base_array[loc1.id_no][loc2.id_no]
    #     if isinstance(loc1, Base):
    #         if isinstance(loc2, Lightning):
    #             return self.ignition_to_base_array[self.to_ignition_id[loc2.id_no]][loc1.id_no]
    #         assert isinstance(loc2, WaterTank)
    #         return self.water_to_base_array[loc2.id_no][loc1.id_no]

    #     assert isinstance(loc1, Lightning) and isinstance(loc2, Lightning)
    #     assert False, "shouldn't be here"
    #     return -1

    # def strike_to_strike(self, strike_id1, strike_id2) -> float:
    #     """Return distance in km between two given strikes."""
    #     pass

    # def strike_to_uav_base(self, strike_id, base_id) -> float:
    #     """Return distance in km from given strike to uav base."""
    #     pass

    # def ignition_to_water(self, strike_id, water_tank_id) -> float:
    #     """Return distance in km from given ignition to water tank."""
    #     pass

    # def ignition_to_wb_base(self, strike_id, base_id) -> float:
    #     """Return distance in km from given ignition to water bomber base."""
    #     pass

    # def water_to_base(self, water_tank_id, base_id) -> float:
    #     """Return distance in km from given water tank to water bomber base."""
    #     pass
