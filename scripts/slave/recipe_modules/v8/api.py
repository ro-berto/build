# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import datetime
import math
import re

from infra.libs.infra_types import freeze
from slave import recipe_api
from slave.recipe_modules.v8 import builders


# Regular expressions for v8 branch names.
RELEASE_BRANCH_RE = re.compile(r'^\d+\.\d+$')
ROLL_BRANCH_RE = re.compile(r'^\d+\.\d+\.\d+$')

# With more than 23 letters, labels are to big for buildbot's popup boxes.
MAX_LABEL_SIZE = 23

# Make sure that a step is not flooded with log lines.
MAX_FAILURE_LOGS = 10

MIPS_TOOLCHAIN = 'mips-2013.11-36-mips-linux-gnu-i686-pc-linux-gnu.tar.bz2'
MIPS_DIR = 'mips-2013.11'

TEST_CONFIGS = freeze({
  'benchmarks': {
    'name': 'Benchmarks',
    'tests': 'benchmarks',
  },
  'mjsunit': {
    'name': 'Mjsunit',
    'tests': 'mjsunit',
    'add_flaky_step': True,
  },
  'mozilla': {
    'name': 'Mozilla',
    'tests': 'mozilla',
    'gclient_apply_config': ['mozilla_tests'],
  },
  'optimize_for_size': {
    'name': 'OptimizeForSize',
    'tests': 'optimize_for_size',
    'add_flaky_step': True,
    'test_args': ['--no-variants', '--shell_flags="--optimize-for-size"'],
  },
  'test262': {
    'name': 'Test262 - no variants',
    'tests': 'test262',
    'test_args': ['--no-variants'],
  },
  'test262_variants': {
    'name': 'Test262',
    'tests': 'test262',
  },
  'test262_es6': {
    'name': 'Test262-es6 - no variants',
    'tests': 'test262-es6',
    'test_args': ['--no-variants'],
  },
  'test262_es6_variants': {
    'name': 'Test262-es6',
    'tests': 'test262-es6',
  },
  'unittests': {
    'name': 'Unittests',
    'tests': ('unittests'),
    'test_args': ['--no-variants'],
  },
  'v8testing': {
    'name': 'Check',
    'tests': ('default'),
    'add_flaky_step': True,
  },
  'webkit': {
    'name': 'Webkit',
    'tests': 'webkit',
    'add_flaky_step': True,
  },
})


# TODO(machenbach): Clean up api indirection. "Run" needs the v8 api while
# "gclient_apply_config" needs the general injection module.
class V8Test(object):
  def __init__(self, name):
    self.name = name

  def run(self, api, **kwargs):
    return api.runtest(TEST_CONFIGS[self.name], **kwargs)

  def gclient_apply_config(self, api):
    for c in TEST_CONFIGS[self.name].get('gclient_apply_config', []):
      api.gclient.apply_config(c)


class V8Presubmit(object):
  @staticmethod
  def run(api, **kwargs):
    return api.presubmit()

  @staticmethod
  def gclient_apply_config(_):
    pass


class V8CheckInitializers(object):
  @staticmethod
  def run(api, **kwargs):
    return api.check_initializers()

  @staticmethod
  def gclient_apply_config(_):
    pass


class V8Fuzzer(object):
  @staticmethod
  def run(api, **kwargs):
    return api.fuzz()

  @staticmethod
  def gclient_apply_config(_):
    pass


class V8DeoptFuzzer(object):
  @staticmethod
  def run(api, **kwargs):
    return api.deopt_fuzz()

  @staticmethod
  def gclient_apply_config(_):
    pass


class V8GCMole(object):
  @staticmethod
  def run(api, **kwargs):
    return api.gc_mole('ia32', 'x64', 'arm', 'arm64')

  @staticmethod
  def gclient_apply_config(_):
    pass


class V8SimpleLeakCheck(object):
  @staticmethod
  def run(api, **kwargs):
    return api.simple_leak_check()

  @staticmethod
  def gclient_apply_config(_):
    pass


V8_NON_STANDARD_TESTS = freeze({
  'deopt': V8DeoptFuzzer,
  'fuzz': V8Fuzzer,
  'gcmole': V8GCMole,
  'presubmit': V8Presubmit,
  'simpleleak': V8SimpleLeakCheck,
  'v8initializers': V8CheckInitializers,
})


