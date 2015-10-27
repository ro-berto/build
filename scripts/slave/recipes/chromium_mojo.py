# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from recipe_engine.types import freeze
from recipe_engine import recipe_api

DEPS = [
  'bot_update',
  'chromium',
  'chromium_android',
  'file',
  'gsutil',
  'raw_io',
  'path',
  'platform',
  'properties',
  'python',
  'step',
]


BUILDERS = freeze({
  'chromium.mojo': {
    'builders': {
      'Chromium Mojo Linux': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
        },
      },
      'Chromium Mojo Android': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
      },
      'Chromium Mojo Linux Perf': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
        },
        'run_perf_tests': True,
        'perf_test_info': {
          'browser_type': 'mandoline-release',
          'perf_id': 'mandoline-linux-release',
          'supported_testnames': [
            'blink_perf.dom',
            'blink_perf.events',
            'blink_perf.mutation',
            'blink_perf.shadow_dom',
            'page_cycler.typical_25',
            'startup.cold.blank_page',
            'startup.warm.blank_page',
          ],
        },
      },
      'Chromium Mojo Android Nexus5 Perf': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
        # TODO(yzshen): Actually run perf tests.
      },
      'Chromium Mojo Windows': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'win',
        },
      },
      'Chromium Mojo Windows 7 Perf': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'win',
        },
        'run_perf_tests': True,
        'perf_test_info': {
          'browser_type': 'mandoline-release',
          'perf_id': 'mandoline-win7-release',
          'supported_testnames': [
            'blink_perf.dom',
            'blink_perf.events',
            'blink_perf.mutation',
            'blink_perf.shadow_dom',
            'page_cycler.typical_25',
            'startup.cold.blank_page',
            'startup.warm.blank_page',
          ],
        },
      },
    },
  },
})


def _GetBotConfig(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername, {})
  return bot_config


@recipe_api.composite_step
def _UploadMandolineToGoogleStorage(api):
  # Get the release version, which is updated daily for Chrome canary.
  v = api.chromium.get_version()
  version = '%s.%s.%s.%s' % (v['MAJOR'], v['MINOR'], v['BUILD'], v['PATCH'])
  assert re.match('^\d+\.\d+\.\d+\.\d+$', version), 'Error: Bad version %r' % v
  api.step.active_result.presentation.step_text = 'Found version %s' % version

  # Check if the current version is already uploaded for the given platform.
  bucket = 'mandoline'
  url = 'gs://%s/%s' % (bucket, version)
  result = api.gsutil.ls(bucket, '', stdout=api.raw_io.output())
  result.presentation.logs['ls result stdout'] = [result.stdout or '']
  if result.stdout and url in result.stdout:
    result = api.gsutil.ls(bucket, version, stdout=api.raw_io.output())
    result.presentation.logs['ls result stdout'] = [result.stdout or '']
  url = '%s/%s' % (url, api.chromium.c.TARGET_PLATFORM)

  if result.stdout and url in result.stdout:
    api.step('skipping mandoline upload: release already exits', None)
    return

  # Read a limited FILES.cfg file-list format, uploading each applicable entry.
  files = api.path['checkout'].join('mandoline', 'tools', 'data', 'FILES.cfg')
  test_data = 'FILES=[{\'filepath\': \'foo\', \'platforms\': [\'linux\'],},]'
  files_data = api.file.read('read FILES.cfg', files, test_data=test_data)
  execution_globals = {}
  exec(files_data, execution_globals)
  gs_path = '%s/%s' % (version, api.chromium.c.TARGET_PLATFORM)
  for file_dictionary in execution_globals['FILES']:
    if api.chromium.c.TARGET_PLATFORM in file_dictionary['platforms']:
      file_path = file_dictionary['filepath']
      local_path = api.chromium.output_dir.join(file_path)
      remote_path = '%s/%s' % (gs_path, file_path)
      args = ['-r'] if file_dictionary.get('directory', False) else []
      api.gsutil.upload(local_path, bucket, remote_path, args=args)


