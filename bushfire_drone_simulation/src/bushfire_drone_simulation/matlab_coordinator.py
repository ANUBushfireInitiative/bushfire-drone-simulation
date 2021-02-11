"""Simple coordinator."""

import logging
from math import inf
from typing import List, Union

import numpy as np

from bushfire_drone_simulation.abstract_coordinator import UAVCoordinator, WBCoordinator
from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.fire_utils import Location
from bushfire_drone_simulation.lightning import Lightning

_LOG = logging.getLogger(__name__)


class MatlabUAVCoordinator(UAVCoordinator):
    """Matlab UAV Coordinator."""

    def process_new_strike(self, lightning: Lightning) -> None:  # pylint: disable=too-many-branches
        """Receive lightning strike that just occurred and assign best uav."""
        if self.precomputed is None:
            base_index = np.argmin(list(map(lightning.distance, self.uav_bases)))
        else:
            base_index = self.precomputed.closest_uav_base(lightning)
        min_arrival_time: float = inf
        best_uav: Union[UAV, None] = None
        assigned_locations: List[Location] = []
        for uav in self.uavs:
            # Check whether the UAV has enough fuel to
            # go to the lightning strike and then to the nearest base
            # and if so determine the arrival time at the lightning strike
            # updating if it is currently the minimum
            temp_arr_time = uav.enough_fuel([lightning, self.uav_bases[base_index]])
            if temp_arr_time is not None:
                if temp_arr_time < min_arrival_time:
                    min_arrival_time = temp_arr_time
                    best_uav = uav
                    assigned_locations = [lightning]
            # Need to go via a base to refuel
            else:
                for uav_base in self.uav_bases:
                    temp_arr_time = uav.enough_fuel(
                        [uav_base, lightning, self.uav_bases[base_index]]
                    )
                    if temp_arr_time is not None:
                        if temp_arr_time < min_arrival_time:
                            min_arrival_time = temp_arr_time
                            best_uav = uav
                            assigned_locations = [uav_base, lightning]
        if best_uav is not None:
            _LOG.debug("Best UAV is: %s", best_uav.get_name())
            for location in assigned_locations:
                best_uav.add_location_to_queue(location, lightning.spawn_time)
            # if via_base is not None:
            #     # The minimum arrival time was achieved by travelling via a base
            #     # Update UAV position accordingly
            #     best_uav.add_location_to_queue(via_base, lightning.spawn_time)
            # # There exists a UAV that has enough fuel, send it to the lightning strike
            # best_uav.add_location_to_queue(lightning, lightning.spawn_time)
        else:
            _LOG.error("No UAVs were available to process lightning strike %s", lightning.id_no)
        for uav in self.uavs:
            uav.go_to_base_when_necessary(self.uav_bases, lightning.spawn_time)


class MatlabWBCoordinator(WBCoordinator):
    """Matlab water bomber coordinator."""

    def process_new_ignition(  # pylint: disable=too-many-branches, too-many-statements
        self, ignition: Lightning
    ) -> None:
        """Decide on water bombers movement with new ignition."""
        assert ignition.inspected_time is not None, "Error: Ignition was not inspected."
        min_arrival_time: float = inf
        best_water_bomber: Union[WaterBomber, None] = None
        assigned_locations: List[Location] = []
        for water_bomber in self.water_bombers:  # pylint: disable=too-many-nested-blocks
            bases = self.water_bomber_bases_dict[water_bomber.type]
            if self.precomputed is None:
                base_index = np.argmin(list(map(ignition.distance, bases)))
            else:
                base_index = self.precomputed.closest_wb_base(ignition, water_bomber.get_type())
            if water_bomber.enough_water([ignition]):
                temp_arr_time = water_bomber.enough_fuel([ignition, bases[base_index]])
                if temp_arr_time is not None:
                    # temp_arr_time = water_bomber.arrival_time([ignition], ignition.inspected_time)
                    if temp_arr_time < min_arrival_time:
                        min_arrival_time = temp_arr_time
                        best_water_bomber = water_bomber
                        assigned_locations = [ignition]
                else:  # Need to refuel
                    _LOG.debug("%s needs to refuel", water_bomber.get_name())
                    for base in bases:
                        temp_arr_time = water_bomber.enough_fuel(
                            [base, ignition, bases[base_index]]
                        )
                        if temp_arr_time is not None:
                            if temp_arr_time < min_arrival_time:
                                min_arrival_time = temp_arr_time
                                best_water_bomber = water_bomber
                                assigned_locations = [base, ignition]

            else:
                # Need to go via a water tank
                # (assuming if we go via a water tank we have enough water)
                _LOG.debug("%s needs to go via a water tank", water_bomber.get_name())
                go_via_base = True
                for water_tank in self.water_tanks:
                    temp_arr_time = water_bomber.enough_fuel(
                        [water_tank, ignition, bases[base_index]]
                    )
                    if water_bomber.check_water_tank(water_tank) and temp_arr_time is not None:
                        if temp_arr_time < min_arrival_time:
                            min_arrival_time = temp_arr_time
                            best_water_bomber = water_bomber
                            assigned_locations = [water_tank, ignition]
                            go_via_base = False
                if go_via_base:
                    for water_tank in self.water_tanks:
                        for base in bases:
                            temp_arr_time = water_bomber.enough_fuel(
                                [
                                    water_tank,
                                    base,
                                    ignition,
                                    bases[base_index],
                                ]
                            )
                            if (
                                water_bomber.check_water_tank(water_tank)
                                and temp_arr_time is not None
                            ):
                                if temp_arr_time < min_arrival_time:
                                    min_arrival_time = temp_arr_time
                                    best_water_bomber = water_bomber
                                    assigned_locations = [water_tank, base, ignition]
                            temp_arr_time = water_bomber.enough_fuel(
                                [
                                    base,
                                    water_tank,
                                    ignition,
                                    bases[base_index],
                                ]
                            )
                            if (
                                water_bomber.check_water_tank(water_tank)
                                and temp_arr_time is not None
                            ):
                                if temp_arr_time < min_arrival_time:
                                    min_arrival_time = temp_arr_time
                                    best_water_bomber = water_bomber
                                    assigned_locations = [base, water_tank, ignition]
        if best_water_bomber is not None:
            _LOG.debug("Best water bomber is: %s", best_water_bomber.get_name())
            for location in assigned_locations:
                best_water_bomber.add_location_to_queue(location, ignition.inspected_time)

        else:
            _LOG.error("No water bombers were available")
        for water_bomber in self.water_bombers:
            bases = self.water_bomber_bases_dict[water_bomber.type]
            water_bomber.go_to_base_when_necessary(bases, ignition.inspected_time)

    def process_new_strike(self, lightning) -> None:
        """Decide on uavs movement with new strike."""
