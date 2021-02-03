# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from RECIPE_MODULES.build.rts_chromium import rts_spec

DEPS = [
    'recipe_engine/path',
    'rts_chromium',
]


def RunSteps(api):
  spec = rts_spec.RTSSpec(
      rts_chromium_version='latest',
      model_version='latest',
      target_change_recall=0.9,
  )

  api.rts_chromium.select_tests_to_skip(
      spec=spec,
      changed_files=[
        '//foo/bar.h',
        '//bar/baz.cc',
      ],
      filter_files_dir=api.path['start_dir'].join('filters'),
  )


def GenTests(api):
  yield api.test('basic')
