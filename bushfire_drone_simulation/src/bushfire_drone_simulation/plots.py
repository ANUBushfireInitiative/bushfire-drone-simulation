"""Module for generating various maplotlib plots of simulation data."""

from math import isinf
from typing import Any, List, Sequence

import matplotlib.pyplot as plt

from bushfire_drone_simulation.fire_utils import Time, WaterTank
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.units import Volume
from bushfire_drone_simulation.water_bomber import WaterBomber


def frequency_histogram(
    axs: Any,
    values: List[float],
    title: str,
    xlabel: str,
    bins: int = 20,
) -> None:
    """Shorthand for generating a simple histogram frequency plot on a set of matplotlib axes.

    Args:
        axs (Any): axs
        values (List[float]): values
        title (str): title
        xlabel (str): xlabel
        bins (int): bins
    """
    axs.hist(values, bins=bins)
    axs.set_title(title)
    axs.set(xlabel=xlabel, ylabel="Frequency")
    axs.set_xlim(left=0)
    axs.set_ylim(bottom=0)


def inspection_time_histogram(axs: Any, inspection_times: List[float]) -> None:
    """Generate an inspection time histogram.

    Args:
        axs (Any): axs
        inspection_times (List[float]): inspection_times
    """
    frequency_histogram(
        axs, inspection_times, "Histogram of UAV inspection times", "Inspection time (Hours)"
    )


def suppression_time_histogram(axs: Any, suppression_times: List[float]) -> None:
    """Generate a suppression time histogram.

    Args:
        axs (Any): axs
        suppression_times (List[float]): suppression_times
    """
    frequency_histogram(
        axs, suppression_times, "Histogram of suppression times", "Suppression time (Hours)"
    )


def suppressions_per_bomber_plot(axs: Any, water_bombers: Sequence[WaterBomber]) -> None:
    """Generate a bar chart displaying the number of suppressions per water bomber.

    Args:
        axs (Any): axs
        water_bombers (List[WaterBomber]): water bombers
    """
    water_bomber_names = [wb.name for wb in water_bombers]
    num_suppressed = [len(wb.strikes_visited) for wb in water_bombers]
    axs.set_title("Lightning strikes suppressed per water bomber")
    axs.bar(water_bomber_names, num_suppressed)
    axs.tick_params(labelrotation=90)


def water_tank_plot(axs: Any, water_tanks: Sequence[WaterTank]) -> None:
    """Generate a bar chart of water tank levels before and after supression.

    Args:
        axs (Any): axs
        water_tanks (List[WaterTank]): water tanks
    """
    water_tank_ids = [i for i, _ in enumerate(water_tanks)]
    axs.set_title("Water tank levels after suppression")
    axs.bar(
        water_tank_ids,
        [
            Volume(wt.initial_capacity).get(units="kL")
            for wt in water_tanks
            if not isinf(wt.initial_capacity)
        ],
        label="Full Capacity",
        color="orange",
    )
    axs.bar(
        water_tank_ids,
        [Volume(wt.capacity).get(units="kL") for wt in water_tanks],
        label="Final Level",
        color="blue",
    )
    axs.legend()
    axs.set(ylabel="kL")


def risk_rating_plot(lightning: List[Lightning]) -> None:
    """Generate inspection against strike time plot coloured by risk rating.

    Args:
        lightning (List[Lightning]): lightning
    """
    spawn_times = [
        Time.from_float(strike.spawn_time).get("hr")
        for strike in lightning
        if strike.inspected_time is not None
    ]
    inspection_times = [
        Time.from_float(strike.inspected_time - strike.spawn_time).get("hr")
        for strike in lightning
        if strike.inspected_time is not None
    ]
    risk_ratings = [strike.risk_rating for strike in lightning if strike.inspected_time is not None]
    plt.scatter(spawn_times, inspection_times, c=risk_ratings, cmap="viridis")
    plt.xlabel("Strike time (Hours)")
    plt.ylabel("Inspection time (Hours)")
    plt.colorbar()
