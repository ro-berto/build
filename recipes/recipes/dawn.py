# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'depot_tools/osx_sdk',
  'goma',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'recipe_engine/time',
]

from recipe_engine.recipe_api import Property

PROPERTIES = {
    'target_cpu': Property(default=None, kind=str),
    'debug': Property(default=False, kind=bool),
    'clang': Property(default=None, kind=bool),
    'gen_fuzz_corpus': Property(default=False, kind=bool)
}

DAWN_REPO = "https://dawn.googlesource.com/dawn"


def _checkout_steps(api):
  solution_path = api.path['cache'].join('builder')
  api.file.ensure_directory('init cache if not exists', solution_path)

  with api.context(cwd=solution_path):
    # Checkout dawn and its dependencies (specified in DEPS) using gclient.
    api.gclient.set_config('dawn')
    api.gclient.c.got_revision_mapping['dawn'] = 'got_revision'
    # Standalone developer dawn builds want the dawn checkout in the same
    # directory the .gclient file is in.  Bots want it in a directory called
    # 'dawn'.  To make both cases work, the dawn DEPS file pulls deps and runs
    # hooks relative to the variable "root" which is set to . by default and
    # then to 'dawn' on bots here:
    api.gclient.c.solutions[0].custom_vars = {'dawn_root': 'dawn'}
    api.bot_update.ensure_checkout()
    api.gclient.runhooks()


def _out_path(target_cpu, debug, clang, static):
  out_dir = 'debug' if debug else 'release'
  if clang:
    out_dir += '_clang'
  if target_cpu:
    out_dir += '_' + target_cpu
  if static:
    out_dir += '_static'
  else:
    out_dir += '_component'
  return out_dir


def _gn_gen_builds(api, target_cpu, debug, clang, use_goma, out_dir, static,
                   swiftshader):
  """calls 'gn gen'"""
  gn_bool = {True: 'true', False: 'false'}
  # Generate build files by GN.
  checkout = api.path['checkout']
  gn_cmd = api.depot_tools.gn_py_path

  # Prepare the arguments to pass in.
  args = [
      'is_debug=%s' % gn_bool[debug],
      'is_component_build=%s' % gn_bool[not static],
      'use_goma=%s' % gn_bool[use_goma],
      'dawn_use_swiftshader=%s' % gn_bool[swiftshader],
  ]

  if use_goma:
    api.goma.ensure_goma()
    args.append('goma_dir="%s"' % api.goma.goma_dir)

  # We run the end2end tests with SwiftShader, but the D3D12 backend,
  # though it would run zero tests, crashes on Windows 7.
  # Disable it for now.
  if swiftshader:
    args.append('dawn_enable_d3d12=false')

  if clang is not None:
    args.append('is_clang=%s' % gn_bool[clang])

  if target_cpu:
    args.append('target_cpu="%s"' % target_cpu)

  with api.context(cwd=checkout):
    api.python('gn gen', gn_cmd,
               ['--root=' + str(checkout), 'gen', '//out/' + out_dir,
                '--args=' + ' '.join(args)])


def _build_steps(api, out_dir, clang, use_goma, *targets):
  debug_path = api.path['checkout'].join('out', out_dir)
  ninja_cmd = [api.depot_tools.ninja_path, '-C', debug_path]
  if use_goma:
    ninja_cmd.extend(['-j', api.goma.recommended_goma_jobs])
  ninja_cmd.extend(targets)

  if use_goma:
    api.goma.build_with_goma(
        name='compile with ninja',
        ninja_command=ninja_cmd,
        ninja_log_outdir=debug_path,
        ninja_log_compiler='clang')
  else:
    api.step('compile with ninja', ninja_cmd)


def _run_unittests(api, out_dir):
  test_path = api.path['checkout'].join('out', out_dir, 'dawn_unittests')
  api.step('Run the Dawn unittests', [test_path])
  api.step('Run the Dawn unittests with the wire', [test_path, '--use-wire'])


def _run_tint_generator_unittests(api, out_dir):
  test_path = api.path['checkout'].join('out', out_dir, 'dawn_unittests')
  api.step('Run the Dawn unittests',
           [test_path, '--enable-toggles=use_tint_generator'])


def _run_swiftshader_end2end_tests(api, out_dir):
  test_path = api.path['checkout'].join('out', out_dir, 'dawn_end2end_tests')
  api.step('Run the Dawn end2end tests with SwiftShader',
           [test_path, '--adapter-vendor-id=0x1AE0'])


def _run_swangle_end2end_tests(api, out_dir):
  test_path = api.path['checkout'].join('out', out_dir, 'dawn_end2end_tests')
  api.step('Run the Dawn end2end tests with ANGLE/SwiftShader',
           [test_path, '--backend=opengles'])


