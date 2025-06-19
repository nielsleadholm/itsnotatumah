"""Custom experiment class for ultrasound experiments."""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from tbp.monty.frameworks.experiments import MontyObjectRecognitionExperiment

from .plotting import plot_combined_figure


@dataclass
class FeatureLogger:
    """Logger to store features for plotting."""

    column_points: List[np.ndarray] = field(default_factory=list)
    center_edge: Optional[Tuple[float, float]] = None
    fitted_circle: Optional[Tuple[float, float, float]] = None
    point_normal: Optional[np.ndarray] = None
    principal_curvatures: Optional[np.ndarray] = None
    mean_depth: float = 0.0

    def update(self, **kwargs):
        """Update feature values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def get_features(self):
        """Get all features as a dictionary."""
        return {
            "column_points": self.column_points,
            "center_edge": self.center_edge,
            "fitted_circle": self.fitted_circle,
            "point_normal": [self.point_normal]
            if self.point_normal is not None
            else [None],
            "principal_curvatures": self.principal_curvatures
            if self.principal_curvatures is not None
            else [0, 0],
            "mean_depth": self.mean_depth,
        }


class UltrasoundExperiment(MontyObjectRecognitionExperiment):
    """Custom experiment class that adds plotting functionality."""

    def __init__(self, config):
        super().__init__(config)
        self.plotting_config = config.get("plotting_config")
        self.feature_logger = FeatureLogger()

    def setup_experiment(self, config):
        """Set up the experiment and store plotting config."""
        super().setup_experiment(config)
        self.feature_logger = FeatureLogger()

    def run_episode_steps(self):
        """Run episode steps with optional plotting."""
        for loader_step, observation in enumerate(self.dataloader):
            # Process the observation first to compute features
            if self.model.is_motor_only_step:
                self.model.pass_features_directly_to_motor_system(observation)
            else:
                self.model.step(observation)

            # Extract features for plotting if enabled
            if (
                self.plotting_config
                and self.plotting_config.get("enabled", False)
                and loader_step % self.plotting_config.get("plot_frequency", 1) == 0
            ):
                agent_id = self.model.motor_system._policy.agent_id
                # Get input image and patch from the patch sensor
                patch_data = observation[agent_id]["patch"]

                input_image = patch_data["img"]
                patch_image = patch_data["img"]
                depth = patch_data["patch_depth"]

                # Get features from the sensor module
                sensor_module = self.model.sensor_modules[0]
                features = sensor_module.plotting_data

                # Extract plotting data
                all_column_points = features.get("column_points", [])
                center_edge_point = features.get("center_edge", None)
                fitted_circle = features.get("fitted_circle", None)
                point_normal = features.get("point_normal", None)
                observed_locations = features.get("observed_locations", [])
                normal_rel_world = features.get("normal_rel_world", [])
                curvature = (
                    features.get("principal_curvatures", [0, 0])[0]
                    if features.get("principal_curvatures") is not None
                    else 0
                )
                depth_meters = features.get(
                    "mean_depth", depth
                )  # Fallback to patch_depth if not in features

                # Determine save path if enabled
                save_path = None
                if self.plotting_config.get("save_path"):
                    os.makedirs(self.plotting_config["save_path"], exist_ok=True)
                    save_path = os.path.join(
                        self.plotting_config["save_path"], f"step_{loader_step}.png"
                    )

                # Plot based on config
                if self.plotting_config.get("plot_patch_features", False):
                    full_image = self.dataloader.dataset.env.get_full_image()

                    # Convert to numpy array if needed
                    if not isinstance(full_image, np.ndarray):
                        try:
                            full_image = np.array(full_image, dtype=np.float32)
                        except Exception as e:
                            print(f"Error converting image to numpy array: {e}")
                            full_image = patch_data["img"]  # Fallback to patch image

                    plot_combined_figure(
                        input_image=full_image,
                        patch_image=patch_data["img"],
                        all_column_points_tuples=all_column_points,
                        center_edge_point=center_edge_point,
                        fitted_circle=fitted_circle,
                        point_normal=point_normal,
                        curvature=curvature,
                        depth_meters=depth_meters,
                        observed_locations=observed_locations,
                        normal_rel_world=normal_rel_world,
                        save_path=save_path,
                        show_hypothesis_space=self.plotting_config.get(
                            "show_hypothesis_space", False
                        ),
                        lm_instance=self.model.learning_modules[0]
                        if self.model.learning_modules
                        else None,
                        hypothesis_input_channel=self.plotting_config.get(
                            "hypothesis_input_channel", "patch"
                        ),
                        hypothesis_evidence_threshold=self.plotting_config.get(
                            "hypothesis_evidence_threshold", -np.inf
                        ),
                        hypothesis_ax_range=self.plotting_config.get(
                            "hypothesis_ax_range", 0.2
                        ),
                        hypothesis_view_elev=self.plotting_config.get(
                            "hypothesis_view_elev", 30
                        ),
                        hypothesis_view_azim=self.plotting_config.get(
                            "hypothesis_view_azim", -60
                        ),
                        display_mlh_focus_plot=self.plotting_config.get(
                            "display_mlh_focus_plot", False
                        ),
                    )

            # Regular experiment step logic
            if self.show_sensor_output:
                self.show_observations(observation, loader_step)

            if self.model.check_reached_max_matching_steps(self.max_steps):
                return loader_step

            if loader_step >= (self.max_total_steps):
                self.model.deal_with_time_out()
                return loader_step

            if self.model.is_done:
                return loader_step

        self.model.set_is_done()
        return loader_step
