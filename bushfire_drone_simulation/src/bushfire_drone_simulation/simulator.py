"""Simulation of bushfire drone simulation."""

import csv
import multiprocessing
from copy import copy
from math import inf
from typing import Dict, List, Optional, Tuple, Type, Union

from tqdm.std import tqdm

from bushfire_drone_simulation.coordinators.abstract_coordinator import (
    UAVCoordinator,
    UnassignedCoordinator,
    WBCoordinator,
)
from bushfire_drone_simulation.coordinators.insertion_coordinator import (
    InsertionUAVCoordinator,
    InsertionWBCoordinator,
)
from bushfire_drone_simulation.coordinators.minimise_mean_time_coordinator import (
    MinimiseMeanTimeUAVCoordinator,
    MinimiseMeanTimeWBCoordinator,
)
from bushfire_drone_simulation.coordinators.reprocess_max_time_coordinator import (
    ReprocessMaxTimeUAVCoordinator,
    ReprocessMaxTimeWBCoordinator,
)
from bushfire_drone_simulation.coordinators.simple_coordinator import (
    SimpleUAVCoordinator,
    SimpleWBCoordinator,
)
from bushfire_drone_simulation.coordinators.unassigned_coordinator import (
    SimpleUnassignedCoordinator,
)
from bushfire_drone_simulation.fire_utils import Target
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.parameters import JSONParameters
from bushfire_drone_simulation.precomputed import PreComputedDistances

UAV_COORDINATORS: Dict[str, Type[UAVCoordinator]] = {
    "SimpleUAVCoordinator": SimpleUAVCoordinator,
    "InsertionUAVCoordinator": InsertionUAVCoordinator,
    "MinimiseMeanTimeUAVCoordinator": MinimiseMeanTimeUAVCoordinator,
    "ReprocessMaxTimeUAVCoordinator": ReprocessMaxTimeUAVCoordinator,
}

WB_COORDINATORS: Dict[str, Type[WBCoordinator]] = {
    "SimpleWBCoordinator": SimpleWBCoordinator,
    "InsertionWBCoordinator": InsertionWBCoordinator,
    "MinimiseMeanTimeWBCoordinator": MinimiseMeanTimeWBCoordinator,
    "ReprocessMaxTimeWBCoordinator": ReprocessMaxTimeWBCoordinator,
}


class Simulator:
    """Class for running the simulation."""

    def __init__(self, params: JSONParameters, scenario_idx: int):
        """Initialize simulation class."""
        self.params = params
        self.scenario_idx = scenario_idx
        self.lightning_strikes = params.get_lightning(scenario_idx)
        self.lightning_queue: List[Lightning] = copy(self.lightning_strikes)
        self.lightning_queue.sort()
        self.ignitions: List[Lightning] = []
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
        self.uav_prioritisation_function = params.get_prioritisation_function("uavs", scenario_idx)
        self.wb_prioritisation_function = params.get_prioritisation_function(
            "water_bombers", scenario_idx
        )
        self.targets: List[Target] = []

    def run_simulation(  # pylint: disable=too-many-branches
        self,
        uav_coordinator: UAVCoordinator,
        wb_coordinator: WBCoordinator,
        unassigned_coordinator: Optional[UnassignedCoordinator] = None,
    ) -> None:
        """Run bushfire drone simulation."""
        uav_coordinator.accept_precomputed_distances(self.precomputed)
        wb_coordinator.accept_precomputed_distances(self.precomputed)
        for uav in self.uavs:
            uav.accept_precomputed_distances(self.precomputed)
        for water_bomber in self.water_bombers:
            water_bomber.accept_precomputed_distances(self.precomputed)

        if unassigned_coordinator is None or not self.lightning_queue:
            update_unassigned_time = inf
        else:
            update_unassigned_time = self.lightning_queue[0].spawn_time

        while self.lightning_queue:
            strike = self.lightning_queue.pop(0)
            inspections = self._update_uavs_to_time(strike.spawn_time)
            uav_coordinator.lightning_strike_inspected(inspections)
            uav_coordinator.new_strike(strike)
            for (inspected, _) in inspections:
                if inspected.ignition:
                    self.ignitions.append(inspected)

            if self.lightning_queue:
                while self.lightning_queue[0].spawn_time > update_unassigned_time:
                    assert unassigned_coordinator is not None
                    inspections = self._update_uavs_to_time(update_unassigned_time)
                    unassigned_coordinator.assign_unassigned_uavs(update_unassigned_time)
                    update_unassigned_time += unassigned_coordinator.dt
                    for (inspected, _) in inspections:
                        if inspected.ignition:
                            self.ignitions.append(inspected)

        inspections = self._update_uavs_to_time(inf)
        for (inspected, _) in inspections:
            if inspected.ignition:
                self.ignitions.append(inspected)

        while self.ignitions:
            ignition = self.ignitions.pop(0)
            assert (
                ignition.inspected_time is not None
            ), f"Ignition {ignition.id_no} was not inspected"
            suppressions = self._update_water_bombers_to_time(ignition.inspected_time)
            wb_coordinator.lightning_strike_suppressed(suppressions)
            wb_coordinator.unsuppressed_strikes.add(ignition)
            wb_coordinator.process_new_ignition(ignition)
            # wb_coordinator.new_ignition(ignition)
            # TODO(get this silly function to work) pylint: disable=fixme

        suppressions = self._update_water_bombers_to_time(inf)

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
        self.summary_results = params.write_simulation_output(
            self.uavs,
            self.water_bombers,
            self.water_tanks,
            self.lightning_strikes,
            self.targets,
            prefix,
        )


