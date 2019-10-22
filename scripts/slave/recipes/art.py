# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'repo',
]

_TARGET_DEVICE_MAP = {
    'walleye-armv7': {
      'bitness': 32,
      'make_jobs': 4,
      'product': 'arm_krait',
      },
    'walleye-armv8': {
      'bitness': 64,
      'make_jobs': 4,
      'product': 'armv8',
      },
    'angler-armv7': {
      'bitness': 32,
      'make_jobs': 4,
      'product': 'arm_krait',
      },
    'fugu': {
      'bitness': 32,
      'make_jobs': 1,
      'product': 'silvermont',
      },
    'mips32': {
      'bitness': 32,
      'make_jobs': 2,
      'product': 'mips32r2_fp_xburst',
      },
    'angler-armv8': {
      'bitness': 64,
      'make_jobs': 4,
      'product': 'armv8',
      },
    'bullhead-armv8': {
      'bitness': 64,
      'make_jobs': 4,
      'product': 'armv8',
      },
    'bullhead-armv7': {
      'bitness': 32,
      'make_jobs': 4,
      'product': 'arm_krait',
      },
    }

def checkout(api):
  api.repo.init('https://android.googlesource.com/platform/manifest',
      '-b', 'master-art')
  api.repo.sync("-f", "-c")
  api.repo.manifest()


def full_checkout(api):
  api.repo.init('https://android.googlesource.com/platform/manifest',
      '-b', 'master')
  api.repo.sync("-f", "-c")
  api.repo.manifest()


def clobber(api):
  # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
  if 'clobber' in api.properties:
    api.file.rmtree('clobber', api.path['start_dir'].join('out'))

