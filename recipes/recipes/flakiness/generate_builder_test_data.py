# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from recipe_engine import post_process
from PB.recipe_engine import result as result_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'depot_tools/gsutil',
    'recipe_engine/buildbucket',
    'recipe_engine/cipd',
    'recipe_engine/file',
    'recipe_engine/futures',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/python',
    'recipe_engine/runtime',
    'recipe_engine/step',
]


def analyze_try_builder_test_history(api, builder, bucket, source,
                                     build_number):
  """Query test history for the given builder, and upload the results to CIPD

  Args:
    builder: (str) name of the try builder
    bucket: (str) name of gs bucket
    source: (str) gs path
    build_number: (int) buildbucket build number
  """
  with api.step.nest('analyze try builder {}'.format(builder)):
    gs_source = source.format(build_number, builder)
    gs_path = 'gs://{}/{}'.format(bucket, gs_source)
    cmd = [
        'vpython3',
        api.resource('query.py'),
        'history',
        '--builder={}'.format(builder),
        '--export-gs-path={}'.format(gs_path),
    ]
    api.step('query test history data', cmd)

    builder_file = api.path.mkstemp()
    api.gsutil.download(bucket, gs_source, builder_file)

    cmd = [
        'vpython3',
        api.resource('query.py'),
        'format',
        '--file={}'.format(builder_file),
    ]
    api.step('format json', cmd)

    dest_source = source.format('latest', builder)
    api.gsutil.upload(
        builder_file,
        bucket,
        dest_source,
        name='copy {} to latest'.format(builder))


def RunSteps(api):
  # This recipe queries ResultDB via BigQuery directly to determine
  # historical test results for each try builder. The historical test results
  # are bundled and uploaded to CIPD such that try builders that check for
  # flakiness can fetch this file to determine new tests.
  cmd = [
      'vpython3',
      api.resource('query.py'), 'builders', '--output-file',
      api.json.output()
  ]
  result = api.step('search for try builders', cmd)
  builders = result.json.output

  build_number = api.buildbucket.build.number
  bucket = 'flake_endorser'
  source = '{}/{}.json'
  if api.runtime.is_experimental:
    source = 'experimental/' + source

  futures = []
  with api.step.nest('generating historical test data'):
    for b in builders:
      futures.append(
          api.futures.spawn(analyze_try_builder_test_history, api, b, bucket,
                            source, build_number))

  for f in futures:
    f.result()


def GenTests(api):
  yield api.test(
      'basic',
      api.runtime(is_experimental=True),
      api.step_data('search for try builders',
                    api.json.output(['builder1', 'builder2'])),
      api.post_check(
          post_process.MustRun,
          'generating historical test data.analyze try builder builder1.'
          'query test history data'),
      api.post_check(post_process.MustRun, ('generating historical test data.'
                                            'analyze try builder builder1.'
                                            'gsutil copy builder1 to latest')),
      api.post_check(
          post_process.MustRun,
          'generating historical test data.analyze try builder builder2.'
          'query test history data'),
      api.post_check(post_process.MustRun, ('generating historical test data.'
                                            'analyze try builder builder2.'
                                            'gsutil copy builder2 to latest')),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
