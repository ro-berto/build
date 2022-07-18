# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .reproducing_step import ReproducingStep

from .batch_strategy import BatchStrategy
from .parallel_strategy import ParallelStrategy
from .repeat_strategy import RepeatStrategy

strategies = {
    BatchStrategy.name: BatchStrategy,
    ParallelStrategy.name: ParallelStrategy,
    RepeatStrategy.name: RepeatStrategy,
}
