# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_checkout',
    'chromium_swarming',
    'chromium_tests',
    'chromium_tests_builder_config',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'depot_tools/git',
    'filter',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'test_utils',
]


# TODO(phajdan.jr): provide coverage (http://crbug.com/693058).
DISABLE_STRICT_COVERAGE = True
