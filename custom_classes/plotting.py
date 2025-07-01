"""Plotting utilities for ultrasound experiments.

This module provides functions to visualize:
- Input images and extracted patches
- Point normals and curvature information
- Evidence plots for object hypotheses
"""

from typing import Optional  # Added for compatibility with Python < 3.10

import matplotlib.colors
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle
from mpl_toolkits.mplot3d import Axes3D
from tbp.monty.frameworks.models.evidence_matching.learning_module import (
    EvidenceGraphLM,
)

# Global figure and axes for continuous updating
_fig = None
_ax1 = None
_ax2 = None
_ax3 = None

# Global variables for hypothesis space plots (second row)
_h_ax1 = None
_h_ax2 = None
_h_ax3 = None
_current_fig_is_double_row = None  # Tracks if the current figure has one or two rows


# Helper function for plot_hypothesis_space
def _plot_single_hypothesis_on_ax(
    ax,  # This should be a 3D axis
    obj_id,
    lm: EvidenceGraphLM,
    input_feature_channel="patch",
    current_evidence_update_threshold=-np.inf,
    title_prefix="Hypotheses for",
):
    """Helper to plot hypothesis space for a single object directly from LM."""
    ax.clear()
    hypothesis_subsampling_rate = 1

    current_title = f"{title_prefix}: {obj_id}"
    ax.set_title(current_title)

    locs = np.array(lm.possible_locations.get(obj_id, []))
    evidence = np.array(lm.evidence.get(obj_id, []))

    if locs.ndim == 1 and locs.size == 0:
        locs = np.empty((0, 3))
    if evidence.ndim == 1 and evidence.size == 0:
        evidence = np.empty((0,))

    # Plot Object Graph Model Points (Grey Scatter)
    object_model_instance = lm.graph_memory.get_graph(obj_id, input_feature_channel)
    graph_data_source = object_model_instance._graph

    original_nodes_to_plot = None
    if hasattr(graph_data_source, "pos") and graph_data_source.pos is not None:
        original_nodes_to_plot = np.array(graph_data_source.pos)
        nodes_for_scatter = original_nodes_to_plot

        if nodes_for_scatter.shape[0] > 0:
            ax.scatter(
                nodes_for_scatter[:, 1],
                nodes_for_scatter[:, 0],
                nodes_for_scatter[:, 2],
                c="grey",
                s=2,
                alpha=0.5,
                label="Model",
            )

    # Plot Hypotheses Scatter
    cmap = plt.cm.get_cmap("seismic")

    relevant_indices = evidence >= current_evidence_update_threshold
    relevant_locs = locs[relevant_indices]
    relevant_evidence_values = evidence[relevant_indices]

    locs_for_scatter = relevant_locs
    evidence_for_scatter = relevant_evidence_values
    if (
        len(relevant_locs) >= hypothesis_subsampling_rate
        and hypothesis_subsampling_rate > 0
    ):
        locs_for_scatter = relevant_locs[::hypothesis_subsampling_rate]
        evidence_for_scatter = relevant_evidence_values[::hypothesis_subsampling_rate]
    elif len(relevant_locs) > 0 and len(locs_for_scatter) == 0:
        locs_for_scatter = relevant_locs[0:1]
        evidence_for_scatter = relevant_evidence_values[0:1]

    if evidence_for_scatter.size > 1:
        vmin = np.percentile(evidence_for_scatter, 5)
        vmax = np.percentile(evidence_for_scatter, 95)
    elif evidence_for_scatter.size == 1:
        vmin = evidence_for_scatter[0] - 0.1
        vmax = evidence_for_scatter[0] + 0.1
    else:
        if relevant_evidence_values.size > 0:
            vmin = np.min(relevant_evidence_values)
            vmax = np.max(relevant_evidence_values)
        elif evidence.size > 0:
            vmin = np.min(evidence)
            vmax = np.max(evidence)
        else:
            vmin = 0
            vmax = 1
    if vmin == vmax:
        vmin -= 0.1
        vmax += 0.1
    if vmin > vmax:
        vmin, vmax = vmax, vmin

    norm = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)

    if locs_for_scatter.shape[0] > 0:
        # Calculate alphas based on current_evidence_update_threshold
        point_alphas_hyp = np.where(
            evidence_for_scatter >= current_evidence_update_threshold, 1.0, 0.5
        )

        # Calculate sizes based on evidence
        point_sizes_hyp = evidence_for_scatter * 10
        point_sizes_hyp[point_sizes_hyp <= 0] = 0.1

        colors_rgba = cmap(norm(evidence_for_scatter))
        colors_rgba[:, 3] = point_alphas_hyp

        ax.scatter(
            locs_for_scatter[:, 1],
            locs_for_scatter[:, 0],
            locs_for_scatter[:, 2],
            c=colors_rgba,
            s=point_sizes_hyp,  # Sizes based on evidence_for_scatter * 10
            alpha=None,  # Alpha is part of c=colors_rgba
        )

    ax.set_xlabel("Y")  # MPL X-axis now shows original Y
    ax.set_ylabel("X")  # MPL Y-axis now shows original X
    ax.set_zlabel("Z")  # MPL Z-axis now shows original Z
    ax.set_aspect("equal")
    ax.view_init(elev=70, azim=90)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])


