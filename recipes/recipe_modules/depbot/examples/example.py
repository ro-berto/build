# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'depbot',
    'recipe_engine/json',
    'recipe_engine/path',
]


def RunSteps(api):
  api.depbot.run(
      src_dir=api.path['checkout'],
      build_dir='out/Release',
      json_out=api.json.output(name='results'))


def GenTests(api):
  yield api.test('basic')
