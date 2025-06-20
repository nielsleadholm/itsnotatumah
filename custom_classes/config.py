"""Configuration classes for the experiment."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PlottingConfig:
    """Configuration for experiment plotting.

    Args:
        enabled: Whether to enable plotting
        save_path: Directory to save plots. If None, plots will be displayed
        plot_frequency: How often to plot (every N steps)
        plot_patch_features: Whether to plot patch features
        show_hypothesis_space: Whether to show the hypothesis space
        display_mlh_focus_plot: Whether to display the MLH path instead of all current
            hypotheses.
    """

    enabled: bool = False
    save_path: Optional[str] = None
    plot_frequency: int = 1
    plot_patch_features: bool = True
    show_hypothesis_space: bool = False
    display_mlh_focus_plot: bool = False
