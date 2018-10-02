# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from contextlib import contextmanager

DEPS = [
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'depot_tools/osx_sdk',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/python',
  'recipe_engine/step',
  'test_utils',
]


def _HasToken(buildername, token):
  # Builder names are a sequence of tokens separated by underscores.
  return '_' + token + '_' in '_' + buildername + '_'


def _GetHostToolSuffix(platform):
  if platform.is_linux:
    if platform.bits == 64:
      return 'linux64'
  elif platform.is_mac:
    return 'mac'
  elif platform.is_win:
    return 'win32'
  raise ValueError('unknown platform')  # pragma: no cover


def _GetHostExeSuffix(platform):
  if platform.is_win:
    return '.exe'
  return ''


def _WindowsCMakeWorkaround(path):
  # CMake does not allow backslashes in several path variables. It writes the
  # string out to a cmake file with configure_file() and fails to escape it
  # correctly. See https://gitlab.kitware.com/cmake/cmake/issues/16254.
  return str(path).replace('\\', '/')


def _GetHostCMakeArgs(buildername, platform, bot_utils):
  args = {}
  if platform.is_win:
    # TODO(davidben): When we've finished switching to NASM, remove this token
    # and make all bots use NASM.
    if _HasToken(buildername, 'nasm'):
      args['CMAKE_ASM_NASM_COMPILER'] = _WindowsCMakeWorkaround(
          bot_utils.join('nasm-win32.exe'))
    else:
      args['CMAKE_ASM_NASM_COMPILER'] = _WindowsCMakeWorkaround(
          bot_utils.join('yasm-win32.exe'))
    args['PERL_EXECUTABLE'] = bot_utils.join('perl-win32', 'perl', 'bin',
                                             'perl.exe')
  return args


def _AppendFlags(args, key, flags):
  if key in args:
    args[key] += ' ' + flags
  else:
    args[key] = flags


def _GetBuilderEnv(buildername):
  env = {}
  if _HasToken(buildername, 'vs2017'):
    env['GYP_MSVS_VERSION'] = '2017'
  return env


def _UsesClang(buildername):
  return any(
      _HasToken(buildername, token) for token in ('asan', 'clang', 'fuzz'))


def _UsesCustomLibCXX(buildername):
  return any(_HasToken(buildername, token) for token in ('msan', 'tsan'))


def _GetGclientVars(buildername):
  ret = {}
  if _UsesClang(buildername):
    ret['checkout_clang'] = 'True'
  if _HasToken(buildername, 'sde'):
    ret['checkout_sde'] = 'True'
  if _HasToken(buildername, 'fuzz'):
    ret['checkout_fuzzer'] = 'True'
  if _HasToken(buildername, 'nasm'):
    ret['checkout_nasm'] = 'True'
  if _UsesCustomLibCXX(buildername):
    ret['checkout_libcxx'] = 'True'
  return ret


