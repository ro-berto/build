# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property
from recipe_engine.config import ConfigGroup, Single

from PB.recipe_modules.build.chromium_tests import properties

DEPS = [
    'adb',
    'archive',
    'build',
    'chromium',
    'chromium_android',
    'chromium_checkout',
    'chromium_swarming',
    'code_coverage',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/gsutil',
    'depot_tools/tryserver',
    'filter',
    'gn',
    'goma',
    'isolate',
    'perf_dashboard',
    'pgo',
    'puppet_service_account',
    'recipe_engine/buildbucket',
    'recipe_engine/commit_position',
    'recipe_engine/context',
    'recipe_engine/cq',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/runtime',
    'recipe_engine/scheduler',
    'recipe_engine/step',
    'recipe_engine/swarming',
    'recipe_engine/time',
    'symupload',
    'test_results',
    'test_utils',
    'traceback',
    'zip',
]

PROPERTIES = properties.InputProperties
