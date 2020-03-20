# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from PB.recipe_modules.build.test_utils import properties

DEPS = [
    'build',
    'chromium',
    'traceback',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/resultdb',
    'recipe_engine/step',
]

PROPERTIES = properties.InputProperties

# TODO(phajdan.jr): provide coverage (http://crbug.com/693058).
DISABLE_STRICT_COVERAGE = True