def _plot_single_hypothesis_mlh_on_ax(
    ax,
    obj_id: str,
    lm: EvidenceGraphLM,
    input_feature_channel: str = "patch",
    observed_locations_world: Optional[np.ndarray] = None,
    observed_normals_world: Optional[np.ndarray] = None,
    title_prefix: str = "MLH Focus for",
):
    """Plots the object model and observed path in the object's MLH frame.

    The object model is plotted in its local coordinates. The observed path
    (locations and normals) is transformed from world coordinates to the
    object's local coordinate frame using the Most Likely Hypothesis (MLH)
    pose for the given obj_id.

    Args:
        ax: Matplotlib 3D axis.
        obj_id: ID of the object to plot.
        lm: EvidenceGraphLM instance.
            Expected to have methods:
            - lm.possible_locations.get(obj_id)
            - lm.evidence.get(obj_id)
            - lm.graph_memory.get_graph(obj_id, input_feature_channel)
            - lm.possible_poses.get(obj_id, []): Returns a list of 4x4
              numpy arrays (object-to-world transforms) for hypotheses
              of obj_id. This is a critical assumed method.
        input_feature_channel: Feature channel for retrieving the object model.
        observed_locations_world: Nx3 array of observed locations in world frame.
        observed_normals_world: Nx3 array of observed normals in world frame.
        title_prefix: Prefix for the plot title.
    """
    ax.clear()

    current_title = f"{title_prefix}: {obj_id}"
    ax.set_title(current_title)

    # Get data from LM
    mlh_info = lm._calculate_most_likely_hypothesis(obj_id)
    object_model_instance = lm.graph_memory.get_graph(obj_id, input_feature_channel)
    graph_data_source = object_model_instance._graph
    nodes_for_scatter = np.array(graph_data_source.pos)

    if nodes_for_scatter.shape[0] > 0:
        ax.scatter(
            nodes_for_scatter[:, 1],
            nodes_for_scatter[:, 0],
            nodes_for_scatter[:, 2],
            c="grey",
            s=2,
            alpha=0.5,
            label="Model",
        )

    scipy_rotation_world_to_obj = mlh_info["rotation"]
    obj_frame_anchor_point = np.array(mlh_info["location"])

    # Transform and plot observed path if available
    if observed_locations_world is not None and len(observed_locations_world) > 0:
        obs_loc_world_np = np.array(observed_locations_world)
        # Assume the 'world_anchor_point' that corresponds to 'obj_frame_anchor_point'
        # is the last observed location.
        world_frame_anchor_point = obs_loc_world_np[-1]  # Taking the last point

        # Transform locations from world to object's local MLH frame
        relative_world_vectors = obs_loc_world_np - world_frame_anchor_point
        rotated_vectors = scipy_rotation_world_to_obj.apply(relative_world_vectors)
        obs_loc_obj_frame = rotated_vectors + obj_frame_anchor_point

        ax.scatter(
            obs_loc_obj_frame[:, 1],
            obs_loc_obj_frame[:, 0],
            obs_loc_obj_frame[:, 2],
            c="blue",
            s=20,
            label="Observed Path (obj frame)",
            alpha=0.7,
        )

        # Plot observed normals if available
        obs_norm_world_np = np.array(observed_normals_world)
        obs_norm_obj_frame = scipy_rotation_world_to_obj.apply(obs_norm_world_np)

        ax.quiver(
            obs_loc_obj_frame[:, 1],  # Original Y to MPL X
            obs_loc_obj_frame[:, 0],  # Original X to MPL Y
            obs_loc_obj_frame[:, 2],  # Original Z to MPL Z
            obs_norm_obj_frame[:, 1],  # Normal Y component
            obs_norm_obj_frame[:, 0],  # Normal X component
            obs_norm_obj_frame[:, 2],  # Normal Z component
            length=0.05,
            normalize=True,
            color="green",
            label="Observed Normals (obj frame)",
            alpha=0.7,
        )

    ax.set_xlabel("Y (object local frame)")
    ax.set_ylabel("X (object local frame)")
    ax.set_zlabel("Z (object local frame)")
    ax.set_aspect("equal")
    # ax.view_init(elev=70, azim=90)
    ax.legend(loc="upper right", fontsize="small")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])