def _GetTargetCMakeArgs(buildername, path, ninja_path, platform):
  checkout = path['checkout']
  bot_utils = checkout.join('util', 'bot')
  args = {'CMAKE_MAKE_PROGRAM': ninja_path}
  if _HasToken(buildername, 'shared'):
    args['BUILD_SHARED_LIBS'] = '1'
  if _HasToken(buildername, 'rel'):
    args['CMAKE_BUILD_TYPE'] = 'Release'
  # 32-bit builds are cross-compiled on the 64-bit bots.
  if _HasToken(buildername, 'win32') and _UsesClang(buildername):
    args['CMAKE_SYSTEM_NAME'] = 'Windows'
    args['CMAKE_SYSTEM_PROCESSOR'] = 'x86'
    _AppendFlags(args, 'CMAKE_CXX_FLAGS', '-m32 -msse2')
    _AppendFlags(args, 'CMAKE_C_FLAGS', '-m32 -msse2')
  if _HasToken(buildername, 'linux32'):
    args['CMAKE_SYSTEM_NAME'] = 'Linux'
    args['CMAKE_SYSTEM_PROCESSOR'] = 'x86'
    _AppendFlags(args, 'CMAKE_CXX_FLAGS', '-m32 -msse2')
    _AppendFlags(args, 'CMAKE_C_FLAGS', '-m32 -msse2')
    _AppendFlags(args, 'CMAKE_ASM_FLAGS', '-m32 -msse2')
  if _HasToken(buildername, 'noasm'):
    args['OPENSSL_NO_ASM'] = '1'
  if _UsesClang(buildername):
    if platform.is_win:
      args['CMAKE_C_COMPILER'] = _WindowsCMakeWorkaround(
          bot_utils.join('llvm-build', 'bin', 'clang-cl.exe'))
      args['CMAKE_CXX_COMPILER'] = _WindowsCMakeWorkaround(
          bot_utils.join('llvm-build', 'bin', 'clang-cl.exe'))
    else:
      args['CMAKE_C_COMPILER'] = bot_utils.join('llvm-build', 'bin', 'clang')
      args['CMAKE_CXX_COMPILER'] = bot_utils.join('llvm-build', 'bin',
                                                  'clang++')
  if _HasToken(buildername, 'asan'):
    args['ASAN'] = '1'
  if _HasToken(buildername, 'cfi'):
    args['CFI'] = '1'
  if _HasToken(buildername, 'msan'):
    args['MSAN'] = '1'
  if _HasToken(buildername, 'tsan'):
    args['TSAN'] = '1'
  if _UsesCustomLibCXX(buildername):
    args['USE_CUSTOM_LIBCXX'] = '1'
  if _HasToken(buildername, 'small'):
    _AppendFlags(args, 'CMAKE_CXX_FLAGS', '-DOPENSSL_SMALL=1')
    _AppendFlags(args, 'CMAKE_C_FLAGS', '-DOPENSSL_SMALL=1')
  if _HasToken(buildername, 'nothreads'):
    _AppendFlags(
        args, 'CMAKE_CXX_FLAGS',
        '-DOPENSSL_NO_THREADS_CORRUPT_MEMORY_AND_LEAK_SECRETS_IF_THREADED=1')
    _AppendFlags(
        args, 'CMAKE_C_FLAGS',
        '-DOPENSSL_NO_THREADS_CORRUPT_MEMORY_AND_LEAK_SECRETS_IF_THREADED=1')
  if _HasToken(buildername, 'android'):
    args['CMAKE_TOOLCHAIN_FILE'] = bot_utils.join(
        'android_ndk', 'build', 'cmake', 'android.toolchain.cmake')
    if _HasToken(buildername, 'arm'):
      args['ANDROID_ABI'] = 'armeabi-v7a'
      args['ANDROID_NATIVE_API_LEVEL'] = 16
    elif _HasToken(buildername, 'aarch64'):
      args['ANDROID_ABI'] = 'arm64-v8a'
      args['ANDROID_NATIVE_API_LEVEL'] = 21
  if _HasToken(buildername, 'fips'):
    args['FIPS'] = '1'
  if _HasToken(buildername, 'ios'):
    args['CMAKE_OSX_SYSROOT'] = 'iphoneos'
    args['CMAKE_OSX_ARCHITECTURES'] = 'armv7'
  if _HasToken(buildername, 'ios64'):
    args['CMAKE_OSX_SYSROOT'] = 'iphoneos'
    args['CMAKE_OSX_ARCHITECTURES'] = 'arm64'
  if _HasToken(buildername, 'fuzz'):
    args['FUZZ'] = '1'
    args['LIBFUZZER_FROM_DEPS'] = '1'
  # Pick one builder to build with the C++ runtime allowed. The default
  # configuration does not compile-check pure virtuals.
  if buildername == 'linux':
    args['BORINGSSL_ALLOW_CXX_RUNTIME'] = '1'
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
  if _HasToken(buildername, 'msan'):
    env['MSAN_SYMBOLIZER_PATH'] = bot_utils.join('llvm-build', 'bin',
                                                 'llvm-symbolizer')
  return env


