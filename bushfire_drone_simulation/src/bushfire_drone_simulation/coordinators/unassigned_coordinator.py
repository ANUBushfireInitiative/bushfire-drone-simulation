"""Coordinator for coordinatoring unassigned drones."""
import os
from math import inf
from typing import List, Optional

import matplotlib.pyplot as plt
import numpy as np

from bushfire_drone_simulation.coordinators.abstract_coordinator import UnassignedCoordinator
from bushfire_drone_simulation.fire_utils import Location, average_location


class SimpleUnassignedCoordinator(UnassignedCoordinator):
    """Class for simple coordinator for unassigned uavs."""

    def assign_unassigned_uavs(  # pylint: disable=too-many-branches, too-many-statements
        self, current_time: float
    ) -> None:
        """Assign unassigned uavs."""
        if self.output_plots:
            uav_lats = [u.lat for u in self.uavs if u.event_queue.is_empty()]
            uav_lons = [u.lon for u in self.uavs if u.event_queue.is_empty()]
            assigned_uav_lats = [u.lat for u in self.uavs if not u.event_queue.is_empty()]
            assigned_uav_lons = [u.lon for u in self.uavs if not u.event_queue.is_empty()]
            poly_x = [point[0] for point in self.polygon_points]
            poly_y = [point[1] for point in self.polygon_points]
            plt.cla()
            plt.scatter(uav_lats, uav_lons)
            plt.scatter(assigned_uav_lats, assigned_uav_lons)
            plt.gca().set_aspect("equal")
            plt.plot(poly_x, poly_y)

            plt.savefig(
                os.path.join(
                    self.output_folder,
                    str(current_time) + " plot.png",
                )
            )
        for uav in self.uavs:  # pylint: disable=too-many-nested-blocks
            if uav.event_queue.is_empty():
                if self.outside_boundary(uav):
                    actual_loc = uav.intermediate_point(
                        self.centre_loc,
                        self.dt / (uav.distance(self.centre_loc) / uav.flight_speed),
                    )
                    base = self.uav_bases[
                        int(np.argmin(list(map(actual_loc.distance, self.uav_bases))))
                    ]
                    if uav.enough_fuel([actual_loc, base]) is not None:
                        uav.unassiged_aircraft_to_location(self.centre_loc, self.dt)
                    else:
                        uav.unassigned_target = None
                else:
                    contributing_locs: List[Location] = []
                    for other_uav in self.uavs:
                        if other_uav.id_no != uav.id_no and other_uav.event_queue.is_empty():
                            dist = uav.distance(other_uav)
                            if dist != 0:
                                contributing_locs.append(
                                    uav.plane_intermediate_point(
                                        other_uav,
                                        -self.uav_const * dist**self.uav_pwr,
                                    )
                                )
                    for target in self.targets:
                        if target.currently_active(current_time):
                            dist = uav.distance(target)
                            if dist != 0:
                                contributing_locs.append(
                                    uav.plane_intermediate_point(
                                        target,
                                        target.attraction_const * dist**target.attraction_power,
                                    )
                                )
                    prev_point = self.polygon[-1]
                    min_dist = inf
                    closest_boundary_point: Optional[Location] = None
                    for point in self.polygon:
                        closest_point = uav.closest_point_on_line(point, prev_point)
                        dist = uav.distance(closest_point)
                        if dist < min_dist:
                            min_dist = dist
                            closest_boundary_point = closest_point
                        prev_point = point
                    if min_dist != 0:
                        assert closest_boundary_point is not None
                        contributing_locs.append(
                            uav.plane_intermediate_point(
                                closest_boundary_point,
                                -self.boundary_const * min_dist**self.boundary_pwr,
                            )
                        )
                    if contributing_locs:
                        uav_target_loc = average_location(contributing_locs)
                        actual_loc = uav_target_loc
                        percentage = self.dt / (uav.distance(uav_target_loc) / uav.flight_speed)
                        if percentage < 1:
                            actual_loc = uav.intermediate_point(uav_target_loc, percentage)
                        if self.outside_boundary(actual_loc):
                            boundary_target = self.find_point_on_boundary(uav, actual_loc)
                            uav.unassigned_target = boundary_target
                        else:
                            base = self.uav_bases[
                                int(np.argmin(list(map(actual_loc.distance, self.uav_bases))))
                            ]
                            if uav.enough_fuel([actual_loc, base]) is not None:
                                uav.unassiged_aircraft_to_location(uav_target_loc, self.dt)
                            else:
                                uav.unassigned_target = None
        for uav in self.uavs:
            uav.go_to_base_when_necessary(self.uav_bases, current_time)
