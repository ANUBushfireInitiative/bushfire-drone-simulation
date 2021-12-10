"""Aircraft testing."""

from pathlib import Path
from typing import List

import pytest
from _pytest.monkeypatch import MonkeyPatch

from bushfire_drone_simulation.aircraft import Status
from bushfire_drone_simulation.main import run_simulation
from bushfire_drone_simulation.simulator import Simulator

FILE_LOC = Path(__file__)
PARAMS_LOC = FILE_LOC.parent / "parameters.json"


@pytest.fixture(name="simulations")
def fixture_simulations(monkeypatch: MonkeyPatch) -> List[Simulator]:
    """Run a simple simulation and output the results."""
    monkeypatch.setattr("builtins.input", lambda _: "Y")
    to_return = []
    to_return += run_simulation(FILE_LOC.parent / "parameters.json")
    return to_return


@pytest.mark.slow
def test_times_chronological(simulations: List[Simulator]) -> None:
    """Are the Aircrafts movements chronological."""
    for simulator in simulations:
        for uav in simulator.uavs:
            for idx, update in enumerate(uav.past_locations[1:]):
                assert (
                    update.time >= uav.past_locations[idx - 1].time
                ), f"The event updates of {uav.get_name()} were not in chronological order"
        for water_bomber in simulator.water_bombers:
            for idx, update in enumerate(water_bomber.past_locations[1:]):
                assert (
                    update.time >= water_bomber.past_locations[idx - 1].time
                ), f"The event updates of {water_bomber.name} were not in chronological order"


@pytest.mark.slow
def test_reasonable_fuel_refill(simulations: List[Simulator]) -> None:
    """Does the Aircraft refill often enough."""
    for simulator in simulations:
        for uav in simulator.uavs:
            time_full = uav.past_locations[0].time
            for idx, update in enumerate(uav.past_locations[1:]):
                if uav.past_locations[idx - 1].status == Status.WAITING_AT_BASE:
                    time_full = update.time
                if update.status == Status.WAITING_AT_BASE:
                    assert (
                        update.time - time_full
                    ) - 1 <= uav.get_range() / uav.flight_speed, (
                        f"{uav.get_name()} should have run out of fuel"
                    )
        for water_bomber in simulator.water_bombers:
            time_full = water_bomber.past_locations[0].time
            for idx, update in enumerate(water_bomber.past_locations[1:]):
                if water_bomber.past_locations[idx - 1].status == Status.WAITING_AT_BASE:
                    time_full = update.time
                if update.status == Status.WAITING_AT_BASE:
                    has_adequate_fuel = (
                        update.time - time_full
                    ) <= water_bomber.get_range() / water_bomber.flight_speed
                    assert (
                        has_adequate_fuel
                    ), f"{water_bomber.get_name()} should have run out of fuel"
                    time_full = update.time


@pytest.mark.slow
def test_aircraft_status(
    simulations: List[Simulator],
) -> None:  # pylint: disable=too-many-branches
    """Does the aircraft status alter reasonably."""
    for simulator in simulations:  # pylint: disable=too-many-nested-blocks
        for uav in simulator.uavs:
            for idx, update in enumerate(uav.past_locations[1:]):
                assert update.status not in [
                    Status.GOING_TO_WATER,
                    Status.WAITING_AT_WATER,
                ], f"{uav.get_name()} should not be waiting at or going to water"
                if update.status == Status.WAITING_AT_BASE:
                    assert (
                        uav.past_locations[idx - 1].status == Status.GOING_TO_BASE
                        or Status.WAITING_AT_BASE
                    ), f"{uav.get_name()} should have previously been going to base"
                if update.status == Status.HOVERING:
                    assert (
                        uav.past_locations[idx - 1].status != Status.WAITING_AT_BASE
                    ), f"{uav.get_name()} should have previously been going to strike"
        for water_bomber in simulator.water_bombers:
            for idx, update in enumerate(water_bomber.past_locations[1:]):
                if update.status == Status.WAITING_AT_BASE:
                    assert (
                        water_bomber.past_locations[idx - 1].status == Status.GOING_TO_BASE
                        or Status.WAITING_AT_BASE
                    ), f"{water_bomber.name} should have previously been going to base"
                if update.status == Status.HOVERING:
                    assert water_bomber.past_locations[idx - 1].status not in [
                        Status.WAITING_AT_BASE,
                        Status.WAITING_AT_WATER,
                    ], f"{water_bomber.name} should have previously been going to strike"
                if update.status == Status.WAITING_AT_WATER:
                    assert water_bomber.past_locations[idx - 1].status in [
                        Status.GOING_TO_WATER,
                        Status.WAITING_AT_WATER,
                    ], f"{water_bomber.name} should have previously been going to water"