def _LogFailingTests(api, step_result):
  if (step_result.test_utils.test_results.valid and
      step_result.retcode <= api.test_utils.MAX_FAILURES_EXIT_STATUS):
      failures = step_result.test_utils.test_results.unexpected_failures
      p = step_result.presentation
      p.step_text += api.test_utils.format_step_text([
        ['unexpected_failures:', failures.keys()],
      ])


@contextmanager
def _CleanupMSVC(api):
  try:
    yield
  finally:
    if api.platform.is_win:
      # cl.exe automatically starts background mspdbsrv.exe daemon which needs
      # to be manually stopped so Swarming can tidy up after itself.
      api.step('taskkill mspdbsrv',
               ['taskkill.exe', '/f', '/t', '/im', 'mspdbsrv.exe'],
               ok_ret='any')


def RunSteps(api):
  buildername = api.buildbucket.builder_name
  with api.context(
      env=_GetBuilderEnv(buildername)), api.osx_sdk('ios'), _CleanupMSVC(api):
    # Print the kernel version on Linux builders. BoringSSL is sensitive to
    # whether the kernel has getrandom support.
    if api.platform.is_linux:
      api.step('uname', ['uname', '-a'])

    # Sync and pull in everything.
    api.gclient.set_config('boringssl')
    if _HasToken(buildername, 'android'):
      api.gclient.c.target_os.add('android')
    api.gclient.c.solutions[0].custom_vars = _GetGclientVars(buildername)
    api.bot_update.ensure_checkout()
    api.gclient.runhooks()

    # Set up paths.
    bot_utils = api.path['checkout'].join('util', 'bot')
    go_env = bot_utils.join('go', 'env.py')
    adb_path = bot_utils.join('android_tools', 'sdk', 'platform-tools', 'adb')
    sde_path = bot_utils.join('sde-' + _GetHostToolSuffix(api.platform))
    build_dir = api.path['checkout'].join('build')
    runner_dir = api.path['checkout'].join('ssl', 'test', 'runner')

    # CMake is stateful, so do a clean build. BoringSSL builds quickly enough
    # that this isn't a concern.
    api.file.rmtree('clean', build_dir)
    api.file.ensure_directory('mkdir', build_dir)

    # If building with MSVC, all commands must run with an environment wrapper.
    # This is necessary both to find the toolchain and the runtime dlls. Rather
    # than copy the runtime to every directory where a binary is installed, just
    # run the tests with the toolchain prefix as well.
    msvc_prefix = _GetTargetMSVCPrefix(buildername, bot_utils)

    # Build BoringSSL itself.
    cmake = bot_utils.join('cmake-' + _GetHostToolSuffix(api.platform), 'bin',
                           'cmake' + _GetHostExeSuffix(api.platform))
    cmake_args = _GetHostCMakeArgs(buildername, api.platform, bot_utils)
    cmake_args.update(
        _GetTargetCMakeArgs(buildername, api.path, api.depot_tools.ninja_path,
                            api.platform))
    with api.context(cwd=build_dir):
      api.python(
          'cmake', go_env, msvc_prefix + [cmake, '-GNinja'] +
          ['-D%s=%s' % (k, v)
           for (k, v) in sorted(cmake_args.items())] + [api.path['checkout']])
    api.python('ninja', go_env,
               msvc_prefix + [api.depot_tools.ninja_path, '-C', build_dir])

    if _HasToken(buildername, 'compile'):
      return

    with api.step.defer_results():
      # The default Linux build may not depend on the C++ runtime. This is easy
      # to check when building shared libraries.
      if buildername == 'linux_shared':
        api.python('check imported libraries', go_env, [
            'go', 'run',
            api.path['checkout'].join('util', 'check_imported_libraries.go'),
            build_dir.join('crypto', 'libcrypto.so'),
            build_dir.join('ssl', 'libssl.so')
        ])

      with api.context(cwd=api.path['checkout']):
        api.python('check filenames', go_env, [
            'go', 'run', api.path['checkout'].join('util', 'check_filenames.go')
        ])

      env = _GetTargetEnv(buildername, bot_utils)

      # Run the unit tests.
      with api.context(cwd=api.path['checkout'], env=env):
        all_tests_args = []
        if _HasToken(buildername, 'sde'):
          all_tests_args += ['-sde', '-sde-path', sde_path.join('sde')]
        if _HasToken(buildername, 'android'):
          api.python('unit tests', go_env, [
              'go', 'run',
              api.path.join('util', 'run_android_tests.go'), '-build-dir',
              build_dir, '-adb', adb_path, '-suite', 'unit', '-all-tests-args',
              ' '.join(all_tests_args), '-json-output',
              api.test_utils.test_results()
          ])
        else:
          api.python('unit tests', go_env, msvc_prefix + [
              'go', 'run',
              api.path.join('util', 'all_tests.go'), '-json-output',
              api.test_utils.test_results()
          ] + all_tests_args)

        _LogFailingTests(api, api.step.active_result)

      # Run the SSL tests.
      if (not _HasToken(buildername, 'sde') and
          not _HasToken(buildername, 'tsan')):
        runner_args = ['-pipe']
        if _HasToken(buildername, 'fuzz'):
          runner_args += ['-fuzzer', '-shim-config', 'fuzzer_mode.json']
        # Limit the number of workers on Android and Mac, to avoid flakiness.
        # https://crbug.com/boringssl/192
        # https://crbug.com/boringssl/199
        if api.platform.is_mac or _HasToken(buildername, 'android'):
          runner_args += ['-num-workers', '1']
        if _HasToken(buildername, 'android'):
          with api.context(cwd=api.path['checkout'], env=env):
            api.python('ssl tests', go_env, [
                'go', 'run',
                api.path.join('util', 'run_android_tests.go'), '-build-dir',
                build_dir, '-adb', adb_path, '-suite', 'ssl', '-runner-args',
                ' '.join(runner_args), '-json-output',
                api.test_utils.test_results()
            ])
        else:
          with api.context(cwd=runner_dir, env=env):
            api.python(
                'ssl tests', go_env, msvc_prefix +
                ['go', 'test', '-json-output',
                 api.test_utils.test_results()] + runner_args)

        _LogFailingTests(api, api.step.active_result)


