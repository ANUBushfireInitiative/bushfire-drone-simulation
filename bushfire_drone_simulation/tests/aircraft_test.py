"""Aircraft testing."""

import os

from bushfire_drone_simulation.aircraft import Status
from bushfire_drone_simulation.main import run_simulation

FILE_LOC = os.path.realpath(__file__)
PARAMS_LOC = os.path.join(os.path.dirname(FILE_LOC), "input_data/parameters.json")


def test_times_chronological(monkeypatch):
    """Are the Aircrafts movements chronological."""
    monkeypatch.setattr("builtins.input", lambda _: "Y")
    for coordinator, _ in run_simulation(PARAMS_LOC):
        for uav in coordinator.uavs:
            for idx, update in enumerate(uav.past_locations):
                if idx != 0:
                    assert update.time > uav.past_locations[idx - 1].time, "uav.id was not chrono"
        for water_bomber in coordinator.water_bombers:
            for idx, update in enumerate(water_bomber.past_locations):
                if idx != 0:
                    assert (
                        update.time > water_bomber.past_locations[idx - 1].time
                    ), "water_bomber.id was not chrono"


def test_reasonable_fuel_refill(monkeypatch):
    """Does the Aircraft refill often enough."""
    monkeypatch.setattr("builtins.input", lambda _: "Y")
    for coordinator, _ in run_simulation(PARAMS_LOC):
        for uav in coordinator.uavs:
            time_full = uav.past_locations[0].time
            for update in uav.past_locations:
                if update.status == Status.WAITING_AT_BASE:
                    assert (
                        update.time - time_full
                    ).get() < uav.get_range().get() / uav.max_velocity.get(), (
                        "The UAV (uav.id) should have run out of fuel"
                    )
                    time_full = update.time
        for water_bomber in coordinator.water_bombers:
            time_full = water_bomber.past_locations[0].time
            for update in water_bomber.past_locations:
                if update.status == Status.WAITING_AT_BASE:
                    has_adequate_fuel = (
                        update.time - time_full
                    ).get() < water_bomber.get_range().get() / water_bomber.max_velocity.get()
                    assert (
                        has_adequate_fuel
                    ), "The Water Bomber (water_bomber.id) should have run out of fuel"
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
                        ), "UAV should have previously been going to base"
                    if update.status == Status.HOVERING:
                        assert (
                            uav.past_locations[idx - 1].status == Status.GOING_TO_STRIKE
                        ), "UAV should have previously been going to strike"
        for water_bomber in coordinator.water_bombers:
            for idx, update in enumerate(water_bomber.past_locations):
                if idx != 0:
                    if update.status == Status.WAITING_AT_BASE:
                        assert (
                            water_bomber.past_locations[idx - 1].status == Status.GOING_TO_BASE
                        ), "Water Bomber should have previously been going to base"
                    if update.status == Status.HOVERING:
                        assert (
                            water_bomber.past_locations[idx - 1].status == Status.GOING_TO_STRIKE
                        ), "Water Bomber should have previously been going to strike"
                    if update.status == Status.WAITING_AT_WATER:
                        assert (
                            water_bomber.past_locations[idx - 1].status == Status.GOING_TO_WATER
                        ), "Water Bomber should have previously been going to water"