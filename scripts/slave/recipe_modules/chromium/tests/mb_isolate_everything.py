# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = ['chromium']

def RunSteps(api):
  api.chromium.set_config('chromium')
  api.chromium.mb_isolate_everything(
      mastername='test_mastername',
      buildername='test_buildername')

def GenTests(api):
  yield api.test(
      'basic',
      api.post_process(post_process.StepCommandRE, 'generate .isolate files', [
          'python', '-u', r'.*/tools/mb/mb\.py', 'isolate-everything', '-m',
          'test_mastername', '-b', 'test_buildername', '--config-file',
          r'.*/tools/mb/mb_config\.pyl', '--goma-dir', '.*', '//out/Release'
      ]),
      api.post_process(post_process.DropExpectation),
  )
