# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'archive',
  'chromium',
  'gclient',
  'json',
  'path',
  'platform',
  'properties',
  'step',
  'step_history',
  'tryserver',
  'v8',
]


V8_TEST_CONFIGS = {
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
    'tests': 'cctest mjsunit webkit',
    'add_flaky_step': True,
    'test_args': ['--no-variants', '--shell_flags="--optimize-for-size"'],
  },
  'test262': {
    'name': 'Test262',
    'tests': 'test262',
  },
  'v8testing': {
    'name': 'Check',
    'tests': 'mjsunit fuzz-natives cctest message preparser',
    'add_flaky_step': True,
  },
  'webkit': {
    'name': 'Webkit',
    'tests': 'webkit',
    'add_flaky_step': True,
  },
}


class V8Test(object):
  def __init__(self, name):
    self.name = name

  def run(self, api, **kwargs):
    return api.v8.runtest(V8_TEST_CONFIGS[self.name], **kwargs)

  def gclient_apply_config(self, api):
    for c in V8_TEST_CONFIGS[self.name].get('gclient_apply_config', []):
      api.gclient.apply_config(c)


class V8Presubmit(object):
  @staticmethod
  def run(api, **kwargs):
    return api.v8.presubmit()

  @staticmethod
  def gclient_apply_config(_):
    pass


class V8CheckInitializers(object):
  @staticmethod
  def run(api, **kwargs):
    return api.v8.check_initializers()

  @staticmethod
  def gclient_apply_config(_):
    pass


class V8GCMole(object):
  @staticmethod
  def run(api, **kwargs):
    return api.v8.gc_mole()

  @staticmethod
  def gclient_apply_config(_):
    pass


class V8SimpleLeakCheck(object):
  @staticmethod
  def run(api, **kwargs):
    return api.v8.simple_leak_check()

  @staticmethod
  def gclient_apply_config(_):
    pass


V8_NON_STANDARD_TESTS = {
  'gcmole': V8GCMole,
  'presubmit': V8Presubmit,
  'simpleleak': V8SimpleLeakCheck,
  'v8initializers': V8CheckInitializers,
}


def CreateTest(test):
  """Wrapper that allows to shortcut common tests with their names.
  Returns a runnable test instance.
  """
  if test in V8_NON_STANDARD_TESTS:
    return V8_NON_STANDARD_TESTS[test]()
  else:
    return V8Test(test)


# Map of GS archive names to urls.
GS_ARCHIVES = {
  'linux_rel_archive': 'gs://chromium-v8/v8-linux-rel',
  'linux_rel_archive_exp': 'gs://chromium-v8/v8-linux-rel-exp',
  'linux_dbg_archive': 'gs://chromium-v8/v8-linux-dbg',
  'linux_nosnap_rel_archive': 'gs://chromium-v8/v8-linux-nosnap-rel',
  'linux_nosnap_dbg_archive': 'gs://chromium-v8/v8-linux-nosnap-dbg',
  'linux64_rel_archive': 'gs://chromium-v8/v8-linux64-rel',
  'linux64_dbg_archive': 'gs://chromium-v8/v8-linux64-dbg',
  'win32_rel_archive': 'gs://chromium-v8/v8-win32-rel',
  'win32_dbg_archive': 'gs://chromium-v8/v8-win32-dbg',
}


