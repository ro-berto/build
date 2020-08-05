# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'build',
    'chromium',
    'chromium_tests',
    'depot_tools/bot_update',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/commit_position',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/runtime',
    'recipe_engine/step',
    'test_results',
    'test_utils',
]

import copy

from recipe_engine import post_process


def RunSteps(api):
  with api.chromium.chromium_layout():
    return api.chromium_tests.main_waterfall_steps()


def GenTests(api):

  def boilerplate(**kwargs):
    mastername = 'chromium.linux'
    builder = 'Linux Tests'
    return sum([
        api.chromium.ci_build(
            mastername=mastername,
            builder=builder,
            parent_buildername='Linux Builder'),
        api.properties.generic(
            swarm_hashes={'fake_test': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee'},
            **kwargs),
        api.platform('linux', 64),
        api.chromium_tests.read_source_side_spec(
            mastername, {
                builder: {
                    'isolated_scripts': [{
                        'isolate_name': 'fake_test',
                        'name': 'fake_test',
                        'results_handler': 'layout tests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                        },
                    }]
                }
            }),
    ], api.empty_test_data())

  base_test_result = {
      'interrupted': False,
      'version': 3,
      'path_delimiter': '/',
      'seconds_since_epoch': 0,
      'tests': {},
      'num_failures_by_type': {},
      'links': {
          'custom_link': 'http://example.com'
      }
  }

  yield (api.test(
      'archive_step_has_gs_acl', boilerplate(gs_acl='public-read'),
      api.post_process(post_process.StepCommandContains,
                       'archive results for fake_test',
                       ['--gs-acl', 'public-read']),
      api.post_process(post_process.DropExpectation)))

  test_result = copy.deepcopy(base_test_result)
  test_result['tests']['foo.html'] = {
      'actual': 'FAIL PASS',
      'expected': 'PASS',
      'is_unexpected': True
  }
  yield (api.test('unexpected_flake_has_warning', boilerplate(),
                  api.step_data('fake_test', api.json.output(test_result)),
                  api.post_process(post_process.StepWarning, 'fake_test'),
                  api.post_process(post_process.DropExpectation)))

  test_result = copy.deepcopy(base_test_result)
  for i in range(35):
    test_result['tests']['test%d.html' % i] = {
        'actual': 'FAIL',
        'expected': 'PASS',
        'is_unexpected': True
    }
  yield (api.test(
      'too_many_failures_has_truncated_results', boilerplate(),
      api.step_data('fake_test', api.json.output(test_result)),
      api.post_process(post_process.StepTextContains, 'fake_test',
                       ['...', 'more', '...']),
      api.post_process(post_process.DropExpectation)))