def setup_host_x86(api,
                   debug,
                   bitness,
                   concurrent_collector=True,
                   generational_cc=True,
                   heap_poisoning=False,
                   gcstress=False,
                   cdex_level='none'):
  checkout(api)
  clobber(api)

  build_top_dir = api.path['start_dir']
  art_tools = api.path['start_dir'].join('art', 'tools')
  env = { 'TARGET_PRODUCT': 'sdk',
          'TARGET_BUILD_VARIANT': 'eng',
          'TARGET_BUILD_TYPE': 'release',
          'LANG': 'en_US.UTF-8',
          'SOONG_ALLOW_MISSING_DEPENDENCIES': 'true',
          'TEMPORARY_DISABLE_PATH_RESTRICTIONS': 'true',
          'ANDROID_BUILD_TOP': build_top_dir,
          'PATH': str(build_top_dir.join('out', 'host', 'linux-x86', 'bin')) +
                  api.path.pathsep +
                  str(build_top_dir.join(
                      'prebuilts', 'jdk', 'jdk9', 'linux-x86', 'bin')) +
                  api.path.pathsep +
                  '%(PATH)s',
          'ART_TEST_RUN_TEST_2ND_ARCH': 'false',
          'ART_TEST_KEEP_GOING': 'true' }

  if bitness == 32:
    env.update({ 'HOST_PREFER_32_BIT' : 'true' })

  if concurrent_collector:
    env.update({ 'ART_USE_READ_BARRIER' : 'true' })
  else:
    env.update({ 'ART_USE_READ_BARRIER' : 'false' })

  # Note: Generational CC only makes sense when read barriers are used
  # (i.e. when the Concurrent Copying collector is used).
  if generational_cc:
    env.update({ 'ART_USE_GENERATIONAL_CC' : 'true' })
  else:
    env.update({ 'ART_USE_GENERATIONAL_CC' : 'false' })

  if heap_poisoning:
    env.update({ 'ART_HEAP_POISONING' : 'true' })
  else:
    env.update({ 'ART_HEAP_POISONING' : 'false' })

  env.update({ 'ART_DEFAULT_COMPACT_DEX_LEVEL' : cdex_level })

  # Common options passed to testrunner.py.
  common_options = ['--verbose', '--host']

  if debug:
    common_options += ['--debug']
  else:
    common_options += ['--ndebug']

  if gcstress:
    common_options += ['--gcstress']

  # Pass down the cdex option to testrunner.py since it doesn't use the build
  # default.
  if cdex_level != 'none':
    common_options += ['--cdex-' + cdex_level]

  with api.context(env=env):
    api.step('build sdk-eng',
             [art_tools.join('buildbot-build.sh'), '-j8', '--host'])

    with api.step.defer_results():
      api.step('test gtest', ['build/soong/soong_ui.bash',
                              '--make-mode',
                              '-j8',
                              'test-art-host-gtest%d' % bitness])

      api.step('test optimizing', ['./art/test/testrunner/testrunner.py',
                                   '-j8',
                                   '--optimizing'] + common_options)

      api.step('test debuggable', ['./art/test/testrunner/testrunner.py',
                                   '-j8',
                                   '--jit',
                                   '--debuggable'] + common_options)

      # Use a lower -j number for interpreter, some tests take a long time
      # to run on it.
      api.step('test interpreter', ['./art/test/testrunner/testrunner.py',
                                    '-j5',
                                    '--interpreter'] + common_options)

      api.step('test baseline', ['./art/test/testrunner/testrunner.py',
                                 '-j8',
                                 '--baseline'] + common_options)

      api.step('test jit', ['./art/test/testrunner/testrunner.py',
                            '-j8',
                            '--jit'] + common_options)

      if cdex_level != "none":
        api.step('test cdex-redefine-stress-optimizing',
                 ['./art/test/testrunner/testrunner.py',
                  '-j8',
                  '--optimizing',
                  '--redefine-stress',
                  '--debuggable'] + common_options)
        api.step('test cdex-redefine-stress-jit',
                 ['./art/test/testrunner/testrunner.py',
                  '-j8',
                  '--jit',
                  '--redefine-stress',
                  '--debuggable'] + common_options)

      api.step('test speed-profile', ['./art/test/testrunner/testrunner.py',
                                      '-j8',
                                      '--speed-profile'] + common_options)

      libcore_command = [art_tools.join('run-libcore-tests.sh'),
                         '--mode=host',
                         '--variant=X%d' % bitness]
      if debug:
        libcore_command.append('--debug')
      if gcstress:
        libcore_command += ['--vm-arg', '-Xgc:gcstress']

      api.step('test libcore', libcore_command)

      jdwp_command = [art_tools.join('run-jdwp-tests.sh'),
                      '--mode=host',
                      '--variant=X%d' % bitness]
      if debug:
        jdwp_command.append('--debug')
      if gcstress:
        jdwp_command += ['--vm-arg', '-Xgc:gcstress']

      api.step('test jdwp jit', jdwp_command)

      # Disable interpreter jdwp runs with gcstress, they time out.
      if not gcstress:
        api.step('test jdwp interpreter', jdwp_command + ['--no-jit'])

      libjdwp_run = art_tools.join('run-libjdwp-tests.sh')
      libjdwp_common_command = [libjdwp_run,
                                '--mode=host',
                                '--variant=X%d' % bitness]
      if debug:
        libjdwp_common_command.append('--debug')
      if gcstress:
        libjdwp_common_command += ['--vm-arg', '-Xgc:gcstress']

      api.step('test libjdwp jit', libjdwp_common_command)

      # Disable interpreter jdwp runs with gcstress, they time out.
      if not gcstress:
        api.step(
            'test libjdwp interpreter', libjdwp_common_command + ['--no-jit'])

      api.step('test dx', ['./dalvik/dx/tests/run-all-tests'])