class V8Api(recipe_api.RecipeApi):
  BUILDERS = builders.BUILDERS

  # Map of GS archive names to urls.
  GS_ARCHIVES = {
    'android_arm_rel_archive': 'gs://chromium-v8/v8-android-arm-rel',
    'android_arm64_rel_archive': 'gs://chromium-v8/v8-android-arm64-rel',
    'arm_rel_archive': 'gs://chromium-v8/v8-arm-rel',
    'arm_dbg_archive': 'gs://chromium-v8/v8-arm-dbg',
    'linux_rel_archive': 'gs://chromium-v8/v8-linux-rel',
    'linux_dbg_archive': 'gs://chromium-v8/v8-linux-dbg',
    'linux_nosnap_rel_archive': 'gs://chromium-v8/v8-linux-nosnap-rel',
    'linux_nosnap_dbg_archive': 'gs://chromium-v8/v8-linux-nosnap-dbg',
    'linux_x87_nosnap_dbg_archive': 'gs://chromium-v8/v8-linux-x87-nosnap-dbg',
    'linux64_rel_archive': 'gs://chromium-v8/v8-linux64-rel',
    'linux64_dbg_archive': 'gs://chromium-v8/v8-linux64-dbg',
    'mips_rel_archive': 'gs://chromium-v8/v8-mips-rel',
    'mipsel_sim_rel_archive': 'gs://chromium-v8/v8-mipsel-sim-rel',
    'mips64el_sim_rel_archive': 'gs://chromium-v8/v8-mips64el-sim-rel',
    'win32_rel_archive': 'gs://chromium-v8/v8-win32-rel',
    'win32_dbg_archive': 'gs://chromium-v8/v8-win32-dbg',
    'v8_for_dart_archive': 'gs://chromium-v8/v8-for-dart-rel',
  }

  def apply_bot_config(self, builders):
    """Entry method for using the v8 api.

    Requires the presence of a bot_config dict for any master/builder pair.
    This bot_config will be used to refine other api methods.
    """

    mastername = self.m.properties.get('mastername')
    buildername = self.m.properties.get('buildername')
    master_dict = builders.get(mastername, {})
    self.bot_config = master_dict.get('builders', {}).get(buildername)
    assert self.bot_config, (
        'Unrecognized builder name %r for master %r.' % (
            buildername, mastername))

    self.set_config('v8',
                    optional=True,
                    **self.bot_config.get('v8_config_kwargs', {}))
    if self.m.tryserver.is_tryserver:
      self.init_tryserver()
    for c in self.bot_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)
    for c in self.bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)
    for c in self.bot_config.get('v8_apply_config', []):
      self.apply_config(c)
    if self.c.nacl.update_nacl_sdk:
      self.c.nacl.NACL_SDK_ROOT = str(self.m.path['slave_build'].join(
          'nacl_sdk', 'pepper_current'))
    # Test-specific configurations.
    for t in self.bot_config.get('tests', []):
      self.create_test(t).gclient_apply_config(self.m)
    # Initialize perf_dashboard api if any perf test should run.
    self.m.perf_dashboard.set_default_config()

  def set_bot_config(self, bot_config):
    """Set bot configuration for testing only."""
    self.bot_config = bot_config

  def init_tryserver(self):
    self.m.chromium.apply_config('trybot_flavor')
    self.apply_config('trybot_flavor')

  def checkout(self, revert=False):
    # Set revision for bot_update.
    revision = self.m.properties.get(
        'parent_got_revision', self.m.properties.get('revision', 'HEAD'))
    solution = self.m.gclient.c.solutions[0]
    branch = self.m.properties.get('branch', 'master')
    needs_branch_heads = False
    if RELEASE_BRANCH_RE.match(branch):
      revision = 'refs/branch-heads/%s:%s' % (branch, revision)
      needs_branch_heads = True
    elif ROLL_BRANCH_RE.match(branch):
      revision = 'refs/heads/%s:%s' % (branch, revision)

    solution.revision = revision
    update_step = self.m.bot_update.ensure_checkout(
        no_shallow=True,
        patch_root=[None, 'v8'][bool(self.m.tryserver.is_tryserver)],
        output_manifest=True,
        with_branch_heads=needs_branch_heads,
        patch_project_roots={'v8': []})

    assert update_step.json.output['did_run']

    # Whatever step is run right before this line needs to emit got_revision.
    self.revision = update_step.presentation.properties['got_revision']
    self.revision_cp = update_step.presentation.properties['got_revision_cp']
    self.revision_number = str(self.m.commit_position.parse_revision(
        self.revision_cp))

  def runhooks(self, **kwargs):
    env = {}
    if self.c.gyp_env.AR:
      env['AR'] = self.c.gyp_env.AR
    if self.c.gyp_env.CC:
      env['CC'] = self.c.gyp_env.CC
    if self.c.gyp_env.CXX:
      env['CXX'] = self.c.gyp_env.CXX
    if self.c.gyp_env.LINK:
      env['LINK'] = self.c.gyp_env.LINK
    if self.c.gyp_env.RANLIB:
      env['RANLIB'] = self.c.gyp_env.RANLIB
    # TODO(machenbach): Make this the default on windows.
    if self.m.chromium.c.gyp_env.GYP_MSVS_VERSION:
      env['GYP_MSVS_VERSION'] = self.m.chromium.c.gyp_env.GYP_MSVS_VERSION
    self.m.chromium.runhooks(env=env, **kwargs)

  def setup_mips_toolchain(self):
    mips_dir = self.m.path['slave_build'].join(MIPS_DIR, 'bin')
    if not self.m.path.exists(mips_dir):
      self.m.gsutil.download_url(
          'gs://chromium-v8/%s' % MIPS_TOOLCHAIN,
          self.m.path['slave_build'],
          name='bootstrapping mips toolchain')
      self.m.step('unzipping',
               ['tar', 'xf', MIPS_TOOLCHAIN],
               cwd=self.m.path['slave_build'])

    self.c.gyp_env.CC = self.m.path.join(mips_dir, 'mips-linux-gnu-gcc')
    self.c.gyp_env.CXX = self.m.path.join(mips_dir, 'mips-linux-gnu-g++')
    self.c.gyp_env.AR = self.m.path.join(mips_dir, 'mips-linux-gnu-ar')
    self.c.gyp_env.RANLIB = self.m.path.join(mips_dir, 'mips-linux-gnu-ranlib')
    self.c.gyp_env.LINK = self.m.path.join(mips_dir, 'mips-linux-gnu-g++')

  def update_nacl_sdk(self):
    return self.m.python(
      'update NaCl SDK',
      self.m.path['build'].join('scripts', 'slave', 'update_nacl_sdk.py'),
      ['--pepper-channel', self.c.nacl.update_nacl_sdk],
      cwd=self.m.path['slave_build'],
    )

  @property
  def bot_type(self):
    return self.bot_config.get('bot_type', 'builder_tester')

  @property
  def should_build(self):
    return self.bot_type in ['builder', 'builder_tester']

  @property
  def should_test(self):
    return self.bot_type in ['tester', 'builder_tester']

  @property
  def should_upload_build(self):
    return self.bot_type == 'builder'

  @property
  def should_download_build(self):
    return self.bot_type == 'tester'

  @property
  def perf_tests(self):
    return self.bot_config.get('perf', [])

  def compile(self, **kwargs):
    env={}
    if self.m.chromium.c.TARGET_PLATFORM == 'android':
      env['ANDROID_NDK_ROOT'] = str(self.m.path['checkout'].join(
          'third_party', 'android_tools', 'ndk'))
    if self.c.nacl.NACL_SDK_ROOT:
      env['NACL_SDK_ROOT'] = self.c.nacl.NACL_SDK_ROOT
    args = []
    if self.c.compile_py.compile_extra_args:
      args.extend(self.c.compile_py.compile_extra_args)
    self.m.chromium.compile(args, env=env, **kwargs)

  # TODO(machenbach): This should move to a dynamorio module as soon as one
  # exists.
  def dr_compile(self):
    self.m.path.makedirs(
      'Create Build Dir',
      self.m.path['slave_build'].join('dynamorio', 'build'))
    self.m.step(
      'Configure Release x64 DynamoRIO',
      ['cmake', '..', '-DDEBUG=OFF'],
      cwd=self.m.path['slave_build'].join('dynamorio', 'build'),
    )
    self.m.step(
      'Compile Release x64 DynamoRIO',
      ['make', '-j5'],
      cwd=self.m.path['slave_build'].join('dynamorio', 'build'),
    )

  @property
  def run_dynamorio(self):
    return self.m.gclient.c.solutions[-1].name == 'dynamorio'

  def upload_build(self):
    self.m.archive.zip_and_upload_build(
          'package build',
          self.m.chromium.c.build_config_fs,
          self.GS_ARCHIVES[self.bot_config['build_gs_archive']],
          src_dir='v8')

  def download_build(self):
    self.m.path.rmtree(
          'build directory',
          self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs))

    self.m.archive.download_and_unzip_build(
          'extract build',
          self.m.chromium.c.build_config_fs,
          self.GS_ARCHIVES[self.bot_config['build_gs_archive']],
          src_dir='v8')


  # TODO(machenbach): Pass api already in constructor to avoid redundant api
  # parameter passing later.
  @recipe_api.non_step
  def create_test(self, test):
    """Wrapper that allows to shortcut common tests with their names.
    Returns a runnable test instance.
    """
    if test in V8_NON_STANDARD_TESTS:
      return V8_NON_STANDARD_TESTS[test]()
    else:
      return V8Test(test)

  #TODO(martiniss) convert loop
  def runtests(self):
    with self.m.step.defer_results():
      for t in self.bot_config.get('tests', []):
        self.create_test(t).run(self)

  def presubmit(self):
    self.m.python(
      'Presubmit',
      self.m.path['checkout'].join('tools', 'presubmit.py'),
      cwd=self.m.path['checkout'],
    )

  def check_initializers(self):
    self.m.step(
      'Static-Initializers',
      ['bash',
       self.m.path['checkout'].join('tools', 'check-static-initializers.sh'),
       self.m.path.join(self.m.path.basename(self.m.chromium.c.build_dir),
                        self.m.chromium.c.build_config_fs,
                        'd8')],
      cwd=self.m.path['checkout'],
    )

  def fuzz(self):
    assert self.m.chromium.c.HOST_PLATFORM == 'linux'
    self.m.step(
      'Fuzz',
      ['bash',
       self.m.path['checkout'].join('tools', 'fuzz-harness.sh'),
       self.m.path.join(self.m.path.basename(self.m.chromium.c.build_dir),
                        self.m.chromium.c.build_config_fs,
                        'd8')],
      cwd=self.m.path['checkout'],
    )

  def gc_mole(self, *archs):
    # TODO(machenbach): Make gcmole work with absolute paths. Currently, a
    # particular clang version is installed on one slave in '/b'.
    env = {
      'CLANG_BIN': (
        self.m.path.join('..', '..', '..', '..', '..', 'gcmole', 'bin')
      ),
      'CLANG_PLUGINS': (
        self.m.path.join('..', '..', '..', '..', '..', 'gcmole')
      ),
    }
    for arch in archs:
      self.m.step(
        'GCMole %s' % arch,
        ['lua', self.m.path.join('tools', 'gcmole', 'gcmole.lua'), arch],
        cwd=self.m.path['checkout'],
        env=env,
      )

  def simple_leak_check(self):
    # TODO(machenbach): Add task kill step for windows.
    relative_d8_path = self.m.path.join(
        self.m.path.basename(self.m.chromium.c.build_dir),
        self.m.chromium.c.build_config_fs,
        'd8')
    step_result = self.m.step(
      'Simple Leak Check',
      ['valgrind', '--leak-check=full', '--show-reachable=yes',
       '--num-callers=20', relative_d8_path, '-e', '"print(1+2)"'],
      cwd=self.m.path['checkout'],
      stderr=self.m.raw_io.output(),
      step_test_data=lambda: self.m.raw_io.test_api.stream_output(
          'tons of leaks', stream='stderr')
    )
    step_result.presentation.logs['stderr'] = step_result.stderr.splitlines()
    if not 'no leaks are possible' in (step_result.stderr):
      step_result.presentation.status = self.m.step.FAILURE
      raise self.m.step.StepFailure('Failed leak check')

  def deopt_fuzz(self):
    full_args = [
      '--mode', self.m.chromium.c.build_config_fs,
      '--arch', self.m.chromium.c.gyp_env.GYP_DEFINES['v8_target_arch'],
      '--progress', 'verbose',
      '--buildbot',
    ]

    # Add builder-specific test arguments.
    full_args += self.c.testing.test_args

    self.m.python(
      'Deopt Fuzz',
      self.m.path['checkout'].join('tools', 'run-deopt-fuzzer.py'),
      full_args,
      cwd=self.m.path['checkout'],
    )

  @staticmethod
  def format_duration(duration_in_seconds):
    duration = datetime.timedelta(seconds=duration_in_seconds)
    time = (datetime.datetime.min + duration).time()
    return time.strftime('%M:%S:') + '%03i' % int(time.microsecond / 1000)

  def _command_results_text(self, results, flaky):
    """Returns log lines for all results of a unique command."""
    assert results
    lines = []

    # Add common description for multiple runs.
    flaky_suffix = ' (flaky in a repeated run)' if flaky else ''
    lines.append('Test: %s%s' % (results[0]['name'], flaky_suffix))
    lines.append('Flags: %s' % ' '.join(results[0]['flags']))
    lines.append('Command: %s' % results[0]['command'])
    lines.append('')

    # Add results for each run of a command.
    for result in sorted(results, key=lambda r: int(r['run'])):
      lines.append('Run #%d' % int(result['run']))
      lines.append('Exit code: %s' % result['exit_code'])
      lines.append('Result: %s' % result['result'])
      if result.get('expected'):
        lines.append('Expected outcomes: %s' % ", ".join(result['expected']))
      lines.append('Duration: %s' % V8Api.format_duration(result['duration']))
      lines.append('')
      if result['stdout']:
        lines.append('Stdout:')
        lines.extend(result['stdout'].splitlines())
        lines.append('')
      if result['stderr']:
        lines.append('Stderr:')
        lines.extend(result['stderr'].splitlines())
        lines.append('')
    return lines

  def _duration_results_text(self, test):
    return [
      'Test: %s' % test['name'],
      'Flags: %s' % ' '.join(test['flags']),
      'Command: %s' % test['command'],
      'Duration: %s' % V8Api.format_duration(test['duration']),
    ]

  def _update_test_presentation(self, output, presentation):
    def all_same(items):
      return all(x == items[0] for x in items)

    # Slowest tests duration summary.
    lines = []
    for test in output['slowest_tests']:
      lines.append(
          '%s %s' %(V8Api.format_duration(test['duration']), test['name']))
    # Slowest tests duration details.
    lines.extend(['', 'Details:', ''])
    for test in output['slowest_tests']:
      lines.extend(self._duration_results_text(test))
    presentation.logs['durations'] = lines

    if not output['results']:
      return

    unique_results = {}
    for result in output['results']:
      # Use test base name as UI label (without suite and directory names).
      label = result['name'].split('/')[-1]
      # Truncate the label if it is still too long.
      if len(label) > MAX_LABEL_SIZE:
        label = label[:MAX_LABEL_SIZE - 2] + '..'
      # Group tests with the same label (usually the same test that ran under
      # different configurations).
      unique_results.setdefault(label, []).append(result)

    failure_count = 0
    flake_count = 0
    for label in sorted(unique_results.keys()[:MAX_FAILURE_LOGS]):
      lines = []

      # Group results by command. The same command might have run multiple
      # times to detect flakes.
      results_per_command = {}
      for result in unique_results[label]:
        results_per_command.setdefault(result['command'], []).append(result)

      for command in results_per_command:
        # Determine flakiness. A test is flaky if not all results from a unique
        # command are the same (e.g. all 'FAIL').
        flaky = not all_same(map(lambda x: x['result'],
                                 results_per_command[command]))

        # Count flakes and failures for summary. The v8 test driver reports
        # failures and reruns of failures.
        flake_count += int(flaky)
        failure_count += int(not flaky)

        lines += self._command_results_text(results_per_command[command],
                                            flaky)
      presentation.logs[label] = lines

    # Summary about flakes and failures.
    presentation.step_text += ('failures: %d<br/>flakes: %d<br/>' %
                               (failure_count, flake_count))

  def _runtest(self, name, test, flaky_tests=None, **kwargs):
    env = {}
    target = self.m.chromium.c.build_config_fs
    if self.c.nacl.update_nacl_sdk:
      # TODO(machenbach): NaCl circumvents the buildbot naming conventions and
      # uses v8 flavor. Make this more uniform.
      target = target.lower()
    full_args = [
      '--target', target,
      '--arch', self.m.chromium.c.gyp_env.GYP_DEFINES['v8_target_arch'],
      '--testname', test['tests'],
    ]

    # Add test-specific test arguments.
    full_args += test.get('test_args', [])

    # Add builder-specific test arguments.
    full_args += self.c.testing.test_args

    if self.run_dynamorio:
      drrun = self.m.path['slave_build'].join(
          'dynamorio', 'build', 'bin64', 'drrun')
      full_args += [
        '--command_prefix',
        '%s -reset_every_nth_pending 0 --' % drrun,
      ]

    if self.c.testing.SHARD_COUNT > 1:
      full_args += [
        '--shard_count=%d' % self.c.testing.SHARD_COUNT,
        '--shard_run=%d' % self.c.testing.SHARD_RUN,
      ]

    if flaky_tests:
      full_args += ['--flaky-tests', flaky_tests]

    llvm_symbolizer_path = self.m.path['checkout'].join(
        'third_party', 'llvm-build', 'Release+Asserts', 'bin',
        'llvm-symbolizer')

    # Indicate whether DCHECKs were enabled.
    if self.m.chromium.c.gyp_env.GYP_DEFINES.get('dcheck_always_on') == 1:
      full_args.append('--dcheck-always-on')

    # Arguments and environment for asan builds:
    if self.m.chromium.c.gyp_env.GYP_DEFINES.get('asan') == 1:
      full_args.append('--asan')
      env['ASAN_OPTIONS'] = " ".join([
        'external_symbolizer_path=%s' % llvm_symbolizer_path,
      ])

    # Arguments and environment for tsan builds:
    if self.m.chromium.c.gyp_env.GYP_DEFINES.get('tsan') == 1:
      full_args.append('--tsan')
      env['TSAN_OPTIONS'] = " ".join([
        'external_symbolizer_path=%s' % llvm_symbolizer_path,
        'exit_code=0',
        'report_thread_leaks=0',
        'history_size=7',
        'report_destroy_locked=0',
      ])

    # Arguments and environment for msan builds:
    if self.m.chromium.c.gyp_env.GYP_DEFINES.get('msan') == 1:
      full_args.append('--msan')
      env['MSAN_OPTIONS'] = " ".join([
        'external_symbolizer_path=%s' % llvm_symbolizer_path,
      ])

    # Environment for nacl builds:
    if self.c.nacl.NACL_SDK_ROOT:
      env['NACL_SDK_ROOT'] = self.c.nacl.NACL_SDK_ROOT

    full_args += ['--json-test-results',
                  self.m.json.output(add_json_log=False)]
    def step_test_data():
      return self.test_api.output_json(
          self._test_data.get('test_failures', False),
          self._test_data.get('wrong_results', False))

    try:
      self.m.python(
        name,
        self.resource('v8testing.py'),
        full_args,
        cwd=self.m.path['checkout'],
        env=env,
        step_test_data=step_test_data,
        **kwargs
      )
    finally:
      # Show test results independent of the step result.
      step_result = self.m.step.active_result
      r = step_result.json.output
      # The output is expected to be a list of architecture dicts that
      # each contain a results list. On buildbot, there is only one
      # architecture.
      if (r and isinstance(r, list) and isinstance(r[0], dict)):
        self._update_test_presentation(r[0], step_result.presentation)

      # Check integrity of the last output. The json list is expected to
      # contain only one element for one (architecture, build config type)
      # pair on the buildbot.
      result = step_result.json.output
      if result and len(result) > 1:
        self.m.python.inline(
            name,
            r"""
            import sys
            print 'Unexpected results set present.'
            sys.exit(1)
            """)

  def runtest(self, test, **kwargs):
    # Get the flaky-step configuration default per test.
    add_flaky_step = test.get('add_flaky_step', False)

    # Overwrite the flaky-step configuration on a per builder basis as some
    # types of builders (e.g. branch, try) don't have any flaky steps.
    if self.c.testing.add_flaky_step is not None:
      add_flaky_step = self.c.testing.add_flaky_step
    if add_flaky_step:
      try:
        self._runtest(test['name'], test, flaky_tests='skip', **kwargs)
      finally:
        self._runtest(test['name'] + ' - flaky', test, flaky_tests='run',
                      **kwargs)
    else:
      self._runtest(test['name'], test, **kwargs)

  @staticmethod
  def mean(values):
    return float(sum(values)) / len(values)

  @staticmethod
  def variance(values, average):
    return map(lambda x: (x - average) ** 2, values)

  @staticmethod
  def standard_deviation(values, average):
    return math.sqrt(V8Api.mean(V8Api.variance(values, average)))

  def perf_upload(self, results, category):
    """Upload performance results to the performance dashboard.

    Args:
      results: A list of result maps. Each result map has an errors and a
               traces item.
      category: Name of the perf category (e.g. ia32 or N5). The bot field
                of the performance dashboard is used to hold this category.
    """
    # Make sure that bots that run perf tests have a revision property.
    if results:
      assert self.revision_number and self.revision, (
          'Revision must be specified for perf tests as '
          'they upload data to the perf dashboard.')

    points = []
    for result in results:
      for trace in result['traces']:
        # Make 'v8' the root of all standalone v8 performance tests.
        test_path = '/'.join(['v8'] + trace['graphs'])

        # Ignore empty traces.
        # TODO(machenbach): Show some kind of failure on the waterfall on empty
        # traces without skipping to upload.
        if not trace['results']:
          continue

        values = map(float, trace['results'])
        average = V8Api.mean(values)

        p = self.m.perf_dashboard.get_skeleton_point(
            test_path, self.revision_number, str(average))
        p['units'] = trace['units']
        p['bot'] = category or p['bot']
        p['supplemental_columns'] = {'a_default_rev': 'r_v8_git',
                                     'r_v8_git': self.revision}

        # A trace might provide a value for standard deviation if the test
        # driver already calculated it, otherwise calculate it here.
        p['error'] = (trace.get('stddev') or
                      str(V8Api.standard_deviation(values, average)))

        points.append(p)

    # Send all perf data to the perf dashboard in one step.
    if points:
      self.m.perf_dashboard.post(points)


  def runperf(self, tests, perf_configs, category=None, suffix='',
              upload=True):
    """Run v8 performance tests and upload results.

    Args:
      tests: A list of tests from perf_configs to run.
      perf_configs: A mapping from test name to a suite configuration json.
      category: Optionally use bot nesting level as category. Bot names are
                irrelevant if several different bots run in the same category
                like ia32.
      suffix: Optional name suffix to differentiate multiple runs of the same
              step.
      upload: If true, uploads results to the performance dashboard.
    Returns: A mapping of test config name->results map. Each results map has
             an errors and a traces item.
    """

    results_mapping = collections.defaultdict(dict)
    def run_single_perf_test(test, name, json_file):
      """Call the v8 perf test runner.

      Performance results are saved in the json test results file as a dict with
      'errors' for accumulated errors and 'traces' for the measurements.
      """
      full_args = [
        '--arch', self.m.chromium.c.gyp_env.GYP_DEFINES['v8_target_arch'],
        '--buildbot',
        '--json-test-results', self.m.json.output(add_json_log=False),
        json_file,
      ]

      step_test_data = lambda: self.test_api.perf_json(
          self._test_data.get('perf_failures', False))

      try:
        self.m.python(
          '%s%s' % (name, suffix),
          self.m.path['checkout'].join('tools', 'run_perf.py'),
          full_args,
          cwd=self.m.path['checkout'],
          step_test_data=step_test_data,
        )
      finally:
        step_result = self.m.step.active_result
        results_mapping[test] = step_result.json.output
        errors = step_result.json.output['errors']
        if errors:
          step_result.presentation.logs['Errors'] = errors
        elif upload:
          # Add a link to the dashboard. This assumes the naming convention
          # step name == suite name. If this convention didn't hold, we'd need
          # to use the path from the json output graphs here.
          self.m.perf_dashboard.add_dashboard_link(
              step_result.presentation,
              'v8/%s' % name,
              self.revision_number,
              bot=category)

    failed = False
    for t in tests:
      assert perf_configs[t]
      assert perf_configs[t]['name']
      assert perf_configs[t]['json']
      try:
        run_single_perf_test(
            t, perf_configs[t]['name'], perf_configs[t]['json'])
      except self.m.step.StepFailure:
        failed = True

    # Collect all perf data of the previous steps.
    if upload:
      self.perf_upload(
          [results_mapping[k] for k in sorted(results_mapping.keys())],
          category)

    if failed:
      raise self.m.step.StepFailure('One or more performance tests failed.')

    return results_mapping

  def merge_perf_results(self, *args, **kwargs):
    """Merge perf results from a list of result files and return the resulting
    json.
    """
    return self.m.python(
      'merge perf results',
      self.resource('merge_perf_results.py'),
      map(str, args),
      stdout=self.m.json.output(),
      **kwargs
    ).stdout

  def maybe_trigger(self):
    triggers = self.bot_config.get('triggers')
    if triggers:
      self.m.trigger(*[{
        'builder_name': builder_name,
        'properties': {
          'revision': self.revision,
          'parent_got_revision': self.revision,
          'parent_got_revision_cp': self.revision_cp,
        },
      } for builder_name in triggers])
