"""Simple coordinator."""

import logging
from queue import Queue
from typing import Dict, List, Tuple, Union

import numpy as np

from bushfire_drone_simulation.abstract_coordinator import UAVCoordinator, WBCoordinator
from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.fire_utils import Base, Time, WaterTank
from bushfire_drone_simulation.lightning import Lightning

_LOG = logging.getLogger(__name__)


class SimpleUAVCoordinator(UAVCoordinator):
    """Simple UAV Coordinator."""

    def __init__(self, uavs: List[UAV], uav_bases: List[Base]):
        """Initialize UAV coordinator."""
        super().__init__(uavs, uav_bases)
        self.assigned_drones: Dict[int, List[Lightning]] = {}
        self.strikes_to_be_processed: "Queue[Lightning]" = Queue()

    def lightning_strike_inspected(self, lightning_strikes: List[Tuple[Lightning, int]]) -> None:
        """Lightning has been inspected."""
        for (strike, uav_id) in lightning_strikes:
            self.uninspected_strikes.remove(strike)
            try:
                self.assigned_drones[uav_id].remove(strike)
            except ValueError:
                assert False, (
                    f"Tried to remove strike {strike.id_no} from "
                    "uav{uav_id}s list but it was not present."
                )

    def process_new_strike(self, lightning: Lightning) -> None:
        """Receive lightning strike that just occurred and coordinate UAV movements."""
        uavs_processed: List[int] = []
        self.strikes_to_be_processed.put(lightning)
        while not self.strikes_to_be_processed.empty():
            strike = self.strikes_to_be_processed.get()
            current_uav_id = self.process_strike(strike)
            if current_uav_id is not None:
                if current_uav_id not in self.assigned_drones:
                    self.assigned_drones[current_uav_id] = [strike]
                    uavs_processed.append(current_uav_id)
                else:
                    if current_uav_id not in uavs_processed:
                        uavs_processed.append(current_uav_id)
                        for old_strike in self.assigned_drones[current_uav_id]:
                            self.strikes_to_be_processed.put(old_strike)
                        self.assigned_drones[current_uav_id] = []
                    self.assigned_drones[current_uav_id].append(strike)

    def process_strike(self, lightning: Lightning) -> Union[int, None]:
        """Assign best uav to given lightning strike.

        Args:
            lightning (Lightning): Lightning strike to be processed

        Returns:
            Union[int, None]: id number of best uav or None if none were avaliable
        """
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
                    via_base = None
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
        return_id = None
        if best_uav is not None:
            return_id = best_uav.id_no
            _LOG.debug("Best UAV is: %s", best_uav.id_no)
            _LOG.debug(
                "Which took %s mins to respond",
                (min_arrival_time - lightning.spawn_time).get("min"),
            )
            if via_base is not None:
                # The minimum arrival time was achieved by travelling via a base
                # Update UAV position accordingly
                best_uav.accept_update(via_base, lightning.spawn_time)
            # There exists a UAV that has enough fuel, send it to the lightning strike
            best_uav.accept_update(lightning, lightning.spawn_time)
            best_uav.print_past_locations()
        else:
            _LOG.error("No UAVs were available to process lightning strike %s", lightning.id_no)

        for uav in self.uavs:
            uav.consider_going_to_base(self.uav_bases, lightning.spawn_time)
        return return_id


class SimpleWBCoordinator(WBCoordinator):
    """Simple water bomber coordinator."""

    def __init__(
        self,
        water_bombers: List[WaterBomber],
        water_bomber_bases: Dict[str, List[Base]],
        water_tanks: List[WaterTank],
    ):
        """Initialize UAV coordinator."""
        super().__init__(water_bombers, water_bomber_bases, water_tanks)
        self.assigned_bombers: Dict[str, List[Lightning]] = {}
        self.strikes_to_be_processed: "Queue[Lightning]" = Queue()

    def lightning_strike_suppressed(self, lightning_strikes: List[Tuple[Lightning, str]]) -> None:
        """Lightning has been suppressed."""
        for (strike, bomber_name) in lightning_strikes:
            self.unsupressed_strikes.remove(strike)
            try:
                self.assigned_bombers[bomber_name].remove(strike)
            except ValueError:
                assert False, (
                    f"Tried to remove strike {strike.id_no} from {bomber_name}s"
                    " list but it was not present."
                )

    def process_new_ignition(self, ignition: Lightning) -> None:
        """Decide on water bombers movement with new ignition."""
        bombers_processed: List[str] = []
        self.strikes_to_be_processed.put(ignition)
        while not self.strikes_to_be_processed.empty():
            strike = self.strikes_to_be_processed.get()
            current_bomber = self.process_ignition(strike)
            if current_bomber is not None:
                if current_bomber not in self.assigned_bombers:
                    self.assigned_bombers[current_bomber] = [strike]
                    bombers_processed.append(current_bomber)
                else:
                    if current_bomber not in bombers_processed:
                        bombers_processed.append(current_bomber)
                        for old_strike in self.assigned_bombers[current_bomber]:
                            self.strikes_to_be_processed.put(old_strike)
                        self.assigned_bombers[current_bomber] = []
                    self.assigned_bombers[current_bomber].append(strike)

    def process_ignition(  # pylint:disable= too-many-branches, too-many-statements
        self, ignition: Lightning
    ) -> Union[str, None]:
        """Assign the best water bomber to given ignition.

        Args:
            ignition (Lightning): Ignition to be processed

        Returns:
            Union[str, None]: Name of assigned water bomber
        """
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
        ret_name: Union[str, None] = None
        if best_water_bomber is not None:
            ret_name = best_water_bomber.get_name()
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
                    best_water_bomber.accept_update(via_base, ignition.inspected_time)
                    best_water_bomber.accept_update(via_water, ignition.inspected_time)
                else:
                    best_water_bomber.accept_update(via_water, ignition.inspected_time)
                    best_water_bomber.accept_update(via_base, ignition.inspected_time)
            elif via_base is not None:
                best_water_bomber.accept_update(via_base, ignition.inspected_time)
            elif via_water is not None:
                best_water_bomber.accept_update(via_water, ignition.inspected_time)
            best_water_bomber.accept_update(ignition, ignition.inspected_time)
            best_water_bomber.print_past_locations()
        else:
            _LOG.error("No water bombers were available")
        for water_bomber in self.water_bombers:
            water_bomber_bases = self.water_bomber_bases_dict[water_bomber.type]
            water_bomber.consider_going_to_base(water_bomber_bases, ignition.inspected_time)
        return ret_name

    def process_new_strike(self, lightning) -> None:
        """Decide on uavs movement with new strike."""
