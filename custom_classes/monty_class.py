# Copyright 2025 Thousand Brains Project
#
# Copyright may exist in Contributors' modifications
# and/or contributions to the work.
#
# Use of this source code is governed by the MIT
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

import requests  # Add requests for HTTP communication
from tbp.monty.frameworks.models.evidence_matching.model import (
    MontyForEvidenceGraphMatching,
)


class MontyForEvidenceGraphMatchingWithGoalStateServer(MontyForEvidenceGraphMatching):
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)

    #     # it does not make sense for the wait factor to exponentially
    #     # grow when objects are viewed for only a few dozen steps.
    #     self.gsg.wait_growth_multiplier = 1

    def _pass_infos_to_motor_system(self):
        """Provide the goal-state on a server to the motor system."""
        super()._pass_infos_to_motor_system()

        # Check if _policy has a driving_goal_state attribute
        if hasattr(self.motor_system._policy, "driving_goal_state"):
            if self.motor_system._policy.driving_goal_state != None:
                # Serialize the goal state to a dictionary
                try:
                    pose_vectors = self.motor_system._policy.driving_goal_state.morphological_features[
                        "pose_vectors"
                    ]
                    location = self.motor_system._policy.driving_goal_state.location
                    use_state = self.motor_system._policy.driving_goal_state.use_state

                except Exception as e:
                    print(f"Error serializing goal state: {e}")
                    return

                if use_state:
                    try:
                        # Assuming the server is running on localhost and port 3003
                        # and has an endpoint /goal_state
                        goal_state_url = "http://localhost:3003/goal_state"
                        # We need to decide on the format of the goal_state.
                        # For now, let's assume it can be serialized to JSON.
                        # If it's a complex object, a custom serialization might be needed.
                        # location as a list of floats
                        location_as_list = [float(x) for x in location]
                        pose_vectors_as_list = [float(x) for x in pose_vectors[0, :]]
                        data_to_send = {
                            "goal_state": {
                                "location": location_as_list,
                                "pose_vectors": pose_vectors_as_list,
                            }
                        }
                        # Print the types and values of the location and pose_vectors
                        print(f"Location type: {type(location_as_list)}")
                        print(f"Location values: {location_as_list}")
                        print(f"Pose vectors type: {type(pose_vectors_as_list)}")
                        print(f"Pose vectors values: {pose_vectors_as_list}")
                        response = requests.post(
                            goal_state_url, json=data_to_send, timeout=0.1
                        )
                        if response.status_code == 200:
                            print("Goal state successfully sent to server.")
                        else:
                            print(
                                f"Failed to send goal state. Server responded with {response.status_code}"
                            )
                    except requests.RequestException as e:
                        print(f"Error sending goal state to server: {e}")
        else:
            # Print all the attributes of the policy and terminate
            print(self.motor_system._policy.__dict__)
            raise Exception("No driving goal state found in policy")