# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from PB.recipe_modules.build.reclient import properties
from PB.recipe_modules.build.reclient import rbe_metrics_bq

DEPS = [
    'build',
    'recipe_engine/buildbucket',
    'recipe_engine/file',
    'recipe_engine/cipd',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/time',
]

PROPERTIES = properties.InputProperties
