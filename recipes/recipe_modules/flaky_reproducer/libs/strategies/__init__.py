# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .reproducing_step import ReproducingStep
from .repeat_strategy import RepeatStrategy
from .batch_strategy import BatchStrategy

strategies = {
    RepeatStrategy.name: RepeatStrategy,
    BatchStrategy.name: BatchStrategy,
}