def setup_target(api,
                 device,
                 debug,
                 concurrent_collector=True,
                 generational_cc=True,
                 heap_poisoning=False,
                 gcstress=False):
  build_top_dir = api.path['start_dir']
  art_tools = api.path['start_dir'].join('art', 'tools')
  # The path to the chroot directory on the device where ART and its
  # dependencies are installed, in case of chroot-based testing.
  chroot_dir='/data/local/art-test-chroot'

  env = {'TARGET_BUILD_VARIANT': 'eng',
         'TARGET_BUILD_TYPE': 'release',
         'LANG': 'en_US.UTF-8',
         'SOONG_ALLOW_MISSING_DEPENDENCIES': 'true',
         'TEMPORARY_DISABLE_PATH_RESTRICTIONS': 'true',
         'ANDROID_BUILD_TOP': build_top_dir,
         'ADB': str(build_top_dir.join('prebuilts', 'runtime', 'adb')),
         'PATH': str(build_top_dir.join(
             'prebuilts', 'jdk', 'jdk9', 'linux-x86', 'bin')) +
                 api.path.pathsep +
                 # Add adb in the path.
                 str(build_top_dir.join('prebuilts', 'runtime')) +
                 api.path.pathsep + '%(PATH)s',
         'ART_TEST_RUN_TEST_2ND_ARCH': 'false',
         'USE_DEX2OAT_DEBUG': 'false',
         'ART_BUILD_HOST_DEBUG': 'false',
         'ART_TEST_KEEP_GOING': 'true'}

  if concurrent_collector:
    env.update({ 'ART_USE_READ_BARRIER' : 'true' })
  else:
    env.update({ 'ART_USE_READ_BARRIER' : 'false' })  # pragma: no cover

  # Note: Generational CC only makes sense when read barriers are used
  # (i.e. when the Concurrent Copying collector is used).
  if generational_cc:
    env.update({ 'ART_USE_GENERATIONAL_CC' : 'true' })
  else:
    env.update({ 'ART_USE_GENERATIONAL_CC' : 'false' })

  if heap_poisoning:
    env.update({ 'ART_HEAP_POISONING' : 'true' })
  else:
    env.update({ 'ART_HEAP_POISONING' : 'false' })


  bitness = _TARGET_DEVICE_MAP[device]['bitness']
  make_jobs = _TARGET_DEVICE_MAP[device]['make_jobs']
  env.update(
      {'TARGET_PRODUCT': _TARGET_DEVICE_MAP[device]['product'],
       'ANDROID_PRODUCT_OUT': build_top_dir.join('out','target', 'product',
         _TARGET_DEVICE_MAP[device]['product'])
      })

  env.update({ 'ART_TEST_CHROOT' : chroot_dir })

  checkout(api)
  clobber(api)

  gtest_env = env.copy()
  gtest_env.update({ 'ART_TEST_NO_SYNC': 'true' })

  test_env = gtest_env.copy()
  test_env.update(
      { 'PATH': str(build_top_dir.join('out', 'host', 'linux-x86', 'bin')) +
                api.path.pathsep +
                str(build_top_dir.join(
                    'prebuilts', 'jdk', 'jdk9', 'linux-x86', 'bin')) +
                api.path.pathsep +
                # Add adb in the path.
                str(build_top_dir.join('prebuilts', 'runtime')) +
                api.path.pathsep +
                '%(PATH)s' })

  # Decrease the number of parallel tests, as some tests eat lots of memory.
  if debug and device == 'fugu':
    make_jobs = 1

  with api.context(env=env):
    api.step('build target', [art_tools.join('buildbot-build.sh'),
                              '-j2', '--target'])

  with api.step.defer_results():
    with api.context(env=test_env):
      # Temporary work-around to try to diagnose excessive timeouts.
      if gcstress:
        api.step('adb reboot', ['adb', 'reboot'])
        api.step('adb wait-for-device', ['adb', 'wait-for-device'])

      api.step('device pre-run cleanup', [
          art_tools.join('cleanup-buildbot-device.sh')])

      api.step('setup device', [art_tools.join('setup-buildbot-device.sh'),
                                '--verbose'])

    with api.context(env=env):
      api.step('sync target', [art_tools.join('buildbot-sync.sh')])

    def test_logging(api, test_name):
      with api.context(env=test_env):
        api.step(test_name + ': adb logcat',
                 ['adb', 'logcat', '-d', '-v', 'threadtime'])
        api.step(test_name + ': crashes',
                 [art_tools.join('symbolize-buildbot-crashes.sh')])
        api.step(test_name + ': adb clear log', ['adb', 'logcat', '-c'])


    with api.context(env=gtest_env):
      api.step('test gtest', [
          art_tools.join('run-gtests.sh'), '-j%d' % (make_jobs)])
    test_logging(api, 'test gtest')

    optimizing_make_jobs = make_jobs
    # Decrease the number of parallel tests for fugu/optimizing, as some tests
    # eat lots of memory.
    if not debug and device == 'fugu':
      optimizing_make_jobs = 1

    # Common options passed to testrunner.py.
    common_options = ['--target', '--verbose']

    if debug:
      common_options += ['--debug']
    else:
      common_options += ['--ndebug']

    if gcstress:
      common_options += ['--gcstress']

    with api.context(env=test_env):
      api.step('test optimizing', ['./art/test/testrunner/testrunner.py',
                                   '-j%d' % (optimizing_make_jobs),
                                   '--optimizing'] + common_options)
    test_logging(api, 'test optimizing')

    with api.context(env=test_env):
      # We pass --optimizing for interpreter debuggable to run AOT checker tests
      # compiled debuggable.
      api.step('test debuggable', ['./art/test/testrunner/testrunner.py',
                                   '-j%d' % (make_jobs),
                                   '--optimizing',
                                   '--debuggable'] + common_options)
    test_logging(api, 'test debuggable')

    with api.context(env=test_env):
      api.step('test jit debuggable', ['./art/test/testrunner/testrunner.py',
                                       '-j%d' % (make_jobs),
                                       '--jit',
                                       '--debuggable'] + common_options)
    test_logging(api, 'test jit debuggable')

    with api.context(env=test_env):
      api.step('test interpreter', ['./art/test/testrunner/testrunner.py',
                                    '-j%d' % (make_jobs),
                                    '--interpreter'] + common_options)
    test_logging(api, 'test interpreter')

    with api.context(env=test_env):
      api.step('test baseline', ['./art/test/testrunner/testrunner.py',
                                    '-j%d' % (make_jobs),
                                    '--baseline'] + common_options)
    test_logging(api, 'test baseline')

    with api.context(env=test_env):
      api.step('test jit', ['./art/test/testrunner/testrunner.py',
                            '-j%d' % (make_jobs),
                            '--jit'] + common_options)
    test_logging(api, 'test jit')

    with api.context(env=test_env):
      api.step('test speed-profile', ['./art/test/testrunner/testrunner.py',
                                      '-j%d' % (make_jobs),
                                      '--speed-profile'] + common_options)
    test_logging(api, 'test speed-profile')

    libcore_command = [art_tools.join('run-libcore-tests.sh'),
                       '--mode=device',
                       '--variant=X%d' % bitness]
    if debug:
      libcore_command.append('--debug')
    if gcstress:
      libcore_command += ['--vm-arg', '-Xgc:gcstress']
    # Ignore failures from Libcore tests using the getrandom() syscall (present
    # since Linux 3.17) on fugu devices, as they run a Linux 3.10 kernel.
    if device == 'fugu':
      libcore_command.append('--no-getrandom')

    # Disable libcore runs with gcstress and debug, they time out.
    if not (gcstress and debug):
      with api.context(env=test_env):
        api.step('test libcore', libcore_command)
      test_logging(api, 'test libcore')

    jdwp_command = [art_tools.join('run-jdwp-tests.sh'),
                    '--mode=device',
                    '--variant=X%d' % bitness]
    if debug:
      jdwp_command.append('--debug')
    if gcstress:
      jdwp_command += ['--vm-arg', '-Xgc:gcstress']

    # Disable jit jdwp runs with gcstress and debug, they time out.
    if not (gcstress and debug):
      with api.context(env=test_env):
        api.step('test jdwp jit', jdwp_command)
      test_logging(api, 'test jdwp jit')

    # Disable interpreter jdwp runs with gcstress, they time out.
    if not gcstress:
      with api.context(env=test_env):
        api.step('test jdwp interpreter', jdwp_command + ['--no-jit'])
      test_logging(api, 'test jdwp interpreter')

    libjdwp_command = [art_tools.join('run-libjdwp-tests.sh'),
                       '--mode=device',
                       '--variant=X%d' % bitness]
    if debug:
      libjdwp_command.append('--debug')
    if gcstress:
      libjdwp_command += ['--vm-arg', '-Xgc:gcstress']

    # Disable jit libjdwp runs with gcstress and debug, they time out.
    if not (gcstress and debug):
      with api.context(env=test_env):
        api.step('test libjdwp jit', libjdwp_command)
      test_logging(api, 'test libjdwp jit')

    # Disable interpreter libjdwp runs with gcstress, they time out.
    if not gcstress:
      with api.context(env=test_env):
        api.step('test libjdwp interpreter', libjdwp_command + ['--no-jit'])
      test_logging(api, 'test libjdwp interpreter')

    with api.context(env=test_env):
      api.step('tear down device', [
          art_tools.join('teardown-buildbot-device.sh')])

      api.step('device post-run cleanup', [
          art_tools.join('cleanup-buildbot-device.sh')])

