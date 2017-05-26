# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'codesearch',
]


def RunSteps(api):
  api.codesearch.set_config('base')
  api.codesearch.run_clang_tool()


def GenTests(api):
  yield (
      api.test('basic')
  )

  yield (
      api.test('run_translation_unit_clang_tool_failed') +
      api.step_data('run translation_unit clang tool', retcode=1)
  )
