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
    'recipe_engine/raw_io',
    'recipe_engine/runtime',
    'recipe_engine/step',
    'tar',
]


def analyze_try_builder_test_history(api, builder, bucket, build_number):
  """Query test history for the given builder, and upload the results to CIPD

  Args:
    builder: (str) name of the try builder
    bucket: (str) name of gs bucket
    build_number: (int) buildbucket build number
  """
  with api.step.nest('analyze try builder {}'.format(builder)):
    source = '{}/{}'
    if api.runtime.is_experimental:
      source = 'experimental/' + source

    # we're setting wildcard suffixes to ensure that the larger tables can
    # partition their results before the export to GS.
    export_source = source + '_*.json'
    gs_source = export_source.format(build_number, builder)
    export_gs_path = 'gs://{}/{}'.format(bucket, gs_source)
    cmd = [
        'vpython3',
        api.resource('query.py'),
        'history',
        '--builder={}'.format(builder),
        '--export-gs-path={}'.format(export_gs_path),
    ]
    api.step('query test history data', cmd)

    builder_folder = api.path.mkdtemp()
    # gsutil.download doesn't support appending args before the cp command.
    api.gsutil(['-m', 'cp', export_gs_path, builder_folder])

    files = api.file.glob_paths(
        'find all paritioned json files',
        builder_folder,
        builder + '_*.json',
        test_data=['[CLEANUP]/builder1_000.json'])

    builder_output_file = api.path['cleanup'].join('{}.json'.format(builder))
    cmd = ['vpython3', api.resource('query.py'), 'format']
    for f in files:
      cmd += ['--file', str(f)]
    cmd += ['--output-file', builder_output_file]
    api.step('format json', cmd)

    tar_filename = '{}.json.tar.gz'.format(builder)
    tar_gz = builder_folder.join(tar_filename)
    pkg = api.tar.make_package(api.path['cleanup'], tar_gz, compression='gz')
    pkg.add_file(builder_output_file)
    pkg.tar('Create {}'.format(tar_filename))

    dest_gs_source = source.format('latest', tar_filename)
    api.gsutil.upload(
        tar_gz,
        bucket,
        dest_gs_source,
        args=['-Z'],
        name='copy {} to latest'.format(tar_filename))


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

  futures = []
  with api.step.nest('generating historical test data'):
    for b in builders:
      futures.append(
          api.futures.spawn(analyze_try_builder_test_history, api, b, bucket,
                            build_number))

  for f in futures:
    f.result()


def GenTests(api):
  yield api.test(
      'basic',
      api.runtime(is_experimental=True),
      api.step_data('search for try builders', api.json.output(['builder1'])),
      api.post_check(
          post_process.MustRun,
          'generating historical test data.analyze try builder builder1.'
          'query test history data'),
      api.post_check(post_process.MustRun,
                     ('generating historical test data.'
                      'analyze try builder builder1.'
                      'gsutil copy builder1.json.tar.gz to latest')),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
