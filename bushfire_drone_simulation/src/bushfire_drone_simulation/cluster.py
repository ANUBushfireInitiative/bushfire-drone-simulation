"""Class for clustering lightning strikes."""
from math import inf, pi
from typing import List

import numpy as np
from matplotlib import path

from bushfire_drone_simulation.fire_utils import EARTH_RADIUS, Location, Target, average_location
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.units import Distance, Duration

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
        boundary_polygon: List[Location],
        radius: Distance,
        min_in_target: int,
    ) -> None:
        """Initialize a cluster.

        Args:
            points (List[Location]): points to cluster
            boundary_polygon (List[Location]): boundary polygon the points fall within
            radius (float): radius of circles to cluster with
            min_in_target (int): cut-off number of points within a circle for considering a target
        """
        self.radius = radius.get()
        self.polygon = boundary_polygon
        self.polygon_points = [(loc.lat, loc.lon) for loc in self.polygon]
        self.boundary = path.Path(self.polygon_points)
        self.min_in_target = min_in_target
        self.radius_in_deg = self.radius * 180 / (pi * EARTH_RADIUS)

    def create_circles(self) -> List[Circle]:
        """Create circles required for clustering."""
        if self.radius == 0:
            return []
        circles = []
        min_lat = inf
        max_lat = -inf
        min_lon = inf
        max_lon = -inf
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

    def cluster_points(
        self, points: List[Location], target_start: float, target_end: float, attraction_const: float, attraction_pwr: float
    ) -> List[Target]:
        """Clusters points based on Mean-Shift Clustering algorithm.

        Args:
            target_start (float): start time of target
            target_end (float): end time of target

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
                    for loc in points:
                        if circle.location.distance(loc) <= self.radius:
                            contained_locs.append(loc)
                    if not contained_locs:
                        circles.remove(circle)
                        continue
                    new_centre = average_location(contained_locs)
                    if circle.location.distance(new_centre) < EPSILON:
                        if len(contained_locs) >= self.min_in_target:
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
                # TODO(some function of contained points and radius) pylint: disable=fixme
                targets.append(
                    Target(
                        circle.location.lat,
                        circle.location.lon,
                        target_start,
                        target_end,
                        attraction_const,
                        attraction_pwr,
                        True,
                    )
                )
        return targets


class LightningCluster(Cluster):
    """Clusters lightning."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        lightning: List[Lightning],
        boundary_polygon: List[Location],
        radius: Distance,
        min_in_target: int,
        target_resolution: Duration,
        look_ahead: Duration,
        attraction_const: float,
        attraction_pwr: float,
    ) -> None:
        """Initialize lightning cluster.

        Args:
            lightning (List[Lightning]): lightning
            radius (float): radius of circles to cluster with
           min_in_target (int): cut-off number of strikes within a circle for considering a target
            target_resolution (float): time between recomputing targets
            look_ahead (float): consider all strikes that spawn in the next look_ahead time
        """
        super().__init__(boundary_polygon, radius, min_in_target)
        self.lightning = lightning
        self.target_resolution = target_resolution.get()
        self.look_ahead = look_ahead.get()
        self.attraction_const = attraction_const
        self.attraction_pwr = attraction_pwr

    def find_min_spawn_time(self) -> float:
        """Return the minimum spawn time of all strikes.

        Returns:
            float: minimum spawn time
        """
        min_time = inf
        for strike in self.lightning:
            if strike.spawn_time < min_time:
                min_time = strike.spawn_time
        return min_time

    def find_max_spawn_time(self) -> float:
        """Return the maximum spawn time of all strikes.

        Returns:
            float: maximum spawn time
        """
        max_time = -inf
        for strike in self.lightning:
            if strike.spawn_time > max_time:
                max_time = strike.spawn_time
        return max_time

    def generate_targets(self) -> List[Target]:
        """Generate all targets for lightning swarm.

        Returns:
            List[Target]: list of targets
        """
        target_list = []
        min_spawn_time = self.find_min_spawn_time()
        max_spawn_time = self.find_max_spawn_time()
        for start_time in np.arange(min_spawn_time, max_spawn_time, self.target_resolution):
            finish_time = start_time + self.look_ahead
            strikes_to_consider: List[Location] = []
            for strike in self.lightning:
                if strike.spawn_time >= start_time and strike.spawn_time <= finish_time:
                    assert isinstance(strike, Location)
                    strikes_to_consider.append(strike)
            targets = self.cluster_points(
                strikes_to_consider, start_time, start_time + self.target_resolution, self.attraction_const, self.attraction_pwr
            )
            target_list += targets
        return target_list
