"""Main entry point for bushfire-drone-simulation."""

import csv
import logging
from pathlib import Path
from sys import stderr
from typing import Dict, List, Type, Union

import typer
from tqdm import tqdm

from bushfire_drone_simulation.abstract_coordinator import UAVCoordinator, WBCoordinator
from bushfire_drone_simulation.gui.gui import start_gui, start_map_gui
from bushfire_drone_simulation.insertion_coordinator import (
    InsertionUAVCoordinator,
    InsertionWBCoordinator,
)
from bushfire_drone_simulation.matlab_coordinator import MatlabUAVCoordinator, MatlabWBCoordinator
from bushfire_drone_simulation.minimise_mean_time_coordinator import (
    MinimiseMeanTimeUAVCoordinator,
    MinimiseMeanTimeWBCoordinator,
)
from bushfire_drone_simulation.new_strikes_first_coordinator import (
    NewStrikesFirstUAVCoordinator,
    NewStrikesFirstWBCoordinator,
)
from bushfire_drone_simulation.parameters import JSONParameters
from bushfire_drone_simulation.reprocess_max_time_coordinator import (
    ReprocessMaxTimeUAVCoordinator,
    ReprocessMaxTimeWBCoordinator,
)
from bushfire_drone_simulation.simulator import Simulator

_LOG = logging.getLogger(__name__)
app = typer.Typer()


UAV_COORDINATORS: Dict[str, Union[Type[UAVCoordinator]]] = {
    "MatlabUAVCoordinator": MatlabUAVCoordinator,
    "NewStrikesFirstUAVCoordinator": NewStrikesFirstUAVCoordinator,
    "InsertionUAVCoordinator": InsertionUAVCoordinator,
    "MinimiseMeanTimeUAVCoordinator": MinimiseMeanTimeUAVCoordinator,
    "ReprocessMaxTimeUAVCoordinator": ReprocessMaxTimeUAVCoordinator,
}

WB_COORDINATORS: Dict[str, Union[Type[WBCoordinator]]] = {
    "MatlabWBCoordinator": MatlabWBCoordinator,
    "NewStrikesFirstWBCoordinator": NewStrikesFirstWBCoordinator,
    "InsertionWBCoordinator": InsertionWBCoordinator,
    "MinimiseMeanTimeWBCoordinator": MinimiseMeanTimeWBCoordinator,
    "ReprocessMaxTimeWBCoordinator": ReprocessMaxTimeWBCoordinator,
}


def main() -> None:
    """Entry point for bushfire_drone_simulation."""
    logging.basicConfig(stream=stderr, level=logging.WARNING)
    app()


@app.command()
def gui(
    parameters_filename: Path = typer.Option("parameters.json", help="Path to parameters file.")
) -> None:
    """Start a GUI version of the drone simulation."""
    simulator = run_simulation(parameters_filename)[0]
    if simulator is not None:
        start_gui(simulator)


@app.command()
def map_gui() -> None:
    """Start a GUI version of the drone simulation."""
    start_map_gui()


@app.command()
def run_simulation(
    parameters_filename: Path = typer.Option("parameters.json", help="Path to parameters file.")
) -> List[Simulator]:
    """Run bushfire drone simulation."""
    params = JSONParameters(parameters_filename)
    to_return = []
    for scenario_idx in tqdm(range(0, len(params.scenarios)), unit="scenario"):
        simulator = Simulator(params, scenario_idx)
        uav_coordinator = UAV_COORDINATORS[params.get_attribute("uav_coordinator", scenario_idx)](
            simulator.uavs, simulator.uav_bases, params, scenario_idx
        )
        wb_coordinator = WB_COORDINATORS[params.get_attribute("wb_coordinator", scenario_idx)](
            simulator.water_bombers,
            simulator.water_bomber_bases_dict,
            simulator.water_tanks,
            params,
            scenario_idx,
        )
        simulator.run_simulation(uav_coordinator, wb_coordinator)

        simulator.output_results(params, scenario_idx)
        to_return.append(simulator)
    write_to_summary_file(to_return, params)
    return to_return


def write_to_summary_file(simulations: List[Simulator], params: JSONParameters) -> None:
    """Write summary results from each simulation to summary file."""
    with open(
        params.output_folder / ("summary_file.csv"),
        "w",
        newline="",
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
                filewriter.writerow(["", "Inspections", "No strikes were insepcted"])
            if "wbs" in simulator.summary_results:
                suppression_results: List[Union[str, float]] = simulator.summary_results["wbs"]
                suppression_results.insert(0, "Suppressions")
                suppression_results.insert(0, "")
                filewriter.writerow(suppression_results)
            else:
                filewriter.writerow(["", "Suppressions", "No strikes were suppressed"])
            filewriter.writerow([])


if __name__ == "__main__":
    main()
