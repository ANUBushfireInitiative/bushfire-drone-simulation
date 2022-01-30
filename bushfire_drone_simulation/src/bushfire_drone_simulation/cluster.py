"""Class for clustering lightning strikes."""
import math
from math import pi
from typing import List

import numpy as np
from matplotlib import path

from bushfire_drone_simulation.coordinators.abstract_coordinator import average_location
from bushfire_drone_simulation.fire_utils import EARTH_RADIUS, Location

EPSILON = 0.01


class Circle:
    """Class of attributes for circle used for clustering."""

    def __init__(self, location: Location, contained_points: int, target: bool):
        """Initialize circle.

        Args:
            location (Location): location of centre
            contained_points (int): number of points contained in circle
            target (bool): True if this circle is a target, False otherwise
        """
        self.location = location
        self.contained_points = contained_points
        self.target = target


class Cluster:
    """Clusters points based on the Mean-Shift Clustering algorithm."""

    def __init__(
        self,
        points: List[Location],
        boundary_polygon: List[Location],
        radius: float,
        min_in_target: int,
    ) -> None:
        """Initialize a cluster.

        Args:
            points (List[Location]): points to cluster
            boundary_polygon (List[Location]): boundary polygon the points fall within
            radius (float): radius of circles to cluster with
            min_in_target (int): cut-off number of points within a circle for considering a target
        """
        self.points = points
        self.radius = radius
        self.polygon = boundary_polygon
        self.polygon_points = [(loc.lat, loc.lon) for loc in self.polygon]
        self.boundary = path.Path(self.polygon_points)
        self.min_in_target = min_in_target
        self.radius_in_deg = radius * 180 / (pi * EARTH_RADIUS)

    def create_circles(self) -> List[Circle]:
        """Create circles required for clustering."""
        circles = []
        min_lat = math.inf
        max_lat = -math.inf
        min_lon = math.inf
        max_lon = -math.inf
        for point in self.polygon:
            if point.lat > max_lat:
                max_lat = point.lat
            if point.lat < min_lat:
                min_lat = point.lat
            if point.lon > max_lon:
                max_lon = point.lon
            if point.lon < min_lon:
                min_lon = point.lon
        for lat in np.arange(min_lat, max_lat, self.radius_in_deg):
            for lon in np.arange(min_lon, max_lon, self.radius_in_deg):
                if self.boundary.contains_point([lat, lon]):
                    circles.append(Circle(Location(lat, lon), 0, False))
        return circles

    def refine_circles(self, circles: List[Circle]) -> None:
        """Remove any circles whose centre falls within another circle and contains less points.

        Args:
            circles (List[Circle]): list of circles

        Returns:
            List[Circle]: refined list of circles
        """
        for idx, circle1 in enumerate(circles):
            for circle2 in circles[idx + 1 :]:
                if circle1.location.distance(circle2.location) < self.radius:
                    if circle1.contained_points > circle2.contained_points:
                        circles.remove(circle2)
                    else:
                        circles.remove(circle1)
                        break

    def cluster_points(self) -> List[Location]:
        """Clusters points based on Mean-Shift Clustering algorithm.

        Returns:
            List[Location]: list of targets
        """
        circles = self.create_circles()
        loop = True
        while loop:
            loop = False
            for circle in circles:
                if not circle.target:
                    loop = True
                    contained_locs = []
                    for loc in self.points:
                        if circle.location.distance(loc) <= self.radius:
                            contained_locs.append(loc)
                    if not contained_locs:
                        circles.remove(circle)
                        continue
                    new_centre = average_location(contained_locs)
                    if circle.location.distance(new_centre) < EPSILON:
                        if len(contained_locs) > self.min_in_target:
                            circle.target = True
                        else:
                            circles.remove(circle)
                            continue
                    circle.location = new_centre
                    circle.contained_points = len(contained_locs)
            self.refine_circles(circles)
        targets = []
        for circle in circles:
            if circle.target:
                targets.append(circle.location)
        return targets


# class LightningCluster:
#     """Clusters lightning."""

#     def __init__(
#         self,
#         lightning: List[Lightning],
#         radius: float,
#         min_in_target: int,
#         target_resolution: float,
#         look_ahead: float,
#     ) -> None:
#         """Initialize lightning cluster

#         Args:
#             lightning (List[Lightning]): lightning
#             radius (float): radius of circles to cluster with
#            min_in_target (int): cut-off number of strikes within a circle for considering a target
#             target_resolution (float): time between recomputing targets
#             look_ahead (float): consider all strikes that spawn in the next look_ahead time
#         """
#         # TODO(make these not times) #pylint: disable=fixme
#         self.lightning = lightning
#         self.radius = radius
