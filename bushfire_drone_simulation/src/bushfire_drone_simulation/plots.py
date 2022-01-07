"""Module for generating various maplotlib plots of simulation data."""

from typing import Any, List


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
    """Genenrate a suppression time histogram.

    Args:
        axs (Any): axs
        suppression_times (List[float]): suppression_times
    """
    frequency_histogram(
        axs, suppression_times, "Histogram of suppression times", "Suppression time (Hours)"
    )
