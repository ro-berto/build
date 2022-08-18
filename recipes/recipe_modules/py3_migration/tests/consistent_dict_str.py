# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'py3_migration',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]


def RunSteps(api):
  d = {
      'x': 1,
      'z': 0,
      'y': 2,
  }

  api.step(
      'foo',
      cmd=['foo'],
      stdin=api.raw_io.input_text(api.py3_migration.consistent_dict_str(d)))


def GenTests(api):
  yield api.test('basic')
