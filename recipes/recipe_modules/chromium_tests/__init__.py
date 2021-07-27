# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from PB.recipe_modules.build.chromium_tests import properties

DEPS = [
    'adb',
    'archive',
    'build',
    'builder_group',
    'chromium',
    'chromium_android',
    'chromium_bootstrap',
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
    'infra/zip',
    'isolate',
    'perf_dashboard',
    'pgo',
    'puppet_service_account',
    'recipe_engine/buildbucket',
    'recipe_engine/cas',
    'recipe_engine/commit_position',
    'recipe_engine/context',
    'recipe_engine/cq',
    'recipe_engine/file',
    'recipe_engine/led',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/resultdb',
    'recipe_engine/runtime',
    'recipe_engine/scheduler',
    'recipe_engine/step',
    'recipe_engine/swarming',
    'recipe_engine/time',
    'skylab',
    'symupload',
    'test_results',
    'test_utils',
    'traceback',
]

# Avoid adding a dependency on the chromium_tests_builder_config module, the
# builder config should be self-contained and should be provided to
# chromium_tests; it shouldn't need to lookup any additional builders or access
# the static DBs
assert not any(
    m in DEPS for m in ('chromium_tests_builder_config',
                        'build/chromium_tests_builder_config'))

PROPERTIES = properties.InputProperties
