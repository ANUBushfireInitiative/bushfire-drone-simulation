"""Main entry point for bushfire-drone-simulation."""

import logging
from pathlib import Path
from sys import stderr
from typing import Dict, List, Type, Union

import typer
from tqdm import tqdm

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
from bushfire_drone_simulation.simulator import Simulator

_LOG = logging.getLogger(__name__)
app = typer.Typer()


UAV_COORDINATORS: Dict[
    str,
    Union[
        Type[MatlabUAVCoordinator],
        Type[NewStrikesFirstUAVCoordinator],
        Type[InsertionUAVCoordinator],
        Type[MinimiseMeanTimeUAVCoordinator],
    ],
] = {
    "MatlabUAVCoordinator": MatlabUAVCoordinator,
    "NewStrikesFirstUAVCoordinator": NewStrikesFirstUAVCoordinator,
    "InsertionUAVCoordinator": InsertionUAVCoordinator,
    "MinimiseMeanTimeUAVCoordinator": MinimiseMeanTimeUAVCoordinator,
}

WB_COORDINATORS: Dict[
    str,
    Union[
        Type[MatlabWBCoordinator],
        Type[NewStrikesFirstWBCoordinator],
        Type[InsertionWBCoordinator],
        Type[MinimiseMeanTimeWBCoordinator],
    ],
] = {
    "MatlabWBCoordinator": MatlabWBCoordinator,
    "NewStrikesFirstWBCoordinator": NewStrikesFirstWBCoordinator,
    "InsertionWBCoordinator": InsertionWBCoordinator,
    "MinimiseMeanTimeWBCoordinator": MinimiseMeanTimeWBCoordinator,
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
            simulator.uavs, simulator.uav_bases
        )
        wb_coordinator = WB_COORDINATORS[params.get_attribute("wb_coordinator", scenario_idx)](
            simulator.water_bombers, simulator.water_bomber_bases_dict, simulator.water_tanks
        )
        simulator.run_simulation(uav_coordinator, wb_coordinator)

        simulator.output_results(params, scenario_idx)
        to_return.append(simulator)
    return to_return


if __name__ == "__main__":
    main()