def setup_aosp_builder(api, read_barrier):
  full_checkout(api)
  clobber(api)
  builds = ['x86', 'x86_64', 'arm', 'arm64']
  build_top_dir = api.path['start_dir']
  with api.step.defer_results():
    for build in builds:
      env = { 'TARGET_PRODUCT': 'aosp_%s' % build,
              'TARGET_BUILD_VARIANT': 'eng',
              'TARGET_BUILD_TYPE': 'release',
              'ANDROID_BUILD_TOP': build_top_dir,
              'JACK_SERVER': 'false',
              'JACK_REPOSITORY': str(build_top_dir.join('prebuilts', 'sdk',
                                                        'tools', 'jacks')),
              'PATH': str(build_top_dir.join(
                  'out', 'host', 'linux-x86', 'bin')) +
                      api.path.pathsep + '%(PATH)s',
              'ART_USE_READ_BARRIER': 'true' if read_barrier else 'false'}
      with api.context(env=env):
        api.step('Pre clean %s' % build, ['rm', '-rf', 'out'])
        api.step('Build %s' % build, ['build/soong/soong_ui.bash',
                                      '--make-mode',
                                      '-j8'])
        api.step('Dump oat boot %s' % build, ['build/soong/soong_ui.bash',
                                              '--make-mode',
                                              '-j8',
                                              'dump-oat-boot-%s' % build])
        api.step('Post clean %s' % build, ['rm', '-rf', 'out'])


