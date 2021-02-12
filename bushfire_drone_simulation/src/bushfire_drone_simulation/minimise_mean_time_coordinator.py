"""Insertion coordinator minmising mean inspection/supression time.

This coordinator aims to minimise the mean inspection/supression time of the lightning strikes
by finding the place within each aircrafts list of locations to 'insert' a recent strike
to visit that minimises this value.
It does not consider also going via a base/water tank to facilitate 'inserting' this extra
strike and rather discounts the option if it does not possess enough fuel or water.

"""

import logging
from math import inf
from typing import List, Optional, Union

import numpy as np

from bushfire_drone_simulation.abstract_coordinator import UAVCoordinator, WBCoordinator
from bushfire_drone_simulation.aircraft import UAV, Event, WaterBomber
from bushfire_drone_simulation.fire_utils import Location
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.linked_list import Node

_LOG = logging.getLogger(__name__)


class MinimiseMeanTimeUAVCoordinator(UAVCoordinator):
    """Insertion UAV Coordinator.

    Coordinator will try to insert the new strike inbetween the uavs current tasks
    and minimise the new strikes inspection time.
    """

    def process_new_strike(  # pylint: disable=too-many-branches, too-many-statements
        self, lightning: Lightning
    ) -> None:
        """Receive lightning strike that just occurred and assign best uav."""
        if self.precomputed is None:
            base_index = np.argmin(list(map(lightning.distance, self.uav_bases)))
        else:
            base_index = self.precomputed.closest_uav_base(lightning)
        min_arrival_time: float = inf
        best_uav: Union[UAV, None] = None
        assigned_locations: List[Location] = []
        start_from: Optional[Union[Node[Event], str]] = None
        # The event from which to start going to assigned locations, str if delete all elements
        for uav in self.uavs:  # pylint: disable=too-many-nested-blocks
            # Go through the queue of every new strike and try inserting the new strike inbetween
            if not uav.event_queue.empty():
                lightning_event: List[Location] = [lightning]
                future_events: List[Location] = []
                base: List[Location] = []
                if isinstance(uav.event_queue.peak_first().position, Lightning):
                    if self.precomputed is None:
                        base = [
                            self.uav_bases[np.argmin(list(map(lightning.distance, self.uav_bases)))]
                        ]
                    else:
                        base = [self.uav_bases[self.precomputed.closest_uav_base(lightning)]]
                no_of_strikes_after_insertion: int = 0
                for event, prev_event in uav.event_queue:
                    future_events.insert(0, event.position)
                    if isinstance(event.position, Lightning):
                        no_of_strikes_after_insertion += 1
                    prev_arrival_time = event.completion_time
                    state = "self"
                    if prev_event is not None:
                        state = prev_event.value
                    enough_fuel = uav.enough_fuel(lightning_event + future_events + base, state)
                    if enough_fuel is not None:
                        new_strike_arr_time = uav.arrival_time([lightning], state)
                        old_strike_arr_time = uav.arrival_time([lightning, event.position], state)
                        cumulative_time = (
                            no_of_strikes_after_insertion
                            * (old_strike_arr_time - prev_arrival_time)
                            + new_strike_arr_time
                        )
                        if cumulative_time < min_arrival_time:
                            min_arrival_time = cumulative_time
                            assigned_locations = lightning_event + future_events
                            if prev_event is None:
                                start_from = "empty"
                            else:
                                start_from = prev_event
                            best_uav = uav

            # Check whether the UAV has enough fuel to
            # go to the lightning strike and then to the nearest base
            # and if so determine the arrival time at the lightning strike
            # updating if it is currently the minimum
            temp_arr_time = uav.enough_fuel([lightning, self.uav_bases[base_index]])
            if temp_arr_time is not None:
                temp_arr_time = uav.arrival_time([lightning])
                if temp_arr_time < min_arrival_time:
                    min_arrival_time = temp_arr_time
                    best_uav = uav
                    assigned_locations = [lightning]
                    start_from = None
            else:  # Need to go via a base to refuel
                for uav_base in self.uav_bases:
                    temp_arr_time = uav.enough_fuel(
                        [uav_base, lightning, self.uav_bases[base_index]]
                    )
                    if temp_arr_time is not None:
                        temp_arr_time = uav.arrival_time([uav_base, lightning])
                        if temp_arr_time < min_arrival_time:
                            min_arrival_time = temp_arr_time
                            best_uav = uav
                            assigned_locations = [uav_base, lightning]
                            start_from = None
        if best_uav is not None:
            _LOG.debug("Best UAV is: %s", best_uav.get_name())
            if start_from is not None:
                if isinstance(start_from, str):
                    best_uav.event_queue.clear()
                else:
                    best_uav.event_queue.delete_from(start_from)
            for location in assigned_locations:
                best_uav.add_location_to_queue(location, lightning.spawn_time)
        else:
            _LOG.error("No UAVs were available to process lightning strike %s", lightning.id_no)
        for uav in self.uavs:
            uav.go_to_base_when_necessary(self.uav_bases, lightning.spawn_time)


