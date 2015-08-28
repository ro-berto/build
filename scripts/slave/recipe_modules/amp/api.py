# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class AmpApi(recipe_api.RecipeApi):

  def __init__(self, *args, **kwargs):
    super(AmpApi, self).__init__(*args, **kwargs)
    self._trigger_file_dir = None
    self._base_results_dir = None

  def setup(self):
    """Sets up necessary configs."""
    self.m.chromium_android.configure_from_properties('base_config')

  def _get_trigger_dir(self):
    if not self._trigger_file_dir:
      self._trigger_file_dir = self.m.path.mkdtemp('amp_trigger')
    return self._trigger_file_dir

  def _get_trigger_file_for_suite(self, suite):
    return self._get_trigger_dir().join('%s.json' % suite)

  def _get_results_dir(self, suite):
    if not self._base_results_dir:
      self._base_results_dir = self.m.path.mkdtemp('amp_results')
    return self._base_results_dir.join(suite)

  def _get_results_zip_path(self, suite):
    return self._get_results_dir(suite).join('results.zip')

  def _get_results_unzipped_path(self, suite):
    return self._get_results_dir(suite).join('unzipped_results')

  def _get_results_logcat_path(self, suite):
    return self._get_results_unzipped_path(suite).join(
        'appurify_results', 'logcat.txt')

  def trigger_test_suite(
      self, suite, test_type, test_type_args, amp_args, verbose=True):
    args = ([test_type] + test_type_args + amp_args
        + ['--trigger', self.m.json.output()])
    if verbose:
      args += ['--verbose']
    if self.m.chromium.c.BUILD_CONFIG == 'Release':
      args += ['--release']

    step_test_data = lambda: self.m.json.test_api.output({
      'env': {
        'device': {
          'brand': 'Foo',
          'name': 'Fone',
          'os_version': '1.2.3',
        },
      },
    })
    step_result = self.m.chromium_android.test_runner(
        '[trigger] %s' % suite,
        args=args,
        step_test_data=step_test_data)
    trigger_data = step_result.json.output
    try:
      device_data = trigger_data['env']['device']
      step_result.presentation.step_text = 'on %s %s %s' % (
          device_data['brand'],
          device_data['name'],
          device_data['os_version'])
    except KeyError:
      step_result.presentation.status = self.m.step.WARNING
      step_result.presentation.step_text = 'unable to find device info'

    self.m.file.write(
        '[trigger] save %s data' % suite,
        self._get_trigger_file_for_suite(suite),
        self.m.json.dumps(trigger_data))

  def collect_test_suite(
      self, suite, test_type, test_type_args, amp_args, verbose=True,
      json_results_path=None, **kwargs):
    args = ([test_type] + test_type_args + amp_args
        + ['--collect', self._get_trigger_file_for_suite(suite)]
        + ['--results-path', self._get_results_zip_path(suite)])
    trigger_data = self.m.json.read(
        '[collect] load %s data' % suite,
        self._get_trigger_file_for_suite(suite),
        step_test_data=lambda: self.m.json.test_api.output({
          'env': {
            'device': {
              'brand': 'Foo',
              'name': 'Fone',
              'os_version': '1.2.3',
            }
          }
        })).json.output
    try:
      device_data = trigger_data['env']['device']
      device_info_text = 'on %s %s %s' % (
          device_data['brand'],
          device_data['name'],
          device_data['os_version'])
    except KeyError:
      device_data = None
      device_info_text = 'unable to find device info'

    if verbose:
      args += ['--verbose']
    if json_results_path:
      args += ['--json-results-path', json_results_path]
    if self.m.chromium.c.BUILD_CONFIG == 'Release':
      args += ['--release']
    try:
      step_result = self.m.chromium_android.test_runner(
          '[collect] %s' % suite,
          args=args, **kwargs)
    except self.m.step.StepFailure as f:
      step_result = f.result
      raise
    finally:
      step_result.presentation.step_text = device_info_text
      if (not device_data and
          step_result.presentation.status == self.m.step.SUCCESS):
        step_result.presentation.status = self.m.step.WARNING

    return step_result

  def upload_logcat_to_gs(self, bucket, suite):
    """Upload the logcat file returned from the appurify results to
    Google Storage.
    """
    step_result = self.m.json.read(
        '[upload logcat] load %s data' % suite,
        self._get_trigger_file_for_suite(suite),
        step_test_data=lambda: self.m.json.test_api.output({
          'test_run': {
            'test_run_id': '12345abcde',
          }
        }))
    trigger_data = step_result.json.output
    try:
      test_run_id = trigger_data['test_run']['test_run_id']
      self.m.zip.unzip(
          step_name='[upload logcat] unzip results for %s' % suite,
          zip_file=self._get_results_zip_path(suite),
          output=self._get_results_unzipped_path(suite))
      self.m.gsutil.upload(
          name='[upload logcat] %s' % suite,
          source=self._get_results_logcat_path(suite),
          bucket=bucket,
          dest='logcats/logcat_%s_%s.txt' % (suite, test_run_id),
          link_name='logcat')
    except KeyError:
      step_result.presentation.status = self.m.step.EXCEPTION
      step_result.presentation.step_text = 'unable to find test run id'

  def gtest_arguments(
      self, suite, isolate_file_path=None):
    """Generate command-line arguments for running gtests.

    Args:
      suite: The name of the test suite to run.
      isolate_file_path: The path to the .isolate file containing data
        dependency information for the test suite.

    Returns:
      A list of command-line arguments as strings.
    """
    gtest_args = ['-s', suite]
    if isolate_file_path:
      gtest_args += ['--isolate-file-path', isolate_file_path]
    return gtest_args

  def instrumentation_test_arguments(
      self, apk_under_test, test_apk, isolate_file_path=None,
      annotation=None):
    """Generate command-line arguments for running instrumentation tests.

    Args:
      apk_under_test: The path to the APK under test.
      test_apk: The path to the test APK.
      isolate_file_path: The path to the .isolate file containing data
        dependency information for the test suite.
      annotation: Comma-separated list of annotations. Will only run
        tests with any of the given annotations.

    Returns:
      A list of command-line arguments as strings.
    """
    instrumentation_test_args = [
        '--apk-under-test', apk_under_test,
        '--test-apk', test_apk,
    ]
    if isolate_file_path:
      instrumentation_test_args += ['--isolate-file-path', isolate_file_path]
    if annotation:
      instrumentation_test_args += ['--annotation', annotation]
    return instrumentation_test_args

  def uirobot_arguments(self, app_under_test=None, minutes=5):
    """Generate command-line arguments for running uirobot tests.

    Args:
      app_under_test: The app to run uirobot tests on.
      minutes: The number of minutes for which the uirobot tests should be
        run. Defaults to 5.

    Returns:
      A list of command-line arguments as strings.
    """
    uirobot_args = ['--minutes', minutes]
    if app_under_test:
      uirobot_args += ['--app-under-test', app_under_test]
    return uirobot_args

  def amp_arguments(
      self, device_type='Android', device_minimum_os=None, device_name=None,
      device_oem=None, device_os=None, device_timeout=None, api_address=None,
      api_port=None, api_protocol=None, network_config=None):
    """Generate command-line arguments for running tests on AMP.

    Args:
      device_name: A list of names of devices to use (e.g. 'Galaxy S4').
        Selects a device at random if unspecified.
      device_minimum_os: A string containing the minimum OS version to use.
        Should not be specified with |device_os|.
      device_oem: A list of names of device OEMs to use (e.g. 'Samsung').
        Selects an OEM at random is unspecified.
      device_os: A list of OS versions to use (e.g. '4.4.2'). Selects an OS
        version at random if unspecified. Should not be specified with
        |device_minimum_os|.
      device_timeout: An optional number of seconds to wait for a device
        meeting the given criteria to be available.
      api_address: The IP address of the AMP API endpoint.
      api_port: The port of the AMP API endpoint.
      api_protocol: The protocol to use to connect to the AMP API endpoint.
      network_config: Use to have AMP run tests in a simulated network
        environment. See the availible network environment options at
        https://appurify.atlassian.net/wiki/display/APD/
          Run+Configurations+-+Test+and+Network

    Returns:
      A list of command-line arguments as strings.
    """
    assert api_address, 'api_address not specified'
    assert api_port, 'api_port not specified'
    assert api_protocol, 'api_protocol not specified'
    assert not (device_minimum_os and device_os), (
        'cannot specify both device_minimum_os and device_os')

    amp_args = [
        '--enable-platform-mode',
        '-e', 'remote_device',
        '--api-key-file',
        self.m.path['build'].join('site_config', '.amp_api_key'),
        '--api-secret-file',
        self.m.path['build'].join('site_config', '.amp_api_secret'),
        '--api-address', api_address,
        '--api-port', api_port,
        '--api-protocol', api_protocol,
        '--device-type', device_type,
    ]
    if device_minimum_os:
      amp_args += ['--remote-device-minimum-os', device_minimum_os]

    for d in device_name or []:
      amp_args += ['--remote-device', d]

    for d in device_oem or []:
      amp_args += ['--device-oem', d]

    for d in device_os or []:
      amp_args += ['--remote-device-os', d]

    if device_timeout:
      amp_args += ['--remote-device-timeout', device_timeout]

    if network_config:
      amp_args += ['--network-config', network_config]

    return amp_args

