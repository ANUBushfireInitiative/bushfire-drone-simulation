"""Module for the centralized coordinator/HQ controlling the UAVs and aircraft."""

import logging
from queue import Queue
from typing import Union

import numpy as np

from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.fire_utils import Base, Time, WaterTank
from bushfire_drone_simulation.lightning import Lightning

_LOG = logging.getLogger(__name__)


class CoordinatorParamaters:  # pylint: disable=too-few-public-methods
    """Parameters for Coordinator.

    TODO: Actually use in Coordinator below
    """

    uav_bases = None
    uavs = None
    water_bombers = None
    water_bomber_bases = None
    water_tanks = None


class Coordinator:
    """Class for centrally coordinating UAVs and water bombers."""

    events: Queue = Queue()

    def __init__(
        self, uavs, uav_bases, water_bombers, water_bomber_bases_dict, water_tanks
    ):  # pylint: disable=too-many-arguments
        """Initialize coordinator."""
        self.uavs = uavs
        self.uav_bases = uav_bases
        self.water_bombers = water_bombers
        self.water_bomber_bases_dict = water_bomber_bases_dict
        self.water_tanks = water_tanks

    def get_next_event_time(self):
        """Return next event time."""
        if not self.events.empty():
            return self.events.queue[0]
        return None

    def lightning_update(self, lightning: Lightning):  # pylint: disable=too-many-branches
        """Coordinator receives lightning strike that just occurred."""
        # If lightning None then process next update, otherwise process lightning strike
        # Determine nearest base to lightning strike
        base_index = np.argmin(list(map(lightning.distance, self.uav_bases)))
        min_arrival_time = Time("inf")
        best_uav = None
        via_base = None
        for uav in self.uavs:
            # Check whether the UAV has enough fuel to
            # go to the lightning strike and then to the nearest base
            # and if so determine the arrival time at the lightning strike
            # updating if it is currently the minimum
            if uav.enough_fuel([lightning, self.uav_bases[base_index]], lightning.spawn_time):
                temp_arr_time = uav.arrival_time([lightning], lightning.spawn_time)
                if temp_arr_time < min_arrival_time:
                    min_arrival_time = temp_arr_time
                    best_uav = uav
            # Need to go via a base to refuel
            else:
                for uav_base in self.uav_bases:
                    if uav.enough_fuel(
                        [uav_base, lightning, self.uav_bases[base_index]],
                        lightning.spawn_time,
                    ):
                        temp_arr_time = uav.arrival_time(
                            [uav_base, lightning], lightning.spawn_time
                        )
                        if temp_arr_time < min_arrival_time:
                            min_arrival_time = temp_arr_time
                            best_uav = uav
                            via_base = uav_base
        if best_uav is not None:
            _LOG.debug("Best UAV is: %s", best_uav.id_no)
            _LOG.debug(
                "Which took %s mins to respond",
                (min_arrival_time - lightning.spawn_time).get("min"),
            )
            if via_base is not None:
                # The minimum arrival time was achieved by travelling via a base
                # Update UAV position accordingly
                best_uav.go_to_base(via_base, lightning.spawn_time)
            # There exists a UAV that has enough fuel, send it to the lightning strike
            # if best_uav.id_no == 34:
            #     print("accoring to C: " + str(best_uav.current_fuel_capacity))
            best_uav.go_to_strike(lightning, lightning.spawn_time)
            best_uav.print_past_locations()
        else:
            # There are no UAVs that can reach the lightning strike without refueling
            # Try going via a base to refuel
            _LOG.error("No UAVs were available")

        for uav in self.uavs:
            uav.consider_going_to_base(self.uav_bases, lightning.spawn_time)

    def ignition_update(
        self, ignition: Lightning
    ):  # pylint: disable=too-many-branches, too-many-statements
        """Coordinator receives ignition strike that just occurred."""
        assert ignition.inspected_time is not None, "Error: Ignition was not inspected."
        min_arrival_time = Time("inf")
        best_water_bomber: Union[WaterBomber, None] = None
        via_water: Union[WaterTank, None] = None
        via_base: Union[Base, None] = None
        fuel_first: Union[bool, None] = None
        for water_bomber in self.water_bombers:  # pylint: disable=too-many-nested-blocks
            water_bomber_bases = self.water_bomber_bases_dict[water_bomber.type]
            base_index = np.argmin(list(map(ignition.distance, water_bomber_bases)))
            if water_bomber.enough_water():
                if water_bomber.enough_fuel(
                    [ignition, water_bomber_bases[base_index]],
                    ignition.inspected_time,
                ):
                    temp_arr_time = water_bomber.arrival_time([ignition], ignition.inspected_time)
                    if temp_arr_time < min_arrival_time:
                        min_arrival_time = temp_arr_time
                        best_water_bomber = water_bomber
                        via_base = None
                        via_water = None
                        fuel_first = None
                else:  # Need to refuel
                    _LOG.debug("Water bomber %s needs to refuel", water_bomber.id_no)
                    for base in water_bomber_bases:
                        if water_bomber.enough_fuel(
                            [base, ignition, water_bomber_bases[base_index]],
                            ignition.inspected_time,
                        ):
                            temp_arr_time = water_bomber.arrival_time(
                                [base, ignition], ignition.inspected_time
                            )
                            if temp_arr_time < min_arrival_time:
                                min_arrival_time = temp_arr_time
                                best_water_bomber = water_bomber
                                via_base = base
                                via_water = None
                                fuel_first = None

            else:
                # Need to go via a water tank
                # (assuming if we go via a water tank we have enough water)
                _LOG.debug("Water bomber %s needs to go via a water tank", water_bomber.id_no)
                for water_tank in self.water_tanks:
                    if water_bomber.check_water_tank(water_tank) and water_bomber.enough_fuel(
                        [water_tank, ignition, water_bomber_bases[base_index]],
                        ignition.inspected_time,
                    ):
                        temp_arr_time = water_bomber.arrival_time(
                            [water_tank, ignition], ignition.inspected_time
                        )
                        if temp_arr_time < min_arrival_time:
                            min_arrival_time = temp_arr_time
                            best_water_bomber = water_bomber
                            via_water = water_tank
                            via_base = None
                            fuel_first = None
                if via_water is None:
                    # Need to also refuel
                    for water_tank in self.water_tanks:
                        for base in water_bomber_bases:
                            if water_bomber.check_water_tank(
                                water_tank
                            ) and water_bomber.enough_fuel(
                                [
                                    water_tank,
                                    base,
                                    ignition,
                                    water_bomber_bases[base_index],
                                ],
                                ignition.inspected_time,
                            ):
                                temp_arr_time = water_bomber.arrival_time(
                                    [water_tank, base, ignition],
                                    ignition.inspected_time,
                                )
                                if temp_arr_time < min_arrival_time:
                                    min_arrival_time = temp_arr_time
                                    best_water_bomber = water_bomber
                                    via_water = water_tank
                                    via_base = base
                                    fuel_first = False
                            if water_bomber.check_water_tank(
                                water_tank
                            ) and water_bomber.enough_fuel(
                                [
                                    base,
                                    water_tank,
                                    ignition,
                                    water_bomber_bases[base_index],
                                ],
                                ignition.inspected_time,
                            ):
                                temp_arr_time = water_bomber.arrival_time(
                                    [base, water_tank, ignition],
                                    ignition.inspected_time,
                                )
                                if temp_arr_time < min_arrival_time:
                                    min_arrival_time = temp_arr_time
                                    best_water_bomber = water_bomber
                                    via_water = water_tank
                                    via_base = base
                                    fuel_first = True

        if best_water_bomber is not None:
            _LOG.debug("Best water bomber is: %s", best_water_bomber.id_no)
            _LOG.debug(
                "Which took %s mins to respond",
                (min_arrival_time - ignition.inspected_time).get("min"),
            )
            if fuel_first is not None:
                assert via_base is not None, "Error: Base not provided despite requiring refueling."
                assert (
                    via_water is not None
                ), "Error: Water tank not provided despite requiring refilling."
                if fuel_first:
                    best_water_bomber.go_to_base(via_base, ignition.inspected_time)
                    best_water_bomber.go_to_water(via_water, ignition.inspected_time)
                else:
                    best_water_bomber.go_to_water(via_water, ignition.inspected_time)
                    best_water_bomber.go_to_base(via_base, ignition.inspected_time)
            elif via_base is not None:
                best_water_bomber.go_to_base(via_base, ignition.inspected_time)
            elif via_water is not None:
                best_water_bomber.go_to_water(via_water, ignition.inspected_time)
            best_water_bomber.go_to_strike(ignition, ignition.inspected_time)
            best_water_bomber.print_past_locations()
        else:
            _LOG.error("No water bombers were available")
        for water_bomber in self.water_bombers:
            water_bomber_bases = self.water_bomber_bases_dict[water_bomber.type]
            water_bomber.consider_going_to_base(water_bomber_bases, ignition.inspected_time)


class Event:
    """Class for storing events."""

    time: Time
    uav: UAV

    def __init__(self, time: Time, uav: UAV):
        """Initialize Event."""
        self.time = time
        self.uav = uav

    def get_time(self):
        """Return time of event."""
        return self.time

    def get_uav(self):
        """Return uav of event."""
        return self.uav
