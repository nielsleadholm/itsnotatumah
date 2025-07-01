"""
Script to determine whether there is miscallibration in the VIVE Tracker positioning.

Loads a series of datasets where the tip of the probe is placed at a fixed location,
but with different orientations.
"""

import json
import numpy as np
import os
import matplotlib.pyplot as plt

# Load JSON data from /Users/nleadholm/tbp/data/ultrasound_test_set

dataset_path = "/Users/nleadholm/tbp/data/ultrasound_test_set"
end_to_end = "end_to_end_calibration"
rotate_on_point_calibration = "rotate_on_point_calibration"
num_samples = 5

samples_first_group = {
    "End-to-end": 3,
    "Rotate-on-point": 2,
}


def analyze_calibration(dataset_path, calibration_path, calibration_type):
    positions = []
    for i in range(num_samples):
        # Load the dataset
        loaded_data = json.load(
            open(os.path.join(dataset_path, calibration_path, f"{i}.json"))
        )

        positions.append(loaded_data["state"]["agent_id_0"]["position"])
    # Convert positions list to numpy array and convert to cm
    positions = np.array(positions) * 100  # Convert from m to cm

    # Calculate mean position and limits (+/- 5cm)
    mean_pos = np.mean(positions, axis=0)
    limit_range = 10  # 10cm
    xlim = (mean_pos[0] - limit_range, mean_pos[0] + limit_range)
    ylim = (mean_pos[1] - limit_range, mean_pos[1] + limit_range)
    zlim = (mean_pos[2] - limit_range, mean_pos[2] + limit_range)

    # Create 3D plot
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")

    print("Positions: ", positions)

    # Plot the positions in cm
    ax.scatter(positions[:, 0], positions[:, 1], positions[:, 2], marker="o")

    # Set axis limits
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_zlim(zlim)

    # Reduce number of ticks on each axis
    ax.xaxis.set_major_locator(plt.MaxNLocator(3))
    ax.yaxis.set_major_locator(plt.MaxNLocator(3))
    ax.zaxis.set_major_locator(plt.MaxNLocator(3))

    # Set labels
    ax.set_xlabel("x (cm)")
    ax.set_ylabel("y (cm)")
    ax.set_zlabel("z (cm)")

    plt.title(f"{calibration_type} calibration")
    plt.show()

    # Print the difference in the mean for each dimension between the first two points, and
    # the last three points (in cm)
    assert (
        len(positions[: samples_first_group[calibration_type]])
        == samples_first_group[calibration_type]
    )
    assert (
        len(positions[samples_first_group[calibration_type] :])
        == num_samples - samples_first_group[calibration_type]
    )
    mean_first_group = np.mean(
        positions[: samples_first_group[calibration_type], :], axis=0
    )
    mean_last_group = np.mean(
        positions[samples_first_group[calibration_type] :, :], axis=0
    )
    print(f"{calibration_type} mean differences...")
    print(f"x: {mean_first_group[0] - mean_last_group[0]:.2f} cm")
    print(f"y: {mean_first_group[1] - mean_last_group[1]:.2f} cm")
    print(f"z: {mean_first_group[2] - mean_last_group[2]:.2f} cm")

    # Calculate and print the Euclidean distance between the first and last group
    euclidean_distance = np.linalg.norm(mean_first_group - mean_last_group)
    print(f"{calibration_type} Euclidean distance: {euclidean_distance:.2f} cm")


if __name__ == "__main__":
    analyze_calibration(dataset_path, end_to_end, "End-to-end")
    analyze_calibration(dataset_path, rotate_on_point_calibration, "Rotate-on-point")