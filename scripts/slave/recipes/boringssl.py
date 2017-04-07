# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property

DEPS = [
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'file',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/shutil',
  'recipe_engine/step',
  'test_utils',
]


def _GetHostToolSuffix(platform):
  if platform.is_linux:
    if platform.bits == 64:
      return 'linux64'
  elif platform.is_mac:
    return 'mac'
  elif platform.is_win:
    return 'win32'
  # TODO(davidben): Add other host platforms as needed.


def _GetHostExeSuffix(platform):
  if platform.is_win:
    return '.exe'
  return ''


def _GetHostCMakeArgs(platform, bot_utils):
  args = {}
  if platform.is_win:
    # CMake does not allow backslashes in this variable. It writes the string
    # out to a cmake file with configure_file() and fails to escape it
    # correctly.
    # TODO(davidben): Fix the bug in CMake upstream and remove this workaround.
    args['CMAKE_ASM_NASM_COMPILER'] = \
        str(bot_utils.join('yasm-win32.exe')).replace('\\', '/')
    args['PERL_EXECUTABLE'] = bot_utils.join('perl-win32', 'perl', 'bin',
                                             'perl.exe')
  return args


def _HasToken(buildername, token):
  # Builder names are a sequence of tokens separated by underscores.
  return '_' + token + '_' in '_' + buildername + '_'


def _AppendFlags(args, key, flags):
  if key in args:
    args[key] += ' ' + flags
  else:
    args[key] = flags


def _GetTargetCMakeArgs(buildername, checkout, ninja_path):
  bot_utils = checkout.join('util', 'bot')
  args = {'CMAKE_MAKE_PROGRAM': ninja_path}
  if _HasToken(buildername, 'shared'):
    args['BUILD_SHARED_LIBS'] = '1'
  if _HasToken(buildername, 'rel'):
    args['CMAKE_BUILD_TYPE'] = 'Release'
  if _HasToken(buildername, 'linux32'):
    # 32-bit Linux is cross-compiled on the 64-bit Linux bot.
    args['CMAKE_SYSTEM_NAME'] = 'Linux'
    args['CMAKE_SYSTEM_PROCESSOR'] = 'x86'
    _AppendFlags(args, 'CMAKE_CXX_FLAGS', '-m32 -msse2')
    _AppendFlags(args, 'CMAKE_C_FLAGS', '-m32 -msse2')
    _AppendFlags(args, 'CMAKE_ASM_FLAGS', '-m32 -msse2')
  if _HasToken(buildername, 'noasm'):
    args['OPENSSL_NO_ASM'] = '1'
  if _HasToken(buildername, 'asan') or _HasToken(buildername, 'clang'):
    args['CMAKE_C_COMPILER'] = bot_utils.join('llvm-build', 'bin', 'clang')
    args['CMAKE_CXX_COMPILER'] = bot_utils.join('llvm-build', 'bin', 'clang++')
  if _HasToken(buildername, 'asan'):
    args['ASAN'] = '1'
  if _HasToken(buildername, 'small'):
    _AppendFlags(args, 'CMAKE_CXX_FLAGS', '-DOPENSSL_SMALL=1')
    _AppendFlags(args, 'CMAKE_C_FLAGS', '-DOPENSSL_SMALL=1')
  if _HasToken(buildername, 'nothreads'):
    _AppendFlags(args, 'CMAKE_CXX_FLAGS', '-DOPENSSL_NO_THREADS=1')
    _AppendFlags(args, 'CMAKE_C_FLAGS', '-DOPENSSL_NO_THREADS=1')
  if _HasToken(buildername, 'android'):
    args['CMAKE_TOOLCHAIN_FILE'] = checkout.join('third_party', 'android-cmake',
                                                 'android.toolchain.cmake')
    args['ANDROID_NDK'] = bot_utils.join('android_tools', 'ndk')
    if _HasToken(buildername, 'arm'):
      args['ANDROID_ABI'] = 'armeabi-v7a'
      args['ANDROID_NATIVE_API_LEVEL'] = 16
    elif _HasToken(buildername, 'aarch64'):
      args['ANDROID_ABI'] = 'arm64-v8a'
      args['ANDROID_NATIVE_API_LEVEL'] = 21
  if _HasToken(buildername, 'fips'):
    args['FIPS'] = '1'
  return args