def plot_hypothesis_space(
    h_ax1,
    h_ax2,
    h_ax3,
    lm: EvidenceGraphLM,
    input_feature_channel="patch",
    current_evidence_update_threshold=-np.inf,
    focus_on_mlh: bool = False,
    observed_patch_locations: Optional[np.ndarray] = None,
    observed_patch_normals: Optional[np.ndarray] = None,
):
    """Plots hypothesis of most likely objects."""

    current_mlh_info = lm.get_current_mlh()
    possible_matches = lm.get_possible_matches()

    top_mlh_obj_id, second_mlh_obj_id = lm.get_top_two_mlh_ids()
    # Overwriting the second MLH to potted_meat_can for debugging
    second_mlh_obj_id = "potted_meat_can"

    if focus_on_mlh:
        # Shows the most likely pose on the object (+sensed path)
        _plot_single_hypothesis_mlh_on_ax(
            h_ax1,
            top_mlh_obj_id,
            lm,
            input_feature_channel,
            observed_locations_world=observed_patch_locations,
            observed_normals_world=observed_patch_normals,
            title_prefix="Most Likely Hypothesis",
        )
        _plot_single_hypothesis_mlh_on_ax(
            h_ax2,
            second_mlh_obj_id,
            lm,
            input_feature_channel,
            observed_locations_world=observed_patch_locations,
            observed_normals_world=observed_patch_normals,
            title_prefix="2nd Object",
        )
    else:
        # Shows all hypotheses on the object
        _plot_single_hypothesis_on_ax(
            h_ax1,
            top_mlh_obj_id,
            lm,
            input_feature_channel,
            current_evidence_update_threshold,
            title_prefix="Top MLH",
        )
        _plot_single_hypothesis_on_ax(
            h_ax2,
            second_mlh_obj_id,
            lm,
            input_feature_channel,
            current_evidence_update_threshold,
            title_prefix="2nd MLH",
        )

    # # Display Text on h_ax3
    # h_ax3.clear()
    # h_ax3.axis("off")

    # mlh_display_id = current_mlh_info.get("graph_id", "N/A")
    # mlh_display_evidence = current_mlh_info.get("evidence", float("nan"))
    # mlh_text = (
    #     f"Most Likely Hypothesis:\n   {mlh_display_id} (Ev: {mlh_display_evidence:.2f})"
    # )
    # h_ax3.text(
    #     0.05,
    #     0.90,
    #     mlh_text,
    #     ha="left",
    #     va="top",
    #     fontsize=11,
    #     weight="bold",
    #     transform=h_ax3.transAxes,
    #     linespacing=1.5,
    # )

    # current_y_pos = 0.75
    # possible_objects_str = "Possible:\n" + "\n".join(
    #     [f"   {obj}" for obj in possible_matches]
    # )
    # h_ax3.text(
    #     0.05,
    #     current_y_pos,
    #     possible_objects_str,  # Use the directly formatted string
    #     ha="left",
    #     va="top",
    #     fontsize=9,
    #     transform=h_ax3.transAxes,
    #     linespacing=1.5,
    # )


