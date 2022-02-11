"""Module for the centralized coordinator/HQ controlling the UAVs and aircraft."""

from abc import abstractmethod
from math import inf
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from matplotlib import path

from bushfire_drone_simulation.fire_utils import Base, Location, Target, WaterTank, assert_bool
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.parameters import JSONParameters
from bushfire_drone_simulation.precomputed import PreComputedDistances
from bushfire_drone_simulation.uav import UAV
from bushfire_drone_simulation.water_bomber import WaterBomber


class UAVCoordinator:
    """Abstract class for coordinating UAVs."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        uavs: List[UAV],
        uav_bases: List[Base],
        parameters: JSONParameters,
        scenario_idx: int,
        prioritisation_function: Callable[[float, float], float],
    ):
        """Initialise UAV Coordinator.

        Args:
            uavs (List[UAV]): List of UAVs (Must match list of uavs in simulator)
            uav_bases (List[Base]): List of UAV bases (Must match list of bases in simulator)
            parameters (JSONParameters): parameters
            scenario_idx (int): scenario_idx
        """
        self.uavs: List[UAV] = uavs
        self.uav_bases: List[Base] = uav_bases
        self.uninspected_strikes: Set[Lightning] = set()
        self.precomputed: Optional[PreComputedDistances] = None
        self.parameters = parameters
        self.scenario_idx = scenario_idx
        self.prioritisation_function = prioritisation_function

    def accept_precomputed_distances(self, precomputed: PreComputedDistances) -> None:
        """Accept precomputed distance class with distances already evaluated."""
        self.precomputed = precomputed

    def new_strike(self, lightning: Lightning) -> None:
        """Decide on uavs movement with new strike."""
        self.uninspected_strikes.add(lightning)
        self.process_new_strike(lightning)

    @abstractmethod
    def process_new_strike(self, lightning: Lightning) -> None:
        """Decide on uavs movement with new strike."""
        # Uavs already updated to time of strike by simulator

    def lightning_strike_inspected(self, lightning_strikes: List[Tuple[Lightning, int]]) -> None:
        """Lightning has been inspected, remove from uninspected strikes."""
        for strike, _ in lightning_strikes:
            try:
                self.uninspected_strikes.remove(strike)
            except KeyError:
                assert False, f"{strike.id_no} was inspected but not in set of uninspected strikes"


class UnassignedCoordinator:
    """Class for centrally coordinatoring unassiged aircraft."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        uavs: List[UAV],
        uav_bases: List[Base],
        targets: List[Target],
        output_folder: Path,
        polygon: List[Location],
        attributes: Dict[str, Any],
    ) -> None:
        """Initialize unassigned drone coordinator."""
        self.uavs = uavs
        self.uav_bases = uav_bases
        self.targets = targets
        self.uav_const: float = attributes["uav_repulsion_const"]
        self.uav_pwr: float = attributes["uav_repulsion_power"]
        self.boundary_const: float = attributes["boundary_repulsion_const"]
        self.boundary_pwr: float = attributes["boundary_repulsion_power"]
        if "output_plots" in attributes:
            self.output_plots: bool = assert_bool(
                attributes["output_plots"],
                "Expected a bool in 'unassigned_drones/output_plots' but got '"
                + str({attributes["output_plots"]})
                + "'",
            )
        else:
            self.output_plots = False
        self.centre_loc: Location = Location(attributes["centre_lat"], attributes["centre_lon"])
        self.dt = attributes["dt"]
        self.polygon = polygon
        self.polygon_points = [(loc.lat, loc.lon) for loc in self.polygon]
        self.boundary = path.Path(self.polygon_points)
        self.output_folder = output_folder

    @abstractmethod
    def assign_unassigned_uavs(self, current_time: float) -> None:
        """Assign unassigned uavs."""

    def outside_boundary(self, location: Location) -> bool:
        """Determine whether a given location falls outside the simulation boundary."""
        return not self.boundary.contains_point([location.lat, location.lon])

    def find_point_on_boundary(self, inside_point: Location, outside_point: Location) -> Location:
        """Return point on boundary where the line between the inside and outside points intersect.

        Return the closest point to inside_point if there are multiple intersections.
        """
        prev_point = self.polygon[-1]
        min_dist = inf
        closest_boundary_point: Optional[Location] = None
        for point in self.polygon:
            intersection_point = intersection(inside_point, outside_point, point, prev_point)
            if intersection_point is not None:
                dist = inside_point.distance(intersection_point)
                if dist < min_dist:
                    min_dist = dist
                    closest_boundary_point = intersection_point
            prev_point = point
        assert closest_boundary_point is not None
        epsilon = 0.001
        if inside_point.lat > closest_boundary_point.lat:
            closest_boundary_point.lat += epsilon
        else:
            closest_boundary_point.lat -= epsilon
        if inside_point.lon < closest_boundary_point.lon:
            closest_boundary_point.lon += epsilon
        else:
            closest_boundary_point.lon -= epsilon
        return closest_boundary_point


