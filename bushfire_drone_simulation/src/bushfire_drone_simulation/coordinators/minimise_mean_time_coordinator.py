"""Insertion coordinator minimizing mean inspection/supression time.

This coordinator aims to minimise the mean inspection/supression time of the lightning strikes
by finding the place within each aircrafts list of locations to 'insert' a recent strike
to visit that minimizes this value.
It does not consider also going via a base/water tank to facilitate 'inserting' this extra
strike and rather discounts the option if it does not possess enough fuel or water.

"""

import logging
from math import inf
from typing import Callable, Dict, List, Optional, Union

import numpy as np

from bushfire_drone_simulation.aircraft import Event
from bushfire_drone_simulation.coordinators.abstract_coordinator import (
    UAVCoordinator,
    WBCoordinator,
)
from bushfire_drone_simulation.fire_utils import Base, Location, WaterTank
from bushfire_drone_simulation.lightning import AllocatedLightning, Lightning
from bushfire_drone_simulation.linked_list import Node
from bushfire_drone_simulation.parameters import JSONParameters
from bushfire_drone_simulation.uav import UAV
from bushfire_drone_simulation.units import DEFAULT_DURATION_UNITS, Duration
from bushfire_drone_simulation.water_bomber import WaterBomber

_LOG = logging.getLogger(__name__)