def _GetTargetMSVCPrefix(buildername, bot_utils):
  if _HasToken(buildername, 'win32'):
    return ['python', bot_utils.join('vs_env.py'), 'x86']
  if _HasToken(buildername, 'win64'):
    return ['python', bot_utils.join('vs_env.py'), 'x64']
  return []


def _GetTargetEnv(buildername, bot_utils):
  env = {}
  if _HasToken(buildername, 'asan'):
    env['ASAN_OPTIONS'] = 'detect_stack_use_after_return=1'
    env['ASAN_SYMBOLIZER_PATH'] = bot_utils.join('llvm-build', 'bin',
                                                 'llvm-symbolizer')
  return env


def _LogFailingTests(api, deferred):
  if not deferred.is_ok:
    error = deferred.get_error()
    if hasattr(error.result, 'test_utils'):
      r = error.result.test_utils.test_results
      p = error.result.presentation
      p.step_text += api.test_utils.format_step_text([
        ['unexpected_failures:', r.unexpected_failures.keys()],
      ])


PROPERTIES = {
  'buildername': Property(),
}


def RunSteps(api, buildername):
  # Sync and pull in everything.
  api.gclient.set_config('boringssl')
  if _HasToken(buildername, 'android'):
    api.gclient.c.target_os.add('android')
  api.bot_update.ensure_checkout()
  api.gclient.runhooks()

  # Set up paths.
  bot_utils = api.path['checkout'].join('util', 'bot')
  go_env = bot_utils.join('go', 'env.py')
  adb_path = bot_utils.join('android_tools', 'sdk', 'platform-tools', 'adb')
  build_dir = api.path['checkout'].join('build')
  runner_dir = api.path['checkout'].join('ssl', 'test', 'runner')

  # CMake is stateful, so do a clean build. BoringSSL builds quickly enough that
  # this isn't a concern.
  api.shutil.rmtree(build_dir, name='clean')
  api.file.makedirs('mkdir', build_dir)

  # If building with MSVC, all commands must run with an environment wrapper.
  # This is necessary both to find the toolchain and the runtime dlls. Rather
  # than copy the runtime to every directory where a binary is installed, just
  # run the tests with the toolchain prefix as well.
  msvc_prefix = _GetTargetMSVCPrefix(buildername, bot_utils)

  # Build BoringSSL itself.
  cmake = bot_utils.join('cmake-' + _GetHostToolSuffix(api.platform), 'bin',
                         'cmake' + _GetHostExeSuffix(api.platform))
  cmake_args = _GetHostCMakeArgs(api.platform, bot_utils)
  cmake_args.update(_GetTargetCMakeArgs(buildername, api.path['checkout'],
                                        api.depot_tools.ninja_path))
  with api.step.context({'cwd': build_dir}):
    api.python('cmake', go_env,
               msvc_prefix + [cmake, '-GNinja'] +
               ['-D%s=%s' % (k, v) for (k, v) in sorted(cmake_args.items())] +
               [api.path['checkout']])
  api.python('ninja', go_env,
             msvc_prefix + [api.depot_tools.ninja_path, '-C', build_dir])

  with api.step.defer_results():
    env = _GetTargetEnv(buildername, bot_utils)

    # Run the unit tests.
    with api.step.context({'cwd': api.path['checkout'], 'env': env}):
      if _HasToken(buildername, 'android'):
        deferred = api.python('unit tests', go_env,
                              ['go', 'run',
                               api.path.join('util', 'run_android_tests.go'),
                               '-build-dir', build_dir,
                               '-adb', adb_path,
                               '-suite', 'unit',
                               '-json-output', api.test_utils.test_results()])
      else:
        deferred = api.python('unit tests', go_env,
                              msvc_prefix + ['go', 'run',
                                             api.path.join('util',
                                                           'all_tests.go'),
                                             '-json-output',
                                             api.test_utils.test_results()])
    _LogFailingTests(api, deferred)

    # Run the SSL tests.
    if _HasToken(buildername, 'android'):
      with api.step.context({'cwd': api.path['checkout'], 'env': env}):
        deferred = api.python('ssl tests', go_env,
                              ['go', 'run',
                               api.path.join('util', 'run_android_tests.go'),
                               '-build-dir', build_dir,
                               '-adb', adb_path,
                               '-suite', 'ssl',
                               '-runner-args', '-pipe',
                               '-json-output', api.test_utils.test_results()])
    else:
      with api.step.context({'cwd': runner_dir, 'env': env}):
        deferred = api.python('ssl tests', go_env,
                              msvc_prefix + ['go', 'test', '-pipe',
                                             '-json-output',
                                             api.test_utils.test_results()])
    _LogFailingTests(api, deferred)


