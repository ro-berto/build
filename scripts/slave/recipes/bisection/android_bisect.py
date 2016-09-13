# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

DEPS = [
    'auto_bisect',
    'bisect_tester',
    'depot_tools/bot_update',
    'chromium',
    'chromium_android',
    'chromium_tests',
    'depot_tools/gclient',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]

REPO_URL = 'https://chromium.googlesource.com/chromium/src.git'

BUILDERS = freeze({
    'tryserver.chromium.perf': {
        'builders': {
            'android_one_perf_bisect': {
                'recipe_config': 'main_builder_rel_mb',
                'gclient_apply_config': ['android', 'perf'],
                'bucket': 'chrome-perf',
            },
            'android_nexus5_perf_bisect': {
                'recipe_config': 'main_builder_rel_mb',
                'gclient_apply_config': ['android', 'perf'],
                'bucket': 'chrome-perf',
            },
            'android_nexus5X_perf_bisect': {
                'recipe_config': 'arm64_builder_rel_mb',
                'gclient_apply_config': ['android', 'perf'],
                'bucket': 'chrome-perf',
            },
            'android_nexus6_perf_bisect': {
                'recipe_config': 'main_builder_rel_mb',
                'gclient_apply_config': ['android', 'perf'],
                'bucket': 'chrome-perf',
            },
            'android_nexus7_perf_bisect': {
                'recipe_config': 'main_builder_rel_mb',
                'gclient_apply_config': ['android', 'perf'],
                'bucket': 'chrome-perf',
            },
            'android_nexus9_perf_bisect': {
                'recipe_config': 'arm64_builder_rel_mb',
                'gclient_apply_config': ['android', 'perf'],
                'bucket': 'chrome-perf',
            },
            'android_s5_perf_bisect': {
                'recipe_config': 'main_builder_rel_mb',
                'gclient_apply_config': ['android', 'perf'],
                'bucket': 'chrome-perf',
            },
            'android_s5_perf_cq': {
                'recipe_config': 'main_builder_rel_mb',
                'gclient_apply_config': ['android', 'perf'],
                'bucket': 'chrome-perf',
            },
            'android_fyi_perf_bisect': {
                'recipe_config': 'main_builder_rel_mb',
                'gclient_apply_config': ['android', 'perf'],
                'bucket': 'chrome-perf',
            },
            'android_webview_arm64_aosp_perf_bisect': {
                'recipe_config': 'main_builder_rel_mb',
                'gclient_apply_config': ['android', 'perf'],
                'bucket': 'chrome-perf',
                'webview': True,
            },
            'android_webview_nexus6_aosp_perf_bisect': {
                'recipe_config': 'main_builder_rel_mb',
                'gclient_apply_config': ['android', 'perf'],
                'bucket': 'chrome-perf',
                'webview': True,
            },
        },
    },
})

from recipe_engine.recipe_api import Property

PROPERTIES = {'mastername': Property(), 'buildername': Property(),}

def RunSteps(api, mastername, buildername):
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  # The following lines configures android bisect bot to to checkout codes,
  # executes runhooks, provisions devices and runs legacy bisect script.
  recipe_config = bot_config.get('recipe_config', 'perf')
  kwargs = {
      'REPO_NAME': 'src',
      'REPO_URL': REPO_URL,
      'INTERNAL': False,
      'BUILD_CONFIG': 'Release',
      'TARGET_PLATFORM': 'android',
  }
  kwargs.update(bot_config.get('kwargs', {}))
  api.chromium_android.configure_from_properties(recipe_config, **kwargs)
  api.chromium.set_config(recipe_config, **kwargs)
  api.chromium.ensure_goma()
  api.chromium_android.c.set_val({'deps_file': 'DEPS'})
  api.gclient.set_config('chromium')
  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)
  update_step = api.auto_bisect.ensure_checkout()
  api.path.c.dynamic_paths['catapult'] = api.m.auto_bisect.working_dir.join(
      'catapult')
  api.chromium_android.clean_local_files()

  bot_db = api.chromium_tests.create_bot_db_from_master_dict(mastername,
                                                             master_dict)

  api.auto_bisect.start_try_job(api, update_step=update_step, bot_db=bot_db,
                                do_not_nest_wait_for_revision=True)


