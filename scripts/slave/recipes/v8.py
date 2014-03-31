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
  'tryserver',
  'v8',
]


V8_TEST_CONFIGS = {
  'benchmarks': {
    'name': 'Benchmarks',
    'tests': 'benchmarks',
    'flaky_step': False,
  },
  'mozilla': {
    'name': 'Mozilla',
    'tests': 'mozilla',
    'flaky_step': False,
    'gclient_apply_config': ['mozilla_tests'],
  },
  'optimize_for_size': {
    'name': 'OptimizeForSize',
    'tests': 'cctest mjsunit webkit',
    'flaky_step': True,
    'test_args': ['--no-variants', '--shell_flags="--optimize-for-size"'],
  },
  'test262': {
    'name': 'Test262',
    'tests': 'test262',
    'flaky_step': False,
  },
  'v8testing': {
    'name': 'Check',
    'tests': 'mjsunit cctest message preparser',
    'flaky_step': True,
  },
  'v8testing_try': {
    'name': 'Check',
    'tests': 'mjsunit cctest message preparser',
    'flaky_step': False,
    'test_args': ['--quickcheck'],
  },
  'webkit': {
    'name': 'Webkit',
    'tests': 'webkit',
    'flaky_step': True,
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
  'linux_dbg_archive': 'gs://chromium-v8/v8-linux-dbg',
  'linux_nosnap_rel_archive': 'gs://chromium-v8/v8-linux-nosnap-rel',
  'linux_nosnap_dbg_archive': 'gs://chromium-v8/v8-linux-nosnap-dbg',
  'linux64_rel_archive': 'gs://chromium-v8/v8-linux64-rel',
  'linux64_dbg_archive': 'gs://chromium-v8/v8-linux64-dbg',
  'win32_rel_archive': 'gs://chromium-v8/v8-win32-rel',
  'win32_dbg_archive': 'gs://chromium-v8/v8-win32-dbg',
}

BUILDERS = {
  'client.v8': {
    'builders': {
####### Category: Linux
      'V8 Linux - builder': {
        'recipe_config': 'v8',
        'chromium_apply_config': ['verify_heap'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_rel_archive',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': [
          'presubmit',
          'v8initializers',
          'v8testing',
          'optimize_for_size',
          'webkit',
          'benchmarks',
          'test262',
          'mozilla',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': [
          'v8testing',
          'benchmarks',
          'test262',
          'mozilla',
          'simpleleak',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - shared': {
        'recipe_config': 'v8',
        'chromium_apply_config': ['shared_library'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosnap': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - nosnap builder',
        'build_gs_archive': 'linux_nosnap_rel_archive',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosnap - debug': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - nosnap debug builder',
        'build_gs_archive': 'linux_nosnap_dbg_archive',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - isolates': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': ['v8testing'],
        'test_args': ['--isolates', 'on'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosse2': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': ['v8testing', 'test262', 'mozilla', 'gcmole'],
        'test_args': ['--shell_flags="--noenable-sse2"'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosse3': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'test_args': ['--shell_flags="--noenable-sse3"'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosse4': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'test_args': ['--shell_flags="--noenable-sse4-1"'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug - isolates': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['v8testing'],
        'test_args': ['--isolates', 'on'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug - nosse2': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'test_args': ['--shell_flags="--noenable-sse2"'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug - nosse3': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'test_args': ['--shell_flags="--noenable-sse3"'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug - nosse4': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'test_args': ['--shell_flags="--noenable-sse4-1"'],
        'testing': {'platform': 'linux'},
      },
####### Category: Linux64
      'V8 Linux64': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux64 - builder',
        'build_gs_archive': 'linux64_rel_archive',
        'tests': [
          'v8initializers',
          'v8testing',
          'optimize_for_size',
          'webkit',
          'test262',
          'mozilla',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - debug': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux64 - debug builder',
        'build_gs_archive': 'linux64_dbg_archive',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
####### Category: Windows
      'V8 Win32 - 1': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Win32 - builder',
        'build_gs_archive': 'win32_rel_archive',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'test_args': ['--shard_count=2', '--shard_run=1'],
        'testing': {'platform': 'win'},
      },
      'V8 Win32 - 2': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Win32 - builder',
        'build_gs_archive': 'win32_rel_archive',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'test_args': ['--shard_count=2', '--shard_run=2'],
        'testing': {'platform': 'win'},
      },
      'V8 Win32 - debug - 1': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Win32 - debug builder',
        'build_gs_archive': 'win32_dbg_archive',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'test_args': ['--shard_count=3', '--shard_run=1'],
        'testing': {'platform': 'win'},
      },
      'V8 Win32 - debug - 2': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Win32 - debug builder',
        'build_gs_archive': 'win32_dbg_archive',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'test_args': ['--shard_count=3', '--shard_run=2'],
        'testing': {'platform': 'win'},
      },
      'V8 Win32 - debug - 3': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Win32 - debug builder',
        'build_gs_archive': 'win32_dbg_archive',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'test_args': ['--shard_count=3', '--shard_run=3'],
        'testing': {'platform': 'win'},
      },
####### Category: Misc
      'V8 Linux64 ASAN': {
        'recipe_config': 'v8',
        'gclient_apply_config': ['clang'],
        'chromium_apply_config': ['clang', 'asan', 'no_lsan'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing'],
        'testing': {'platform': 'linux'},
      },
      # This builder is used as a staging area for builders on the main
      # waterfall to be switched to recipes.
      'V8 Linux - recipe': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': [
          'v8testing',
          'benchmarks',
          'test262',
          'mozilla',
          'simpleleak',
        ],
        'testing': {'platform': 'linux'},
      },
####### Category: FYI
      'V8 Win32 - nosnap - shared': {
        'recipe_config': 'v8',
        'chromium_apply_config': ['vs', 'shared_library', 'no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing'],
        'testing': {'platform': 'win'},
      },
    },
  },
  'tryserver.v8': {
    'builders': {
      'v8_linux_rel': {
        'recipe_config': 'v8',
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing_try'],
        'testing': {'platform': 'linux'},
      },
    },
  },
}

RECIPE_CONFIGS = {
  'v8': {
    'v8_config': 'v8',
  },
}

def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  assert bot_config, (
      'Unrecognized builder name %r for master %r.' % (
          buildername, mastername))
  recipe_config_name = bot_config['recipe_config']
  assert recipe_config_name, (
      'Unrecognized builder name %r for master %r.' % (
          buildername, mastername))
  recipe_config = RECIPE_CONFIGS[recipe_config_name]

  api.v8.set_config(recipe_config['v8_config'],
                    optional=True,
                    **bot_config.get('v8_config_kwargs', {}))

  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)
  for c in bot_config.get('chromium_apply_config', []):
    api.chromium.apply_config(c)

  # Test-specific configurations.
  for t in bot_config.get('tests', []):
    CreateTest(t).gclient_apply_config(api)

  if api.tryserver.is_tryserver:
    api.chromium.apply_config('trybot_flavor')

  if api.platform.is_win:
    yield api.chromium.taskkill()

  yield api.v8.checkout()

  if api.tryserver.is_tryserver:
    yield api.tryserver.maybe_apply_issue()

  steps = [api.v8.runhooks(), api.chromium.cleanup_temp()]

  if 'clang' in bot_config.get('gclient_apply_config', []):
    steps.append(api.v8.update_clang())

  bot_type = bot_config.get('bot_type', 'builder_tester')

  if bot_type in ['builder', 'builder_tester']:
    steps.append(api.v8.compile())

  if bot_type == 'builder':
    steps.append(api.archive.zip_and_upload_build(
        'package build',
        api.chromium.c.build_config_fs,
        GS_ARCHIVES[bot_config['build_gs_archive']],
        src_dir='v8'))

  if bot_type == 'tester':
    steps.append(api.path.rmtree(
        'build directory',
        api.chromium.c.build_dir.join(api.chromium.c.build_config_fs)))

    steps.append(api.archive.download_and_unzip_build(
        'extract build',
        api.chromium.c.build_config_fs,
        GS_ARCHIVES[bot_config['build_gs_archive']],
        abort_on_failure=True,
        src_dir='v8'))

  test_args = bot_config.get('test_args', [])
  if bot_type in ['tester', 'builder_tester']:
    steps.extend([CreateTest(t).run(api, test_args=test_args)
                  for t in bot_config.get('tests', [])])
  yield steps


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  for mastername, master_config in BUILDERS.iteritems():
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
