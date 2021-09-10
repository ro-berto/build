# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'depot_tools/depot_tools',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/legacy_annotation',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/resultdb',
    'recipe_engine/step',
]
