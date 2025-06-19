# Copyright 2025 Thousand Brains Project
#
# Copyright may exist in Contributors' modifications
# and/or contributions to the work.
#
# Use of this source code is governed by the MIT
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

from .robot_lab_experiments import CONFIGS as ROBOT_LAB_EXPERIMENTS
from .ultrasound_experiments import CONFIGS as ULTRASOUND_EXPERIMENTS

CONFIGS = dict()
CONFIGS.update(ROBOT_LAB_EXPERIMENTS)
CONFIGS.update(ULTRASOUND_EXPERIMENTS)