class MinimiseMeanTimeWBCoordinator(WBCoordinator):
    """Insertion water bomber coordinator.

    Coordinator will try to insert the new strike inbetween the uavs current tasks
    and minimise the new strikes inspection time.
    """

    def process_new_ignition(  # pylint: disable=too-many-branches, too-many-statements
        self, ignition: Lightning
    ) -> None:
        """Decide on water bombers movement with new ignition."""
        assert ignition.inspected_time is not None, "Error: Ignition was not inspected."
        min_arrival_time: float = inf
        best_water_bomber: Union[WaterBomber, None] = None
        assigned_locations: List[Location] = []
        start_from: Optional[Union[Node[Event], str]] = None
        for water_bomber in self.water_bombers:  # pylint: disable=too-many-nested-blocks
            bases = self.water_bomber_bases_dict[water_bomber.type]
            # Go through the queue of every new strike and try inserting the new strike inbetween
            if not water_bomber.event_queue.empty():
                ignition_event: List[Location] = [ignition]
                future_events: List[Location] = []
                final_strike_base: List[Location] = []
                if isinstance(water_bomber.event_queue.peak_first().position, Lightning):
                    if self.precomputed is None:
                        final_strike_base = [bases[np.argmin(list(map(ignition.distance, bases)))]]
                    else:
                        final_strike_base = [
                            bases[self.precomputed.closest_wb_base(ignition, water_bomber.type)]
                        ]
                no_of_strikes_after_insertion: int = 0
                for event, prev_event in water_bomber.event_queue:
                    if isinstance(event.position, Location):
                        no_of_strikes_after_insertion += 1
                    prev_arrival_time = event.completion_time
                    future_events.insert(0, event.position)
                    state = "self"
                    if prev_event is not None:
                        state = prev_event.value
                    if water_bomber.enough_water(ignition_event + future_events, state):
                        enough_fuel = water_bomber.enough_fuel(
                            ignition_event + future_events + final_strike_base, state
                        )
                        if enough_fuel is not None:
                            new_strike_arr_time = water_bomber.arrival_time([ignition], state)
                            old_strike_arr_time = water_bomber.arrival_time(
                                [ignition, event.position], state
                            )
                            cumulative_time = (
                                no_of_strikes_after_insertion
                                * (old_strike_arr_time - prev_arrival_time)
                                + new_strike_arr_time
                            )
                            if cumulative_time < min_arrival_time:
                                min_arrival_time = cumulative_time
                                assigned_locations = ignition_event + future_events
                                if prev_event is None:
                                    start_from = "empty"
                                else:
                                    start_from = prev_event
                                best_water_bomber = water_bomber

            if self.precomputed is None:
                base_index = np.argmin(list(map(ignition.distance, bases)))
            else:
                base_index = self.precomputed.closest_wb_base(ignition, water_bomber.get_type())
            if water_bomber.enough_water([ignition]):
                temp_arr_time = water_bomber.enough_fuel([ignition, bases[base_index]])
                if temp_arr_time is not None:
                    temp_arr_time = water_bomber.arrival_time([ignition])
                    if temp_arr_time < min_arrival_time:
                        min_arrival_time = temp_arr_time
                        best_water_bomber = water_bomber
                        assigned_locations = [ignition]
                        start_from = None
                else:  # Need to refuel
                    _LOG.debug("%s needs to refuel", water_bomber.get_name())
                    for base in bases:
                        temp_arr_time = water_bomber.enough_fuel(
                            [base, ignition, bases[base_index]]
                        )
                        if temp_arr_time is not None:
                            temp_arr_time = water_bomber.arrival_time([base, ignition])
                            if temp_arr_time < min_arrival_time:
                                min_arrival_time = temp_arr_time
                                best_water_bomber = water_bomber
                                assigned_locations = [base, ignition]
                                start_from = None

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
                        temp_arr_time = water_bomber.arrival_time([water_tank, ignition])
                        if temp_arr_time < min_arrival_time:
                            min_arrival_time = temp_arr_time
                            best_water_bomber = water_bomber
                            assigned_locations = [water_tank, ignition]
                            go_via_base = False
                            start_from = None
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
                                temp_arr_time = water_bomber.arrival_time(
                                    [water_tank, base, ignition]
                                )
                                if temp_arr_time < min_arrival_time:
                                    min_arrival_time = temp_arr_time
                                    best_water_bomber = water_bomber
                                    assigned_locations = [water_tank, base, ignition]
                                    start_from = None
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
                                temp_arr_time = water_bomber.arrival_time(
                                    [base, water_tank, ignition]
                                )
                                if temp_arr_time < min_arrival_time:
                                    min_arrival_time = temp_arr_time
                                    best_water_bomber = water_bomber
                                    assigned_locations = [base, water_tank, ignition]
                                    start_from = None
        if best_water_bomber is not None:
            _LOG.debug("Best water bomber is: %s", best_water_bomber.get_name())
            if start_from is not None:
                if isinstance(start_from, str):
                    best_water_bomber.event_queue.clear()
                else:
                    best_water_bomber.event_queue.delete_from(start_from)
            for location in assigned_locations:
                best_water_bomber.add_location_to_queue(location, ignition.inspected_time)

        else:
            _LOG.error("No water bombers were available")
        for water_bomber in self.water_bombers:
            bases = self.water_bomber_bases_dict[water_bomber.type]
            water_bomber.go_to_base_when_necessary(bases, ignition.inspected_time)

    def process_new_strike(self, lightning) -> None:
        """Decide on uavs movement with new strike."""
