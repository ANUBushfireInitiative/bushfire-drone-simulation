"""Simulation of bushfire drone simulation."""

from math import inf
from queue import PriorityQueue, Queue
from typing import Dict, List, Optional, Tuple, Union

from bushfire_drone_simulation.abstract_coordinator import (
    UAVCoordinator,
    UnassigedCoordinator,
    WBCoordinator,
)
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.parameters import JSONParameters
from bushfire_drone_simulation.precomupted import PreComputedDistances


class Simulator:
    """Class for running the simulation."""

    def __init__(self, params: JSONParameters, scenario_idx: int):
        """Initialize simulation class."""
        self.lightning_queue: "Queue[Lightning]" = PriorityQueue()
        self.lightning_strikes = params.get_lightning(scenario_idx)
        for strike in self.lightning_strikes:
            self.lightning_queue.put(strike)
        self.ignitions: "Queue[Lightning]" = Queue()
        self.water_bomber_bases_list = params.get_water_bomber_bases_all(scenario_idx)
        water_bombers, water_bomber_bases_dict = params.process_water_bombers(
            self.water_bomber_bases_list, scenario_idx
        )
        self.uavs = params.process_uavs(scenario_idx)
        self.uav_bases = params.get_uav_bases(scenario_idx)
        self.water_bombers = water_bombers
        self.water_bomber_bases_dict = water_bomber_bases_dict
        self.water_tanks = params.get_water_tanks(scenario_idx)
        self.precomputed = PreComputedDistances(
            self.lightning_strikes, self.uav_bases, self.water_bomber_bases_dict, self.water_tanks
        )
        self.summary_results: Dict[str, List[Union[float, str]]] = {}
        self.animation_data: Dict[str, List[List[float]]] = {}

    def run_simulation(  # pylint: disable=too-many-branches
        self,
        uav_coordinator: UAVCoordinator,
        wb_coordinator: WBCoordinator,
        unassigned_coordinator: Optional[UnassigedCoordinator] = None,
    ) -> None:
        """Run bushfire drone simulation."""
        uav_coordinator.accept_precomputed_distances(self.precomputed)
        wb_coordinator.accept_precomputed_distances(self.precomputed)
        for uav in self.uavs:
            uav.accept_precomputed_distances(self.precomputed)
        for water_bomber in self.water_bombers:
            water_bomber.accept_precomputed_distances(self.precomputed)

        if unassigned_coordinator is None or self.lightning_queue.empty():
            update_unassigned_time = inf
        else:
            update_unassigned_time = self.lightning_queue.queue[0].spawn_time

        while not self.lightning_queue.empty():
            strike = self.lightning_queue.get()
            inspections = self._update_uavs_to_time(strike.spawn_time)
            uav_coordinator.lightning_strike_inspected(inspections)
            uav_coordinator.new_strike(strike)
            for (inspected, _) in inspections:
                if inspected.ignition:
                    self.ignitions.put(inspected)

            if not self.lightning_queue.empty():
                while self.lightning_queue.queue[0].spawn_time > update_unassigned_time:
                    assert unassigned_coordinator is not None
                    # print("UPDATING UAVS TO TIME " + str(update_unassigned_time / 60) + " mins")
                    inspections = self._update_uavs_to_time(update_unassigned_time)
                    unassigned_coordinator.assign_unassigned_uavs(update_unassigned_time)
                    update_unassigned_time += unassigned_coordinator.dt
                    for (inspected, _) in inspections:
                        if inspected.ignition:
                            self.ignitions.put(inspected)

        print("UPDATING UAVS TO TIME INF")
        inspections = self._update_uavs_to_time(inf)
        for (inspected, _) in inspections:
            if inspected.ignition:
                self.ignitions.put(inspected)

        while not self.ignitions.empty():
            ignition = self.ignitions.get()
            assert (
                ignition.inspected_time is not None
            ), f"Ignition {ignition.id_no} was not inspected"
            # print("UPDATING WBS TO TIME " + str(ignition.inspected_time.get()))
            suppressions = self._update_water_bombers_to_time(ignition.inspected_time)
            wb_coordinator.lightning_strike_suppressed(suppressions)
            wb_coordinator.unsuppressed_strikes.add(ignition)
            wb_coordinator.process_new_ignition(ignition)
            # wb_coordinator.new_ignition(ignition)
            # TODO(get this silly function to work) pylint: disable=fixme

        # print("UPDATING WBS TO TIME INF")
        suppressions = self._update_water_bombers_to_time(inf)

        if unassigned_coordinator is not None:
            self.animation_data = unassigned_coordinator.output

    def _update_to_time(
        self, time: float
    ) -> Tuple[List[Tuple[Lightning, int]], List[Tuple[Lightning, str]]]:
        """Update all aircraft to given time."""
        inspections = self._update_uavs_to_time(time)
        suppressions = self._update_water_bombers_to_time(time)
        return inspections, suppressions

    def _update_uavs_to_time(self, time: float) -> List[Tuple[Lightning, int]]:
        """Update all UAVs to given time, return list of inspected strikes."""
        strikes_inspected: List[Tuple[Lightning, int]] = []
        for uav in self.uavs:
            inspections, _ = uav.update_to_time(time)
            for inspection in inspections:
                strikes_inspected.append((inspection, uav.id_no))
        return strikes_inspected

    def _update_water_bombers_to_time(self, time: float) -> List[Tuple[Lightning, str]]:
        """Update all water bombers to given time, return list of suppressed strikes."""
        strikes_suppressed: List[Tuple[Lightning, str]] = []
        for water_bomber in self.water_bombers:
            _, suppressions = water_bomber.update_to_time(time)
            for suppression in suppressions:
                strikes_suppressed.append((suppression, water_bomber.get_name()))
        return strikes_suppressed

    def output_results(self, params: JSONParameters, scenario_idx: int) -> None:
        """Write results of simulation to output folder."""
        prefix = ""
        if "scenario_name" in params.scenarios[scenario_idx]:
            prefix = str(params.get_attribute("scenario_name", scenario_idx)) + "_"

        inspection_times, suppression_times = params.write_to_simulation_output_file(
            self.lightning_strikes, prefix
        )
        params.write_to_uav_updates_file(self.uavs, prefix)
        params.write_to_wb_updates_file(self.water_bombers, prefix)
        params.write_to_input_parameters_folder(scenario_idx)
        self.summary_results = params.create_plots(
            inspection_times,
            suppression_times,
            self.water_bombers,
            self.water_tanks,
            prefix,
        )
