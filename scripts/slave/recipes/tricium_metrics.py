# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from google.protobuf import json_format
from PB.tricium.data import Data

DEPS = [
    'chromium',
    'chromium_checkout',
    'depot_tools/gclient',
    'depot_tools/git',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/cipd',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/tricium',
]


def _RunMetricsAnalyzer(api, checkout_dir, prev_dir, src_metrics_paths,
                        patch_path):
  packages_dir = api.path['cleanup'].join('packages')
  ensure_file = api.cipd.EnsureFile()
  ensure_file.add_package('infra/tricium/function/metrics', 'live')
  api.cipd.ensure(packages_dir, ensure_file)

  metrics = packages_dir.join('metrics_analyzer')
  out_dir = api.path['cleanup'].join('out')
  enums_path = api.path.join('src', 'tools', 'metrics', 'histograms',
                             'enums.xml')
  api.step('metrics', [
      metrics, '-input', checkout_dir, '-output', out_dir, '-previous',
      prev_dir, '-patch', patch_path, '-enums', enums_path, '--'
  ] + src_metrics_paths)

  # This is where the Tricium metrics analyzer should write all results to.
  out_file = out_dir.join('tricium', 'data', 'results.json')

  text_result = api.file.read_text('metrics_output', out_file)
  results_msg = json_format.Parse(text_result, Data.Results())
  result = api.step('write_results', [])
  result.presentation.properties['tricium'] = json_format.MessageToJson(
      results_msg)


def RunSteps(api):
  assert api.tryserver.is_tryserver

  with api.chromium.chromium_layout():
    api.gclient.set_config('chromium')
    api.chromium.set_config('chromium')

    bot_config = {}
    checkout_dir = api.chromium_checkout.get_checkout_dir(bot_config)
    with api.context(cwd=checkout_dir):
      api.chromium_checkout.ensure_checkout(bot_config)

    src_dir = checkout_dir.join('src')
    with api.context(cwd=src_dir):
      # Do not analyze removed files.
      affected = [
          f for f in api.chromium_checkout.get_files_affected_by_patch()
          if api.path.exists(src_dir.join(f))
      ]

      metrics_filenames = {'histograms.xml', 'fieldtrial_testing_config.json'}
      metrics_paths = [
          path for path in affected
          if api.path.basename(path) in metrics_filenames
      ]

      if not metrics_paths:
        api.python.succeeding_step(
            'no_metrics_paths',
            'No files relevant to Tricium metrics analysis were changed')
        return

      # Put last version of changed files in temporary directory.
      prev_dir = api.path['cleanup'].join('previous')
      for path in metrics_paths:
        prev_dir_path = prev_dir.join('src', path)
        api.file.ensure_directory('create_directories',
                                  api.path.dirname(prev_dir_path))
        api.git(
            'show',
            'HEAD~:' + path,
            stdout=api.raw_io.output(leak_to=prev_dir_path))

      # Get the diff itself, with paths formatted as Tricium analyzer expects.
      patch_path = api.path['cleanup'].join('tricium_generated_diff.patch')
      diff_arg_list = [
          'diff', 'FETCH_HEAD~', 'FETCH_HEAD', '--output=' + str(patch_path),
          '--src-prefix=' + str(api.path.join('a', 'src', '')),
          '--dst-prefix=' + str(api.path.join('b', 'src', '')), '--'
      ] + metrics_paths
      api.git(*diff_arg_list)

      # Prepend src/ to each path, as the Tricium analyzer expects.
      src_metrics_paths = [api.path.join('src', p) for p in metrics_paths]

      # Run the metrics analyzer.
      with api.step.nest('metrics'):
        _RunMetricsAnalyzer(api, checkout_dir, prev_dir, src_metrics_paths,
                            patch_path)


def GenTests(api):

  def test_with_patch(name,
                      affected_files,
                      include_diff=True,
                      auto_exist_files=True,
                      author='ltina@google.com'):
    test = (
        api.test(name) + api.properties.tryserver(
            build_config='Release',
            mastername='tryserver.chromium.linux',
            buildername='tricium-metrics-analysis',
            buildnumber='1234',
            patch_set=1) + api.platform('linux', 64))

    if include_diff:
      test += api.step_data('git diff to analyze patch',
                            api.raw_io.stream_output('\n'.join(affected_files)))

    if auto_exist_files:
      test += api.path.exists(*[
          api.path['cache'].join('builder', 'src', x) for x in affected_files
      ])

    return test

  yield (test_with_patch('no_files', affected_files=[]) + api.post_process(
      post_process.DoesNotRun, 'metrics') + api.post_process(
          post_process.StatusSuccess) + api.post_process(
              post_process.DropExpectation))

  yield (
      test_with_patch('no_analysis_non_xml', affected_files=['some/file.txt']) +
      api.post_process(post_process.DoesNotRun, 'metrics') + api.post_process(
          post_process.StatusSuccess) + api.post_process(
              post_process.DropExpectation))

  yield (test_with_patch('no_analysis_xml', affected_files=['some/file.xml']) +
         api.post_process(post_process.DoesNotRun, 'metrics') +
         api.post_process(post_process.StatusSuccess) + api.post_process(
             post_process.DropExpectation))

  yield (test_with_patch(
      'removed_file',
      affected_files=['some/test/test2/histograms.xml'],
      auto_exist_files=False) + api.post_process(
          post_process.DoesNotRun, 'metrics') + api.post_process(
              post_process.StatusSuccess) + api.post_process(
                  post_process.DropExpectation))

  yield (
      test_with_patch(
          'analyze_xml',
          affected_files=['some/test/test2/histograms.xml']) + api.step_data(
              'metrics.metrics_output',
              api.file.read_json({
                  "comments": [{
                      "category": "Metrics/Removed",
                      "message": "[ERROR]: Removed",
                      "path": "testdata/src/rm/remove_histogram.xml"
                  }]
              })) + api.post_process(post_process.StepSuccess, 'metrics') +
      api.post_process(post_process.StatusSuccess) + api.post_check(
          lambda check, steps:
            '[ERROR]: Removed' in
            steps['metrics.write_results'].output_properties['tricium']
      ) + api.post_process(post_process.DropExpectation))
