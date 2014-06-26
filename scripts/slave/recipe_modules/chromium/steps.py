# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

class ArchiveBuildStep(object):
  def __init__(self, gs_bucket, gs_acl=None):
    self.gs_bucket = gs_bucket
    self.gs_acl = gs_acl

  def run(self, api):
    return api.chromium.archive_build(
        'archive build',
        self.gs_bucket,
        gs_acl=self.gs_acl,
    )

  @staticmethod
  def compile_targets(_):
    return []


class CheckpermsTest(object):
  @staticmethod
  def run(api):
    return api.chromium.checkperms()

  @staticmethod
  def compile_targets(_):
    return []


class Deps2GitTest(object):
  @staticmethod
  def run(api):
    return api.chromium.deps2git()

  @staticmethod
  def compile_targets(_):
    return []


class Deps2SubmodulesTest(object):
  @staticmethod
  def run(api):
    return api.chromium.deps2submodules()

  @staticmethod
  def compile_targets(_):
    return []


class GTestTest(object):
  def __init__(self, name, args=None, flakiness_dash=False):
    self.name = name
    self.args = args or []
    self.flakiness_dash = flakiness_dash

  def run(self, api):
    if api.chromium.c.TARGET_PLATFORM == 'android':
      return api.chromium_android.run_test_suite(self.name, self.args)

    return api.chromium.runtest(self.name,
                                test_type=self.name,
                                args=self.args,
                                annotate='gtest',
                                xvfb=True,
                                flakiness_dash=self.flakiness_dash)

  def compile_targets(self, api):
    if api.chromium.c.TARGET_PLATFORM == 'android':
      return [self.name + '_apk']

    # On iOS we rely on 'All' target being compiled instead of using
    # individual targets.
    if api.chromium.c.TARGET_PLATFORM == 'ios':
      return []

    return [self.name]


class DynamicGTestTests(object):
  def __init__(self, buildername, flakiness_dash=True):
    self.buildername = buildername
    self.flakiness_dash = flakiness_dash

  @staticmethod
  def _canonicalize_test(test):
    if isinstance(test, basestring):
      return {'test': test, 'shard_index': 0, 'total_shards': 1}
    return test

  def _get_test_spec(self, api):
    all_test_specs = api.step_history['read test spec'].json.output
    return all_test_specs.get(self.buildername, {})

  def _get_tests(self, api):
    return [self._canonicalize_test(t) for t in
            self._get_test_spec(api).get('gtest_tests', [])]

  def run(self, api):
    steps = []
    for test in self._get_tests(api):
      args = []
      if test['shard_index'] != 0 or test['total_shards'] != 1:
        args.extend(['--test-launcher-shard-index=%d' % test['shard_index'],
                     '--test-launcher-total-shards=%d' % test['total_shards']])
      steps.append(api.chromium.runtest(
          test['test'], test_type=test['test'], args=args, annotate='gtest',
          xvfb=True, flakiness_dash=self.flakiness_dash))

    return steps

  def compile_targets(self, api):
    explicit_targets = self._get_test_spec(api).get('compile_targets', [])
    test_targets = [t['test'] for t in self._get_tests(api)]
    # Remove duplicates.
    return sorted(set(explicit_targets + test_targets))


class TelemetryUnitTests(object):
  @staticmethod
  def run(api):
    return api.chromium.run_telemetry_unittests()

  @staticmethod
  def compile_targets(_):
    return ['chrome']

class TelemetryPerfUnitTests(object):
  @staticmethod
  def run(api):
    return api.chromium.run_telemetry_perf_unittests()

  @staticmethod
  def compile_targets(_):
    return ['chrome']


class NaclIntegrationTest(object):
  @staticmethod
  def run(api):
    args = [
      '--mode', api.chromium.c.BUILD_CONFIG,
    ]
    return api.python(
        'nacl_integration',
        api.path['checkout'].join('chrome',
                                  'test',
                                  'nacl_test_injection',
                                  'buildbot_nacl_integration.py'),
        args)

  @staticmethod
  def compile_targets(_):
    return ['chrome']


class AndroidInstrumentationTest(object):
  def __init__(self, name, compile_target, test_data=None,
               adb_install_apk=None):
    self.name = name
    self.compile_target = compile_target

    self.test_data = test_data
    self.adb_install_apk = adb_install_apk

  def run(self, api):
    assert api.chromium.c.TARGET_PLATFORM == 'android'
    if self.adb_install_apk:
      yield api.chromium_android.adb_install_apk(
          self.adb_install_apk[0], self.adb_install_apk[1])
    yield api.chromium_android.run_instrumentation_suite(
        self.name, test_data=self.test_data,
        flakiness_dashboard='test-results.appspot.com',
        verbose=True)

  def compile_targets(self, _):
    return [self.compile_target]

class MojoPythonTests(object):
  @staticmethod
  def run(api):
    args = ['--write-full-results-to',
            api.json.test_results(add_json_log=False)]

    def followup_fn(step_result):
      r = step_result.json.test_results
      p = step_result.presentation

      p.step_text += api.test_utils.format_step_text([
          ['unexpected_failures:', r.unexpected_failures.keys()],
      ])

    return api.python(
        'mojo_python_tests',
        api.path['checkout'].join('mojo', 'tools', 'run_mojo_python_tests.py'),
        args, followup_fn=followup_fn,
        step_test_data=lambda: api.json.test_api.canned_test_output(
            "{'tests': {}}"))

  @staticmethod
  def compile_targets(_):
    return []


IOS_TESTS = [
  GTestTest('base_unittests'),
  GTestTest('components_unittests'),
  GTestTest('crypto_unittests'),
  GTestTest('gfx_unittests'),
  GTestTest('url_unittests'),
  GTestTest('content_unittests'),
  GTestTest('net_unittests'),
  GTestTest('ui_unittests'),
  GTestTest('sync_unit_tests'),
  GTestTest('sql_unittests'),
]
