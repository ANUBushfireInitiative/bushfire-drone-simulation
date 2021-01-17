"""Aircraft testing."""

import os

from bushfire_drone_simulation.aircraft import Status
from bushfire_drone_simulation.main import run_simulation
from bushfire_drone_simulation.units import Duration

FILE_LOC = os.path.realpath(__file__)
PARAMS_LOC = os.path.join(os.path.dirname(FILE_LOC), "parameters.json")


def test_times_chronological(monkeypatch):
    """Are the Aircrafts movements chronological."""
    monkeypatch.setattr("builtins.input", lambda _: "Y")
    for coordinator, _ in run_simulation(PARAMS_LOC):
        for uav in coordinator.uavs:
            for idx, update in enumerate(uav.past_locations):
                if idx != 0:
                    assert (
                        update.time >= uav.past_locations[idx - 1].time
                    ), f"The event updates of uav {uav.id_no} were not in chronological order"
        for water_bomber in coordinator.water_bombers:
            for idx, update in enumerate(water_bomber.past_locations):
                if idx != 0:
                    assert update.time >= water_bomber.past_locations[idx - 1].time, (
                        f"The event updates of water bomber {water_bomber.name} were not"
                        " in chronological order"
                    )


def test_reasonable_fuel_refill(monkeypatch):
    """Does the Aircraft refill often enough."""
    monkeypatch.setattr("builtins.input", lambda _: "Y")
    for coordinator, _ in run_simulation(PARAMS_LOC):
        for uav in coordinator.uavs:
            time_full = uav.past_locations[0].time
            for idx, update in enumerate(uav.past_locations):
                if idx != 0:
                    if uav.past_locations[idx - 1].status == Status.WAITING_AT_BASE:
                        time_full = update.time
                    if update.status == Status.WAITING_AT_BASE:
                        assert (update.time - time_full) - Duration(
                            1
                        ) <= uav.get_range().div_by_speed(
                            uav.max_velocity
                        ), f"UAV {uav.id_no} should have run out of fuel"
        for water_bomber in coordinator.water_bombers:
            time_full = water_bomber.past_locations[0].time
            for idx, update in enumerate(water_bomber.past_locations):
                if idx != 0:
                    if water_bomber.past_locations[idx - 1].status == Status.WAITING_AT_BASE:
                        time_full = update.time
                    if update.status == Status.WAITING_AT_BASE:
                        has_adequate_fuel = (
                            update.time - time_full
                        ) <= water_bomber.get_range().div_by_speed(water_bomber.max_velocity)
                        assert (
                            has_adequate_fuel
                        ), f"Water bomber {water_bomber.name} should have run out of fuel"
                        time_full = update.time


def test_aricraft_status(monkeypatch):  # pylint: disable=too-many-branches
    """Does the aircraft status alter reasonably."""
    monkeypatch.setattr("builtins.input", lambda _: "Y")
    for coordinator, _ in run_simulation(PARAMS_LOC):  # pylint: disable=too-many-nested-blocks
        for uav in coordinator.uavs:
            for idx, update in enumerate(uav.past_locations):
                if idx != 0:
                    if update.status == Status.WAITING_AT_BASE:
                        assert (
                            uav.past_locations[idx - 1].status == Status.GOING_TO_BASE
                        ), f"UAV {uav.id_no} should have previously been going to base"
                    if update.status == Status.HOVERING:
                        assert (
                            uav.past_locations[idx - 1].status == Status.GOING_TO_STRIKE
                        ), "UAV {uav.id_no} should have previously been going to strike"
        for water_bomber in coordinator.water_bombers:
            for idx, update in enumerate(water_bomber.past_locations):
                if idx != 0:
                    if update.status == Status.WAITING_AT_BASE:
                        assert (
                            water_bomber.past_locations[idx - 1].status == Status.GOING_TO_BASE
                        ), (
                            "Water Bomber {water_bomber.name} "
                            "should have previously been going to base"
                        )
                    if update.status == Status.HOVERING:
                        assert (
                            water_bomber.past_locations[idx - 1].status == Status.GOING_TO_STRIKE
                        ), (
                            "Water Bomber {water_bomber.name} "
                            "should have previously been going to strike"
                        )
                    if update.status == Status.WAITING_AT_WATER:
                        assert (
                            water_bomber.past_locations[idx - 1].status == Status.GOING_TO_WATER
                        ), (
                            "Water Bomber {water_bomber.name} "
                            "should have previously been going to water"
                        )
