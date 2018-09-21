# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'auto_bisect_staging',
    'bisect_tester_staging',
    'chromium',
    'chromium_tests',
    'depot_tools/gclient',
    'recipe_engine/buildbucket',
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
  bot_config = api.chromium_tests.create_bot_config_object(
      [api.chromium_tests.create_bot_id(mastername, buildername)])
  api.chromium_tests.configure_build(bot_config)
  api.gclient.apply_config('perf')
  # TODO(robertocn): remove do_not_nest_wait_for_revision once downstream
  # expectations have been fixed, and make it behave like this by default.
  update_step, bot_db = api.chromium_tests.prepare_checkout(
      bot_config, disable_syntax_validation=True)
  api.path.c.dynamic_paths['catapult'] = api.path['start_dir'].join(
      'catapult')
  api.path.c.dynamic_paths['bisect_results'] = api.path['start_dir'].join(
      'bisect_results')
  api.auto_bisect_staging.start_try_job(api, update_step=update_step,
                                        bot_db=bot_db,
                                        do_not_nest_wait_for_revision=True)


def GenTests(api):

  def try_build(**kwargs):
    params = dict(
        project='chromium',
        builder='linux_perf_bisect',
        git_repo='https://chromium.googlesource.com/chromium/src',
    )
    params.update(kwargs)
    return api.buildbucket.try_build(**params)

  yield (
      api.test('basic') +
      try_build() +
      api.properties.tryserver(
          path_config='kitchen',
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect') +
      api.override_step_data(
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

View online at https://console.developers.google.com/\
m/cloudstorage/b/chromium-telemetry/o/html-results/results-with
"""

  results_without_patch = """*RESULT dummy: dummy= [5.83,6.013,5.573]ms
Avg dummy: 5.907711ms
Sd  dummy: 0.255921ms
RESULT telemetry_page_measurement_results: num_failed= 0 count
RESULT telemetry_page_measurement_results: num_errored= 0 count

View online at https://console.developers.google.com/\
m/cloudstorage/b/chromium-telemetry/o/html-results/results-without
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

  yield (
      api.test('basic_perf_tryjob') +
      try_build() +
      api.properties.tryserver(
          path_config='kitchen',
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          gerrit_project='chromium',
          is_test=True) +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('tools/run-perf-test.cfg')) +
      api.override_step_data('load config', api.json.output(config_json)) +
      api.step_data('Running WITHOUT patch.gsutil exists', retcode=1) +
      api.step_data(
          'Running WITH patch.buildbucket.put',
          stdout=api.json.output(buildbucket_put_response)) +
      api.step_data(
          'Running WITHOUT patch.buildbucket.put',
          stdout=api.json.output(buildbucket_put_response)) +
      api.step_data(
          'Running WITH patch.buildbucket.get',
          stdout=api.json.output(buildbucket_get_response)) +
      api.step_data(
          'Running WITH patch.buildbucket.get (2)',
          stdout=api.json.output(buildbucket_get_response)) +
      api.step_data(
          'Running WITH patch.Performance Test (With Patch) 1 of 1',
          api.raw_io.output_text(
              str(results_with_patch), name='stdout_proxy')) +
     api.step_data(
          'Running WITHOUT patch.Performance Test (Without Patch) 1 of 1',
          api.raw_io.output_text(
              str(results_without_patch), name='stdout_proxy')) +
     api.step_data(
        'Notify dashboard.Post bisect results',
        api.json.output({'status_code': 200})))

  perf_try_json = {
      'command': 'src/tools/perf/run_benchmark -v --browser=release sunspider' +
          ' --upload-bucket=private',
      'max_time_minutes': '25',
      'repeat_count': '1',
      'truncate_percent': '25',
      'target_arch': 'ia32',
  }

  yield (
      api.test('basic_perf_tryjob_with_bucket') +
      try_build() +
      api.properties.tryserver(
          path_config='kitchen',
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          gerrit_project='chromium',
          is_test=True) +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('tools/run-perf-test.cfg')) +
      api.override_step_data('load config', api.json.output(perf_try_json)) +
      api.step_data('Running WITHOUT patch.gsutil exists', retcode=1) +
      api.step_data(
         'Running WITH patch.buildbucket.put',
         stdout=api.json.output(buildbucket_put_response)) +
      api.step_data(
         'Running WITHOUT patch.buildbucket.put',
         stdout=api.json.output(buildbucket_put_response)) +
      api.step_data(
         'Running WITH patch.buildbucket.get',
         stdout=api.json.output(buildbucket_get_response)) +
      api.step_data(
         'Running WITH patch.buildbucket.get (2)',
         stdout=api.json.output(buildbucket_get_response)) +
      api.step_data(
         'Running WITH patch.Performance Test (With Patch) 1 of 1',
         stdout=api.raw_io.output_text(str(results_without_patch))) +
      api.step_data(
         'Running WITHOUT patch.Performance Test (Without Patch) 1 of 1',
         stdout=api.raw_io.output_text(str(results_with_patch))) +
      api.step_data(
         'Notify dashboard.Post bisect results',
         api.json.output({'status_code': 200})))

  perf_try_json = {
      'command': 'src/tools/perf/run_benchmark -v --browser=release sunspider',
      'max_time_minutes': '25',
      'repeat_count': '1',
      'truncate_percent': '25',
      'target_arch': 'ia32',
  }

  yield (
      api.test('deps_perf_tryjob') +
      try_build(
          git_repo='https://chromium.googlesource.com/v8/v8',
      ) +
      api.properties.tryserver(
          path_config='kitchen',
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          patch_project='v8',
          deps_revision_overrides={'src/v8': 'feeedbeed'},
          gerrit_project='chromium',
          is_test=True) +
      api.properties(perf_try_config=perf_try_json) +
      api.override_step_data(
          'git diff to analyze patch', api.raw_io.stream_output('')) +
      api.step_data('Running WITHOUT patch.gsutil exists', retcode=1) +
      api.step_data(
         'Running WITH patch.buildbucket.put',
         stdout=api.json.output(buildbucket_put_response)) +
      api.step_data(
         'Running WITHOUT patch.buildbucket.put',
         stdout=api.json.output(buildbucket_put_response)) +
      api.step_data(
         'Running WITH patch.buildbucket.get',
         stdout=api.json.output(buildbucket_get_response)) +
      api.step_data(
         'Running WITH patch.buildbucket.get (2)',
         stdout=api.json.output(buildbucket_get_response)) +
      api.step_data(
         'Running WITH patch.Performance Test (With Patch) 1 of 1',
         api.raw_io.output_text(
             str(results_with_patch), name='stdout_proxy')) +
      api.step_data(
         'Running WITHOUT patch.Performance Test (Without Patch) 1 of 1',
         api.raw_io.output_text(
             str(results_without_patch), name='stdout_proxy')) +
      api.step_data(
         'Notify dashboard.Post bisect results',
         api.json.output({'status_code': 200})))

  config_json.update({'metric': 'dummy/dummy'})

  yield (
      api.test('basic_perf_tryjob_with_metric') +
      try_build() +
      api.properties.tryserver(
          path_config='kitchen',
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          gerrit_project='chromium',
          is_test=True) +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('tools/run-perf-test.cfg')) +
      api.override_step_data('load config', api.json.output(config_json)) +
      api.step_data('Running WITHOUT patch.gsutil exists', retcode=1) +
      api.step_data(
          'Running WITH patch.buildbucket.put',
          stdout=api.json.output(buildbucket_put_response)) +
      api.step_data(
          'Running WITHOUT patch.buildbucket.put',
          stdout=api.json.output(buildbucket_put_response)) +
      api.step_data(
          'Running WITH patch.buildbucket.get',
          stdout=api.json.output(buildbucket_get_response)) +
      api.step_data(
          'Running WITH patch.buildbucket.get (2)',
          stdout=api.json.output(buildbucket_get_response)) +
      api.step_data(
          'Running WITH patch.Performance Test (With Patch) 1 of 1',
          api.raw_io.output_text(
              str(results_with_patch), name='stdout_proxy')) +
      api.step_data(
          'Running WITHOUT patch.Performance Test (Without Patch) 1 of 1',
          api.raw_io.output_text(
              str(results_without_patch), name='stdout_proxy')) +
      api.step_data(
          'Notify dashboard.Post bisect results',
          api.json.output({'status_code': 200})))

  config_valueset = config_json
  config_valueset['command'] += ' --output_format=valueset'

  yield (
      api.test('basic_perf_tryjob_with_metric_valueset') +
      try_build() +
      api.properties.tryserver(
          path_config='kitchen',
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          gerrit_project='chromium',
          is_test=True) +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('tools/run-perf-test.cfg')) +
      api.override_step_data(
          'load config', api.json.output(config_valueset)) +
      api.step_data('Running WITHOUT patch.gsutil exists', retcode=1) +
      api.step_data(
          'Running WITH patch.buildbucket.put',
          stdout=api.json.output(buildbucket_put_response)) +
      api.step_data(
          'Running WITHOUT patch.buildbucket.put',
          stdout=api.json.output(buildbucket_put_response)) +
      api.step_data(
          'Running WITH patch.buildbucket.get',
          stdout=api.json.output(buildbucket_get_response)) +
      api.step_data(
          'Running WITH patch.buildbucket.get (2)',
          stdout=api.json.output(buildbucket_get_response)) +
      api.step_data(
          'Running WITH patch.Performance Test (With Patch) 1 of 1',
          api.raw_io.output_text(
              str(results_with_patch), name='stdout_proxy')) +
      api.step_data(
          'Running WITHOUT patch.Performance Test (Without Patch) 1 of 1',
          api.raw_io.output_text(
              str(results_without_patch), name='stdout_proxy')) +
      api.step_data(
          'Notify dashboard.Post bisect results',
          api.json.output({'status_code': 200})))

  yield (
      api.test('perf_tryjob_failed_test') +
      try_build() +
      api.properties.tryserver(
          path_config='kitchen',
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          gerrit_project='chromium',
          is_test=True) +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('tools/run-perf-test.cfg')) +
      api.override_step_data('load config', api.json.output(config_json)) +
      api.step_data('Running WITHOUT patch.gsutil exists', retcode=1) +
      api.step_data(
          'Running WITH patch.buildbucket.put',
          stdout=api.json.output(buildbucket_put_response)) +
      api.step_data(
          'Running WITHOUT patch.buildbucket.put',
          stdout=api.json.output(buildbucket_put_response)) +
      api.step_data(
          'Running WITH patch.buildbucket.get',
          stdout=api.json.output(buildbucket_get_response)) +
      api.step_data(
          'Running WITH patch.buildbucket.get (2)',
          stdout=api.json.output(buildbucket_get_response)) +
      api.step_data(
          'Running WITH patch.Performance Test (With Patch) 1 of 1',
          retcode=1))

  config_json.update({'good_revision': '306475', 'bad_revision': '306476'})

  yield (
      api.test('basic_perf_tryjob_with_revisions') +
      try_build() +
      api.properties.tryserver(
          path_config='kitchen',
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          gerrit_project='chromium',
          is_test=True) +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('tools/run-perf-test.cfg')) +
      api.override_step_data('load config', api.json.output(config_json)) +
      api.step_data(
          'resolving commit_pos ' + config_json['good_revision'],
          stdout=api.raw_io.output_text(
              'hash:d49c331def2a3bbf3ddd0096eb51551155')) +
      api.step_data(
          'resolving commit_pos ' + config_json['bad_revision'],
          stdout=api.raw_io.output_text(
              'hash:bad49c331def2a3bbf3ddd0096eb51551155')) +
      api.step_data('Running WITHOUT patch.gsutil exists', retcode=1) +
      api.step_data(
          'Running WITH patch.buildbucket.put',
          stdout=api.json.output(buildbucket_put_response)) +
      api.step_data(
          'Running WITHOUT patch.buildbucket.put',
          stdout=api.json.output(buildbucket_put_response)) +
      api.step_data(
          'Running WITH patch.buildbucket.get',
          stdout=api.json.output(buildbucket_get_response)) +
      api.step_data(
          'Running WITH patch.buildbucket.get (2)',
          stdout=api.json.output(buildbucket_get_response)) +
      api.step_data(
          'Running WITH patch.Performance Test (With Patch) 1 of 1',
          api.raw_io.output_text(
              str(results_with_patch), name='stdout_proxy')) +
      api.step_data(
          'Running WITHOUT patch.Performance Test (Without Patch) 1 of 1',
          api.raw_io.output_text(
              str(results_without_patch), name='stdout_proxy')) +
      api.step_data('Notify dashboard.Post bisect results',
                    api.json.output({'status_code': 200})))

  config_json = {
      'max_time_minutes': '25',
      'repeat_count': '1',
      'truncate_percent': '25',
      'target_arch': 'ia32',
  }

  yield (api.test('perf_tryjob_config_error') +
      try_build() +
      api.properties.tryserver(
          path_config='kitchen',
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect') + api.properties(
              requester='abcdxyz@chromium.org') + api.override_step_data(
                  'git diff to analyze patch',
                  api.raw_io.stream_output('tools/run-perf-test.cfg')) +
             api.override_step_data('load config', api.json.output(config_json))
       )

  yield (api.test('perf_tryjob_no_config') +
      try_build() +
      api.properties.tryserver(
          path_config='kitchen',
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect',
          gerrit_project='chromium',
          is_test=True) +
      api.properties(requester='commit-bot@chromium.org') +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('tools/no_benchmark_file')))
