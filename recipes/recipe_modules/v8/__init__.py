# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import ConfigGroup, Single

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'archive',
    'build',
    'builder_group',
    'chromium',
    'chromium_swarming',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/git',
    'depot_tools/gitiles',
    'depot_tools/gsutil',
    'depot_tools/osx_sdk',
    'depot_tools/tryserver',
    'gn',
    'infra/docker',
    'isolate',
    'perf_dashboard',
    'recipe_engine/buildbucket',
    'recipe_engine/commit_position',
    'recipe_engine/context',
    'recipe_engine/cq',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/legacy_annotation',
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
    'recipe_engine/url',
    'test_utils',
]

# TODO(phajdan.jr): provide coverage (http://crbug.com/693058).
DISABLE_STRICT_COVERAGE = True
