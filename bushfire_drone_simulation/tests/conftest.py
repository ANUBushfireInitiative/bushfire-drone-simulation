"""Fixtures for pytest."""

from functools import reduce
from pathlib import Path
from typing import Any, List, Tuple

import pytest

from bushfire_drone_simulation.parameters import JSONParameters
from bushfire_drone_simulation.simulator import Simulator, run_simulations

FILE_LOC = Path(__file__)
PARAMS_LOC = FILE_LOC.parent / "parameters.json"


@pytest.fixture(name="simulations_list", scope="session")
def fixture_simulations_list(
    session_mocker: Any, tmpdir_factory: Any
) -> List[Tuple[List[Simulator], JSONParameters]]:
    """Run test simulations and return with corresponding parameters."""
    session_mocker.patch("builtins.input", return_value="Y")
    to_return: List[Tuple[List[Simulator], JSONParameters]] = []
    params = JSONParameters(PARAMS_LOC)
    output_folder = Path(tmpdir_factory.mktemp("output"))
    params.output_folder = output_folder
    for scenario in params.scenarios:
        scenario["output_folder_name"] = output_folder
    to_return.append((run_simulations(params, use_parallel=False), params))
    return to_return


@pytest.fixture(name="simulations")
def fixture_simulations(
    simulations_list: List[Tuple[List[Simulator], JSONParameters]]
) -> List[Simulator]:
    """Get a list of all test simulations."""
    return reduce(list.__add__, [pair[0] for pair in simulations_list])