def run_simulation(simulator: Simulator) -> Simulator:
    """Run single simulation."""
    uav_coordinator = UAV_COORDINATORS[
        simulator.params.get_attribute("uav_coordinator", simulator.scenario_idx)
    ](
        simulator.uavs,
        simulator.uav_bases,
        simulator.params,
        simulator.scenario_idx,
        simulator.uav_prioritisation_function,
    )
    wb_coordinator = WB_COORDINATORS[
        simulator.params.get_attribute("wb_coordinator", simulator.scenario_idx)
    ](
        simulator.water_bombers,
        simulator.water_bomber_bases_dict,
        simulator.water_tanks,
        simulator.params,
        simulator.scenario_idx,
        simulator.wb_prioritisation_function,
    )
    unassigned_coordinator: Optional[UnassignedCoordinator] = None
    if "unassigned_uavs" in simulator.params.parameters:
        attributes, targets, polygon, folder = simulator.params.process_unassigned_uavs(
            simulator.scenario_idx, simulator.lightning_strikes
        )
        unassigned_coordinator = SimpleUnassignedCoordinator(
            simulator.uavs, simulator.uav_bases, targets, folder, polygon, attributes
        )
        simulator.targets = targets
    simulator.run_simulation(uav_coordinator, wb_coordinator, unassigned_coordinator)
    simulator.output_results(simulator.params, simulator.scenario_idx)
    return simulator


def run_simulations(params: JSONParameters, use_parallel: bool = False) -> List[Simulator]:
    """Run bushfire drone simulation."""
    params.write_to_input_parameters_folder()
    simulators = [Simulator(params, i) for i in range(len(params.scenarios))]
    with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
        for simulator in tqdm(
            pool.imap_unordered(run_simulation, simulators)
            if use_parallel
            else map(run_simulation, simulators),
            total=len(simulators),
            unit="scenario",
            smoothing=0,
        ):
            simulators[simulator.scenario_idx] = simulator
    write_to_summary_file(simulators, params)
    return simulators


def write_to_summary_file(simulations: List[Simulator], params: JSONParameters) -> None:
    """Write summary results from each simulation to summary file."""
    with open(
        params.output_folder / ("summary_file.csv"),
        "w",
        newline="",
        encoding="utf8",
    ) as outputfile:
        filewriter = csv.writer(outputfile)
        filewriter.writerow(
            [
                "Scenario Name",
                "",
                "Mean time (hr)",
                "Max time (hr)",
                "99th percentile (hr)",
                "90th percentile (hr)",
                "50th percentile (hr)",
            ]
        )
        for scenario_idx, simulator in enumerate(simulations):
            name: str
            if "scenario_name" in params.scenarios[scenario_idx]:
                name = str(params.get_attribute("scenario_name", scenario_idx))
            else:
                name = str(scenario_idx)
            if "uavs" in simulator.summary_results:
                inspection_results: List[Union[str, float]] = simulator.summary_results["uavs"]
                inspection_results.insert(0, "Inspections")
                inspection_results.insert(0, name)
                filewriter.writerow(inspection_results)
            else:
                filewriter.writerow(["", "Inspections", "No strikes were inspected"])
            if "wbs" in simulator.summary_results:
                suppression_results: List[Union[str, float]] = simulator.summary_results["wbs"]
                suppression_results.insert(0, "Suppressions")
                suppression_results.insert(0, "")
                filewriter.writerow(suppression_results)
            else:
                filewriter.writerow(["", "Suppressions", "No strikes were suppressed"])
            filewriter.writerow([])
