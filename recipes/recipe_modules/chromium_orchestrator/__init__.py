# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from PB.recipe_modules.build.chromium_orchestrator import properties

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'builder_group',
    'chromium',
    'chromium_checkout',
    'chromium_swarming',
    'chromium_tests',
    'chromium_tests_builder_config',
    'code_coverage',
    'depot_tools/gclient',
    'depot_tools/gitiles',
    'depot_tools/tryserver',
    'flakiness',
    'isolate',
    'profiles',
    'recipe_engine/buildbucket',
    'recipe_engine/cas',
    'recipe_engine/cq',
    'recipe_engine/cipd',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/swarming',
    'test_utils',
]

PROPERTIES = properties.InputProperties
