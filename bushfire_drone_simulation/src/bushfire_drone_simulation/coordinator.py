"""Module for the centralized coordinator/HQ controlling the UAVs and aircraft."""

import queue

from bushfire_drone_simulation.aircraft import UAV, UAVStatus
from bushfire_drone_simulation.fire_utils import Time, minimum_distance
from bushfire_drone_simulation.lightning import Lightning


class CoordinatorParamaters:  # pylint: disable=too-few-public-methods
    """Parameters for Coordinator.

    TODO: Actually use in Coordinator below
    """

    uav_bases = None
    uavs = None
    water_bombers = None
    water_bomber_bases = None
    water_tanks = None


class Coordinator:
    """Class for centrally coordinating UAVs and water bombers."""

    uav_bases = None
    uavs = None
    water_bombers = None
    water_bomber_bases = None
    water_tanks = None
    events = queue.Queue(maxsize=0)

    def __init__(
        self, uavs, uav_bases, water_bombers, water_bomber_bases, water_tanks
    ):  # pylint: disable=too-many-arguments
        """Initialize coordinator."""
        self.uav_bases = uav_bases
        self.uavs = uavs
        self.water_bombers = water_bombers
        self.water_bomber_bases = water_bomber_bases
        self.water_tanks = water_tanks

    def get_next_event_time(self):
        """Return next event time."""
        if not self.events.empty():
            return self.events.queue[0]
        return None

    def lightning_update(self, lightning: Lightning = None):
        """Coordinator receives lightning strike that just occured."""
        # If lightning None then process next update, otherwise process lightning strike
        if lightning is None:
            self.events.get().get_uav.complete_update()
        else:
            # Determine nearest base to lightning strike
            base_index, _ = minimum_distance(self.uav_bases, lightning)
            min_arrival_time = Time("9999/99/99/99/99/99")
            best_uav = None
            for uav in self.uavs:
                # Check whether the UAV has enough fuel to
                # go to the lightning strike and then to the nearest base
                # and if so determine the arrival time at the lightning strike
                # updating if it is currently the minimum
                if uav.enough_fuel(
                    [lightning.position, self.uav_bases[base_index]], lightning.spawn_time
                ):
                    temp_arr_time = uav.arrival_time([lightning.position], lightning.spawn_time)
                    # print("lightning spawn time is ", lightning.spawn_time.time.get())
                    if temp_arr_time.time.get() < min_arrival_time.time.get():
                        min_arrival_time = temp_arr_time
                        best_uav = uav
            if best_uav is not None:
                # There exists a UAV that has enough fuel,
                # send it to the lightning strike and then to refuel
                best_uav.update_position(
                    lightning.position, lightning.spawn_time, UAVStatus.WAITING
                )
                print(best_uav.id_no)
                print(lightning.spawn_time.time.get() - min_arrival_time.time.get())
                lightning.inspected(best_uav, min_arrival_time)  # change location of this in future

            else:
                # There are no UVAs that can reach the lighnting strike without refuling
                # Try going via a base to refuel
                self.via_base(lightning, base_index)

        for uav in self.uavs:
            uav.consider_going_to_base(self.uav_bases, lightning.spawn_time)

    def via_base(self, lightning: Lightning, base_index: int):
        """Via base."""
        min_arrival_time = Time("9999/99/99/99/99/99")
        best_uav = None
        via_base = None
        for uav in self.uavs:
            for uav_base in self.uav_bases:
                if uav.enough_fuel(
                    [uav_base, lightning.position, self.uav_bases[base_index]],
                    lightning.spawn_time,
                ):
                    temp_arr_time = uav.arrival_time(
                        self, [uav_base, lightning.position], lightning.spawn_time
                    )
                    if temp_arr_time < min_arrival_time:
                        min_arrival_time = temp_arr_time
                        best_uav = uav
                        via_base = uav_base
        if best_uav is not None:
            best_uav.update_position(via_base.position, lightning.spawn_time, UAVStatus.WAITING)
            best_uav.update_position(lightning.position, lightning.spawn_time, UAVStatus.WAITING)
            lightning.inspected(best_uav, min_arrival_time)  # change location of this in future
        else:
            print("no uavs")

    def ignition_update(self, ignition: Lightning = None):
        """Coordinator receives ignition strike that just occured."""
        # If lightning None then process next update, otherwise process lightning strike
        if ignition is None:
            self.events.get().get_uav.complete_update()
        else:
            base_index, _ = minimum_distance(self.water_bomber_bases, ignition)
            min_arrival_time = Time("9999/99/99/99/99/99")
            best_water_bomber = None
            for water_bomber in self.water_bombers:
                if water_bomber.enough_water():
                    if water_bomber.enough_fuel(
                        [ignition.location, self.water_bomber_bases[base_index]],
                        ignition.spawn_time,
                    ):
                        temp_arr_time = water_bomber.arrival_time(
                            [ignition.location], ignition.spawn_time
                        )
                    if temp_arr_time < min_arrival_time:
                        min_arrival_time = temp_arr_time
                        best_water_bomber = water_bomber

            if best_water_bomber is not None:
                # Want to go to base then lightning
                best_water_bomber.update_position(
                    ignition.position, ignition.spawn_time, UAVStatus.WAITING
                )
                ignition.inspected_by(best_water_bomber)
                ignition.inspected_time(min_arrival_time)


class Event:
    """Class for storing events."""

    time: Time
    uav: UAV

    def __init__(self, time: Time, uav: UAV):
        """Initialize Event."""
        self.time = time
        self.uav = uav

    def get_time(self):
        """Return time of event."""
        return self.time

    def get_uav(self):
        """Return uav of event."""
        return self.uav