def _generate_fuzz_corpus(api, target_cpu, debug, clang, use_goma):
  out_dir_component = _out_path(target_cpu, debug, clang, static=False)
  _gn_gen_builds(
      api,
      target_cpu,
      debug,
      clang,
      use_goma,
      out_dir_component,
      static=False,
      swiftshader=True)

  # Build the targets
  _build_steps(api, out_dir_component, clang, use_goma, 'dawn_unittests',
               'dawn_end2end_tests')

  # Collect the traces in temporary directories.
  testcase_dir = api.path['tmp_base'].join('testcases')
  hashed_testcase_dir = api.path['tmp_base'].join('hashed_testcases')

  api.file.ensure_directory('mkdir {}'.format(testcase_dir), testcase_dir)
  api.file.ensure_directory('mkdir {}'.format(hashed_testcase_dir),
                            hashed_testcase_dir)

  api.step('Trace the dawn_unittests', [
      api.path['checkout'].join('out', out_dir_component, 'dawn_unittests'),
      '--use-wire', '--wire-trace-dir={}'.format(testcase_dir)
  ])

  api.step('Trace the dawn_end2end_tests with SwiftShader', [
      api.path['checkout'].join('out', out_dir_component, 'dawn_end2end_tests'),
      '--adapter-vendor-id=0x1AE0', '--use-wire',
      '--wire-trace-dir={}'.format(testcase_dir)
  ])

  testcases = api.file.listdir('listdir {}'.format(testcase_dir), testcase_dir)

  # Hash the traces so we have a unique name per trace.
  api.python.inline(
      'Hash testcases',
      """
    import hashlib
    from shutil import copyfile
    import os
    import sys

    for arg in sys.argv[1:]:
      h = hashlib.md5(open(arg, "rb").read()).hexdigest()
      copyfile(arg, os.path.join("%s", "trace_" + h))
    """ % (hashed_testcase_dir),
      args=testcases)

  # Upload test cases to the fuzzer corpus directories
  for fuzzer_name in [
      'dawn_wire_server_and_frontend_fuzzer',
      'dawn_wire_server_and_vulkan_backend_fuzzer',
      'dawn_wire_server_and_d3d12_backend_fuzzer'
  ]:
    api.gsutil.upload(
        hashed_testcase_dir.join('*'),
        'clusterfuzz-corpus',
        'libfuzzer/{}'.format(fuzzer_name),
        args=['-r', '-n'],  # recursive, no clobber
        parallel_upload=True,
        multithreaded=True,
        name='Upload to the {} seed corpus'.format(fuzzer_name))


def RunSteps(api, target_cpu, debug, clang, gen_fuzz_corpus):
  env = {}
  if api.platform.is_win:
    env['DEPOT_TOOLS_WIN_TOOLCHAIN_ROOT'] = (
    api.path['cache'].join('win_toolchain'))

  use_goma = bool(clang or clang is None)

  with api.context(env=env):
    _checkout_steps(api)
    if gen_fuzz_corpus:
      _generate_fuzz_corpus(api, target_cpu, debug, clang, use_goma)
      return

    out_dir_static = _out_path(target_cpu, debug, clang, static=True)
    out_dir_component = _out_path(target_cpu, debug, clang, static=False)
    with api.osx_sdk('mac'):
      # Static build all targets and run unittests
      _gn_gen_builds(
          api,
          target_cpu,
          debug,
          clang,
          use_goma,
          out_dir_static,
          static=True,
          swiftshader=False)
      _build_steps(api, out_dir_static, clang, use_goma)
      _run_unittests(api, out_dir_static)
      _run_tint_generator_unittests(api, out_dir_static)

      # Component build and run dawn_end2end_tests with SwiftShader
      # When using SwiftShader a component build should be used.
      # See anglebug.com/4396.
      _gn_gen_builds(
          api,
          target_cpu,
          debug,
          clang,
          use_goma,
          out_dir_component,
          static=False,
          swiftshader=True)
      _build_steps(api, out_dir_component, clang, use_goma,
                   'dawn_end2end_tests')
      _run_swiftshader_end2end_tests(api, out_dir_component)
      _run_swangle_end2end_tests(api, out_dir_component)


def GenTests(api):
  yield api.test(
      'linux',
      api.platform('linux', 64),
      api.buildbucket.ci_build(
          project='dawn', builder='linux', git_repo=DAWN_REPO),
  )
  yield api.test(
      'linux_gcc',
      api.platform('linux', 64),
      api.properties(clang=False),
      api.buildbucket.ci_build(
          project='dawn', builder='linux', git_repo=DAWN_REPO),
  )
  yield api.test(
      'mac',
      api.platform('mac', 64),
      api.buildbucket.ci_build(
          project='dawn', builder='mac', git_repo=DAWN_REPO),
  )
  yield api.test(
      'win',
      api.platform('win', 64),
      api.buildbucket.ci_build(
          project='dawn', builder='win', git_repo=DAWN_REPO),
  )
  yield api.test(
      'win_clang',
      api.platform('win', 64),
      api.properties(clang=True),
      api.buildbucket.ci_build(
          project='dawn', builder='win', git_repo=DAWN_REPO),
  )
  yield api.test(
      'win_rel_msvc_x86',
      api.platform('win', 64),
      api.properties(clang=False, debug=False, target_cpu='x86'),
      api.buildbucket.ci_build(
          project='dawn', builder='win', git_repo=DAWN_REPO),
  )
  yield api.test(
      'linux_gen_fuzz_corpus',
      api.platform('linux', 64),
      api.properties(gen_fuzz_corpus=True),
      api.buildbucket.ci_build(
          project='dawn', builder='linux', git_repo=DAWN_REPO),
  )