def GenTests(api):
  config_json_main = {
      'command': ('./tools/perf/run_benchmark -v --browser=android-chrome '
                'sunspider'),
      'max_time_minutes': '25',
      'client_operation_id': '12345726327327',
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


  for _, master_dict in BUILDERS.items():
    for buildername in master_dict.get('builders', {}):
      config_json = config_json_main.copy()
      yield (api.test('basic_' + buildername) + api.properties.tryserver(
        path_config='kitchen',
        mastername='tryserver.chromium.perf',
        buildername=buildername,
        patch_storage='rietveld',
        patchset='20001',
        issue='12345',
        is_test=True,
        rietveld="https://codereview.chromium.org") + api.override_step_data(
              'git diff to analyze patch',
              api.raw_io.stream_output('tools/auto_bisect/bisect.cfg')))

      yield (
          api.test('basic_perf_tryjob_' + buildername) +
          api.properties.tryserver(
        path_config='kitchen',
        mastername='tryserver.chromium.perf',
        buildername=buildername,
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
                        stdout=api.raw_io.output(str(results_with_patch))))
      config_json.update({'metric': 'dummy/dummy'})

      yield (api.test('basic_perf_tryjob_with_metric_' + buildername) +
             api.properties.tryserver(
          path_config='kitchen',
          mastername='tryserver.chromium.perf',
          buildername=buildername,
          patch_storage='rietveld',
          patchset='20001',
          issue='12345',
          is_test=True,
          rietveld="https://codereview.chromium.org") + api.override_step_data(
                       'git diff to analyze patch',
                       api.raw_io.stream_output('tools/run-perf-test.cfg')) +
              api.override_step_data('load config',
                   api.json.output(config_json)) +
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
                  stdout=api.raw_io.output(results_with_patch)))

      yield (api.test('perf_tryjob_failed_test_' + buildername) +
          api.properties.tryserver(
              path_config='kitchen',
              mastername='tryserver.chromium.perf',
              buildername=buildername,
              patch_storage='rietveld',
              patchset='20001',
              issue='12345',
              is_test=True,
              rietveld="https://codereview.chromium.org") +
          api.override_step_data(
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
          api.step_data('Performance Test (With Patch) 1 of 1', retcode=1))
      config_json.update({'good_revision': '306475',
                          'bad_revision': '306476'})

      yield (
          api.test('basic_perf_tryjob_with_revisions_' + buildername) +
          api.properties.tryserver(
              path_config='kitchen',
              mastername='tryserver.chromium.perf',
              buildername=buildername,
              patch_storage='rietveld',
              patchset='20001',
              issue='12345',
              is_test=True,
              rietveld="https://codereview.chromium.org") +
          api.override_step_data(
              'git diff to analyze patch',
              api.raw_io.stream_output('tools/run-perf-test.cfg')) +
          api.override_step_data('load config', api.json.output(config_json)) +
          api.step_data('resolving commit_pos ' + config_json['good_revision'],
                        stdout=api.raw_io.output(
                            'hash:d49c331def2a3bbf3ddd0096eb51551155')) +
          api.step_data('resolving commit_pos ' + config_json['bad_revision'],
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
              stdout=api.raw_io.output(results_with_patch)))

      config_json = {
          'max_time_minutes': '25',
          'repeat_count': '1',
          'truncate_percent': '25',
          'target_arch': 'ia32',
      }

      yield (
          api.test('perf_tryjob_config_error_' + buildername) +
          api.properties.tryserver(
              path_config='kitchen',
              mastername='tryserver.chromium.perf',
              buildername=buildername) + api.properties(
                  requester='abcdxyz@chromium.org') + api.override_step_data(
                      'git diff to analyze patch',
                      api.raw_io.stream_output('tools/run-perf-test.cfg')) +
          api.override_step_data('load config', api.json.output(config_json)))

      yield (
          api.test('perf_cq_run_benchmark_' + buildername) +
          api.properties.tryserver(
                path_config='kitchen',
                mastername='tryserver.chromium.perf',
                buildername=buildername,
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

      yield (api.test('perf_cq_no_changes_' + buildername) +
          api.properties.tryserver(
                path_config='kitchen',
                mastername='tryserver.chromium.perf',
                buildername=buildername,
                patch_storage='rietveld',
                patchset='20001',
                issue='12345',
                is_test=True,
                rietveld="https://codereview.chromium.org") +
          api.properties(requester='commit-bot@chromium.org') +
          api.override_step_data(
                 'git diff to analyze patch',
                 api.raw_io.stream_output('tools/no_benchmark_file')))

      yield (
          api.test('perf_cq_no_benchmark_to_run_' + buildername) +
          api.properties.tryserver(
                path_config='kitchen',
                mastername='tryserver.chromium.perf',
                buildername=buildername,
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
                     '--browser=android-chromium page_cycler.intl_ar_fa_he',
          'metric': 'warm_times/page_load_time',
          'repeat_count': '2',
          'max_time_minutes': '5',
          'truncate_percent': '25',
          'bug_id': '425582',
          'gs_bucket': 'chrome-perf',
          'builder_host': 'master4.golo.chromium.org',
          'builder_port': '8341'
      }
      yield (api.test('basic_recipe_' + buildername) +
          api.properties.tryserver(
              path_config='kitchen',
              mastername='tryserver.chromium.perf',
              buildername=buildername) +
          api.step_data(
              'saving url to temp file',
              stdout=api.raw_io.output('/tmp/dummy1')) +
          api.step_data(
              'saving json to temp file',
              stdout=api.raw_io.output('/tmp/dummy2')) +
          api.properties(
                      bisect_config=bisect_config) + api.properties(
                          job_name='f7a7b4135624439cbd27fdd5133d74ec') +
             api.bisect_tester(tempfile='/tmp/dummy') +
             api.properties(parent_got_revision='1111111') + api.properties(
                 parent_build_archive_url='gs://test-domain/test-archive.zip'))

      local_bisect_config = {
          'test_type': 'perf',
          'command': './tools/perf/run_benchmark -v '
                     '--browser=android-chromium page_cycler.intl_ar_fa_he',
          'metric': 'warm_times/page_load_time',
          'repeat_count': '2',
          'max_time_minutes': '5',
          'truncate_percent': '25',
          'bug_id': '425582',
          'gs_bucket': 'chrome-perf',
          'builder_host': 'master4.golo.chromium.org',
          'builder_port': '8341',
          'good_revision': '306475',
          'bad_revision': '306476',
          'dummy_job_names': True
      }

  buildername = 'android_one_perf_bisect'
  good_revision_hash = 'e28dc0d49c331def2a3bbf3ddd0096eb51551155'
  bad_revision_hash = 'fc6dfc7ff5b1073408499478969261b826441144'
  working_device = [
      {
        "battery": {
            "status": "5",
            "scale": "100",
            "temperature": "249",
            "level": "100",
            "AC powered": "false",
            "health": "2",
            "voltage": "4286",
            "Wireless powered": "false",
            "USB powered": "true",
            "technology": "Li-ion",
            "present": "true"
        },
        "wifi_ip": "",
        "imei_slice": "Unknown",
        "ro.build.id": "LRX21O",
        "ro.build.product": "product_name",
        "build_detail":
            "google/razor/flo:5.0/LRX21O/1570415:userdebug/dev-keys",
        "serial": "1111",
        "adb_status": "device",
        "blacklisted": False,
        "usb_status": True,
    },
    {
      "adb_status": "offline",
      "blacklisted": True,
      "serial": "03e0363a003c6ad4",
      "usb_status": False,
    },
    {
      "adb_status": "unauthorized",
      "blacklisted": True,
      "serial": "03e0363a003c6ad5",
      "usb_status": True,
    },
    {
      "adb_status": "device",
      "blacklisted": True,
      "serial": "03e0363a003c6ad6",
      "usb_status": True,
    }
  ]

  two_devices = [
        {
          "battery": {
              "status": "5",
              "scale": "100",
              "temperature": "249",
              "level": "100",
              "AC powered": "false",
              "health": "2",
              "voltage": "4286",
              "Wireless powered": "false",
              "USB powered": "true",
              "technology": "Li-ion",
              "present": "true"
          },
          "wifi_ip": "",
          "imei_slice": "Unknown",
          "ro.build.id": "LRX21O",
          "ro.build.product": "product_name",
          "build_detail":
              "google/razor/flo:5.0/LRX21O/1570415:userdebug/dev-keys",
          "serial": "2222",
          "adb_status": "device",
          "blacklisted": False,
          "usb_status": True,
      },
      {
        "battery": {
            "status": "5",
            "scale": "100",
            "temperature": "249",
            "level": "100",
            "AC powered": "false",
            "health": "2",
            "voltage": "4286",
            "Wireless powered": "false",
            "USB powered": "true",
            "technology": "Li-ion",
            "present": "true"
        },
        "wifi_ip": "",
        "imei_slice": "Unknown",
        "ro.build.id": "LRX21O",
        "ro.build.product": "product_name",
        "build_detail":
            "google/razor/flo:5.0/LRX21O/1570415:userdebug/dev-keys",
        "serial": "1111",
        "adb_status": "device",
        "blacklisted": False,
        "usb_status": True,
    },
      {
        "adb_status": "offline",
        "blacklisted": True,
        "serial": "03e0363a003c6ad4",
        "usb_status": False,
      },
      {
        "adb_status": "unauthorized",
        "blacklisted": True,
        "serial": "03e0363a003c6ad5",
        "usb_status": True,
      },
      {
        "adb_status": "device",
        "blacklisted": True,
        "serial": "03e0363a003c6ad6",
        "usb_status": True,
      }
    ]

  # simulate the scenario when the first tested device works
  yield (api.test('local_basic_recipe_basic_device') +
    api.properties.tryserver(
        mastername='tryserver.chromium.perf', buildername=buildername) +
    api.properties(
        path_config='kitchen',
        bisect_config=local_bisect_config,
        job_name='f7a7b4135624439cbd27fdd5133d74ec',
        local_test=True,
        parent_got_revision='1111111',
        parent_build_archive_url='gs://test-domain/test-archive.zip') +
    api.bisect_tester(tempfile='/tmp/dummy') +
    api.step_data(
        'Gathering reference values.saving json to temp file',
        stdout=api.raw_io.output('/tmp/dummy3')) +
    api.step_data(
        'Gathering reference values.saving json to temp file (2)',
        stdout=api.raw_io.output('/tmp/dummy4')) +
    api.override_step_data('device_status',
        api.json.output(two_devices)) +
    api.override_step_data('device_status (2)',
        api.json.output(two_devices)) +
    api.step_data('Resolving reference range.crrev get commit hash for ' +
        ('refs/heads/master@{#%s}' % local_bisect_config['bad_revision']),
        stdout=api.json.output(
            {'git_sha': bad_revision_hash}))+
    api.step_data('Resolving reference range.crrev get commit hash for ' +
        ('refs/heads/master@{#%s}' % local_bisect_config[
            'good_revision']),
        stdout=api.json.output(
            {'git_sha': good_revision_hash}))+
    api.step_data('Expanding revision range.for revisions %s:%s' % (
        good_revision_hash, bad_revision_hash),
        stdout=api.json.output([[bad_revision_hash, 'ignored'],
            [good_revision_hash, 'ignored']])) +
    api.step_data('Post bisect results',
        stdout=api.json.output({'status_code': 200})))

  # simulate the scenario when the no device is connected.
  yield (api.test('local_basic_recipe_no_device') +
    api.properties.tryserver(
        mastername='tryserver.chromium.perf', buildername=buildername) +
    api.properties(
        path_config='kitchen',
        bisect_config=local_bisect_config,
        job_name='f7a7b4135624439cbd27fdd5133d74ec',
        local_test=True,
        parent_got_revision='1111111',
        parent_build_archive_url='gs://test-domain/test-archive.zip') +
    api.bisect_tester(tempfile='/tmp/dummy') +
    api.override_step_data('device_status', api.json.output([])) +
    api.override_step_data('device_status (2)', api.json.output([])))

  # simulate the scenario when tests fail not because of device
  # disconnection.
  yield (api.test('local_basic_recipe_failed_device') +
    api.properties.tryserver(
        mastername='tryserver.chromium.perf', buildername=buildername) +
    api.properties(
        path_config='kitchen',
        bisect_config=local_bisect_config,
        job_name='f7a7b4135624439cbd27fdd5133d74ec',
        local_test=True,
        parent_got_revision='1111111',
        parent_build_archive_url='gs://test-domain/test-archive.zip') +
    api.bisect_tester(tempfile='/tmp/dummy') +
    api.step_data(
        'Gathering reference values.saving json to temp file',
        stdout=api.raw_io.output('/tmp/dummy3')) +
    api.step_data(
        'Gathering reference values.saving json to temp file (2)',
        stdout=api.raw_io.output('/tmp/dummy4')) +
    api.override_step_data('device_status',
        api.json.output(working_device)) +
    api.override_step_data('device_status (2)',
        api.json.output(working_device)) +
    api.step_data('Resolving reference range.crrev get commit hash for ' +
        ('refs/heads/master@{#%s}' % local_bisect_config['bad_revision']),
        stdout=api.json.output(
            {'git_sha': bad_revision_hash}))+
    api.step_data('Resolving reference range.crrev get commit hash for ' +
        ('refs/heads/master@{#%s}' % local_bisect_config[
            'good_revision']),
          stdout=api.json.output(
              {'git_sha': good_revision_hash}))+
    api.step_data('Expanding revision range.for revisions %s:%s' % (
        good_revision_hash, bad_revision_hash),
        stdout=api.json.output([[bad_revision_hash, 'ignored'],
            [good_revision_hash, 'ignored']])) +
    api.step_data('Debug Info', retcode=1) +
    api.step_data('Post bisect results',
        stdout=api.json.output({'status_code': 200})) +
    api.override_step_data('device_status (3)',
        api.json.output(working_device)))

  # simulate the scenario when tests fail because of device disconnection.
  yield (api.test('local_basic_recipe_disconnected_device') +
    api.properties.tryserver(
        mastername='tryserver.chromium.perf', buildername=buildername) +
    api.properties(
        path_config='kitchen',
        bisect_config=local_bisect_config,
        job_name='f7a7b4135624439cbd27fdd5133d74ec',
        local_test=True,
        parent_got_revision='1111111',
        parent_build_archive_url='gs://test-domain/test-archive.zip') +
    api.bisect_tester(tempfile='/tmp/dummy') +
    api.step_data(
        'Gathering reference values.saving json to temp file',
        stdout=api.raw_io.output('/tmp/dummy3')) +
    api.step_data(
        'Gathering reference values.saving json to temp file (2)',
        stdout=api.raw_io.output('/tmp/dummy4')) +
    api.step_data(
        'Gathering reference values.saving json to temp file (3)',
        stdout=api.raw_io.output('/tmp/dummy5')) +
    api.step_data(
        'Gathering reference values.saving json to temp file (4)',
        stdout=api.raw_io.output('/tmp/dummy6')) +
    api.override_step_data('device_status',
        api.json.output(two_devices)) +
    api.override_step_data('device_status (2)',
        api.json.output(two_devices)) +
    api.step_data('Resolving reference range.crrev get commit hash for ' +
        ('refs/heads/master@{#%s}' % local_bisect_config['bad_revision']),
        stdout=api.json.output(
            {'git_sha': bad_revision_hash}))+
    api.step_data('Resolving reference range.crrev get commit hash for ' +
        ('refs/heads/master@{#%s}' % local_bisect_config[
            'good_revision']),
        stdout=api.json.output(
            {'git_sha': good_revision_hash}))+
    api.step_data('Expanding revision range.for revisions %s:%s' % (
            good_revision_hash, bad_revision_hash),
        stdout=api.json.output([[bad_revision_hash, 'ignored'], [
            good_revision_hash, 'ignored']])) +
    # Simulating disconnect by raising failure and changing the output of
    # multiple_device_status
    api.step_data('Debug Info', retcode=1) +
    api.override_step_data('device_status (3)',
        api.json.output(working_device)) +
    api.step_data('Expanding revision range.for revisions %s:%s (2)' % (
            good_revision_hash, bad_revision_hash),
        stdout=api.json.output([[bad_revision_hash, 'ignored'], [
            good_revision_hash, 'ignored']])) +
    api.step_data('Post bisect results',
        stdout=api.json.output({'status_code': 200})))
