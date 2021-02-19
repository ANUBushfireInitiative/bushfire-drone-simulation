"""Module for the centralized coordinator/HQ controlling the UAVs and aircraft."""

from abc import abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from matplotlib import path

from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.fire_utils import Base, Location, Target, WaterTank
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.parameters import JSONParameters
from bushfire_drone_simulation.precomupted import PreComputedDistances


class UAVCoordinator:
    """Class for centrally coordinating UAVs."""

    def __init__(
        self, uavs: List[UAV], uav_bases: List[Base], parameters: JSONParameters, scenario_idx: int
    ):
        """Initialize coordinator."""
        self.uavs: List[UAV] = uavs
        self.uav_bases: List[Base] = uav_bases
        self.uninspected_strikes: Set[Lightning] = set()
        self.precomputed: Optional[PreComputedDistances] = None
        self.parameters = parameters
        self.scenario_idx = scenario_idx

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


class UnassigedCoordinator:
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
        self.target_const: float = attributes["target_attraction_const"]
        self.target_pwr: float = attributes["target_attraction_power"]
        self.boundary_const: float = attributes["boundary_repulsion_const"]
        self.boundary_pwr: float = attributes["boundary_repulsion_power"]
        self.centre_loc: Location = Location(attributes["centre_lat"], attributes["centre_lon"])
        self.dt = attributes["dt"]
        self.polygon = polygon
        self.polygon_points = [(loc.lat, loc.lon) for loc in self.polygon]
        self.boundary = path.Path(self.polygon_points)
        self.output_folder = output_folder
        self.output: Dict[str, List[List[float]]] = {}
        self.output["uav_lats"] = []
        self.output["uav_lons"] = []
        self.output["assigned_uav_lats"] = []
        self.output["assigned_uav_lons"] = []

    @abstractmethod
    def assign_unassigned_uavs(self, current_time: float) -> None:
        """Assign unassigned uavs."""

    def outside_boundary(self, location: Location) -> bool:
        """Determine whether a given location falls outside the simulation boundary."""
        return not self.boundary.contains_point([location.lat, location.lon])


def average_location(locations: List[Location]) -> Location:
    """Return the average location given a list of locations."""
    lat_sum: float = 0
    lon_sum: float = 0
    for location in locations:
        lat_sum += location.lat
        lon_sum += location.lon
    return Location(lat_sum / len(locations), lon_sum / len(locations))


class WBCoordinator:
    """Class for centrally coordinating water bombers."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        water_bombers: List[WaterBomber],
        water_bomber_bases: Dict[str, List[Base]],
        water_tanks: List[WaterTank],
        parameters: JSONParameters,
        scenario_idx: int,
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
        # water bombers already updated to time of strike by simulator

    def lightning_strike_suppressed(self, lightning_strikes: List[Tuple[Lightning, str]]) -> None:
        """Lightning has been suppressed."""
        for (strike, _) in lightning_strikes:
            self.unsuppressed_strikes.remove(strike)
