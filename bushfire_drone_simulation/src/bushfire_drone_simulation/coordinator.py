"""Module for the centralized coordinator/HQ controlling the UAVs and aircraft."""

import logging
import queue

from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.fire_utils import Time, minimum
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.units import Distance

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

    uav_bases = None
    uavs = None
    water_bombers = None
    water_bomber_bases = None
    water_tanks = None
    events = queue.Queue(maxsize=0)

    def __init__(
        self, uavs, uav_bases, water_bombers, water_bomber_bases, water_tanks
    ):  # pylint: disable=too-many-arguments
        """Initialize coordinator."""
        self.uav_bases = uav_bases
        self.uavs = uavs
        self.water_bombers = water_bombers
        self.water_bomber_bases = water_bomber_bases
        self.water_tanks = water_tanks

    def get_next_event_time(self):
        """Return next event time."""
        if not self.events.empty():
            return self.events.queue[0]
        return None

    def lightning_update(self, lightning: Lightning = None):
        """Coordinator receives lightning strike that just occured."""
        # If lightning None then process next update, otherwise process lightning strike
        if lightning is None:
            self.events.get().get_uav.complete_update()
        else:
            # Determine nearest base to lightning strike
            base_index, _ = minimum(self.uav_bases, Distance(1000000), lightning.position.distance)
            min_arrival_time = Time("9999/99/99/99/99/99")
            best_uav = None
            via_base = None
            for uav in self.uavs:
                # Check whether the UAV has enough fuel to
                # go to the lightning strike and then to the nearest base
                # and if so determine the arrival time at the lightning strike
                # updating if it is currently the minimum
                if uav.enough_fuel(
                    [lightning.position, self.uav_bases[base_index]], lightning.spawn_time
                ):
                    temp_arr_time = uav.arrival_time([lightning.position], lightning.spawn_time)
                    if temp_arr_time < min_arrival_time:
                        min_arrival_time = temp_arr_time
                        best_uav = uav
                # Via a base to refuel
                for uav_base in self.uav_bases:
                    if uav.enough_fuel(
                        [uav_base, lightning.position, self.uav_bases[base_index]],
                        lightning.spawn_time,
                    ):
                        temp_arr_time = uav.arrival_time(
                            [uav_base, lightning.position], lightning.spawn_time
                        )
                        if temp_arr_time < min_arrival_time:
                            min_arrival_time = temp_arr_time
                            best_uav = uav
                            via_base = uav_base
            if best_uav is not None:
                _LOG.info("Best UAV is: %s", best_uav.id_no)
                _LOG.info(
                    "Which took %s mins to respond",
                    (min_arrival_time - lightning.spawn_time).get("min"),
                )
                if via_base is not None:
                    # The minimum arrival time was achieved by travelling via a base
                    # Update UAV position accordingly
                    best_uav.go_to_base(via_base, lightning.spawn_time)
                # There exists a UAV that has enough fuel, send it to the lightning strike
                best_uav.go_to_strike(lightning, lightning.spawn_time, min_arrival_time)
            else:
                # There are no UVAs that can reach the lighnting strike without refuling
                # Try going via a base to refuel
                _LOG.error("No UAVs were available")

        for uav in self.uavs:
            uav.consider_going_to_base(self.uav_bases, lightning.spawn_time)

    def ignition_update(
        self, ignition: Lightning = None
    ):  # pylint: disable=too-many-branches, too-many-statements
        """Coordinator receives ignition strike that just occured."""
        # If lightning None then process next update, otherwise process lightning strike
        if ignition is None:  # pylint: disable=too-many-nested-blocks
            self.events.get().get_uav.complete_update()
        else:
            base_index, _ = minimum(
                self.water_bomber_bases, Distance(1000000), ignition.position.distance
            )
            min_arrival_time = Time("9999/99/99/99/99/99")
            best_water_bomber: WaterBomber = None
            via_water: int = None
            via_base: int = None
            fuel_first: bool = None
            for water_bomber in self.water_bombers:
                if water_bomber.enough_water():
                    if water_bomber.enough_fuel(
                        [ignition.position, self.water_bomber_bases[base_index]],
                        ignition.spawn_time,
                    ):
                        temp_arr_time = water_bomber.arrival_time(
                            [ignition.position], ignition.spawn_time
                        )
                        if temp_arr_time < min_arrival_time:
                            min_arrival_time = temp_arr_time
                            best_water_bomber = water_bomber
                    else:  # Need to refuel
                        for base in self.water_bomber_bases:
                            if water_bomber.enough_fuel(
                                [base, ignition.position, self.water_bomber_bases[base_index]]
                            ):
                                temp_arr_time = water_bomber.arrival_time(
                                    [base, ignition.position], ignition.spawn_time
                                )
                                if temp_arr_time < min_arrival_time:
                                    min_arrival_time = temp_arr_time
                                    best_water_bomber = water_bomber
                                    via_base = base

                else:
                    # self.not_enough_water(
                    #     water_bomber,
                    #     best_water_bomber,
                    #     min_arrival_time,
                    #     via_base,
                    #     ignition,
                    #     base_index,
                    # )
                    # Need to go via a water tank
                    # (assuming if we go via a water tank we have enough water)
                    _LOG.info("Water bomber %s needs to go via a water tank", water_bomber.id_no)
                    for water_tank in self.water_tanks:
                        if water_bomber.enough_fuel(
                            [water_tank, ignition.position, self.water_bomber_bases[base_index]],
                            ignition.spawn_time,
                        ):
                            temp_arr_time = water_bomber.arrival_time(
                                [water_tank, ignition.position], ignition.spawn_time
                            )
                            if temp_arr_time < min_arrival_time:
                                min_arrival_time = temp_arr_time
                                best_water_bomber = water_bomber
                                via_water = water_tank
                    if via_water is None:
                        # Need to also refuel
                        for water_tank in self.water_tanks:
                            for base in self.water_bomber_bases:
                                if water_bomber.enough_fuel(
                                    [
                                        water_tank,
                                        base,
                                        ignition.position,
                                        self.water_bomber_bases[base_index],
                                    ],
                                    ignition.spawn_time,
                                ):
                                    temp_arr_time = water_bomber.arrival_time(
                                        [water_tank, base, ignition.position], ignition.spawn_time
                                    )
                                    if temp_arr_time < min_arrival_time:
                                        min_arrival_time = temp_arr_time
                                        best_water_bomber = water_bomber
                                        via_water = water_tank
                                        via_base = base
                                        fuel_first = False
                                if water_bomber.enough_fuel(
                                    [
                                        base,
                                        water_tank,
                                        ignition.position,
                                        self.water_bomber_bases[base_index],
                                    ],
                                    ignition.spawn_time,
                                ):
                                    temp_arr_time = water_bomber.arrival_time(
                                        [base, water_tank, ignition.position], ignition.spawn_time
                                    )
                                    if temp_arr_time < min_arrival_time:
                                        min_arrival_time = temp_arr_time
                                        best_water_bomber = water_bomber
                                        via_water = water_tank
                                        via_base = base
                                        fuel_first = True

            if best_water_bomber is not None:
                _LOG.info("Best water bomber is: %s", best_water_bomber.id_no)
                _LOG.info(
                    "Which took %s mins to respond",
                    (min_arrival_time - ignition.spawn_time).get("min"),
                )
                if fuel_first is not None:
                    if fuel_first:
                        best_water_bomber.go_to_base(via_base, ignition.spawn_time)
                        best_water_bomber.go_to_water(via_water, ignition.spawn_time)
                    else:
                        best_water_bomber.go_to_water(via_water, ignition.spawn_time)
                        best_water_bomber.go_to_base(via_base, ignition.spawn_time)
                elif via_water is not None:
                    best_water_bomber.go_to_water(via_water, ignition.spawn_time)
                elif via_base is not None:
                    best_water_bomber.go_to_base(via_base, ignition.spawn_time)
                best_water_bomber.go_to_strike(ignition, ignition.spawn_time, min_arrival_time)
            else:
                _LOG.error("No water bomber were available")
        for water_bomber in self.water_bombers:
            water_bomber.consider_going_to_base(self.water_bomber_bases, ignition.spawn_time)

    def go_via_base(
        self, water_bomber, ignition, base_index, best_water_bomber, via_base, min_arrival_time
    ):  # pylint: disable=too-many-arguments
        """Via base."""
        for base in self.water_bomber_bases:
            if water_bomber.enough_fuel(
                [base, ignition.position, self.water_bomber_bases[base_index]], ignition.spawn_time
            ):
                temp_arr_time = water_bomber.arrival_time(
                    [base, ignition.position], ignition.spawn_time
                )
                if temp_arr_time < min_arrival_time:
                    min_arrival_time = temp_arr_time
                    best_water_bomber = water_bomber
                    via_base = base
        return min_arrival_time, best_water_bomber, via_base

    def not_enough_water(
        self, water_bomber, best_water_bomber, min_arrival_time, via_base, ignition, base_index
    ):  # pylint: disable=too-many-arguments
        """Return optimal path to ignition site given a water bomber who needs to refill water."""
        via_water: int = None
        fuel_first: bool = None
        # Need to go via a water tank
        # (assuming if we go via a water tank we have enough water)
        _LOG.info("Water bomber %s needs to go via a water tank", water_bomber.id_no)
        for water_tank in self.water_tanks:
            if water_bomber.enough_fuel(
                [water_tank, ignition.position, self.water_bomber_bases[base_index]],
                ignition.spawn_time,
            ):
                temp_arr_time = water_bomber.arrival_time(
                    [water_tank, ignition.position], ignition.spawn_time
                )
                if temp_arr_time < min_arrival_time:
                    min_arrival_time = temp_arr_time
                    best_water_bomber = water_bomber
                    via_water = water_tank
        if via_water is None:
            # Need to also refuel
            for water_tank in self.water_tanks:
                for base in self.water_bomber_bases:
                    if water_bomber.enough_fuel(
                        [
                            water_tank,
                            base,
                            ignition.position,
                            self.water_bomber_bases[base_index],
                        ],
                        ignition.spawn_time,
                    ):
                        temp_arr_time = water_bomber.arrival_time(
                            [water_tank, base, ignition.position], ignition.spawn_time
                        )
                        if temp_arr_time < min_arrival_time:
                            min_arrival_time = temp_arr_time
                            best_water_bomber = water_bomber
                            via_water = water_tank
                            via_base = base
                            fuel_first = False
                    if water_bomber.enough_fuel(
                        [
                            base,
                            water_tank,
                            ignition.position,
                            self.water_bomber_bases[base_index],
                        ],
                        ignition.spawn_time,
                    ):
                        temp_arr_time = water_bomber.arrival_time(
                            [base, water_tank, ignition.position], ignition.spawn_time
                        )
                        if temp_arr_time < min_arrival_time:
                            min_arrival_time = temp_arr_time
                            best_water_bomber = water_bomber
                            via_water = water_tank
                            via_base = base
                            fuel_first = True
        return min_arrival_time, best_water_bomber, via_water, via_base, fuel_first


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
