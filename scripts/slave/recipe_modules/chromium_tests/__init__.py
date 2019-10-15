# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property
from recipe_engine.config import ConfigGroup, Single

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
  'puppet_service_account',
  'recipe_engine/buildbucket',
  'recipe_engine/commit_position',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'recipe_engine/scheduler',
  'recipe_engine/time',
  'test_results',
  'test_utils',
  'traceback',
  'zip',
]

PROPERTIES = {
    # TODO(https://crbug.com/979330) git cl format won't work when there's
    # protos, so use the ConfigGroup to provide an interface compatible with
    # what the proto would be
    '$build/chromium_tests':
        Property(
            param_name='input_properties',
            kind=ConfigGroup(
                # For branch CQ/CI support there will be builders in different
                # buckets with the same name. The jobs for these same-named
                # builders will have different names. This option indicates that
                # any jobs triggered by this build will have the bucket name and
                # a '-' inserted before the builder name.
                #
                # This format lines up with the behavior of lucicfg: the job
                # name is the builder name if only a single builder has the name
                # and the aforementioned format is used if there are jobs in
                # different buckets with the same name.
                #
                # WARNING: This should only be used for builders that do not
                # trigger builders in different buckets. We don't have bucket
                # information for builders in the recipes, only the bucket of
                # the currently running builder.
                bucketed_triggers=Single(bool),),
            default={},
        ),
}
