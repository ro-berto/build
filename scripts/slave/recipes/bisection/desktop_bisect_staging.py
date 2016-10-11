# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'auto_bisect_staging',
    'bisect_tester_staging',
    'chromium',
    'chromium_tests',
    'depot_tools/gclient',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]


def RunSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  # TODO(akuegel): Explicitly load the builder configs instead of relying on
  # builder.py from chromium_tests recipe module.
  bot_config = api.chromium_tests.create_bot_config_object(mastername,
                                                           buildername)
  api.chromium_tests.configure_build(bot_config)
  api.gclient.apply_config('perf')
  # TODO(robertocn): remove do_not_nest_wait_for_revision once downstream
  # expectations have been fixed, and make it behave like this by default.
  update_step, bot_db = api.chromium_tests.prepare_checkout(bot_config)
  api.path.c.dynamic_paths['catapult'] = api.path['slave_build'].join(
      'catapult')
  api.auto_bisect_staging.start_try_job(api, update_step=update_step,
                                        bot_db=bot_db,
                                        do_not_nest_wait_for_revision=True)


def GenTests(api):
  yield (api.test('basic') + api.properties.tryserver(
      path_config='kitchen',
      mastername='tryserver.chromium.perf',
      buildername='linux_perf_bisect') + api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('tools/auto_bisect/bisect.cfg')))

  config_json = {
      'command': './tools/perf/run_benchmark -v --browser=release sunspider',
      'max_time_minutes': '25',
      'repeat_count': '1',
      'truncate_percent': '25',
      'target_arch': 'ia32',
  }

  results_with_patch = """*RESULT dummy: dummy= [5.83,6.013,5.573]ms
Avg dummy: 5.907711ms
Sd  dummy: 0.255921ms
RESULT telemetry_page_measurement_results: num_failed= 0 count
RESULT telemetry_page_measurement_results: num_errored= 0 count

View online at http://storage.googleapis.com/chromium-telemetry/\
html-results/results-with_patch
"""

  results_without_patch = """*RESULT dummy: dummy= [5.83,6.013,5.573]ms
Avg dummy: 5.907711ms
Sd  dummy: 0.255921ms
RESULT telemetry_page_measurement_results: num_failed= 0 count
RESULT telemetry_page_measurement_results: num_errored= 0 count

View online at http://storage.googleapis.com/chromium-telemetry/html-results/\
results-without_patch
"""

  buildbucket_put_response = {
       "results":[{
        "build":{
         "status": "SCHEDULED",
         "created_ts": "1459200369835900",
         "bucket": "user.username",
         "result_details_json": "null",
         "status_changed_ts": "1459200369835930",
         "created_by": "user:username@example.com",
         "updated_ts": "1459200369835940",
         "utcnow_ts": "1459200369962370",
         "parameters_json": "{\"This_has_been\": \"removed\"}",
         "id": "9016911228971028736"
         },
       "kind": "buildbucket#resourcesItem",
       "etag": "\"8uCIh8TRuYs4vPN3iWmly9SJMqw\""
      }]
     }

  buildbucket_get_response = {
    "build":{
      "bucket": "master.tryserver.chromium.perf",
      "id": "9009962699124567824",
      "result": "SUCCESS",
      "status": "COMPLETED",
      "status_changed_utc": "Mon Jun 13 19:32:37 2016",
      "updated_utc": "Mon Jun 13 19:32:37 2016",
      "url": "http://build.chromium.org/p/tryserver.chromium.perf/builders/linux_perf_bisect/builds/6537",
      "utcnow_utc": "Tue Jun 21 21:33:56 2016"
    }
}

  yield (api.test('basic_perf_tryjob') + api.properties.tryserver(
      path_config='kitchen',
      mastername='tryserver.chromium.perf',
      buildername='linux_perf_bisect',
      patch_storage='rietveld',
      patchset='20001',
      issue='12345',
      is_test=True,
      rietveld="https://codereview.chromium.org") + api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('tools/run-perf-test.cfg')) +
         api.override_step_data('load config', api.json.output(config_json)) +
         api.step_data('gsutil exists', retcode=1) +
         api.step_data('buildbucket.put',
                            stdout=api.json.output(buildbucket_put_response)) +
         api.step_data('buildbucket.put (2)',
                            stdout=api.json.output(buildbucket_put_response)) +
         api.step_data('buildbucket.get',
                        stdout=api.json.output(buildbucket_get_response)) +
         api.step_data('buildbucket.get (2)',
                        stdout=api.json.output(buildbucket_get_response)) +
         api.step_data('Performance Test (Without Patch) 1 of 1',
                       stdout=api.raw_io.output(str(results_without_patch))) +
         api.step_data('Performance Test (With Patch) 1 of 1',
                       stdout=api.raw_io.output(str(results_with_patch))) +
         api.step_data('Post bisect results',
                       stdout=api.json.output({'status_code': 200})))
  perf_try_json = {
      'command': 'src/tools/perf/run_benchmark -v --browser=release sunspider',
      'max_time_minutes': '25',
      'repeat_count': '1',
      'truncate_percent': '25',
      'target_arch': 'ia32',
  }
  yield (api.test('deps_perf_tryjob') + api.properties.tryserver(
      path_config='kitchen',
      mastername='tryserver.chromium.perf',
      buildername='linux_perf_bisect',
      patch_project='v8',
      deps_revision_overrides={'src/v8': 'feeedbeed'},
      patch_storage='rietveld',
      patchset='20001',
      issue='12345',
      is_test=True,
      rietveld="https://codereview.chromium.org")
      + api.properties(perf_try_config=perf_try_json)
      + api.override_step_data(
          'git diff to analyze patch', api.raw_io.stream_output('')) +
         api.step_data('gsutil exists', retcode=1) +
         api.step_data('buildbucket.put',
                            stdout=api.json.output(buildbucket_put_response)) +
         api.step_data('buildbucket.put (2)',
                            stdout=api.json.output(buildbucket_put_response)) +
         api.step_data('buildbucket.get',
                        stdout=api.json.output(buildbucket_get_response)) +
         api.step_data('buildbucket.get (2)',
                        stdout=api.json.output(buildbucket_get_response)) +
         api.step_data('Performance Test (Without Patch) 1 of 1',
                       stdout=api.raw_io.output(str(results_without_patch))) +
         api.step_data('Performance Test (With Patch) 1 of 1',
                       stdout=api.raw_io.output(str(results_with_patch))) +
         api.step_data('Post bisect results',
                       stdout=api.json.output({'status_code': 200})))
  config_json.update({'metric': 'dummy/dummy'})

  yield (api.test('basic_perf_tryjob_with_metric') + api.properties.tryserver(
      path_config='kitchen',
      mastername='tryserver.chromium.perf',
      buildername='linux_perf_bisect',
      patch_storage='rietveld',
      patchset='20001',
      issue='12345',
      is_test=True,
      rietveld="https://codereview.chromium.org") + api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('tools/run-perf-test.cfg')) +
         api.override_step_data('load config', api.json.output(config_json)) +
         api.step_data('gsutil exists', retcode=1) +
         api.step_data('buildbucket.put',
                            stdout=api.json.output(buildbucket_put_response)) +
         api.step_data('buildbucket.put (2)',
                            stdout=api.json.output(buildbucket_put_response)) +
         api.step_data('buildbucket.get',
                        stdout=api.json.output(buildbucket_get_response)) +
         api.step_data('buildbucket.get (2)',
                        stdout=api.json.output(buildbucket_get_response)) +
         api.step_data('Performance Test (Without Patch) 1 of 1',
                       stdout=api.raw_io.output(results_without_patch)) +
         api.step_data('Performance Test (With Patch) 1 of 1',
                       stdout=api.raw_io.output(results_with_patch)) +
         api.step_data('Post bisect results',
                       stdout=api.json.output({'status_code': 200})))


  yield (api.test('perf_tryjob_failed_test') + api.properties.tryserver(
      path_config='kitchen',
      mastername='tryserver.chromium.perf',
      buildername='linux_perf_bisect',
      patch_storage='rietveld',
      patchset='20001',
      issue='12345',
      is_test=True,
      rietveld="https://codereview.chromium.org") + api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('tools/run-perf-test.cfg')) +
         api.override_step_data('load config', api.json.output(config_json)) +
         api.step_data('gsutil exists', retcode=1) +
         api.step_data('buildbucket.put',
                            stdout=api.json.output(buildbucket_put_response)) +
         api.step_data('buildbucket.put (2)',
                            stdout=api.json.output(buildbucket_put_response)) +
         api.step_data('buildbucket.get',
                        stdout=api.json.output(buildbucket_get_response)) +
         api.step_data('buildbucket.get (2)',
                        stdout=api.json.output(buildbucket_get_response)) +
         api.step_data('Performance Test (With Patch) 1 of 1',
                       retcode=1))

  config_json.update({'good_revision': '306475', 'bad_revision': '306476'})

  yield (
      api.test('basic_perf_tryjob_with_revisions') + api.properties.tryserver(
          path_config='kitchen',
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          patch_storage='rietveld',
          patchset='20001',
          issue='12345',
          is_test=True,
          rietveld="https://codereview.chromium.org") + api.override_step_data(
              'git diff to analyze patch',
              api.raw_io.stream_output('tools/run-perf-test.cfg')) +
      api.override_step_data('load config', api.json.output(config_json)) +
      api.step_data(
          'resolving commit_pos ' + config_json['good_revision'],
          stdout=api.raw_io.output('hash:d49c331def2a3bbf3ddd0096eb51551155')) +
      api.step_data(
          'resolving commit_pos ' + config_json['bad_revision'],
          stdout=api.raw_io.output(
              'hash:bad49c331def2a3bbf3ddd0096eb51551155')) +
      api.step_data('gsutil exists', retcode=1) +
      api.step_data('buildbucket.put',
                            stdout=api.json.output(buildbucket_put_response)) +
      api.step_data('buildbucket.get',
                            stdout=api.json.output(buildbucket_get_response)) +
      api.step_data(
          'Performance Test (d49c331def2a3bbf3ddd0096eb51551155) 1 of 1',
          stdout=api.raw_io.output(results_without_patch)) +
      api.step_data(
              'Performance Test (bad49c331def2a3bbf3ddd0096eb51551155) 1 of 1',
              stdout=api.raw_io.output(results_with_patch)) +
      api.step_data('Post bisect results',
                    stdout=api.json.output({'status_code': 200})))

  config_json = {
      'max_time_minutes': '25',
      'repeat_count': '1',
      'truncate_percent': '25',
      'target_arch': 'ia32',
  }

  yield (api.test('perf_tryjob_config_error') + api.properties.tryserver(
      path_config='kitchen',
      mastername='tryserver.chromium.perf',
      buildername='linux_perf_bisect') + api.properties(
          requester='abcdxyz@chromium.org') + api.override_step_data(
              'git diff to analyze patch',
              api.raw_io.stream_output('tools/run-perf-test.cfg')) +
         api.override_step_data('load config', api.json.output(config_json)))

  yield (api.test('perf_cq_run_benchmark') +
      api.properties.tryserver(
          path_config='kitchen',
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          patch_storage='rietveld',
          patchset='20001',
          issue='12345',
          is_test=True,
          rietveld="https://codereview.chromium.org") +
      api.properties(requester='commit-bot@chromium.org') +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('tools/perf/benchmarks/blink_perf.py')) +
      api.step_data('buildbucket.put',
              stdout=api.json.output(buildbucket_put_response)) +
      api.step_data('buildbucket.get',
              stdout=api.json.output(buildbucket_get_response)))

  yield (api.test('perf_cq_no_changes') +
      api.properties.tryserver(
          path_config='kitchen',
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          patch_storage='rietveld',
          patchset='20001',
          issue='12345',
          is_test=True,
          rietveld="https://codereview.chromium.org") +
      api.properties(requester='commit-bot@chromium.org') +
      api.override_step_data(
              'git diff to analyze patch',
              api.raw_io.stream_output('tools/no_benchmark_file')))

  yield (api.test('perf_cq_no_benchmark_to_run') +
      api.properties.tryserver(
          path_config='kitchen',
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          patch_storage='rietveld',
          patchset='20001',
          issue='12345',
          is_test=True,
          rietveld="https://codereview.chromium.org") +
      api.properties(requester='commit-bot@chromium.org') +
      api.override_step_data(
              'git diff to analyze patch',
              api.raw_io.stream_output('tools/perf/benchmarks/sunspider.py')) +
      api.step_data('buildbucket.put',
              stdout=api.json.output(buildbucket_put_response)) +
      api.step_data('buildbucket.get',
              stdout=api.json.output(buildbucket_get_response)))

  bisect_config = {
      'test_type': 'perf',
      'command': './tools/perf/run_benchmark -v '
                 '--browser=release page_cycler.intl_ar_fa_he',
      'metric': 'warm_times/page_load_time',
      'repeat_count': '2',
      'max_time_minutes': '5',
      'truncate_percent': '25',
      'bug_id': '425582',
      'gs_bucket': 'chrome-perf',
      'builder_host': 'master4.golo.chromium.org',
      'builder_port': '8341',
  }
  yield (
      api.test('basic_linux_bisect_tester_recipe') + api.properties.tryserver(
          path_config='kitchen',
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect') + api.step_data(
              'saving url to temp file',
              stdout=api.raw_io.output('/tmp/dummy1')) + api.step_data(
                  'saving json to temp file',
                  stdout=api.raw_io.output('/tmp/dummy2')) + api.properties(
                      bisect_config=bisect_config) + api.properties(
                          job_name='f7a7b4135624439cbd27fdd5133d74ec') +
      api.bisect_tester_staging(tempfile='/tmp/dummy') + api.properties(
          parent_got_revision='1111111') + api.properties(
              parent_build_archive_url='gs://test-domain/test-archive.zip'))

  bisect_ret_code_config = {
      'test_type': 'return_code',
      'command': './tools/perf/run_benchmark -v '
                 '--browser=release page_cycler.intl_ar_fa_he',
      'metric': 'warm_times/page_load_time',
      'repeat_count': '2',
      'max_time_minutes': '5',
      'truncate_percent': '25',
      'bug_id': '425582',
      'gs_bucket': 'chrome-perf',
      'builder_host': 'master4.golo.chromium.org',
      'builder_port': '8341',
  }
  yield (api.test('basic_linux_bisect_tester_recipe_ret_code') +
         api.properties.tryserver(path_config='kitchen',
                                  mastername='tryserver.chromium.perf',
                                  buildername='linux_perf_bisect') +
         api.step_data('saving url to temp file',
                       stdout=api.raw_io.output('/tmp/dummy1')) + api.step_data(
                           'saving json to temp file',
                           stdout=api.raw_io.output('/tmp/dummy2')) +
         api.properties(bisect_config=bisect_ret_code_config) + api.properties(
             job_name='f7a7b4135624439cbd27fdd5133d74ec') +
         api.bisect_tester_staging(tempfile='/tmp/dummy') + api.properties(
             parent_got_revision='1111111') + api.properties(
                 parent_build_archive_url='gs://test-domain/test-archive.zip'))
