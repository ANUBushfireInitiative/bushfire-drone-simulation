"""Insertion coordinator.

This coordinator aims to minimise the inspection/supression time of the most recent strike
by finding the place within each aircrafts list of locations to 'insert' this strike to
minimizes the inspection/supression time.
It does not consider also going via a base/water tank to facilitate 'inserting' this extra
strike and rather discounts the option if it does not possess enough fuel or water.
"""

import logging
from math import inf
from typing import List, Optional, Union

import numpy as np

from bushfire_drone_simulation.aircraft import UAV, Event, WaterBomber
from bushfire_drone_simulation.coordinators.abstract_coordinator import (
    UAVCoordinator,
    WBCoordinator,
)
from bushfire_drone_simulation.fire_utils import Base, Location
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.linked_list import Node

_LOG = logging.getLogger(__name__)


class InsertionUAVCoordinator(UAVCoordinator):
    """Insertion UAV Coordinator.

    Coordinator will try to insert the new strike in between the uavs current tasks
    and minimise the new strikes inspection time.
    """

    def process_new_strike(  # pylint: disable=too-many-branches, too-many-statements
        self, lightning: Lightning
    ) -> None:
        """Receive lightning strike that just occurred and assign best uav."""
        if self.precomputed is None:
            base_index = int(np.argmin(list(map(lightning.distance, self.uav_bases))))
        else:
            base_index = self.precomputed.closest_uav_base(lightning)
        min_arrival_time: float = inf
        best_uav: Union[UAV, None] = None
        assigned_locations: List[Location] = []
        start_from: Optional[Union[Node[Event], str]] = None
        # The event from which to start going to assigned locations, str if delete all elements
        for uav in self.uavs:  # pylint: disable=too-many-nested-blocks
            # Go through the queue of every new strike and try inserting the new strike in between
            if not uav.event_queue.is_empty():
                lightning_event: List[Location] = [lightning]
                future_events: List[Location] = []
                base: List[Location] = []
                last_event_position = uav.event_queue.peak_last().position
                if isinstance(last_event_position, Lightning):
                    if self.precomputed is None:
                        base = [
                            self.uav_bases[
                                int(
                                    np.argmin(
                                        list(map(last_event_position.distance, self.uav_bases))
                                    )
                                )
                            ]
                        ]
                    else:
                        base = [
                            self.uav_bases[self.precomputed.closest_uav_base(last_event_position)]
                        ]

                for event, prev_event in uav.event_queue.iterate_backwards():
                    assert isinstance(
                        event, Event
                    ), f"{uav.get_name()}s event queue contained a non event"
                    future_events.insert(0, event.position)
                    if prev_event is None:  # no more events in queue, use aircraft current state
                        temp_arr_time = uav.enough_fuel(
                            lightning_event + future_events + base,
                            self.prioritisation_function,
                            "self",
                        )
                    else:
                        assert isinstance(
                            prev_event.value, Event
                        ), f"{uav.get_name()}s event queue contained a non event"
                        temp_arr_time = uav.enough_fuel(
                            lightning_event + future_events + base,
                            self.prioritisation_function,
                            prev_event.value,
                        )
                    if temp_arr_time is not None:
                        if temp_arr_time < min_arrival_time:
                            min_arrival_time = temp_arr_time
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
            temp_arr_time = uav.enough_fuel(
                [lightning, self.uav_bases[base_index]], self.prioritisation_function
            )
            if temp_arr_time is not None:
                if temp_arr_time < min_arrival_time:
                    min_arrival_time = temp_arr_time
                    best_uav = uav
                    assigned_locations = [lightning]
                    start_from = None
            else:  # Need to go via a base to refuel
                for uav_base in self.uav_bases:
                    temp_arr_time = uav.enough_fuel(
                        [uav_base, lightning, self.uav_bases[base_index]],
                        self.prioritisation_function,
                    )
                    if temp_arr_time is not None:
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
                    best_uav.event_queue.delete_after(start_from)
            for location in assigned_locations:
                best_uav.add_location_to_queue(location, lightning.spawn_time)
        else:
            _LOG.error("No UAVs were available to process lightning strike %s", lightning.id_no)
        for uav in self.uavs:
            uav.go_to_base_when_necessary(self.uav_bases, lightning.spawn_time)


