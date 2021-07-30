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
    'depot_tools/gerrit',
    'depot_tools/git',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/cipd',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/tricium',
]


def _RunMetricsAnalyzer(api, src_dir, prev_dir, metrics_paths, patch_path):
  packages_dir = api.path['cleanup'].join('packages')
  version = 'test' if bool(api.tryserver.get_footer('Tricium-Test')) else 'live'

  with api.step.nest('load_' + version + '_analyzer'):
    ensure_file = api.cipd.EnsureFile()
    ensure_file.add_package('infra/tricium/function/metrics', version)
    api.cipd.ensure(packages_dir, ensure_file)

  metrics = packages_dir.join('metrics_analyzer')
  out_dir = api.path['cleanup'].join('out')
  enums_path = api.path.join('tools', 'metrics', 'histograms',
                             'enums.xml')
  api.step('metrics', [
      metrics, '-input', src_dir, '-output', out_dir, '-previous',
      prev_dir, '-patch', patch_path, '-enums', enums_path, '--'
  ] + metrics_paths)

  # This is where the Tricium metrics analyzer should write all results to.
  out_file = out_dir.join('tricium', 'data', 'results.json')

  text_result = api.file.read_text('metrics_output', out_file)
  results_msg = json_format.Parse(text_result, Data.Results())
  result = api.step('write_results', [])
  result.presentation.properties['tricium'] = json_format.MessageToJson(
      results_msg)


def RunSteps(api):
  assert api.tryserver.is_tryserver

  # Do not run if "Tricium-Skip-Metrics" is in the commit message footer.
  if bool(api.tryserver.get_footer('Tricium-Skip-Metrics')):
    return

  with api.chromium.chromium_layout():
    api.gclient.set_config('chromium')
    api.chromium.set_config('chromium')

    # Do not rebase the patch, so that the Tricium analyzer observes the correct
    # line numbers. Otherwise, line numbers would be relative to origin/master,
    # which will typically be synced to include changes subsequent to the actual
    # patch.
    api.chromium_checkout.ensure_checkout(gerrit_no_rebase_patch_ref=True)

    src_dir = api.chromium_checkout.checkout_dir.join('src')
    with api.context(cwd=src_dir):
      # Do not analyze removed files.
      affected = [
          f for f in api.chromium_checkout.get_files_affected_by_patch()
          if api.path.exists(src_dir.join(f))
      ]

      metrics_filenames = {
          'histograms.xml', 'fieldtrial_testing_config.json',
          'histogram_suffixes_list.xml'
      }
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
      prev_dir = api.path['cleanup'].join('previous', 'src')
      for path in metrics_paths:
        prev_dir_path = prev_dir.join(path)
        api.file.ensure_directory('create_directories',
                                  api.path.dirname(prev_dir_path))
        # `git show` throws an error if the file doesn't exist. This could
        # happen when users just added a new histograms.xml. In this case,
        # we just need to touch an empty file as the placeholder.
        try:
          api.git(
              'show',
              'FETCH_HEAD~:' + path,
              stdout=api.raw_io.output(leak_to=prev_dir_path))
        except Exception:
          api.step('touch an empty file', ['touch', prev_dir_path])

      # Get the diff itself, with paths formatted as Tricium analyzer expects.
      patch_path = api.path['cleanup'].join('tricium_generated_diff.patch')
      diff_arg_list = [
          'diff', 'FETCH_HEAD~', 'FETCH_HEAD', '--output=' + str(patch_path),
          '--'
      ] + metrics_paths
      api.git(*diff_arg_list)

      # Run the metrics analyzer.
      with api.step.nest('metrics'):
        _RunMetricsAnalyzer(api, src_dir, prev_dir, metrics_paths, patch_path)


def GenTests(api):

  def test_with_patch(name,
                      affected_files,
                      include_diff=True,
                      auto_exist_files=True,
                      include_parse=False,
                      skip_footer=False,
                      test_footer=False):
    test = (
        api.test(name) + api.properties.tryserver(
            build_config='Release',
            buildername='tricium-metrics-analysis',
            buildnumber='1234',
            patch_set=1))

    skip_footer_json = {'Tricium-Skip-Metrics': True} if skip_footer else {}
    test += api.override_step_data('parse description',
                                   api.json.output(skip_footer_json))

    if include_diff:
      test += api.step_data('git diff to analyze patch',
                            api.raw_io.stream_output('\n'.join(affected_files)))

    if include_parse:
      test_footer_json = {'Tricium-Test': True} if test_footer else {}
      test += api.override_step_data('metrics.parse description',
                                     api.json.output(test_footer_json))

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
      'no_analysis_skip_footer',
      affected_files=['some/test/test2/histograms.xml'],
      skip_footer=True,
      include_diff=False) + api.post_process(
          post_process.DoesNotRun, 'bot_update') + api.post_process(
              post_process.StatusSuccess) + api.post_process(
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
          'test_version_if_footer',
          affected_files=['some/test/test2/histograms.xml'],
          include_parse=True,
          test_footer=True) + api.step_data('metrics.metrics_output',
                                            api.file.read_json({})) +
      api.post_process(post_process.DoesNotRun, 'metrics.load_live_analyzer') +
      api.post_process(post_process.StepSuccess, 'metrics.load_test_analyzer') +
      api.post_process(post_process.StepSuccess, 'metrics') + api.post_process(
          post_process.StatusSuccess) + api.post_process(
              post_process.DropExpectation))

  yield (
      test_with_patch(
          'analyze_xml_live',
          affected_files=['some/test/test2/histograms.xml'],
          include_parse=True) + api.step_data(
              'metrics.metrics_output',
              api.file.read_json({
                  "comments": [{
                      "category": "Metrics/Removed",
                      "message": "[ERROR]: Removed",
                      "path": "testdata/src/rm/remove_histograms.xml"
                  }]
              })) +
      api.post_process(post_process.DoesNotRun, 'metrics.load_test_analyzer') +
      api.post_process(post_process.StepSuccess, 'metrics.load_live_analyzer') +
      api.post_process(post_process.StepSuccess, 'metrics') +
      api.post_process(post_process.StatusSuccess) +
      api.post_check(lambda check, steps: '[ERROR]: Removed' in steps[
          'metrics.write_results'].output_properties['tricium']) +
      api.post_process(post_process.DropExpectation))

  yield (
      test_with_patch(
          'show_file_path_not_found_but_succeed',
          affected_files=['some/test/test2/histograms.xml'],
          include_parse=True) +
      # Simulate a file missing error, this could happen if users add a new file
      # Make sure the exception is captured and the analyzer shouldn't fail.
      api.step_data('git show', retcode=128) + api.step_data(
          'metrics.metrics_output',
          api.file.read_json({
              "comments": [{
                  "category": "Metrics/Removed",
                  "message": "[ERROR]: Removed",
                  "path": "testdata/src/rm/remove_histograms.xml"
              }]
          })) +
      api.post_process(post_process.DoesNotRun, 'metrics.load_test_analyzer') +
      api.post_process(post_process.StepSuccess, 'metrics.load_live_analyzer') +
      api.post_process(post_process.StepSuccess, 'metrics') +
      api.post_process(post_process.StatusSuccess) +
      api.post_check(lambda check, steps: '[ERROR]: Removed' in steps[
          'metrics.write_results'].output_properties['tricium']) +
      api.post_process(post_process.DropExpectation))
