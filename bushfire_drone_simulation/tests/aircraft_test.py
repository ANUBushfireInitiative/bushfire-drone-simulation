"""Aircraft testing."""

from pathlib import Path
from typing import List, Sequence

import pytest
from _pytest.monkeypatch import MonkeyPatch

from bushfire_drone_simulation.aircraft import EPSILON, Aircraft, Status, WaterBomber
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
        for aircraft in [*simulator.uavs, *simulator.water_bombers]:
            for idx, update in enumerate(aircraft.past_locations[1:]):
                assert (
                    update.time >= aircraft.past_locations[idx].time
                ), f"The event updates of {aircraft.get_name()} were not in chronological order"


@pytest.mark.slow
def test_reasonable_fuel_refill(simulations: List[Simulator]) -> None:
    """Does the Aircraft refill often enough."""
    for simulator in simulations:
        for aircraft in [*simulator.uavs, *simulator.water_bombers]:
            time_full = aircraft.past_locations[0].time
            for update in aircraft.past_locations[1:]:
                if update.status == Status.WAITING_AT_BASE:
                    assert (
                        update.time - time_full
                    ) - 1 <= aircraft.get_range() / aircraft.flight_speed, (
                        f"{aircraft.get_name()} should have run out of fuel"
                    )
                    time_full = update.time


@pytest.mark.slow
def test_aircraft_status(
    simulations: List[Simulator],
) -> None:  # pylint: disable=too-many-branches
    """Does the aircraft status alter reasonably."""
    for simulator in simulations:  # pylint: disable=too-many-nested-blocks
        for aircraft in [*simulator.uavs, *simulator.water_bombers]:
            for idx, update in enumerate(aircraft.past_locations[1:]):
                if update.status == Status.WAITING_AT_BASE:
                    assert (
                        aircraft.past_locations[idx - 1].status == Status.GOING_TO_BASE
                        or Status.WAITING_AT_BASE
                    ), f"{aircraft.get_name()} should have previously been going to base"
                if update.status == Status.HOVERING:
                    assert (
                        aircraft.past_locations[idx - 1].status != Status.WAITING_AT_BASE
                    ), f"{aircraft.get_name()} should have previously been going to strike"
                if update.status == Status.WAITING_AT_WATER:
                    assert isinstance(
                        aircraft, WaterBomber
                    ), f"{aircraft.get_name()} should not be waiting at water"
                    assert aircraft.past_locations[idx - 1].status in [
                        Status.GOING_TO_WATER,
                        Status.WAITING_AT_WATER,
                    ], f"{aircraft.name} should have previously been going to water"
                assert (
                    isinstance(aircraft, WaterBomber) or update.status != Status.GOING_TO_WATER
                ), f"{aircraft.get_name()} should not be waiting at or going to water"


@pytest.mark.slow
def test_aircraft_speed(simulations: List[Simulator]) -> None:
    """Does the Aircraft refill often enough."""
    for simulator in simulations:
        for aircraft in [*simulator.uavs, *simulator.water_bombers]:
            for idx, update in enumerate(aircraft.past_locations[1:]):
                prev_update = aircraft.past_locations[idx - 1]
                distance = update.distance(prev_update)
                time = update.time - prev_update.time
                assert (
                    aircraft.flight_speed + EPSILON >= distance / time
                ), f"{aircraft.get_name()} exceeded flight speed"
