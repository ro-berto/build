# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import six

DEPS = [
    'py3_migration',
    'recipe_engine/json',
    'recipe_engine/step',
]


def RunSteps(api):
  values = [0, 1, 2]
  # Ensure that the ordering for values is different for python3
  if six.PY3:
    values = list(reversed(values))

  api.step(
      'foo',
      cmd=['foo'],
      stdin=api.json.input(api.py3_migration.consistent_ordering(values)))


def GenTests(api):
  yield api.test('basic')