def intersection(
    loc_1: Location, loc_2: Location, loc_3: Location, loc_4: Location
) -> Optional[Location]:
    """Return the intersection between the line segments connecting loc 1 and 2 and loc 3 and 4.

    Or None if they do not intersect
    """
    if ccw(loc_1, loc_3, loc_4) != ccw(loc_2, loc_3, loc_4) and ccw(loc_1, loc_2, loc_3) != ccw(
        loc_1, loc_2, loc_4
    ):
        grad_1 = (loc_1.lat - loc_2.lat) / (loc_1.lon - loc_2.lon)
        grad_2 = (loc_3.lat - loc_4.lat) / (loc_3.lon - loc_4.lon)
        int_1 = -grad_1 * loc_1.lon + loc_1.lat
        ret_lon = (grad_2 * loc_3.lon - loc_3.lat + int_1) / (grad_2 - grad_1)
        ret_lat = grad_1 * ret_lon + int_1
        return Location(ret_lat, ret_lon)
    return None


def ccw(loc_1: Location, loc_2: Location, loc_3: Location) -> bool:
    """Return whether or not loc_1, loc_2 and loc_3 are ordered counterclockwise."""
    return (loc_3.lat - loc_1.lat) * (loc_2.lon - loc_1.lon) > (loc_2.lat - loc_1.lat) * (
        loc_3.lon - loc_1.lon
    )


class WBCoordinator:
    """Class for centrally coordinating water bombers."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        water_bombers: List[WaterBomber],
        water_bomber_bases: Dict[str, List[Base]],
        water_tanks: List[WaterTank],
        parameters: JSONParameters,
        scenario_idx: int,
        prioritisation_function: Callable[[float, float], float],
    ):
        """Initialize coordinator."""
        self.water_bombers: List[WaterBomber] = water_bombers
        self.water_bomber_bases_dict: Dict[str, List[Base]] = water_bomber_bases
        self.water_tanks: List[WaterTank] = water_tanks
        self.uninspected_strikes: Set[Lightning] = set()
        self.unsuppressed_strikes: Set[Lightning] = set()
        self.precomputed: Optional[PreComputedDistances] = None
        self.parameters = parameters
        self.scenario_idx = scenario_idx
        self.prioritisation_function = prioritisation_function

    def accept_precomputed_distances(self, precomputed: PreComputedDistances) -> None:
        """Accept precomputed distance class with distances already evaluated."""
        self.precomputed = precomputed

    def new_strike(self, lightning: Lightning) -> None:
        """Decide on water bombers movement with new strike."""
        self.uninspected_strikes.add(lightning)
        self.process_new_strike(lightning)

    @abstractmethod
    def process_new_strike(self, lightning: Lightning) -> None:
        """Decide on water bombers movement with new strike."""
        # Water bombers already updated to time of strike by simulator

    def new_ignition(self, ignition: Lightning) -> None:
        """Decide on water bombers movement with new ignition."""
        print("hellooooo")
        self.unsuppressed_strikes.add(ignition)
        print("adding " + str(ignition.id_no) + " to unsuppressed_strikes")
        self.process_new_ignition(ignition)

    @abstractmethod
    def process_new_ignition(self, ignition: Lightning) -> None:
        """Decide on water bombers movement with new ignition."""
        # Water bombers already updated to time of strike by simulator

    def lightning_strike_suppressed(self, lightning_strikes: List[Tuple[Lightning, str]]) -> None:
        """Lightning has been suppressed."""
        for (strike, _) in lightning_strikes:
            self.unsuppressed_strikes.remove(strike)