@recipe_api.composite_step
def _RunApptests(api):
  runner = api.path['checkout'].join('mojo', 'tools', 'apptest_runner.py')
  api.python('app_tests', runner, [api.chromium.output_dir, '--verbose'])


def _RunUnitAndAppTests(api):
  with api.step.defer_results():
    api.chromium.runtest('html_viewer_unittests')
    api.chromium.runtest('ipc_mojo_unittests')
    api.chromium.runtest('mojo_common_unittests')
    api.chromium.runtest('mojo_public_application_unittests')
    api.chromium.runtest('mojo_public_bindings_unittests')
    api.chromium.runtest('mojo_public_environment_unittests')
    api.chromium.runtest('mojo_public_system_unittests')
    api.chromium.runtest('mojo_public_utility_unittests')
    api.chromium.runtest('mojo_runner_unittests')
    api.chromium.runtest('mojo_shell_unittests')
    api.chromium.runtest('mojo_surfaces_lib_unittests')
    api.chromium.runtest('mojo_system_unittests')
    api.chromium.runtest('mojo_view_manager_lib_unittests')
    api.chromium.runtest('resource_provider_unittests')
    api.chromium.runtest('window_manager_unittests')
    _RunApptests(api)


def _RunPerfTests(api, perf_test_info):
  tests = api.chromium.list_perf_tests(perf_test_info['browser_type'], 1)

  # TODO(yzshen): Remove this filter once we annotate tests disabled for
  # Mandoline in Telemetry. Consider reusing
  # chromium_tests.steps.DynamicPerfTests.
  tests = dict((k, v) for k, v in tests.json.output['steps'].iteritems()
      if str(k) in perf_test_info['supported_testnames'])

  with api.step.defer_results():
    for test_name, test in sorted(tests.iteritems()):
      test_name = str(test_name)
      annotate = api.chromium.get_annotate_by_test_name(test_name)
      cmd = test['cmd'].split()
      cmd.extend(
          ['--extra-browser-args=--override-use-gl-with-osmesa-for-tests'])

      api.chromium.runtest(
          cmd[1] if len(cmd) > 1 else cmd[0],
          args=cmd[2:],
          name=test_name,
          annotate=annotate,
          python_mode=True,
          results_url='https://chromeperf.appspot.com',
          perf_dashboard_id=test.get('perf_dashboard_id', test_name),
          perf_id=perf_test_info['perf_id'],
          test_type=test.get('perf_dashboard_id', test_name),
          xvfb=True,
          chartjson_file=True)


def RunSteps(api):
  # TODO(yzshen): Perf bots should retrieve build results from builders of the
  # same architecture.
  api.chromium.configure_bot(BUILDERS, ['gn'])

  api.bot_update.ensure_checkout(force=True)

  api.chromium.runhooks()

  api.chromium.run_mb(api.properties.get('mastername'),
                      api.properties.get('buildername'),
                      use_goma=True)

  api.chromium.compile(targets=['mandoline:all'])

  if api.chromium.c.TARGET_PLATFORM == 'android':
    api.chromium_android.detect_and_setup_devices()

  bot_config = _GetBotConfig(api)
  if bot_config.get('run_perf_tests', False):
    _RunPerfTests(api, bot_config['perf_test_info'])
  else:
    _RunUnitAndAppTests(api)
    # TODO(msw): Fix 'get version' failures on Windows: http://crbug.com/548026
    if api.chromium.c.TARGET_PLATFORM != 'win':
      _UploadMandolineToGoogleStorage(api)


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test

  # Ensure upload is skipped if version/platform binaries are already uploaded.
  test = api.test('test_upload_skipped_for_existing_binaries')
  test += api.platform.name('linux')
  test += api.properties.generic(buildername='Chromium Mojo Android',
                                 mastername='chromium.mojo')
  # This relies on api.chromium.get_version's hard-coded step_test_data version.
  test_ls = api.raw_io.output('gs://mandoline/37.0.2021.0/android/')
  test += api.step_data('gsutil ls gs://mandoline/', stdout=test_ls)
  test += api.step_data('gsutil ls gs://mandoline/37.0.2021.0', stdout=test_ls)
  yield test
