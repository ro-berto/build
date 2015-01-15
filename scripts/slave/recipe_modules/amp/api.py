# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api


class AmpApi(recipe_api.RecipeApi):

  def run_android_test_suite(self, step_name, test_type, test_type_args,
                             amp_args, verbose=True):
    """Runs an android test suite on AMP.

    Args:
      step_name: The user-visible name of the step.
      test_type: The type of test to run
        (e.g. 'gtest', 'instrumentation', etc.)
      test_type_args: A list of command-line arguments specific to the test
        type.
      amp_args: A list of command-line arguments specific to AMP.
    """
    args = [test_type] + test_type_args + amp_args
    if verbose:
      args += ['--verbose']
    self.m.python(
        step_name,
        self.m.path['checkout'].join('build', 'android', 'test_runner.py'),
        args=args)

  @recipe_api.non_step
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

  @recipe_api.non_step
  def uirobot_arguments(self, apk_under_test=None, minutes=5):
    """Generate command-line arguments for running uirobot tests.

    Args:
      apk_under_test: The APK to run uirobot tests on.
      minutes: The number of minutes for which the uirobot tests should be
        run. Defaults to 5.

    Returns:
      A list of command-line arguments as strings.
    """
    uirobot_args = ['--minutes', minutes]
    if apk_under_test:
      uirobot_args += ['--apk-under-test', apk_under_test]
    return uirobot_args

  @recipe_api.non_step
  def amp_arguments(
      self, device_name=None, device_os=None, trigger=None, collect=None,
      api_address=None, api_port=None, api_protocol=None):
    """Generate command-line arguments for running tests on AMP.

    Args:
      device_name: The name of the device to use (e.g. 'Galaxy S4').
        Selects a device at random if unspecified.
      device_os: The OS version to use (e.g. '4.4.2'). Selects an OS version
        at random if unspecified.
      trigger: If set, the file to test run information should be loaded.
        Indicates that the scripts should only start the tests.
      collect: If set, the file from which test run information should be
        loaded. Indicates that the scripts should only collect the test
        results.
      api_address: The IP address of the AMP API endpoint.
      api_port: The port of the AMP API endpoint.
      api_protocol: The protocol to use to connect to the AMP API endpoint.

    Returns:
      A list of command-line arguments as strings.
    """
    if not api_address:
      raise self.m.step.StepFailure('api_address not specified')
    if not api_port:
      raise self.m.step.StepFailure('api_port not specified')
    if not api_protocol:
      raise self.m.step.StepFailure('api_protocol not specified')

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
    ]
    if device_name:
      amp_args += ['--remote-device', device_name]
    if device_os:
      amp_args += ['--remote-device-os', device_os]
    if trigger:
      amp_args += ['--trigger', trigger]
    if collect:
      amp_args += ['--collect', collect]

    return amp_args

