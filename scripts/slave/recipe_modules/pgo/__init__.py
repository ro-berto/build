# Copyright (c) 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from PB.recipe_modules.build.pgo import properties

DEPS = [
    'chromium',
    'code_coverage',
    'depot_tools/git',
    'depot_tools/gitiles',
    'depot_tools/gsutil',
    'profiles',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
]

PROPERTIES = properties.InputProperties
