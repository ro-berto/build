# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'recipe_engine/path',
    'gn',
]


def RunSteps(api):
  api.gn.clean(
      api.path['start_dir'].join('out', 'Release'),
      step_name='foobar')


def GenTests(api):
  yield api.test('basic')
