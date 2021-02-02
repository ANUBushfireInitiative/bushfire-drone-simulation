"""Module for the centralized coordinator/HQ controlling the UAVs and aircraft."""

from abc import abstractmethod
from typing import Dict, List, Set, Tuple

from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.fire_utils import Base, WaterTank
from bushfire_drone_simulation.lightning import Lightning


class UAVCoordinator:
    """Class for centrally coordinating UAVs."""

    def __init__(self, uavs: List[UAV], uav_bases: List[Base]):
        """Initialize coordinator."""
        self.uavs: List[UAV] = uavs
        self.uav_bases: List[Base] = uav_bases
        self.uninspected_strikes: Set[Lightning] = set()

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
        for (strike, _) in lightning_strikes:
            self.uninspected_strikes.remove(strike)


class WBCoordinator:
    """Class for centrally coordinating water bombers."""

    def __init__(
        self,
        water_bombers: List[WaterBomber],
        water_bomber_bases: Dict[str, List[Base]],
        water_tanks: List[WaterTank],
    ):
        """Initialize coordinator."""
        self.water_bombers: List[WaterBomber] = water_bombers
        self.water_bomber_bases_dict: Dict[str, List[Base]] = water_bomber_bases
        self.water_tanks: List[WaterTank] = water_tanks
        self.uninspected_strikes: Set[Lightning] = set()
        self.unsuppressed_strikes: Set[Lightning] = set()

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