_CONFIG_MAP = {
  'x86': {
    'host-x86-ndebug': {
      'debug': False,
      'bitness': 32,
    },
    'host-x86-debug': {
      'debug': True,
      'bitness': 32,
    },
    'host-x86_64-ndebug': {
      'debug': False,
      'bitness': 64,
    },
    'host-x86_64-debug': {
      'debug': True,
      'bitness': 64,
    },
    'host-x86-cms': {
      'debug': True,
      'bitness': 32,
      'concurrent_collector': False,
      'generational_cc': False,
    },
    'host-x86_64-cms': {
      'debug': True,
      'bitness': 64,
      'concurrent_collector': False,
      'generational_cc': False,
    },
    'host-x86-poison-debug': {
      'debug': True,
      'bitness': 32,
      'heap_poisoning': True,
    },
    'host-x86_64-poison-debug': {
      'debug': True,
      'bitness': 64,
      'heap_poisoning': True,
    },
    'host-x86-gcstress-debug': {
      'bitness': 32,
      'debug': True,
      'gcstress': True,
    },
    'host-x86_64-non-gen-cc': {
      'bitness': 64,
      'debug': True,
      'generational_cc': False,
    },
    'host-x86_64-cdex-fast': {
      'debug': True,
      'bitness': 64,
      'cdex_level': 'fast',
    },
  },
  # TODO: Remove device names.
  'target': {
    'angler-armv7-ndebug': {
      'device': 'angler-armv7',
      'debug': False,
    },
    'angler-armv7-debug': {
      'device': 'angler-armv7',
      'debug': True,
    },
    'walleye-armv7-poison-debug': {
      'device': 'walleye-armv7',
      'debug': True,
      'heap_poisoning': True,
    },
    'walleye-armv8-poison-ndebug': {
      'device': 'walleye-armv8',
      'debug': False,
      'heap_poisoning': True,
    },
    'walleye-armv8-poison-debug': {
      'device': 'walleye-armv8',
      'debug': True,
      'heap_poisoning': True
    },
    'fugu-ndebug': {
      'device': 'fugu',
      'debug': False,
    },
    'fugu-debug': {
      'device': 'fugu',
      'debug': True,
    },
    'angler-armv7-non-gen-cc': {
      'device': 'angler-armv7',
      'debug': True,
      'generational_cc': False,
    },
    'angler-armv8-ndebug': {
      'device': 'angler-armv8',
      'debug': False,
    },
    'angler-armv8-debug': {
      'device': 'angler-armv8',
      'debug': True,
    },
    'angler-armv8-non-gen-cc': {
      'device': 'angler-armv8',
      'debug': True,
      'generational_cc': False,
    },
    'bullhead-armv8-gcstress-ndebug': {
      'device': 'bullhead-armv8',
      'debug': False,
      'gcstress': True,
    },
    'bullhead-armv8-gcstress-debug': {
      'device': 'bullhead-armv8',
      'debug': True,
      'gcstress': True,
    },
    'bullhead-armv7-gcstress-ndebug': {
      'device': 'bullhead-armv7',
      'debug': False,
      'gcstress': True,
    },
  },

  'aosp': {
    'aosp-builder-cms': {
      'read_barrier': False
    },
    'aosp-builder-cc': {
      'read_barrier': True
    },
  },
}

