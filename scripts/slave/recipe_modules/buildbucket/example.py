# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This file is a recipe demonstrating the buildbucket recipe module."""


import json


DEPS = [
    'buildbucket',
    'service_account',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]


def RunSteps(api):
  if api.buildbucket.properties is None:
    return

  build_parameters = {
      'builder_name': 'linux_perf_bisect',
      'properties': {
          'bisect_config': {
              'bad_revision': '351054',
              'bug_id': 537649,
              'command': ('src/tools/perf/run_benchmark -v '
                          '--browser=release --output-format=chartjson '
                          '--also-run-disabled-tests speedometer'),
              'good_revision': '351045',
              'gs_bucket': 'chrome-perf',
              'max_time_minutes': '20',
              'metric': 'Total/Total',
              'recipe_tester_name': 'linux_perf_bisect',
              'repeat_count': '10',
              'test_type': 'perf'
          },
      }
  }
  build_tags = {'master': 'overriden.master.url',
                'builder': 'overriden_builder'}
  build_tags2 = {'master': 'someother.master.url', 'builder': 'some_builder'}
  build_parameters_mac = build_parameters.copy()
  build_parameters_mac['builder_name'] = 'mac_perf_bisect'
  example_bucket = 'master.user.username'

  # By default api.buildbucket is configured to use production buildbucket.
  service_account = api.service_account.get_json_path('username')

  put_build_result = api.buildbucket.put(
      [{'bucket': example_bucket,
        'parameters': build_parameters,
        'tags': build_tags,
        'client_operation_id': 'random_client_op_id'},
       {'bucket': example_bucket,
        'parameters': build_parameters_mac,
        'tags': build_tags2,
        'client_operation_id': 'random_client_op_id2'}],
      service_account)

  new_job_id = put_build_result.stdout['builds'][0]['id']

  get_build_result = api.buildbucket.get_build(new_job_id, service_account)

  # Switching configs for expectations coverage only.
  api.buildbucket.set_config('test_buildbucket')

  if get_build_result.stdout['build']['status'] == 'SCHEDULED':
    # Switching configs for expectations coverage only.
    api.buildbucket.set_config('dev_buildbucket')
    api.buildbucket.cancel_build(new_job_id, service_account)


def GenTests(api):
  mock_buildbucket_multi_response ="""
    {
      "builds":[{
       "status": "SCHEDULED",
       "created_ts": "1459200369835900",
       "bucket": "user.username",
       "result_details_json": "null",
       "status_changed_ts": "1459200369835930",
       "created_by": "user:username@example.com",
       "updated_ts": "1459200369835940",
       "utcnow_ts": "1459200369962370",
       "parameters_json": "{\\"This_has_been\\": \\"removed\\"}",
       "id": "9016911228971028736"
      }, {
       "status": "SCHEDULED",
       "created_ts": "1459200369835999",
       "bucket": "user.username",
       "result_details_json": "null",
       "status_changed_ts": "1459200369835988",
       "created_by": "user:username@example.com",
       "updated_ts": "1459200369835944",
       "utcnow_ts": "1459200369962377",
       "parameters_json": "{\\"This_has_been\\": \\"removed\\"}",
       "id": "9016911228971328738"
      }
       ],
     "kind": "buildbucket#resourcesItem",
     "etag": "\\"8uCIh8TRuYs4vPN3iWmly9SJMqw\\""
   }
  """
  mock_buildbucket_single_response = """
    {
      "build":{
       "status": "SCHEDULED",
       "created_ts": "1459200369835900",
       "bucket": "user.username",
       "result_details_json": "null",
       "status_changed_ts": "1459200369835930",
       "created_by": "user:username@example.com",
       "updated_ts": "1459200369835940",
       "utcnow_ts": "1459200369962370",
       "parameters_json": "{\\"This_has_been\\": \\"removed\\"}",
       "id": "9016911228971028736"
       },
     "kind": "buildbucket#resourcesItem",
     "etag": "\\"8uCIh8TRuYs4vPN3iWmly9SJMqw\\""
   }
  """
  yield (api.test('basic') +
         api.step_data(
             'buildbucket.put',
             stdout=api.raw_io.output(mock_buildbucket_multi_response)) +
         api.step_data(
             'buildbucket.get',
             stdout=api.raw_io.output(mock_buildbucket_single_response)) +
         api.properties(
             buildbucket={'build': {'tags': [
                 'buildset:patch/rietveld/cr.chromium.org/123/10001']}}))
  yield (api.test('basic_win') +
         api.step_data(
             'buildbucket.put',
             stdout=api.raw_io.output(mock_buildbucket_multi_response)) +
         api.step_data(
             'buildbucket.get',
             stdout=api.raw_io.output(mock_buildbucket_single_response)) +
         api.platform('win', 32) +
         api.properties(
             buildbucket={'build': {'tags': [
                 'buildset:patch/rietveld/cr.chromium.org/123/10001']}}))

  yield (api.test('no_properties'))