def plot_patch_with_features(
    ax1,
    ax2,
    ax3,
    input_image,
    patch_image,
    all_column_points_tuples,
    center_edge_point,
    fitted_circle,
    point_normal,
    curvature,
    depth_meters,
    observed_locations,
    normal_rel_world,
):
    """Plot a patch with overlaid features and observed locations on the given axes.

    Args:
        ax1: Matplotlib axis for the input image.
        ax2: Matplotlib axis for the patch image and features.
        ax3: Matplotlib 3D axis for observed locations.
        input_image: The full input image
        patch_image: The extracted patch
        all_column_points_tuples: List of (x,y) points for column detection
        center_edge_point: (x,y) of detected center edge
        fitted_circle: (x,y,r) of fitted circle
        point_normal: (x,y,z) point normal vector
        curvature: Computed curvature value
        depth_meters: Depth in meters
        observed_locations: List of [x,y,z] observed patch world locations.
        normal_rel_world: List of [nx,ny,nz] observed normal vectors in world frame.
    """
    # Clear previous plots on the provided axes
    # ax1.clear()
    # ax2.clear()
    ax3.clear()

    # # Plot full input image on the left
    # ax1.imshow(input_image, cmap="gray")
    # ax1.set_title("Input Image")
    # ax1.axis("off")

    # # Plot patch with features on the right
    # ax2.imshow(patch_image, cmap="gray")
    # ax2.set_title("Patch with Features")

    # legend_elements = []

    # # Plot column points
    # if all_column_points_tuples and len(all_column_points_tuples) > 0:
    #     points = np.array(all_column_points_tuples)
    #     ax2.scatter(points[:, 0], points[:, 1], c="r", s=1)
    #     legend_elements.append(
    #         plt.Line2D(
    #             [0],
    #             [0],
    #             marker="o",
    #             color="w",
    #             markerfacecolor="r",
    #             markersize=5,
    #             label="Points on Edge",
    #         )
    #     )

    # if center_edge_point is not None:
    #     ax2.scatter(center_edge_point[0], center_edge_point[1], c="g", s=50)
    #     legend_elements.append(
    #         plt.Line2D(
    #             [0],
    #             [0],
    #             marker="o",
    #             color="w",
    #             markerfacecolor="g",
    #             markersize=8,
    #             label="Center Edge",
    #         )
    #     )

    # if fitted_circle is not None:
    #     circle_patch = Circle(
    #         (fitted_circle[0], fitted_circle[1]),
    #         fitted_circle[2],
    #         fill=False,
    #         color="b",
    #     )
    #     ax2.add_patch(circle_patch)
    #     legend_elements.append(plt.Line2D([0], [0], color="b", label="Fitted Circle"))

    # if point_normal is not None and center_edge_point is not None:
    #     scale = 20
    #     start_x = center_edge_point[0]
    #     start_y = center_edge_point[1]
    #     plot_dx = point_normal[0] * scale
    #     plot_dy = point_normal[1] * scale
    #     ax2.arrow(
    #         start_x,
    #         start_y,
    #         plot_dx,
    #         plot_dy,
    #         head_width=3,
    #         head_length=5,
    #         fc="y",
    #         ec="y",
    #     )
    #     legend_elements.append(plt.Line2D([0], [0], color="y", label="Point Normal"))

    # text = f"Curvature: {curvature:.3f}\nDepth: {depth_meters * 100:.3f}cm"
    # ax2.text(
    #     5,
    #     patch_image.shape[0] - 20,
    #     text,
    #     color="white",
    #     fontsize=8,
    #     bbox=dict(facecolor="black", alpha=0.5),
    # )

    # if legend_elements:
    #     ax2.legend(handles=legend_elements, loc="upper right")
    # ax2.axis("off")

    locations_np = np.array(observed_locations)
    # Convert from meters to centimeters
    x = locations_np[:, 1] * 100
    y = locations_np[:, 0] * 100
    z = locations_np[:, 2] * 100
    ax3.scatter(x, y, z, c="b", marker="o", s=10, label="Observed Locations")
    if normal_rel_world and len(normal_rel_world) == len(observed_locations):
        normals_np = np.array(normal_rel_world)
        if normals_np.ndim == 2 and normals_np.shape[1] == 3:
            u = normals_np[:, 1]
            v = normals_np[:, 0]
            w = normals_np[:, 2]
            ax3.quiver(
                x,
                y,
                z,
                u,
                v,
                w,
                length=10,  # Increased length to match cm scale
                normalize=True,
                color="r",
                label="World Normals",
            )
    ax3.set_xlabel("X (world) [cm]")
    ax3.set_ylabel("Y (world) [cm]")
    ax3.set_zlabel("Z (world) [cm]")
    ax3.set_title("Observed Patch Locations")
    if len(x) > 1:
        ax3.set_xlim([np.min(x) - 10, np.max(x) + 10])  # Adjusted margins to cm
        ax3.set_ylim([np.min(y) - 10, np.max(y) + 10])
        ax3.set_zlim([np.min(z) - 10, np.max(z) + 10])
    elif len(x) == 1:
        ax3.set_xlim([x[0] - 50, x[0] + 50])  # Adjusted margins to cm
        ax3.set_ylim([y[0] - 50, y[0] + 50])
        ax3.set_zlim([z[0] - 50, z[0] + 50])
    ax3.view_init(elev=20.0, azim=-35)
    ax3.grid(True)
    # ax3.set_xticks([])
    # ax3.set_yticks([])
    # ax3.set_zticks([])