_CONFIG_DISPATCH_MAP = {
  'x86': setup_host_x86,
  'target': setup_target,
  'aosp': setup_aosp_builder,
}

def RunSteps(api):
  builder_found = False
  buildername = api.buildbucket.builder_name
  for builder_type, builder_config in _CONFIG_MAP.iteritems():
    if buildername in builder_config:
      builder_found = True
      builder_dict = builder_config[buildername]
      _CONFIG_DISPATCH_MAP[builder_type](api, **builder_dict)
      break

  if not builder_found: # pragma: no cover
    error = "Builder not found in recipe's local config!"
    raise KeyError(error)

def GenTests(api):

  def test(name, builder):
    return api.test(
        name,
        api.buildbucket.ci_build(
            project='art',
            builder=builder,
        ),
        api.properties(bot_id='TestSlave'),
    )

  for builders in _CONFIG_MAP.values():
    for buildername in builders:
      for clb in (None, True):
        yield (
            test(
                '%s__%s' % (
                    buildername, ('' if clb else 'no') + 'clobber'),
                buildername,
            ) +
            (api.properties(clobber='') if clb else api.properties())
          )
  yield (
      test('x86_32_test_failure', 'host-x86-ndebug') +
      api.step_data('test jdwp interpreter', retcode=1))

  yield (
      test('target_angler_setup_failure', 'angler-armv7-ndebug') +
      api.step_data('setup device', retcode=1))
  yield (
      test('target_angler_test_failure', 'angler-armv7-ndebug') +
      api.step_data('test jdwp interpreter', retcode=1))
  yield (
      test(
          'target_angler_device_pre_run_cleanup_failure',
          'angler-armv7-ndebug') +
      api.step_data('device pre-run cleanup', retcode=1))
  yield (
      test('aosp_x86_build_failure', 'aosp-builder-cms') +
      api.step_data('Build x86', retcode=1))
#  These tests *should* exist, but can't be included as they cause the recipe
#  simulation to error out, instead of showing that the build should become
#  purple instead. This may need to be fixed in the simulation test script.
#  yield (
#      api.test('invalid mastername') +
#      api.properties(
#        mastername='client.art.does_not_exist',
#        buildername='aosp-builder-cms',
#        bot_id='TestSlave',
#      )
#    )
#  yield (
#      api.test('invalid buildername') +
#      api.properties(
#        mastername='client.art',
#        buildername='builder_does_not_exist',
#        bot_id='TestSlave',
#      )
#    )