def GenTests(api):
  tests = [
    # To ensure full test coverage, add a test for each builder configuration.
    ('linux', api.platform('linux', 64)),
    ('linux_shared', api.platform('linux', 64)),
    ('linux32', api.platform('linux', 64)),
    ('linux_noasm_asan', api.platform('linux', 64)),
    ('linux_small', api.platform('linux', 64)),
    ('linux_nothreads', api.platform('linux', 64)),
    ('linux_rel', api.platform('linux', 64)),
    ('linux32_rel', api.platform('linux', 64)),
    ('linux_clang_rel', api.platform('linux', 64)),
    ('linux_fips', api.platform('linux', 64)),
    ('linux_fips_rel', api.platform('linux', 64)),
    ('linux_fips_clang', api.platform('linux', 64)),
    ('linux_fips_clang_rel', api.platform('linux', 64)),
    ('mac', api.platform('mac', 64)),
    ('mac_small', api.platform('mac', 64)),
    ('mac_rel', api.platform('mac', 64)),
    ('win32', api.platform('win', 64)),
    ('win32_small', api.platform('win', 64)),
    ('win32_rel', api.platform('win', 64)),
    ('win64', api.platform('win', 64)),
    ('win64_small', api.platform('win', 64)),
    ('win64_rel', api.platform('win', 64)),
    ('android_arm', api.platform('linux', 64)),
    ('android_arm_rel', api.platform('linux', 64)),
    ('android_aarch64', api.platform('linux', 64)),
    ('android_aarch64_rel', api.platform('linux', 64)),
    # This is not a builder configuration, but it ensures _AppendFlags handles
    # appending to CMAKE_CXX_FLAGS when there is already a value in there.
    ('linux_nothreads_small', api.platform('linux', 64)),
  ]
  for (buildername, host_platform) in tests:
    yield (
      api.test(buildername) +
      host_platform +
      api.properties.generic(mastername='client.boringssl',
                             buildername=buildername, bot_id='bot_id') +
      api.override_step_data('unit tests',
                             api.test_utils.canned_test_output(True)) +
      api.override_step_data('ssl tests',
                             api.test_utils.canned_test_output(True))
    )

  yield (
    api.test('failed_unit_tests') +
    api.platform('linux', 64) +
    api.properties.generic(mastername='client.boringssl', buildername='linux',
                           bot_id='bot_id') +
    api.override_step_data('unit tests',
                           api.test_utils.canned_test_output(False)) +
    api.override_step_data('ssl tests',
                           api.test_utils.canned_test_output(True))
  )

  yield (
    api.test('failed_ssl_tests') +
    api.platform('linux', 64) +
    api.properties.generic(mastername='client.boringssl', buildername='linux',
                           bot_id='bot_id') +
    api.override_step_data('unit tests',
                           api.test_utils.canned_test_output(True)) +
    api.override_step_data('ssl tests',
                           api.test_utils.canned_test_output(False))
  )

  yield (
    api.test('gerrit_cl') +
    api.platform('linux', 64) +
    api.properties.tryserver(
        gerrit_project='boringssl',
        gerrit_url='https://boringssl-review.googlesource.com',
        mastername='actually-no-master', buildername='linux',
        bot_id='swarming-slave')
  )