class MinimiseMeanTimeUAVCoordinator(UAVCoordinator):
    """Insertion UAV Coordinator.

    Coordinator will try to insert the new strike in between the uavs current tasks
    and minimise the new strikes inspection time.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        uavs: List[UAV],
        uav_bases: List[Base],
        parameters: JSONParameters,
        scenario_idx: int,
        prioritisation_function: Callable[[float, float], float],
    ):
        """Initialize coordinator."""
        super().__init__(uavs, uav_bases, parameters, scenario_idx, prioritisation_function)
        self.max_inspection_time: float = 0
        self.consider_max_inspection_time: bool = True
        self.reprocess_max = False

    def process_new_strike(  # pylint: disable=too-many-branches, too-many-statements
        self, lightning: Lightning
    ) -> None:
        """Receive lightning strike that just occurred and assign best uav."""
        mean_time_power = float(
            self.parameters.get_attribute("uav_mean_time_power", self.scenario_idx)
        )
        target_from_params = self.parameters.get_attribute(
            "target_maximum_inspection_time", self.scenario_idx
        )
        if target_from_params == "inf":
            target_max_time = inf
        else:
            target_max_time = Duration(target_from_params, "hr").get(DEFAULT_DURATION_UNITS)
        if self.precomputed is None:
            index_of_closest_base = int(np.argmin(list(map(lightning.distance, self.uav_bases))))
        else:
            index_of_closest_base = self.precomputed.closest_uav_base(lightning)
        min_arrival_time: float = inf
        min_arr_time_above_target: float = inf
        best_uav: Optional[UAV] = None
        best_uav_above_target: Optional[UAV] = None
        assigned_locations: List[Location] = []
        assigned_locations_above_target: List[Location] = []
        start_from: Optional[Union[Node[Event], str]] = None
        start_from_above_target: Optional[Union[Node[Event], str]] = None
        # The event from which to start going to assigned locations, str if delete all elements
        for uav in self.uavs:  # pylint: disable=too-many-nested-blocks
            # Go through the queue of every new strike and try inserting the new strike in between
            if not uav.event_queue.is_empty():
                lightning_event: List[Location] = [lightning]
                future_events: List[Location] = []
                prev_inspection_times: List[AllocatedLightning] = []
                closest_base_to_last_event: Optional[Base] = None
                last_event_position = uav.event_queue.peak_last().position
                if isinstance(last_event_position, Lightning):
                    if self.precomputed is None:
                        closest_base_to_last_event = self.uav_bases[
                            int(np.argmin(list(map(last_event_position.distance, self.uav_bases))))
                        ]
                    else:
                        closest_base_to_last_event = self.uav_bases[
                            self.precomputed.closest_uav_base(last_event_position)
                        ]
                for event, prev_event in uav.event_queue.iterate_backwards():
                    future_events.insert(0, event.position)
                    if isinstance(event.position, Lightning):
                        prev_inspection_times.append(
                            AllocatedLightning(
                                event.position, event.completion_time - event.position.spawn_time
                            )
                        )
                    prev_arrival_time = event.completion_time
                    prev_state: Union[Event, str] = "self"
                    if prev_event is not None:
                        prev_state = prev_event.value
                    enough_fuel = uav.enough_fuel(
                        lightning_event
                        + future_events
                        + (
                            [closest_base_to_last_event]
                            if closest_base_to_last_event is not None
                            else []
                        ),
                        self.prioritisation_function,
                        prev_state,
                    )
                    if enough_fuel is not None:
                        new_strike_arr_time = uav.arrival_time([lightning], prev_state)
                        new_event_arr_time = uav.arrival_time(
                            [lightning, event.position], prev_state
                        )
                        additional_arr_time = new_event_arr_time - prev_arrival_time
                        cumulative_time = (
                            new_strike_arr_time - lightning.spawn_time
                        ) ** mean_time_power
                        time_exceeded_target: bool = False
                        for allocated_lightning in prev_inspection_times:
                            cumulative_time += (
                                self.prioritisation_function(
                                    allocated_lightning.time + additional_arr_time,
                                    allocated_lightning.lightning.risk_rating,
                                )
                                ** mean_time_power
                                - self.prioritisation_function(
                                    allocated_lightning.time,
                                    allocated_lightning.lightning.risk_rating,
                                )
                                ** mean_time_power
                            )
                            if (
                                self.prioritisation_function(
                                    allocated_lightning.time + additional_arr_time,
                                    allocated_lightning.lightning.risk_rating,
                                )
                                > target_max_time
                            ):
                                time_exceeded_target = True
                        if time_exceeded_target:
                            if cumulative_time < min_arr_time_above_target:
                                min_arr_time_above_target = cumulative_time
                                assigned_locations_above_target = lightning_event + future_events
                                if prev_event is None:
                                    start_from_above_target = "empty"
                                else:
                                    start_from_above_target = prev_event
                                best_uav_above_target = uav
                        elif cumulative_time < min_arrival_time:
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
            temp_arr_time = uav.enough_fuel(
                [lightning, self.uav_bases[index_of_closest_base]], self.prioritisation_function
            )
            if temp_arr_time is not None:
                inspection_time = uav.arrival_time([lightning]) - lightning.spawn_time
                temp_arr_time = inspection_time**mean_time_power
                if inspection_time > target_max_time:
                    if temp_arr_time < min_arr_time_above_target:  # type: ignore
                        min_arr_time_above_target = temp_arr_time  # type: ignore
                        assigned_locations_above_target = [lightning]
                        start_from_above_target = None
                        best_uav_above_target = uav

                elif temp_arr_time < min_arrival_time:  # type: ignore
                    min_arrival_time = temp_arr_time  # type: ignore
                    best_uav = uav
                    assigned_locations = [lightning]
                    start_from = None
            else:  # Need to go via a base to refuel
                for uav_base in self.uav_bases:
                    temp_arr_time = uav.enough_fuel(
                        [uav_base, lightning, self.uav_bases[index_of_closest_base]],
                        self.prioritisation_function,
                    )
                    if temp_arr_time is not None:
                        inspection_time = (
                            uav.arrival_time([uav_base, lightning]) - lightning.spawn_time
                        )
                        temp_arr_time = inspection_time**mean_time_power

                        if inspection_time > target_max_time:
                            if temp_arr_time < min_arr_time_above_target:  # type: ignore
                                min_arr_time_above_target = temp_arr_time  # type: ignore
                                assigned_locations_above_target = [uav_base, lightning]
                                start_from_above_target = None
                                best_uav_above_target = uav

                        elif temp_arr_time < min_arrival_time:  # type: ignore
                            min_arrival_time = temp_arr_time  # type: ignore
                            best_uav = uav
                            assigned_locations = [uav_base, lightning]
                            start_from = None

        if best_uav is None:
            # We cannot keep the strike's inspection time under the target time
            # So revert to minimising mean time instead
            if best_uav_above_target is None:
                _LOG.error("No UAVs were available to process lightning strike %s", lightning.id_no)
            else:
                _LOG.debug("Couldn't stay below max inspection time target")
                best_uav = best_uav_above_target
                assigned_locations = assigned_locations_above_target
                start_from = None
                if start_from_above_target is not None:
                    start_from = start_from_above_target
        if (
            self.consider_max_inspection_time and self.reprocess_max
        ):  # pylint: disable=too-many-nested-blocks, R1702
            self.consider_max_inspection_time = False  # Don't reprocess next time
            if best_uav is not None:
                _LOG.debug("Best UAV is: %s", best_uav.get_name())
                # Insert strike
                if start_from is not None:
                    if isinstance(start_from, str):
                        best_uav.event_queue.clear()
                    else:
                        best_uav.event_queue.delete_after(start_from)
                for location in assigned_locations:
                    best_uav.add_location_to_queue(location)
                max_inspection_time: float = 0
                prior_to_strike: Optional[Node[Event]] = None
                remaining_events: List[Location] = []
                after_strike_events: List[Location] = []
                strike_to_reprocess: Optional[Lightning] = None
                # Only check strikes that would may have been altered by the insertion
                for event, prev_event in best_uav.event_queue.iterate_backwards():
                    if isinstance(event.position, Lightning):
                        inspection_time = self.prioritisation_function(
                            event.completion_time - event.position.spawn_time,
                            event.position.risk_rating,
                        )
                        # prioritisation_function here
                        if inspection_time > max_inspection_time:
                            max_inspection_time = inspection_time
                            strike_to_reprocess = event.position
                            prior_to_strike = prev_event
                            after_strike_events = []
                            after_strike_events = after_strike_events + remaining_events
                    remaining_events.insert(0, event.position)
                if self.max_inspection_time < max_inspection_time:
                    self.max_inspection_time = max_inspection_time
                    # Remove strike to reprocess
                    if prior_to_strike is not None:
                        best_uav.event_queue.delete_after(prior_to_strike)
                    else:
                        best_uav.event_queue.clear()
                    for location in after_strike_events:
                        best_uav.add_location_to_queue(location)
                    for event in best_uav.event_queue:
                        if isinstance(event.position, Lightning):
                            inspection_time = self.prioritisation_function(
                                event.completion_time - event.position.spawn_time,
                                event.position.risk_rating,
                            )
                            self.max_inspection_time = max(
                                self.max_inspection_time, inspection_time
                            )  # TODO(I dont see why this is necessary) pylint: disable=fixme
                    assert isinstance(strike_to_reprocess, Lightning)
                    self.process_new_strike(strike_to_reprocess)

        else:  # Don't reprocess anything!
            self.consider_max_inspection_time = True
            if best_uav is not None:
                _LOG.debug("Best UAV is: %s", best_uav.get_name())
                if start_from is not None:
                    if isinstance(start_from, str):
                        best_uav.event_queue.clear()
                    else:
                        best_uav.event_queue.delete_after(start_from)
                for location in assigned_locations:
                    best_uav.add_location_to_queue(location)
                for event in best_uav.event_queue:
                    if isinstance(event.position, Lightning):
                        inspection_time = event.completion_time - event.position.spawn_time
                        if inspection_time > self.max_inspection_time:
                            self.max_inspection_time = inspection_time
        for uav in self.uavs:
            uav.go_to_base_when_necessary(self.uav_bases, lightning.spawn_time)


class MinimiseMeanTimeWBCoordinator(WBCoordinator):
    """Insertion water bomber coordinator.

    Coordinator will try to insert the new strike in between the uavs current tasks
    and minimise the new strikes inspection time.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        water_bombers: List[WaterBomber],
        water_bomber_bases: Dict[str, List[Base]],
        water_tanks: List[WaterTank],
        parameters: JSONParameters,
        scenario_idx: int,
        prioritisation_function: Callable[[float, float], float],
    ):
        """Initialize coordinator."""
        super().__init__(
            water_bombers,
            water_bomber_bases,
            water_tanks,
            parameters,
            scenario_idx,
            prioritisation_function,
        )
        self.max_inspection_time: float = 0
        self.consider_max_inspection_time: bool = True
        self.reprocess_max = False

    def process_new_ignition(  # pylint: disable=too-many-branches, too-many-statements
        self, ignition: Lightning
    ) -> None:
        """Decide on water bombers movement with new ignition."""
        mean_time_power = float(
            self.parameters.get_attribute("wb_mean_time_power", self.scenario_idx)
        )
        target_from_params = self.parameters.get_attribute(
            "target_maximum_suppression_time", self.scenario_idx
        )
        if target_from_params == "inf":
            target_max_time = inf
        else:
            target_max_time = Duration(target_from_params, "hr").get(DEFAULT_DURATION_UNITS)
        assert ignition.inspected_time is not None, "Error: Ignition was not inspected."
        min_arrival_time: float = inf
        min_arr_time_above_target: float = inf
        best_water_bomber: Union[WaterBomber, None] = None
        best_water_bomber_above_target: Union[WaterBomber, None] = None
        assigned_locations: List[Location] = []
        assigned_locations_above_target: List[Location] = []
        start_from: Optional[Union[Node[Event], str]] = None
        start_from_above_target: Optional[Union[Node[Event], str]] = None

        for water_bomber in self.water_bombers:  # pylint: disable=too-many-nested-blocks
            bases = self.water_bomber_bases_dict[water_bomber.type]
            # Go through the queue of every new strike and try inserting the new strike in between
            if not water_bomber.event_queue.is_empty():
                ignition_event: List[Location] = [ignition]
                future_events: List[Location] = []
                last_event_position = water_bomber.event_queue.peak_last().position
                prev_suppression_times: List[float] = []
                closest_base_to_last_event: Optional[Base] = None
                if not isinstance(last_event_position, Base):
                    if self.precomputed is None or not isinstance(last_event_position, Lightning):
                        closest_base_to_last_event = bases[
                            int(np.argmin(list(map(last_event_position.distance, bases))))
                        ]
                    else:
                        closest_base_to_last_event = bases[
                            self.precomputed.closest_wb_base(last_event_position, water_bomber.type)
                        ]
                for event, prev_event in water_bomber.event_queue.iterate_backwards():
                    future_events.insert(0, event.position)
                    if isinstance(event.position, Location):
                        prev_suppression_times.append(event.completion_time - ignition.spawn_time)
                    prev_arrival_time = event.completion_time
                    prev_state: Union[Event, str] = "self"
                    if prev_event is not None:
                        prev_state = prev_event.value
                    if water_bomber.enough_water(ignition_event + future_events, prev_state):
                        enough_fuel = water_bomber.enough_fuel(
                            ignition_event
                            + future_events
                            + (
                                [closest_base_to_last_event]
                                if closest_base_to_last_event is not None
                                else []
                            ),
                            self.prioritisation_function,
                            prev_state,
                        )
                        if enough_fuel is not None:
                            new_strike_arr_time = water_bomber.arrival_time([ignition], prev_state)
                            new_event_arr_time = water_bomber.arrival_time(
                                [ignition, event.position], prev_state
                            )
                            additional_arr_time = new_event_arr_time - prev_arrival_time
                            cumulative_time = (
                                new_strike_arr_time - ignition.spawn_time
                            ) ** mean_time_power
                            time_exceeded_target: bool = False
                            for time in prev_suppression_times:
                                cumulative_time += (
                                    time + additional_arr_time
                                ) ** mean_time_power - time**mean_time_power
                                if time + additional_arr_time > target_max_time:
                                    time_exceeded_target = True
                            if time_exceeded_target:
                                if cumulative_time < min_arr_time_above_target:
                                    min_arr_time_above_target = cumulative_time
                                    assigned_locations_above_target = ignition_event + future_events
                                    if prev_event is None:
                                        start_from_above_target = "empty"
                                    else:
                                        start_from_above_target = prev_event
                                    best_water_bomber_above_target = water_bomber
                            elif cumulative_time < min_arrival_time:
                                min_arrival_time = cumulative_time
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
                    suppression_time = water_bomber.arrival_time([ignition]) - ignition.spawn_time
                    temp_arr_time = suppression_time**mean_time_power
                    if suppression_time > target_max_time:
                        if temp_arr_time < min_arr_time_above_target:  # type: ignore
                            min_arr_time_above_target = temp_arr_time  # type: ignore
                            assigned_locations_above_target = [ignition]
                            start_from_above_target = None
                            best_water_bomber_above_target = water_bomber
                    elif temp_arr_time < min_arrival_time:  # type: ignore
                        min_arrival_time = temp_arr_time  # type: ignore
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
                            suppression_time = (
                                water_bomber.arrival_time([base, ignition]) - ignition.spawn_time
                            )
                            temp_arr_time = suppression_time**mean_time_power
                            if suppression_time > target_max_time:
                                if temp_arr_time < min_arr_time_above_target:  # type: ignore
                                    min_arr_time_above_target = temp_arr_time  # type: ignore
                                    assigned_locations_above_target = [base, ignition]
                                    start_from_above_target = None
                                    best_water_bomber_above_target = water_bomber
                            elif temp_arr_time < min_arrival_time:  # type: ignore
                                min_arrival_time = temp_arr_time  # type: ignore
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
                        suppression_time = (
                            water_bomber.arrival_time([water_tank, ignition]) - ignition.spawn_time
                        )
                        temp_arr_time = suppression_time**mean_time_power
                        if suppression_time > target_max_time:
                            if temp_arr_time < min_arr_time_above_target:  # type: ignore
                                min_arr_time_above_target = temp_arr_time  # type: ignore
                                assigned_locations_above_target = [water_tank, ignition]
                                start_from_above_target = None
                                best_water_bomber_above_target = water_bomber
                        elif temp_arr_time < min_arrival_time:  # type: ignore
                            min_arrival_time = temp_arr_time  # type: ignore
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
                                suppression_time = (
                                    water_bomber.arrival_time([water_tank, base, ignition])
                                    - ignition.spawn_time
                                )
                                temp_arr_time = suppression_time**mean_time_power
                                if suppression_time > target_max_time:
                                    if temp_arr_time < min_arr_time_above_target:  # type: ignore
                                        min_arr_time_above_target = temp_arr_time  # type: ignore
                                        assigned_locations_above_target = [
                                            water_tank,
                                            base,
                                            ignition,
                                        ]
                                        start_from_above_target = None
                                        best_water_bomber_above_target = water_bomber
                                elif temp_arr_time < min_arrival_time:  # type: ignore
                                    min_arrival_time = temp_arr_time  # type: ignore
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
                                suppression_time = (
                                    water_bomber.arrival_time([base, water_tank, ignition])
                                    - ignition.spawn_time
                                )
                                temp_arr_time = suppression_time**mean_time_power
                                if suppression_time > target_max_time:
                                    if temp_arr_time < min_arr_time_above_target:  # type: ignore
                                        min_arr_time_above_target = temp_arr_time  # type: ignore
                                        assigned_locations_above_target = [
                                            base,
                                            water_tank,
                                            ignition,
                                        ]
                                        start_from_above_target = None
                                        best_water_bomber_above_target = water_bomber
                                elif temp_arr_time < min_arrival_time:  # type: ignore
                                    min_arrival_time = temp_arr_time  # type: ignore
                                    best_water_bomber = water_bomber
                                    assigned_locations = [base, water_tank, ignition]
                                    start_from = None
        if best_water_bomber is None:
            if best_water_bomber_above_target is None:
                _LOG.error("No water bombers were available to suppress strike %s", ignition.id_no)
            else:
                _LOG.debug("Couldn't stay below max inspection time target")
                best_water_bomber = best_water_bomber_above_target
                assigned_locations = assigned_locations_above_target
                start_from = None
                if start_from_above_target is not None:
                    start_from = start_from_above_target
        if (
            self.consider_max_inspection_time and self.reprocess_max
        ):  # pylint: disable=too-many-nested-blocks
            self.consider_max_inspection_time = False
            if best_water_bomber is not None:
                _LOG.debug("Best bomber is: %s", best_water_bomber.get_name())
                if start_from is not None:
                    if isinstance(start_from, str):
                        best_water_bomber.event_queue.clear()
                    else:
                        best_water_bomber.event_queue.delete_after(start_from)
                for location in assigned_locations:
                    best_water_bomber.add_location_to_queue(location)
                max_inspection_time: float = 0
                prior_to_strike: Optional[Node[Event]] = None
                remaining_events: List[Location] = []
                after_strike_events: List[Location] = []
                strike_to_reprocess: Optional[Lightning] = None
                for event, prev_event in best_water_bomber.event_queue.iterate_backwards():
                    if isinstance(event.position, Lightning):
                        inspection_time = event.completion_time - event.position.spawn_time
                        if inspection_time > max_inspection_time:
                            max_inspection_time = inspection_time
                            strike_to_reprocess = event.position
                            prior_to_strike = prev_event
                            after_strike_events = []
                            after_strike_events = after_strike_events + remaining_events
                    remaining_events.insert(0, event.position)
                if self.max_inspection_time < max_inspection_time:
                    self.max_inspection_time = max_inspection_time
                    if prior_to_strike is not None:
                        best_water_bomber.event_queue.delete_after(prior_to_strike)
                    else:
                        best_water_bomber.event_queue.clear()
                    for location in after_strike_events:
                        best_water_bomber.add_location_to_queue(location)
                    for event in best_water_bomber.event_queue:
                        if isinstance(event.position, Lightning):
                            inspection_time = event.completion_time - event.position.spawn_time
                            self.max_inspection_time = max(
                                self.max_inspection_time, inspection_time
                            )
                    assert isinstance(strike_to_reprocess, Lightning)
                    self.process_new_ignition(strike_to_reprocess)

        else:  # Don't reprocess anything!
            self.consider_max_inspection_time = True
            if best_water_bomber is not None:
                _LOG.debug("Best bomber is: %s", best_water_bomber.get_name())
                if start_from is not None:
                    if isinstance(start_from, str):
                        best_water_bomber.event_queue.clear()
                    else:
                        best_water_bomber.event_queue.delete_after(start_from)
                for location in assigned_locations:
                    best_water_bomber.add_location_to_queue(location)
                for event in best_water_bomber.event_queue:
                    if isinstance(event.position, Lightning):
                        inspection_time = event.completion_time - event.position.spawn_time
                        if inspection_time > self.max_inspection_time:
                            self.max_inspection_time = inspection_time

        for water_bomber in self.water_bombers:
            bases = self.water_bomber_bases_dict[water_bomber.type]
            water_bomber.go_to_water_if_necessary(self.water_tanks, bases)
            water_bomber.go_to_base_when_necessary(bases, ignition.inspected_time)

    def process_new_strike(self, lightning: Lightning) -> None:
        """Decide on water bombers movement with new strike."""
