"""Insertion coordinator minimizing mean inspection/supression time.

This coordinator aims to minimise the mean inspection/supression time of the lightning strikes
by finding the place within each aircrafts list of locations to 'insert' a recent strike
to visit that minimizes this value.
It does not consider also going via a base/water tank to facilitate 'inserting' this extra
strike and rather discounts the option if it does not possess enough fuel or water.

"""

import logging
from typing import Callable, Dict, List

from bushfire_drone_simulation.coordinators.minimise_mean_time_coordinator import (
    MinimiseMeanTimeUAVCoordinator,
    MinimiseMeanTimeWBCoordinator,
)
from bushfire_drone_simulation.fire_utils import Base, WaterTank
from bushfire_drone_simulation.parameters import JSONParameters
from bushfire_drone_simulation.uav import UAV
from bushfire_drone_simulation.water_bomber import WaterBomber

_LOG = logging.getLogger(__name__)


class ReprocessMaxTimeUAVCoordinator(MinimiseMeanTimeUAVCoordinator):
    """Insertion UAV Coordinator.

    Coordinator will try to insert the new strike in between the uavs current tasks
    and minimise the new strikes inspection time.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        uavs: List[UAV],
        uav_bases: List[Base],
        parameters: JSONParameters,
        scenario_idx: int,
        prioritisation_function: Callable[[float, float], float],
    ):
        """Initialize coordinator."""
        super().__init__(uavs, uav_bases, parameters, scenario_idx, prioritisation_function)
        self.reprocess_max: bool = True


class ReprocessMaxTimeWBCoordinator(MinimiseMeanTimeWBCoordinator):
    """Insertion water bomber coordinator.

    Coordinator will try to insert the new strike in between the uavs current tasks
    and minimise the new strikes inspection time.
    """

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
        super().__init__(
            water_bombers,
            water_bomber_bases,
            water_tanks,
            parameters,
            scenario_idx,
            prioritisation_function,
        )
        self.reprocess_max = True
