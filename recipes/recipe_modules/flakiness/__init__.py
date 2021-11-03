# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from PB.recipe_modules.build.flakiness import properties

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium',
    'chromium_checkout',
    'chromium_swarming',
    'depot_tools/bot_update',
    'depot_tools/gerrit',
    'depot_tools/tryserver',
    'isolate',
    'py3_migration',
    'recipe_engine/buildbucket',
    'recipe_engine/commit_position',
    'recipe_engine/json',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/resultdb',
    'recipe_engine/step',
    'test_results',
]

PROPERTIES = properties.InputProperties
