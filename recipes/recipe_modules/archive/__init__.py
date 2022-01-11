# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from PB.recipe_modules.build.archive import properties

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'build',
    'builder_group',
    'chromium',
    'chromium_checkout',
    'depot_tools/depot_tools',
    'depot_tools/gitiles',
    'depot_tools/gsutil',
    'infra/zip',
    'infra/cloudkms',
    'infra/provenance',
    'py3_migration',
    'recipe_engine/buildbucket',
    'recipe_engine/cipd',
    'recipe_engine/commit_position',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/runtime',
    'recipe_engine/step',
    'recipe_engine/time',
    'squashfs',
    'tar',
]

PROPERTIES = properties.InputProperties
