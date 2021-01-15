# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'rts',
    'recipe_engine/platform',
]

from recipe_engine import post_process


def RunSteps(api):
  changed_files = [
      '//foo/bar.h',
      '//bar/baz.cc',
  ]

  api.rts.select_tests_to_skip(
      changed_files,
      'src/testing/rts_exclude_file.txt',
      target_change_recall=.90)


def GenTests(api):

  yield api.test(
      'basic',
      api.platform('linux', 64),
  )