class InsertionWBCoordinator(WBCoordinator):
    """Insertion water bomber coordinator.

    Coordinator will try to insert the new strike in between the uavs current tasks
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
            # Go through the queue of every new strike and try inserting the new strike in between
            if not water_bomber.event_queue.is_empty():
                ignition_event: List[Location] = [ignition]
                future_events: List[Location] = []
                closest_base_to_last_event: List[Location] = []
                last_event_position = water_bomber.event_queue.peak_last().position
                if not isinstance(last_event_position, Base):
                    if self.precomputed is None or not isinstance(last_event_position, Lightning):
                        closest_base_to_last_event = [
                            bases[int(np.argmin(list(map(last_event_position.distance, bases))))]
                        ]
                    else:
                        closest_base_to_last_event = [
                            bases[
                                self.precomputed.closest_wb_base(
                                    last_event_position, water_bomber.type
                                )
                            ]
                        ]
                for event, prev_event in water_bomber.event_queue.iterate_backwards():
                    future_events.insert(0, event.position)
                    temp_arr_time = None
                    if prev_event is None:  # no more events in queue, use aircraft current state
                        if water_bomber.enough_water(ignition_event + future_events, "self"):
                            temp_arr_time = water_bomber.enough_fuel(
                                ignition_event + future_events + closest_base_to_last_event,
                                self.prioritisation_function,
                                "self",
                            )
                    else:
                        if water_bomber.enough_water(
                            ignition_event + future_events, prev_event.value
                        ):
                            temp_arr_time = water_bomber.enough_fuel(
                                ignition_event + future_events + closest_base_to_last_event,
                                self.prioritisation_function,
                                prev_event.value,
                            )
                    if temp_arr_time is not None:
                        if temp_arr_time < min_arrival_time:
                            min_arrival_time = temp_arr_time
                            assigned_locations = ignition_event + future_events
                            if prev_event is None:
                                start_from = "empty"
                            else:
                                start_from = prev_event
                            best_water_bomber = water_bomber

            if self.precomputed is None:
                base_index = int(np.argmin(list(map(ignition.distance, bases))))
            else:
                base_index = self.precomputed.closest_wb_base(ignition, water_bomber.get_type())
            if water_bomber.enough_water([ignition]):
                temp_arr_time = water_bomber.enough_fuel(
                    [ignition, bases[base_index]], self.prioritisation_function
                )
                if temp_arr_time is not None:
                    if temp_arr_time < min_arrival_time:
                        min_arrival_time = temp_arr_time
                        best_water_bomber = water_bomber
                        assigned_locations = [ignition]
                        start_from = None
                else:  # Need to refuel
                    _LOG.debug("%s needs to refuel", water_bomber.get_name())
                    for base in bases:
                        temp_arr_time = water_bomber.enough_fuel(
                            [base, ignition, bases[base_index]], self.prioritisation_function
                        )
                        if temp_arr_time is not None:
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
                        [water_tank, ignition, bases[base_index]], self.prioritisation_function
                    )
                    if water_bomber.check_water_tank(water_tank) and temp_arr_time is not None:
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
                                ],
                                self.prioritisation_function,
                            )
                            if (
                                water_bomber.check_water_tank(water_tank)
                                and temp_arr_time is not None
                            ):
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
                                ],
                                self.prioritisation_function,
                            )
                            if (
                                water_bomber.check_water_tank(water_tank)
                                and temp_arr_time is not None
                            ):
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
                    best_water_bomber.event_queue.delete_after(start_from)
            for location in assigned_locations:
                best_water_bomber.add_location_to_queue(location, ignition.inspected_time)

        else:
            _LOG.error("No water bombers were available")
        for water_bomber in self.water_bombers:
            bases = self.water_bomber_bases_dict[water_bomber.type]
            water_bomber.go_to_base_when_necessary(bases, ignition.inspected_time)

    def process_new_strike(self, lightning: Lightning) -> None:
        """Decide on water bombers movement with new strike."""
