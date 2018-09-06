# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import functools

from recipe_engine import post_process
from recipe_engine.config import List
from recipe_engine.recipe_api import Property

DEPS = [
    'gn',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
]

PROPERTIES = {
    'targets': Property(kind=List(str), default=[]),
    'output_type': Property(kind=str, default=None),
}


def RunSteps(api, targets, output_type):
  refs = api.gn.refs(
      api.path['checkout'].join('out', 'Release'),
      targets,
      output_type=output_type)
  assert refs == set(['target3', 'target4'])


def GenTests(api):
  yield (api.test('basic') + api.properties(targets=['target1', 'target2']) +
         api.override_step_data(
             'calculate gn refs', stdout=api.raw_io.output('target3\ntarget4'))
         + api.post_process(post_process.DropExpectation))

  yield (api.test('basic_with_type') + api.properties(
      targets=['target1', 'target2'],
      output_type='executable',
  ) + api.override_step_data(
      'calculate gn refs', stdout=api.raw_io.output('target3\ntarget4')) +
         api.post_process(post_process.DropExpectation))
