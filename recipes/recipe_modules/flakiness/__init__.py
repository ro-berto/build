# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from PB.recipe_modules.build.flakiness import properties

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
    'recipe_engine/resultdb',
    'recipe_engine/step',
]

PROPERTIES = properties.InputProperties