def plot_combined_figure(
    input_image,
    patch_image,
    all_column_points_tuples,
    center_edge_point,
    fitted_circle,
    point_normal,
    curvature,
    depth_meters,
    observed_locations,
    normal_rel_world,
    save_path=None,
    show_hypothesis_space: bool = False,
    lm_instance: EvidenceGraphLM = None,
    hypothesis_input_channel="patch",
    hypothesis_evidence_threshold=-np.inf,
    display_mlh_focus_plot: bool = False,
):
    """Manages the overall figure and calls plotting functions for different sections.

    The first row always shows the input image, patch features, and observed locations.
    The second row (optional) shows hypothesis space visualizations.

    Args:
        input_image: The full input image.
        patch_image: The extracted patch.
        all_column_points_tuples: List of (x,y) points for column detection.
        center_edge_point: (x,y) of detected center edge.
        fitted_circle: (x,y,r) of fitted circle.
        point_normal: (x,y,z) point normal vector.
        curvature: Computed curvature value.
        depth_meters: Depth in meters.
        observed_locations: List of [x,y,z] observed patch world locations.
        normal_rel_world: List of [nx,ny,nz] observed normal vectors in world frame.
        save_path: Optional path to save the plot.
        show_hypothesis_space: If True, adds and plots on a second row for hypothesis space.
        lm_instance: EvidenceGraphLM instance for hypothesis space plotting.
        hypothesis_input_channel: Input feature channel for hypothesis space plotting.
        hypothesis_evidence_threshold: Evidence threshold for hypothesis space plotting.
        display_mlh_focus_plot: If True and show_hypothesis_space is True,
                                the hypothesis plots will focus on the MLH object view
                                with transformed observed path. Defaults to False.
    """
    global _fig, _ax1, _ax2, _ax3, _h_ax1, _h_ax2, _h_ax3, _current_fig_is_double_row

    needs_rebuild = _fig is None or (
        _current_fig_is_double_row is not None
        and _current_fig_is_double_row != show_hypothesis_space
    )

    if needs_rebuild:
        if _fig is not None:
            plt.close(_fig)  # Close the old figure

        plt.ion()  # Ensure interactive mode is on

        if show_hypothesis_space:
            _fig = plt.figure(figsize=(18, 12))
            gs = _fig.add_gridspec(1, 3)  # Use gridspec for better layout control
            # _ax1 = _fig.add_subplot(gs[0, 0])
            # _ax2 = _fig.add_subplot(gs[0, 1])
            _ax3 = _fig.add_subplot(gs[0, 0], projection="3d")
            _h_ax1 = _fig.add_subplot(gs[0, 1], projection="3d")
            _h_ax2 = _fig.add_subplot(gs[0, 2], projection="3d")
            # _h_ax3 = _fig.add_subplot(gs[0, 3])  # Text axis
            _current_fig_is_double_row = True
        else:
            _fig = plt.figure(figsize=(18, 6))
            gs = _fig.add_gridspec(1, 3)  # Use gridspec
            # _ax1 = _fig.add_subplot(gs[0, 0])
            # _ax2 = _fig.add_subplot(gs[0, 1])
            _ax3 = _fig.add_subplot(gs[0, 0], projection="3d")
            _h_ax1, _h_ax2, _h_ax3 = (
                None,
                None,
                None,
            )  # Explicitly nullify hypothesis axes
            _current_fig_is_double_row = False

        if hasattr(_fig.canvas, "manager") and _fig.canvas.manager is not None:
            _fig.canvas.manager.set_window_title("Ultrasound Visualizer")

    # Call the function to plot patch features on the (first row) axes
    plot_patch_with_features(
        _ax1,
        _ax2,
        _ax3,
        input_image,
        patch_image,
        all_column_points_tuples,
        center_edge_point,
        fitted_circle,
        point_normal,
        curvature,
        depth_meters,
        observed_locations,
        normal_rel_world,
    )

    # If show_hypothesis_space is true, call the function to plot on the second row axes
    if show_hypothesis_space and lm_instance is not None:
        plot_hypothesis_space(
            _h_ax1,
            _h_ax2,
            _h_ax3,
            lm_instance,
            input_feature_channel=hypothesis_input_channel,
            current_evidence_update_threshold=hypothesis_evidence_threshold,
            focus_on_mlh=display_mlh_focus_plot,
            observed_patch_locations=observed_locations,
            observed_patch_normals=normal_rel_world,
        )

    plt.tight_layout(pad=1.5, h_pad=2.0, w_pad=1.0)

    if save_path:
        plt.savefig(save_path, bbox_inches="tight", dpi=300)

    if _fig:
        _fig.canvas.draw()
        _fig.canvas.flush_events()
        plt.pause(1.0)  # Short pause to allow plot to update
