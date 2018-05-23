# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
  'repo',
]

_TARGET_DEVICE_MAP = {
    'volantis-armv7': {
      'bitness': 32,
      'make_jobs': 4,
      'product': 'arm_krait',
      },
    'volantis-armv8': {
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
  api.repo.sync()

def full_checkout(api):
  api.repo.init('https://android.googlesource.com/platform/manifest',
      '-b', 'master')
  api.repo.sync()

def clobber(api):
  # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
  if 'clobber' in api.properties:
    api.file.rmtree('clobber', api.path['start_dir'].join('out'))

def setup_host_x86(api, debug, bitness, concurrent_collector=True,
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
          'SOONG_ALLOW_MISSING_DEPENDENCIES': 'true',
          'ANDROID_BUILD_TOP': build_top_dir,
          'JACK_SERVER': 'false',
          'JACK_REPOSITORY': str(build_top_dir.join('prebuilts', 'sdk',
                                                    'tools', 'jacks')),
          'PATH': str(build_top_dir.join('out', 'host', 'linux-x86', 'bin')) +
                  api.path.pathsep + '%(PATH)s',
          'ART_TEST_RUN_TEST_2ND_ARCH': 'false',
          'ART_TEST_FULL': 'false',
          'ART_TEST_KEEP_GOING': 'true' }

  if bitness == 32:
    env.update({ 'HOST_PREFER_32_BIT' : 'true' })

  if concurrent_collector:
    env.update({ 'ART_USE_READ_BARRIER' : 'true' })
  else:
    env.update({ 'ART_USE_READ_BARRIER' : 'false' })

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
      api.step('test gtest',
          ['make', '-j8', 'test-art-host-gtest%d' % bitness])

      api.step('test optimizing', ['./art/test/testrunner/testrunner.py',
                                   '-j8',
                                   '--optimizing'] + common_options)

      api.step('test debuggable', ['./art/test/testrunner/testrunner.py',
                                   '-j8',
                                   '--optimizing',
                                   '--debuggable'] + common_options)

      # Use a lower -j number for interpreter, some tests take a long time
      # to run on it.
      api.step('test interpreter', ['./art/test/testrunner/testrunner.py',
                                    '-j5',
                                    '--interpreter'] + common_options)

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
      api.step('test jdwp aot', jdwp_command + ['--no-jit'])

      libjdwp_run = art_tools.join('run-libjdwp-tests.sh')
      libjdwp_common_command = [libjdwp_run,
                                '--mode=host',
                                '--variant=X%d' % bitness]
      if debug:
        libjdwp_common_command.append('--debug')
      if gcstress:
        libjdwp_common_command += ['--vm-arg', '-Xgc:gcstress']

      api.step('test libjdwp jit', libjdwp_common_command)
      api.step('test libjdwp aot', libjdwp_common_command + ['--no-jit'])

      api.step('test dx', ['./dalvik/dx/tests/run-all-tests'])

def setup_target(api,
    serial,
    debug,
    device,
    chroot=False,
    concurrent_collector=True,
    heap_poisoning=False,
    gcstress=False):
  build_top_dir = api.path['start_dir']
  art_tools = api.path['start_dir'].join('art', 'tools')
  # The path to the chroot directory on the device where ART and its
  # dependencies are installed, in case of chroot-based testing.
  chroot_dir='/data/local/art-test-chroot'
  # The path to the local directory on the device where ART and its
  # dependencies are installed, if case no chroot is used.
  android_root = '/data/local/tmp/system'

  env = {'TARGET_BUILD_VARIANT': 'eng',
         'TARGET_BUILD_TYPE': 'release',
         'SOONG_ALLOW_MISSING_DEPENDENCIES': 'true',
         'ANDROID_SERIAL': serial,
         'ANDROID_BUILD_TOP': build_top_dir,
         'JACK_SERVER': 'false',
         'JACK_REPOSITORY': str(build_top_dir.join('prebuilts', 'sdk', 'tools',
                                                   'jacks')),
         'PATH': str(build_top_dir.join('out', 'host', 'linux-x86', 'bin')) +
                 api.path.pathsep + '%(PATH)s',
         'ART_TEST_RUN_TEST_2ND_ARCH': 'false',
         'ART_TEST_FULL': 'false',
         'USE_DEX2OAT_DEBUG': 'false',
         'ART_BUILD_HOST_DEBUG': 'false',
         'ART_TEST_KEEP_GOING': 'true'}

  if concurrent_collector:
    env.update({ 'ART_USE_READ_BARRIER' : 'true' })
  else:
    env.update({ 'ART_USE_READ_BARRIER' : 'false' })

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

  if chroot:
    env.update({ 'ART_TEST_CHROOT' : chroot_dir }) # pragma: no cover
  else:
    env.update({ 'ART_TEST_ANDROID_ROOT' : android_root })
    if bitness == 32:
      env.update({ 'CUSTOM_TARGET_LINKER': '%s/bin/linker' % android_root  })
    else:
      env.update({ 'CUSTOM_TARGET_LINKER': '%s/bin/linker64' % android_root  })

  checkout(api)
  clobber(api)

  # Decrease the number of parallel tests, as some tests eat lots of memory.
  if debug and device == 'fugu':
    make_jobs = 1

  with api.context(env=env):
    api.step('build target', [art_tools.join('buildbot-build.sh'),
                              '-j8', '--target'])

  with api.step.defer_results():
    with api.context(env=env):
      api.step('setup device', [art_tools.join('setup-buildbot-device.sh')])

      api.step('device cleanup', [art_tools.join('cleanup-buildbot-device.sh')])

      api.step('sync target', ['make', 'test-art-target-sync'])

    def test_logging(api, test_name):
      with api.context(env=env):
        api.step(test_name + ': adb logcat',
                 ['adb', 'logcat', '-d', '-v', 'threadtime'])
        api.step(test_name + ': crashes',
                 [art_tools.join('symbolize-buildbot-crashes.sh')])
        api.step(test_name + ': adb clear log', ['adb', 'logcat', '-c'])

    test_env = env.copy()
    test_env.update({ 'ART_TEST_NO_SYNC': 'true' })
    test_env.update({ 'ANDROID_ROOT': android_root })

    with api.context(env=test_env):
      api.step('test gtest', ['make', '-j%d' % (make_jobs),
        'test-art-target-gtest%d' % bitness])
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

    if chroot:
      common_options += ['--chroot', '"$ART_TEST_CHROOT"'] # pragma: no cover

    with api.context(env=test_env):
      api.step('test optimizing', ['./art/test/testrunner/testrunner.py',
                                   '-j%d' % (optimizing_make_jobs),
                                   '--optimizing',
                                   '--debuggable',
                                   '--ndebuggable'] + common_options)
    test_logging(api, 'test optimizing')

    with api.context(env=test_env):
      api.step('test interpreter', ['./art/test/testrunner/testrunner.py',
                                    '-j%d' % (make_jobs),
                                    '--interpreter'] + common_options)
    test_logging(api, 'test interpreter')

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
    if chroot:
      libcore_command += ['--chroot', '"$ART_TEST_CHROOT"'] # pragma: no cover

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
    if chroot:
      jdwp_command += ['--chroot', '"$ART_TEST_CHROOT"'] # pragma: no cover

    with api.context(env=test_env):
      api.step('test jdwp jit', jdwp_command)
    test_logging(api, 'test jdwp jit')

    with api.context(env=test_env):
      api.step('test jdwp aot', jdwp_command + ['--no-jit'])
    test_logging(api, 'test jdwp aot')

    libjdwp_command = [art_tools.join('run-libjdwp-tests.sh'),
                       '--mode=device',
                       '--variant=X%d' % bitness]
    if debug:
      libjdwp_command.append('--debug')
    if gcstress:
      libjdwp_command += ['--vm-arg', '-Xgc:gcstress']
    if chroot:
      libjdwp_command += ['--chroot', '"$ART_TEST_CHROOT"'] # pragma: no cover

    with api.context(env=test_env):
      api.step('test libjdwp jit', libjdwp_command)
    test_logging(api, 'test libjdwp jit')

    with api.context(env=test_env):
      api.step('test libjdwp aot', libjdwp_command + ['--no-jit'])
    test_logging(api, 'test libjdwp aot')

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
              'PATH': str(build_top_dir.join('out', 'host', 'linux-x86', 'bin')) +
                      api.path.pathsep + '%(PATH)s',
              'ART_USE_READ_BARRIER': 'true' if read_barrier else 'false'}
      with api.context(env=env):
        api.step('Clean oat %s' % build, ['make', '-j8', 'clean-oat-host'])
        api.step('build %s' % build, ['make', '-j8'])

def setup_valgrind_runner(api, bitness):
  # ART doesn't support valgrind host 32 anymore.
  assert bitness == 64
  checkout(api)
  clobber(api)
  build_top_dir = api.path['start_dir']
  run = api.path['start_dir'].join('art', 'test', 'testrunner', 'run_build_test_target.py')
  with api.step.defer_results():
    env = { 'TARGET_PRODUCT': 'sdk',
            'TARGET_BUILD_VARIANT': 'eng',
            'TARGET_BUILD_TYPE': 'release',
            'ANDROID_BUILD_TOP': build_top_dir,
            'PATH': str(build_top_dir.join('out', 'host', 'linux-x86', 'bin')) +
                    api.path.pathsep + '%(PATH)s',
            'JACK_SERVER': 'false',
            'JACK_REPOSITORY': str(build_top_dir.join('prebuilts', 'sdk',
                                                      'tools', 'jacks')) }

    with api.context(env=env):
      api.step('run valgrind tests', [run, '-j8', 'art-gtest-valgrind%d' % bitness])


_CONFIG_MAP = {
  'client.art': {

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
      },
      'host-x86_64-cms': {
        'debug': True,
        'bitness': 64,
        'concurrent_collector': False,
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
      'host-x86_64-cdex-fast': {
        'debug': True,
        'bitness': 64,
        'cdex_level': 'fast',
      },
    },
    # TODO: Remove device names.
    'target': {
      'angler-armv7-ndebug': {
        'serial': '84B7N16728001219',
        'device': 'angler-armv7',
        'debug': False,
      },
      'angler-armv7-debug': {
        'serial': '84B7N15B03000729',
        'device': 'angler-armv7',
        'debug': True,
      },
      'volantis-armv7-poison-debug': {
        'serial': 'FA7BN1A04406',
        'device': 'volantis-armv7',
        'debug': True,
        'heap_poisoning': True
      },
      'volantis-armv8-poison-ndebug': {
        'serial': 'FA7BN1A04412',
        'device': 'volantis-armv8',
        'debug': False,
        'heap_poisoning': True,
      },
      'volantis-armv8-poison-debug': {
        'serial': 'FA7BN1A04433',
        'device': 'volantis-armv8',
        'debug': True,
        'heap_poisoning': True
      },
      'fugu-ndebug': {
        'serial': '0BCDB85D',
        'device': 'fugu',
        'debug': False,
      },
      'fugu-debug': {
        'serial': 'E6B27F19',
        'device': 'fugu',
        'debug': True,
      },
      'angler-armv7-cms': {
        'serial': '84B7N15B03000329',
        'device': 'angler-armv7',
        'debug': True,
        'concurrent_collector': False,
      },
      'angler-armv8-ndebug': {
        'serial': '84B7N16728001299',
        'device': 'angler-armv8',
        'debug': False,
      },
      'angler-armv8-debug': {
        'serial': '84B7N15B03000660',
        'device': 'angler-armv8',
        'debug': True,
      },
      'angler-armv8-cms': {
        'serial': '84B7N15B03000641',
        'device': 'angler-armv8',
        'debug': True,
        'concurrent_collector': False,
      },
      'bullhead-armv8-gcstress-ndebug': {
        'serial': '00c5a4683f54164f',
        'device': 'bullhead-armv8',
        'debug': False,
        'gcstress': True,
        'concurrent_collector': True,
      },
      'bullhead-armv8-gcstress-debug': {
        'serial': '01e0c128ccf732ca',
        'device': 'bullhead-armv8',
        'debug': True,
        'gcstress': True,
        'concurrent_collector': True,
      },
      'bullhead-armv7-gcstress-ndebug': {
        'serial': '02022c7ec2834126',
        'device': 'bullhead-armv7',
        'debug': False,
        'gcstress': True,
        'concurrent_collector': True,
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

    'valgrind': {
      'host-x86_64-valgrind': {
        'bitness': 64
      },
    },
  },
}

_CONFIG_DISPATCH_MAP = {
  'client.art': {
    'x86': setup_host_x86,
    'target': setup_target,
    'aosp': setup_aosp_builder,
    'valgrind': setup_valgrind_runner,
  }
}

def RunSteps(api):
  if api.properties['mastername'] not in _CONFIG_MAP: # pragma: no cover
    error = "Master not found in recipe's local config!"
    raise KeyError(error)

  builder_found = False
  config = _CONFIG_MAP[api.properties['mastername']]
  for builder_type in config:
    if api.properties['buildername'] in config[builder_type]:
      builder_found = True
      builder_dict = config[builder_type][api.properties['buildername']]
      _CONFIG_DISPATCH_MAP[api.properties['mastername']][builder_type](api,
          **builder_dict)
      break

  if not builder_found: # pragma: no cover
    error = "Builder not found in recipe's local config!"
    raise KeyError(error)

def GenTests(api):
  for mastername, config_dict in _CONFIG_MAP.iteritems():
    for builders in config_dict.values():
      for buildername in builders:
        for clb in (None, True):
          yield (
              api.test("%s__ON__%s__%s" % (buildername, mastername,
                ("" if clb else "no") + "clobber")) +
              api.properties(
                mastername=mastername,
                buildername=buildername,
                bot_id='TestSlave',
                # Buildbot uses clobber='' to mean clobber, however
                # api.properties(clobber=None) will set clobber=None!
                # so we have to not even mention it to avoid our
                # 'clobber' in api.properties logic triggering above.
              ) + (api.properties(clobber='') if clb else api.properties())
            )
  yield (
      api.test('x86_32_test_failure') +
      api.properties(
        mastername='client.art',
        buildername='host-x86-ndebug',
        bot_id='TestSlave',
      ) +
      api.step_data('test jdwp aot', retcode=1))
  yield (
      api.test('target_angler_setup_failure') +
      api.properties(
        mastername='client.art',
        buildername='angler-armv7-ndebug',
        bot_id='TestSlave',
      )
      + api.step_data('setup device', retcode=1))
  yield (
      api.test('target_angler_test_failure') +
      api.properties(
        mastername='client.art',
        buildername='angler-armv7-ndebug',
        bot_id='TestSlave',
      ) +
      api.step_data('test jdwp aot', retcode=1))
  yield (
      api.test('target_angler_device_cleanup_failure') +
      api.properties(
        mastername='client.art',
        buildername='angler-armv7-ndebug',
        bot_id='TestSlave',
      ) +
      api.step_data('device cleanup', retcode=1))
  yield (
      api.test('aosp_x86_build_failure') +
      api.properties(
        mastername='client.art',
        buildername='aosp-builder-cms',
        bot_id='TestSlave',
      ) +
      api.step_data('build x86', retcode=1))
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
