# Copyright 2025 Thousand Brains Project
#
# Copyright may exist in Contributors' modifications
# and/or contributions to the work.
#
# Use of this source code is governed by the MIT
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.
from tbp.monty.frameworks.models.motor_policies import (
    InformedPolicy,
    JumpToGoalStateMixin,
)


class UltrasoundMotorPolicy(InformedPolicy, JumpToGoalStateMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def step(self, data):
        return super().step(data)
