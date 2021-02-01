"""Simulation of bushfire drone simulation."""

from queue import PriorityQueue, Queue
from typing import List, Tuple

from bushfire_drone_simulation.abstract_coordinator import UAVCoordinator, WBCoordinator
from bushfire_drone_simulation.aircraft import UAV, Aircraft, WaterBomber
from bushfire_drone_simulation.fire_utils import Base, Time
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.parameters import JSONParameters


class AircraftEvent:  # pylint: disable=too-few-public-methods
    """Event assoicated to an aircraft."""

    def __init__(self, time: Time, aircraft: Aircraft):
        """Init AircraftEvent class."""
        self.time = time
        self.aircraft = aircraft

    def __lt__(self, other: "AircraftEvent") -> bool:
        """Less than operator for AircraftEvent."""
        return self.time < other.time


class Simulator:
    """Class for running the simulation."""

    def __init__(self, params: JSONParameters, scenario_idx: int):
        """Init Simulation class."""
        self.lightning_queue: "Queue[Lightning]" = PriorityQueue()
        self.lightning_strikes = params.get_lightning(scenario_idx)
        for strike in self.lightning_strikes:
            self.lightning_queue.put(strike)
        self.ignitions: "Queue[Lightning]" = Queue()
        water_bombers, water_bomber_bases_dict = params.process_water_bombers(
            params.get_water_bomber_bases_all(scenario_idx), scenario_idx
        )
        self.uavs: List[UAV] = params.process_uavs(scenario_idx)
        self.uav_bases: List[Base] = params.get_uav_bases(scenario_idx)
        self.water_bombers: List[WaterBomber] = water_bombers
        self.water_bomber_bases_dict = water_bomber_bases_dict
        self.water_tanks = params.get_water_tanks(scenario_idx)

    def run_simulation(
        self, uav_coordinator: UAVCoordinator, wb_coordinator: WBCoordinator
    ) -> None:
        """Run bushfire drone simulation."""
        while not self.lightning_queue.empty():
            strike = self.lightning_queue.get()
            inspections = self._update_uavs_to_time(strike.spawn_time)
            uav_coordinator.lightning_strike_inspected(inspections)
            uav_coordinator.new_strike(strike)
            for (inspected, _) in inspections:
                if inspected.ignition:
                    self.ignitions.put(inspected)

        inspections = self._update_uavs_to_time(Time("inf"))
        for (inspected, _) in inspections:
            if inspected.ignition:
                self.ignitions.put(inspected)

        while not self.ignitions.empty():
            ignition = self.ignitions.get()
            assert (
                ignition.inspected_time is not None
            ), f"Ignition {ignition.id_no} was not inspected"
            suppressions = self._update_water_bombers_to_time(ignition.inspected_time)
            wb_coordinator.lightning_strike_suppressed(suppressions)
            wb_coordinator.unsupressed_strikes.add(ignition)
            wb_coordinator.process_new_ignition(ignition)
            # wb_coordinator.new_ignition(ignition)
            # TODO(get this silly function to work) pylint: disable=fixme

        suppressions = self._update_water_bombers_to_time(Time("inf"))

    def _update_to_time(
        self, time: Time
    ) -> Tuple[List[Tuple[Lightning, int]], List[Tuple[Lightning, str]]]:
        """Update all aircraft to given time."""
        inspections = self._update_uavs_to_time(time)
        suppressions = self._update_water_bombers_to_time(time)
        return inspections, suppressions

    def _update_uavs_to_time(self, time: Time) -> List[Tuple[Lightning, int]]:
        """Update all UAVs to given time, return list of inspected strikes."""
        strikes_inspected: List[Tuple[Lightning, int]] = []
        for uav in self.uavs:
            inspections, _ = uav.update_to_time(time)
            for inspection in inspections:
                print("strike " + str(inspection.id_no) + " inspected!")
                strikes_inspected.append((inspection, uav.id_no))
        return strikes_inspected

    def _update_water_bombers_to_time(self, time) -> List[Tuple[Lightning, str]]:
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

        inspection_times, supression_times_ignitions_only = params.write_to_simulation_output_file(
            self.lightning_strikes, prefix
        )
        params.write_to_uav_updates_file(self.uavs, prefix)
        params.write_to_wb_updates_file(self.water_bombers, prefix)
        params.write_to_input_parameters_folder(scenario_idx)
        params.create_plots(
            inspection_times,
            supression_times_ignitions_only,
            self.water_bombers,
            self.water_tanks,
            prefix,
        )
