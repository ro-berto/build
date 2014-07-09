# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'filter',
  'path',
  'properties',
  'raw_io',
]

def GenSteps(api):
  api.path['checkout'] = api.path['slave_build']
  yield api.filter.does_patch_require_compile()
  assert (api.filter.result and api.properties['example_result']) or \
      (not api.filter.result and not api.properties['example_result'])

def GenTests(api):
  # Trivial test with no exclusions and nothing matching.
  yield (api.test('basic') +
         api.properties(filter_exclusions=[]) +
         api.properties(example_result=None) +
         api.override_step_data(
          'analyze',
          api.raw_io.stream_output('xx')) +
         api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('yy')))
  
  # Matches exclusions
  yield (api.test('match_exclusion') +
         api.properties(filter_exclusions=['fo.*']) +
         api.properties(example_result=1) +
         api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('foo.cc')))

  # Doesnt match exclusion.
  yield (api.test('doesnt_match_exclusion') +
         api.properties(filter_exclusions=['fo.*']) +
         api.properties(example_result=None) +
         api.override_step_data(
          'analyze',
          api.raw_io.stream_output('xx')) +
         api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('bar.cc')))

  # Analyze returns matching result.
  yield (api.test('analyzes_returns_true') +
         api.properties(example_result=1) +
         api.override_step_data(
          'analyze',
          api.raw_io.stream_output('Found dependency')))
