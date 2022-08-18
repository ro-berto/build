# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'py3_migration',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]


def RunSteps(api):
  try:
    assert False, 'test exception'
  except AssertionError as e:
    api.step.empty(
        'foo', step_text=api.py3_migration.consistent_exception_repr(e))


def GenTests(api):
  yield api.test('basic')
