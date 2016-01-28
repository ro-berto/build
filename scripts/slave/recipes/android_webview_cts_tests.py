# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Recipe for running WebView CTS using system WebView.
"""
DEPS = [
  'adb',
  'depot_tools/bot_update',
  'chromium',
  'chromium_android',
  'file',
  'depot_tools/gclient',
  'recipe_engine/json',
  'recipe_engine/raw_io',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'test_utils',
]

REPO_URL = 'https://chromium.googlesource.com/chromium/src.git'

# TODO(hush): Put the CTS zip file in the google storage
# and use gs_utils to download.
CTS_FILE_URL = "https://dl.google.com/dl/android/cts/android-cts-5.1_r1-linux_x86-arm.zip"
CTS_FILE_NAME = "android-cts-5.1_r1-linux_x86-arm.zip"
# WebView user agent is changed, and new CTS hasn't been published to reflect
# that.
EXPECTED_FAILURE = {
    'android.webkit.cts.WebSettingsTest': ['testUserAgentString_default'],
    #crbug.com/534643, crbug.com/514474, crbug.com/563493
    'android.webkit.cts.WebViewTest': ['testPageScroll', 'testStopLoading',
        'testJavascriptInterfaceForClientPopup', 'testRequestImageRef'],
    #crbug.com/514473
    'android.webkit.cts.WebViewSslTest':
        ['testSslErrorProceedResponseNotReusedForDifferentHost']
}

WEBVIEW_APK = 'SystemWebView.apk'

def FindTestReportXml(test_output):
  for line in test_output.split('\n'):
    split = line.split('Created xml report file at file://')
    if (len(split) > 1):
      return split[1]

  raise Exception(
      "Failed to parse the CTS output for the xml report file location")

def RunSteps(api):
  api.chromium_android.configure_from_properties('main_builder',
                                                 REPO_NAME='src',
                                                 REPO_URL=REPO_URL,
                                                 INTERNAL=False,
                                                 BUILD_CONFIG='Release')

  # Sync code.
  api.gclient.set_config('perf')
  api.gclient.apply_config('android')
  api.bot_update.ensure_checkout(force=True)
  api.chromium_android.clean_local_files()

  # Gyp the chromium checkout.
  api.chromium.runhooks()

  # Build the WebView apk
  api.chromium.compile(targets=['system_webview_apk'])

  api.chromium_android.spawn_logcat_monitor()
  api.chromium_android.device_status_check()
  api.chromium_android.provision_devices(
      min_battery_level=95, disable_network=True, disable_java_debug=True,
      reboot_timeout=180)

  api.adb.list_devices()
  # Install WebView
  api.chromium_android.adb_install_apk(WEBVIEW_APK)

  cts_dir = api.path['slave_build'].join('tmp', 'cts')
  cts_zip_path = cts_dir.join(CTS_FILE_NAME)

  # Step 1 Download cts to build bot dir to tmp/cts.
  api.step('Download Cts', ['curl', CTS_FILE_URL, '-o',
      cts_dir.join(CTS_FILE_NAME), '-z', cts_zip_path, '--create-dirs'])

  # Step 2 Extract cts zip file
  api.step('Extract Cts', ['unzip', '-o', CTS_FILE_NAME, '-d', './'],
      cwd=cts_dir)

  # Step 3 Run cts tests
  adb_path = api.path['slave_build'].join('src', 'third_party', 'android_tools',
      'sdk', 'platform-tools')
  env = {'PATH': api.path.pathsep.join([str(adb_path), '%(PATH)s'])}
  result = api.step('Run Cts', [cts_dir.join('android-cts', 'tools',
      'cts-tradefed'), 'run', 'cts', '-p', 'android.webkit'], env=env,
      stdout=api.raw_io.output())

  result.presentation.logs['stdout'] = result.stdout.splitlines()

  # This import is okay since we don't use any os-accessing functions.
  from xml.etree import ElementTree

  report_xml = api.file.read('Read test result and report failures',
      FindTestReportXml(result.stdout))
  root = ElementTree.fromstring(report_xml)

  not_executed_tests = []
  unexpected_test_failures = []
  test_classes = root.findall(
      './TestPackage/TestSuite[@name="android"]/TestSuite[@name="webkit"]/'
      'TestSuite[@name="cts"]/TestCase')

  for test_class in test_classes:
    class_name = 'android.webkit.cts.%s' % test_class.get('name')
    test_methods = test_class.findall('./Test')

    for test_method in test_methods:
      method_name = '%s#%s' % (class_name, test_method.get('name'))
      if test_method.get('result') == 'notExecuted':
        not_executed_tests.append(method_name)
      elif (test_method.find('./FailedScene') is not None and
          test_method.get('name') not in EXPECTED_FAILURE.get(class_name, [])):
        unexpected_test_failures.append(method_name)

  if unexpected_test_failures or not_executed_tests:
    api.step.active_result.presentation.status = api.step.FAILURE
    api.step.active_result.presentation.step_text += (
        api.test_utils.format_step_text(
            [['unexpected failures:', unexpected_test_failures],
             ['not executed:', not_executed_tests]]))

  api.chromium_android.logcat_dump()
  api.chromium_android.stack_tool_steps()
  api.chromium_android.test_report()

  if unexpected_test_failures:
    raise api.step.StepFailure("Unexpected Test Failures.")
  if not_executed_tests:
    raise api.step.StepFailure("Tests not executed.")

def GenTests(api):
  result_xml_with_unexecuted_tests = """<TestResult>
                          <TestPackage>
                            <TestSuite name='android'>
                              <TestSuite name='webkit'>
                                <TestSuite name='cts'>
                                  <TestCase name='WebSettingsTest'>
                                    <Test name='test' result='notExecuted'>
                                    </Test>
                                  </TestCase>
                                </TestSuite>
                              </TestSuite>
                            </TestSuite>
                          </TestPackage>
                        </TestResult>  """
  yield api.test('Test_parsing_report_xml_with_unexecuted_tests') + \
      api.override_step_data('Run Cts', api.raw_io.stream_output(
          'Created xml report file at file:///path/to/testResult.xml',
          stream='stdout')) + \
      api.override_step_data('Read test result and report failures',
          api.raw_io.output(result_xml_with_unexecuted_tests)) + \
      api.properties.generic(mastername='chromium.android')

  result_xml_with_expected_failure = """<TestResult>
                          <TestPackage>
                            <TestSuite name='android'>
                              <TestSuite name='webkit'>
                                <TestSuite name='cts'>
                                  <TestCase name='WebSettingsTest'>
                                    <Test name='testUserAgentString_default'>
                                      <FailedScene> </FailedScene>
                                    </Test>
                                  </TestCase>
                                </TestSuite>
                              </TestSuite>
                            </TestSuite>
                          </TestPackage>
                        </TestResult>  """

  yield api.test('Test_parsing_report_xml_with_expected_failure') + \
      api.override_step_data('Run Cts', api.raw_io.stream_output(
          'Created xml report file at file:///path/to/testResult.xml',
          stream='stdout')) + \
      api.override_step_data('Read test result and report failures',
          api.raw_io.output(result_xml_with_expected_failure)) + \
      api.properties.generic(mastername='chromium.android')

  result_xml_with_unexpected_failure_class= """<TestResult>
                          <TestPackage>
                            <TestSuite name='android'>
                              <TestSuite name='webkit'>
                                <TestSuite name='cts'>
                                  <TestCase name='unexpected failed classname'>
                                    <Test name='testUserAgentString_default'>
                                      <FailedScene> </FailedScene>
                                    </Test>
                                  </TestCase>
                                </TestSuite>
                              </TestSuite>
                            </TestSuite>
                          </TestPackage>
                        </TestResult>  """

  yield api.test('Test_parsing_report_xml_with_unexpected_class_failed') + \
      api.override_step_data('Run Cts', api.raw_io.stream_output(
          'Created xml report file at file:///path/to/testResult.xml',
          stream='stdout')) + \
      api.override_step_data('Read test result and report failures',
          api.raw_io.output(result_xml_with_unexpected_failure_class)) + \
      api.properties.generic(mastername='chromium.android')

  result_xml_with_unexpected_failure_method = """<TestResult>
                          <TestPackage>
                            <TestSuite name='android'>
                              <TestSuite name='webkit'>
                                <TestSuite name='cts'>
                                  <TestCase name='WebSettingsTest'>
                                    <Test name='unexpected failed methodname'>
                                      <FailedScene> </FailedScene>
                                    </Test>
                                  </TestCase>
                                </TestSuite>
                              </TestSuite>
                            </TestSuite>
                          </TestPackage>
                        </TestResult>  """

  yield api.test('Test_parsing_report_xml_with_unexpected_method_failed') + \
      api.override_step_data('Run Cts', api.raw_io.stream_output(
          'Created xml report file at file:///path/to/testResult.xml',
          stream='stdout')) + \
      api.override_step_data('Read test result and report failures',
          api.raw_io.output(result_xml_with_unexpected_failure_method)) + \
      api.properties.generic(mastername='chromium.android')

  yield api.test('Test_parsing_invalid_cts_output') + \
      api.override_step_data('Run Cts', api.raw_io.stream_output(
          'Invalid CTS output here...',
          stream='stdout')) + \
      api.properties.generic(mastername='chromium.android') + \
      api.expect_exception('Exception')