def _CIBuild(api, builder):
  return api.buildbucket.ci_build(
      project='boringssl',
      builder=builder,
      git_repo='https://boringssl.googlesource.com/boringssl')


def _TryBuild(api, builder):
  return api.buildbucket.try_build(
      project='boringssl',
      builder=builder,
      git_repo='https://boringssl.googlesource.com/boringssl')


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
    ('linux_clang_rel_msan', api.platform('linux', 64)),
    ('linux_clang_cfi', api.platform('linux', 64)),
    ('linux_fuzz', api.platform('linux', 64)),
    ('linux_fips', api.platform('linux', 64)),
    ('linux_fips_rel', api.platform('linux', 64)),
    ('linux_fips_clang', api.platform('linux', 64)),
    ('linux_fips_clang_rel', api.platform('linux', 64)),
    ('linux_fips_noasm_asan', api.platform('linux', 64)),
    ('mac', api.platform('mac', 64)),
    ('mac_small', api.platform('mac', 64)),
    ('mac_rel', api.platform('mac', 64)),
    ('win32', api.platform('win', 64)),
    ('win32_small', api.platform('win', 64)),
    ('win32_rel', api.platform('win', 64)),
    ('win32_vs2017', api.platform('win', 64)),
    ('win32_vs2017_clang', api.platform('win', 64)),
    ('win32_nasm', api.platform('win', 64)),
    ('win64', api.platform('win', 64)),
    ('win64_small', api.platform('win', 64)),
    ('win64_rel', api.platform('win', 64)),
    ('win64_vs2017', api.platform('win', 64)),
    ('win64_vs2017_clang', api.platform('win', 64)),
    ('win64_nasm', api.platform('win', 64)),
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
      _CIBuild(api, buildername) +
      api.override_step_data('unit tests',
                             api.test_utils.canned_test_output(True)) +
      api.override_step_data('ssl tests',
                             api.test_utils.canned_test_output(True))
    )

  compile_only_tests = [
    ('ios_compile', api.platform('mac', 64)),
    ('ios64_compile', api.platform('mac', 64)),
  ]
  for (buildername, host_platform) in compile_only_tests:
    yield (
      api.test(buildername) +
      host_platform +
      _CIBuild(api, buildername)
    )

  unit_test_only_tests = [
    ('linux_sde', api.platform('linux', 64)),
    ('linux32_sde', api.platform('linux', 64)),
    ('linux_clang_rel_tsan', api.platform('linux', 64)),
  ]
  for (buildername, host_platform) in unit_test_only_tests:
    yield (
      api.test(buildername) +
      host_platform +
      _CIBuild(api, buildername) +
      api.override_step_data('unit tests',
                             api.test_utils.canned_test_output(True))
    )

  yield (
    api.test('failed_imported_libraries') +
    api.platform('linux', 64) +
    _CIBuild(api, 'linux_shared') +
    api.override_step_data('check imported libraries', retcode=1) +
    api.override_step_data('unit tests',
                           api.test_utils.canned_test_output(True)) +
    api.override_step_data('ssl tests',
                           api.test_utils.canned_test_output(True))
  )

  yield (
    api.test('failed_filenames') +
    api.platform('linux', 64) +
    _CIBuild(api, 'linux') +
    api.override_step_data('check filenames', retcode=1) +
    api.override_step_data('unit tests',
                           api.test_utils.canned_test_output(True)) +
    api.override_step_data('ssl tests',
                           api.test_utils.canned_test_output(True))
  )

  yield (
    api.test('failed_unit_tests') +
    api.platform('linux', 64) +
    _CIBuild(api, 'linux') +
    api.override_step_data('unit tests',
                           api.test_utils.canned_test_output(False)) +
    api.override_step_data('ssl tests',
                           api.test_utils.canned_test_output(True))
  )

  # Test that the cleanup step works correctly with test failures.
  yield (
    api.test('failed_unit_tests_win') +
    api.platform('win', 64) +
    _CIBuild(api, 'win64') +
    api.override_step_data('unit tests',
                           api.test_utils.canned_test_output(False)) +
    api.override_step_data('ssl tests',
                           api.test_utils.canned_test_output(True))
  )

  yield (
    api.test('failed_ssl_tests') +
    api.platform('linux', 64) +
    _CIBuild(api, 'linux') +
    api.override_step_data('unit tests',
                           api.test_utils.canned_test_output(True)) +
    api.override_step_data('ssl tests',
                           api.test_utils.canned_test_output(False))
  )

  # The taskkill step may fail if mspdbsrv has already exitted. This should
  # still be accepted.
  yield (
    api.test('failed_taskkill') +
    api.platform('win', 64) +
    _CIBuild(api, 'win64') +
    api.override_step_data('unit tests',
                           api.test_utils.canned_test_output(True)) +
    api.override_step_data('ssl tests',
                           api.test_utils.canned_test_output(True)) +
    api.override_step_data('taskkill mspdbsrv', retcode=1)
  )

  yield (
    api.test('gerrit_cl') +
    api.platform('linux', 64) +
    _TryBuild(api, 'linux')
  )