def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = api.v8.BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  assert bot_config, (
      'Unrecognized builder name %r for master %r.' % (
          buildername, mastername))

  api.v8.set_config('v8',
                    optional=True,
                    **bot_config.get('v8_config_kwargs', {}))
  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)
  for c in bot_config.get('chromium_apply_config', []):
    api.chromium.apply_config(c)
  for c in bot_config.get('v8_apply_config', []):
    api.v8.apply_config(c)

  # Test-specific configurations.
  for t in bot_config.get('tests', []):
    CreateTest(t).gclient_apply_config(api)

  if api.tryserver.is_tryserver:
    api.chromium.apply_config('trybot_flavor')
    api.chromium.apply_config('optimized_debug')
    api.v8.apply_config('trybot_flavor')

  api.step.auto_resolve_conflicts = True

  if api.platform.is_win:
    yield api.chromium.taskkill()

  yield api.v8.checkout()

  if api.tryserver.is_tryserver:
    yield api.tryserver.maybe_apply_issue()

  yield api.v8.runhooks()
  yield api.chromium.cleanup_temp()

  if 'clang' in bot_config.get('gclient_apply_config', []):
    yield api.v8.update_clang()

  bot_type = bot_config.get('bot_type', 'builder_tester')
  if bot_type in ['builder', 'builder_tester']:
    if api.tryserver.is_tryserver:
      yield api.v8.compile(name='compile (with patch)',
                           abort_on_failure=False,
                           can_fail_build=False)
      if api.step_history['compile (with patch)'].retcode != 0:
        api.gclient.apply_config('v8_lkgr')
        yield (
          api.v8.checkout(),
          api.tryserver.maybe_apply_issue(),
          api.v8.runhooks(),
          api.v8.compile(name='compile (with patch, lkgr, clobber)',
                         force_clobber=True)
        )
    else:
      yield api.v8.compile()

  if bot_type == 'builder':
    yield(api.archive.zip_and_upload_build(
          'package build',
          api.chromium.c.build_config_fs,
          GS_ARCHIVES[bot_config['build_gs_archive']],
          src_dir='v8'))

  if bot_type == 'tester':
    yield(api.path.rmtree(
          'build directory',
          api.chromium.c.build_dir.join(api.chromium.c.build_config_fs)))

    yield(api.archive.download_and_unzip_build(
          'extract build',
          api.chromium.c.build_config_fs,
          GS_ARCHIVES[bot_config['build_gs_archive']],
          abort_on_failure=True,
          src_dir='v8'))

  steps = []
  if bot_type in ['tester', 'builder_tester']:
    steps.extend([CreateTest(t).run(api) for t in bot_config.get('tests', [])])
  yield steps


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  for mastername, master_config in api.v8.BUILDERS.iteritems():
    for buildername, bot_config in master_config['builders'].iteritems():
      bot_type = bot_config.get('bot_type', 'builder_tester')

      if bot_type in ['builder', 'builder_tester']:
        assert bot_config['testing'].get('parent_buildername') is None

      v8_config_kwargs = bot_config.get('v8_config_kwargs', {})
      test = (
        api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                                 _sanitize_nonalpha(buildername))) +
        api.properties.generic(mastername=mastername,
                               buildername=buildername,
                               parent_buildername=bot_config.get(
                                   'parent_buildername')) +
        api.platform(bot_config['testing']['platform'],
                     v8_config_kwargs.get('TARGET_BITS', 64))
      )

      if mastername.startswith('tryserver'):
        test += (api.properties(
            revision='12345',
            patch_url='svn://svn-mirror.golo.chromium.org/patch'))

      yield test

  yield (
    api.test('try_compile_failure') +
    api.properties.tryserver(mastername='tryserver.v8',
                             buildername='v8_win_rel',
                             revision=None) +
    api.platform('win', 32) +
    api.step_data('compile (with patch)', retcode=1)
  )

  mastername = 'client.v8'
  buildername = 'V8 Linux - isolates'
  bot_config = api.v8.BUILDERS[mastername]['builders'][buildername]
  def TestFailures(wrong_results):
    suffix = "_wrong_results" if wrong_results else ""
    return (
      api.test('full_%s_%s_test_failures%s' % (_sanitize_nonalpha(mastername),
                                               _sanitize_nonalpha(buildername),
                                               suffix)) +
      api.properties.generic(mastername=mastername,
                             buildername=buildername,
                             parent_buildername=bot_config.get(
                                 'parent_buildername')) +
      api.platform(bot_config['testing']['platform'],
                   v8_config_kwargs.get('TARGET_BITS', 64)) +
      api.v8(test_failures=True, wrong_results=wrong_results)
    )

  yield TestFailures(wrong_results=False)
  yield TestFailures(wrong_results=True)
