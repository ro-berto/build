# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from RECIPE_MODULES.build.rts import rts_spec

DEPS = [
    'rts',
    'recipe_engine/platform',
]


def RunSteps(api):
  changed_files = [
      '//foo/bar.h',
      '//bar/baz.cc',
  ]
  spec = rts_spec.RTSSpec(
      rts_chromium_version='latest',
      model_version='latest',
      skip_test_files_path='src/testing/rts_exclude_file.txt',
      target_change_recall=0.9,
  )

  api.rts.select_tests_to_skip(spec, changed_files)


def GenTests(api):

  yield api.test(
      'basic',
      api.platform('linux', 64),
  )
