"""Coordinators testing.

Compares meaningful attributes of coordinators
"""

from pathlib import Path
from statistics import mean
from typing import List, Optional, Tuple

import pytest
from _pytest.monkeypatch import MonkeyPatch

from bushfire_drone_simulation.fire_utils import Time
from bushfire_drone_simulation.main import run_simulation
from bushfire_drone_simulation.parameters import JSONParameters
from bushfire_drone_simulation.simulator import Simulator

FILE_LOC = Path(__file__)
PARAMS_LOC = FILE_LOC.parent / "parameters.json"


@pytest.fixture(name="simulations_list")
def fixture_simulations_list(
    monkeypatch: MonkeyPatch,
) -> List[Tuple[List[Simulator], JSONParameters]]:
    """Run a simple simulation and output the results."""
    monkeypatch.setattr("builtins.input", lambda _: "Y")
    to_return: List[Tuple[List[Simulator], JSONParameters]] = []
    to_return.append(
        (
            run_simulation(FILE_LOC.parent / "parameters.json"),
            JSONParameters(FILE_LOC.parent / "parameters.json"),
        )
    )
    return to_return


@pytest.mark.slow
def test_coordinator_properties(
    simulations_list: List[Tuple[List[Simulator], JSONParameters]]
) -> None:
    """Does the Minimise Mean Time coordinator have the lowest mean time."""
    for simulators, params in simulations_list:
        reprocess_max_time_simulation: Optional[Simulator] = None
        minimise_mean_time_simulation: Optional[Simulator] = None
        simple_simulation: Optional[Simulator] = None
        insertion_simulation: Optional[Simulator] = None
        for scenario_idx in range(len(params.scenarios)):
            if (
                str(params.get_attribute("scenario_name", scenario_idx))
                == "ReprocessMaxTimeCoordinator"
            ):
                reprocess_max_time_simulation = simulators[scenario_idx]
            if (
                str(params.get_attribute("scenario_name", scenario_idx))
                == "MinimiseMeanTimeCoordinator"
            ):
                minimise_mean_time_simulation = simulators[scenario_idx]
            if str(params.get_attribute("scenario_name", scenario_idx)) == "SimpleCoordinator":
                simple_simulation = simulators[scenario_idx]
            if str(params.get_attribute("scenario_name", scenario_idx)) == "InsertionCoordinator":
                insertion_simulation = simulators[scenario_idx]
        assert (
            reprocess_max_time_simulation is not None
        ), "Not testing Reprocess Max Time coordinator"
        assert (
            minimise_mean_time_simulation is not None
        ), "Not testing Minimise Mean Time coordinator"
        assert simple_simulation is not None, "Not testing Simple Time coordinator"
        assert insertion_simulation is not None, "Not testing Insertion Time coordinator"
        assert mean(get_inspection_times(minimise_mean_time_simulation)) >= mean(
            get_inspection_times(reprocess_max_time_simulation)
        ), "Minimise mean time returned a higher mean inspection time than Reprocess max time"
        assert mean(get_inspection_times(minimise_mean_time_simulation)) >= mean(
            get_inspection_times(insertion_simulation)
        ), "Minimise mean time returned a higher mean inspection time than Insertion"
        assert mean(get_inspection_times(minimise_mean_time_simulation)) >= mean(
            get_inspection_times(simple_simulation)
        ), "Minimise mean time returned a higher mean inspection time than Simple"
        assert max(get_inspection_times(minimise_mean_time_simulation)) <= max(
            get_inspection_times(reprocess_max_time_simulation)
        ), "Reprocess max time returned a higher maximum inspection time than Minimise mean time"
        assert mean(get_supression_times(minimise_mean_time_simulation)) >= mean(
            get_supression_times(reprocess_max_time_simulation)
        ), "Minimise mean time returned a higher mean supression time than Reprocess max time"
        assert mean(get_supression_times(minimise_mean_time_simulation)) >= mean(
            get_supression_times(insertion_simulation)
        ), "Minimise mean time returned a higher mean supression time than Insertion"
        assert mean(get_supression_times(minimise_mean_time_simulation)) >= mean(
            get_supression_times(simple_simulation)
        ), "Minimise mean time returned a higher mean supression time than Simple"
        assert max(get_supression_times(minimise_mean_time_simulation)) <= max(
            get_supression_times(reprocess_max_time_simulation)
        ), "Reprocess max time returned a higher max supression time than Minimise mean time"


def get_inspection_times(
    simulation: Simulator,
) -> List[float]:
    """Return list of inspection times of lightning strikes.

    Confirms that each strike was inspected.

    Args:
        simulation (Simulation): simulation that lightning strikes occured in

    Returns:
        List[float]: list of inspection times
    """
    inspection_times: List[float] = []
    for strike in simulation.lightning_strikes:
        assert strike.inspected_time is not None, f"Lightning strike {strike} was not inspected"
        inspection_times.append(
            Time.from_float(strike.inspected_time - strike.spawn_time).get("hr"),
        )
    return inspection_times


def get_supression_times(
    simulation: Simulator,
) -> List[float]:
    """Return list of supression times of lightning strikes.

    Confirms that all ignighted strikes were supressed.

    Args:
        simulation (Simulation): simulation that lightning strikes occured in

    Returns:
        List[float]: list of supression times
    """
    suppression_times: List[float] = []
    for strike in simulation.lightning_strikes:
        if strike.ignition:
            assert (
                strike.suppressed_time is not None
            ), f"Lightning strike {strike} ignighted but was not supressed"
            suppression_times.append(
                Time.from_float(strike.suppressed_time - strike.spawn_time).get("hr"),
            )
    return suppression_times
