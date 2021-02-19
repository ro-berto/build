# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'builder_group',
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'depot_tools/gsutil',
    'depot_tools/osx_sdk',
    'depot_tools/tryserver',
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
    'clang': Property(default=False, kind=bool),
    'component': Property(default=False, kind=bool),
    'memory_tool': Property(default=None, kind=str),
    'msvc': Property(default=False, kind=bool),
    'rel': Property(default=False, kind=bool),
    'selected_tests_only': Property(default=False, kind=bool),
    'skia_paths': Property(default=False, kind=bool),
    'skia': Property(default=False, kind=bool),
    'skip_test': Property(default=False, kind=bool),
    'target_cpu': Property(default=None, kind=str),
    'target_os': Property(default=None, kind=str),
    'v8': Property(default=True, kind=bool),
    'xfa': Property(default=False, kind=bool),
}


def _is_goma_enabled(msvc):
  return not msvc


def _checkout_step(api, target_os):
  solution_path = api.path['cache'].join('builder')
  api.file.ensure_directory('init cache if not exists', solution_path)

  with api.context(cwd=solution_path):
    # Checkout pdfium and its dependencies (specified in DEPS) using gclient.
    api.gclient.set_config('pdfium')
    if target_os:
      api.gclient.c.target_os = {target_os}
    api.gclient.c.got_revision_mapping['pdfium'] = 'got_revision'
    update_step = api.bot_update.ensure_checkout()

    api.gclient.runhooks()
    return update_step.presentation.properties['got_revision']


def _generate_out_path(memory_tool, skia, skia_paths, xfa, v8, clang, msvc, rel,
                       component):
  out_dir = 'release' if rel else 'debug'

  if skia:
    out_dir += '_skia'
  if skia_paths:
    out_dir += '_skiapaths'
  if xfa:
    out_dir += '_xfa'
  if v8:
    out_dir += '_v8'

  if clang:
    out_dir += '_clang'
  elif msvc:
    out_dir += '_msvc'

  if component:
    out_dir += '_component'

  if memory_tool == 'asan':
    out_dir += '_asan'
  elif memory_tool == 'msan':
    out_dir += '_msan'
  elif memory_tool == 'ubsan':
    out_dir += '_ubsan'

  return out_dir


# _gn_gen_builds() calls 'gn gen' and returns a dictionary of
# the used build configuration to be used by Gold.
def _gn_gen_builds(api, memory_tool, skia, skia_paths, xfa, v8, target_cpu,
                   clang, msvc, rel, component, target_os, out_dir):
  enable_goma = _is_goma_enabled(msvc)
  if enable_goma:
    api.goma.ensure_goma()
  gn_bool = {True: 'true', False: 'false'}
  # Generate build files by GN.
  checkout = api.path['checkout']
  gn_cmd = api.depot_tools.gn_py_path

  # Prepare the arguments to pass in.
  args = [
      'is_debug=%s' % gn_bool[not rel],
      'is_component_build=%s' % gn_bool[component],
      'pdf_enable_v8=%s' % gn_bool[v8],
      'pdf_enable_xfa=%s' % gn_bool[xfa],
      'pdf_use_skia=%s' % gn_bool[skia],
      'pdf_use_skia_paths=%s' % gn_bool[skia_paths],
      'pdf_is_standalone=true',
  ]
  if enable_goma:
    args.extend([
        'use_goma=true',
        'goma_dir="%s"' % api.goma.goma_dir,
    ])
  if api.platform.is_win and not memory_tool:
    args.append('symbol_level=1')
  if api.platform.is_win:
    assert not clang or not msvc
    if clang:
      args.append('is_clang=true')
    elif msvc:
      args.append('is_clang=false')
    else:
      # Default to Clang.
      args.append('is_clang=true')
  else:
    # All other platforms already build with Clang, so no need to set it.
    assert not clang

  if memory_tool == 'asan':
    args.append('is_asan=true')
    if api.platform.is_win:
      # ASAN requires Clang. Until Clang is default on Windows for certain,
      # bots should set it explicitly.
      assert clang
      # No LSAN support.
    else:
      args.append('is_lsan=true')
  elif memory_tool == 'msan':
    assert not api.platform.is_win
    args.extend(['is_msan=true'])
  elif memory_tool == 'ubsan':
    assert not api.platform.is_win
    args.extend(['is_ubsan_security=true', 'is_ubsan_no_recover=true'])

  if target_os:
    args.append('target_os="%s"' % target_os)
  if target_cpu == 'x86':
    args.append('target_cpu="x86"')

  with api.context(cwd=checkout):
    api.python('gn gen', gn_cmd, [
        '--check', '--root=' + str(checkout), 'gen', '//out/' + out_dir,
        '--args=' + ' '.join(args)
    ])

  # convert the arguments to key values pairs for gold usage.
  return _gold_build_config(args)


def _build_steps(api, clang, msvc, out_dir):
  enable_goma = _is_goma_enabled(msvc)
  debug_path = api.path['checkout'].join('out', out_dir)
  ninja_cmd = [api.depot_tools.ninja_path, '-C', debug_path]
  if enable_goma:
    ninja_cmd.extend(['-j', api.goma.recommended_goma_jobs])
  ninja_cmd.append('pdfium_all')

  if enable_goma:
    api.goma.build_with_goma(
        name='compile with ninja',
        ninja_command=ninja_cmd,
        ninja_log_outdir=debug_path,
        ninja_log_compiler='clang' if clang else 'unknown')
  else:
    api.step('compile with ninja', ninja_cmd)


# TODO(https://crbug.com/pdfium/11): |selected_tests_only| currently only
# enables unit tests and embedder tests for trybots. Remove this parameter
# once all the tests can pass with Skia/SkiaPaths enabled.
# _run_tests() runs the tests and uploads the results to Gold.
def _run_tests(api, memory_tool, v8, xfa, out_dir, build_config, revision,
               selected_tests_only):
  env = {}
  COMMON_SANITIZER_OPTIONS = ['allocator_may_return_null=1']
  COMMON_UNIX_SANITIZER_OPTIONS = [
      'detect_leaks=1',
      'symbolize=1',
      # Note: deliberate lack of comma.
      'external_symbolizer_path='
      'third_party/llvm-build/Release+Asserts/bin/llvm-symbolizer',
  ]
  if memory_tool == 'asan':
    options = []
    options.extend(COMMON_SANITIZER_OPTIONS)
    if not api.platform.is_win:
      options.extend(COMMON_UNIX_SANITIZER_OPTIONS)
    env.update({'ASAN_OPTIONS': ' '.join(options)})
  elif memory_tool == 'msan':
    assert not api.platform.is_win
    options = []
    options.extend(COMMON_SANITIZER_OPTIONS)
    options.extend(COMMON_UNIX_SANITIZER_OPTIONS)
    env.update({'MSAN_OPTIONS': ' '.join(options)})
  elif memory_tool == 'ubsan':
    assert not api.platform.is_win
    options = []
    options.extend(COMMON_SANITIZER_OPTIONS)
    options.extend(COMMON_UNIX_SANITIZER_OPTIONS)
    env.update({'UBSAN_OPTIONS': ' '.join(options)})

  # This variable swallows the exception raised by a failed step. The step
  # will still show up as failed, but processing will continue.
  test_exception = None

  unittests_path = str(api.path['checkout'].join('out', out_dir,
                                                 'pdfium_unittests'))
  if api.platform.is_win:
    unittests_path += '.exe'
  with api.context(cwd=api.path['checkout'], env=env):
    try:
      api.step('unittests', [unittests_path])
    except api.step.StepFailure as e:
      test_exception = e

  embeddertests_path = str(api.path['checkout'].join('out', out_dir,
                                                     'pdfium_embeddertests'))
  if api.platform.is_win:
    embeddertests_path += '.exe'
  with api.context(cwd=api.path['checkout'], env=env):
    try:
      api.step('embeddertests', [embeddertests_path])
    except api.step.StepFailure as e:
      test_exception = e

  if selected_tests_only:
    if test_exception:
      raise test_exception  # pylint: disable=E0702
    return

  script_args = ['--build-dir', api.path.join('out', out_dir)]

  # Add the arguments needed to upload the resulting images.
  gold_output_dir = api.path['checkout'].join('out', out_dir, 'gold_output')
  gold_props = _get_gold_props(api, build_config, revision)
  script_args.extend([
      '--gold_properties',
      gold_props,
      '--gold_output_dir',
      gold_output_dir,
  ])

  if v8:
    javascript_path = str(api.path['checkout'].join('testing', 'tools',
                                                    'run_javascript_tests.py'))
    with api.context(cwd=api.path['checkout'], env=env):
      additional_args = _get_modifiable_script_args(api, build_config)
      try:
        api.python('javascript tests', javascript_path,
                   script_args + additional_args)
      except api.step.StepFailure as e:
        test_exception = e

      additional_args = _get_modifiable_script_args(
          api, build_config, javascript_disabled=True)
      try:
        api.python('javascript tests (javascript disabled)', javascript_path,
                   script_args + additional_args)
      except api.step.StepFailure as e:
        test_exception = e

      if xfa:
        additional_args = _get_modifiable_script_args(
            api, build_config, xfa_disabled=True)
        try:
          api.python('javascript tests (xfa disabled)', javascript_path,
                     script_args + additional_args)
        except api.step.StepFailure as e:
          test_exception = e

  pixel_tests_path = str(api.path['checkout'].join('testing', 'tools',
                                                   'run_pixel_tests.py'))
  with api.context(cwd=api.path['checkout'], env=env):
    additional_args = _get_modifiable_script_args(api, build_config)
    try:
      api.python('pixel tests', pixel_tests_path, script_args + additional_args)
    except api.step.StepFailure as e:
      test_exception = e

  if v8:
    with api.context(cwd=api.path['checkout'], env=env):
      additional_args = _get_modifiable_script_args(
          api, build_config, javascript_disabled=True)
      try:
        api.python('pixel tests (javascript disabled)', pixel_tests_path,
                   script_args + additional_args)
      except api.step.StepFailure as e:
        test_exception = e

    if xfa:
      with api.context(cwd=api.path['checkout'], env=env):
        additional_args = _get_modifiable_script_args(
            api, build_config, xfa_disabled=True)
        try:
          api.python('pixel tests (xfa disabled)', pixel_tests_path,
                     script_args + additional_args)
        except api.step.StepFailure as e:
          test_exception = e

  corpus_tests_path = str(api.path['checkout'].join('testing', 'tools',
                                                    'run_corpus_tests.py'))
  with api.context(cwd=api.path['checkout'], env=env):
    additional_args = _get_modifiable_script_args(api, build_config)
    try:
      api.python('corpus tests', corpus_tests_path,
                 script_args + additional_args)
    except api.step.StepFailure as e:
      test_exception = e

  if v8:
    with api.context(cwd=api.path['checkout'], env=env):
      additional_args = _get_modifiable_script_args(
          api, build_config, javascript_disabled=True)
      try:
        api.python('corpus tests (javascript disabled)', corpus_tests_path,
                   script_args + additional_args)
      except api.step.StepFailure as e:
        test_exception = e

    if xfa:
      with api.context(cwd=api.path['checkout'], env=env):
        additional_args = _get_modifiable_script_args(
            api, build_config, xfa_disabled=True)
        try:
          api.python('corpus tests (xfa disabled)', corpus_tests_path,
                     script_args + additional_args)
        except api.step.StepFailure as e:
          test_exception = e

  if test_exception:
    raise test_exception  # pylint: disable=E0702


def _get_gold_props(api, build_config, revision):
  """Get the --gold_properties parameter value to be passed
  to the testing call to generate the dm.json file expected
  by Gold and to upload the generated images.
  The string can be passed directly into run_corpus_tests.py.
  """
  builder_name = api.m.buildbucket.builder_name.strip()
  props = [
      'gitHash',
      revision,
      'master',
      api.builder_group.for_current,
      'builder',
      builder_name,
      'build_number',
      str(api.m.buildbucket.build.number),
  ]

  # Add the trybot information if this is a trybot run.
  if api.m.tryserver.gerrit_change:
    props.extend([
        'issue',
        str(api.m.tryserver.gerrit_change.change),
        'patchset',
        str(api.m.tryserver.gerrit_change.patchset),
        'patch_storage',
        'gerrit',
        'buildbucket_build_id',
        str(api.buildbucket.build.id),
    ])

  return ' '.join(props)


def _get_modifiable_script_args(api,
                                build_config,
                                javascript_disabled=False,
                                xfa_disabled=False):
  """Construct and get the additional arguments for
  run_corpus_tests.py that can be modified based on whether
  javascript is disabled.
  Returns a list that can be concatenated with the other script
  arguments.
  """

  # Add the os from the builder name to the set of unique identifers.
  keys = build_config.copy()
  builder_name = api.m.buildbucket.builder_name.strip()
  keys['os'] = builder_name.split('_')[0]
  keys['javascript_runtime'] = 'disabled' if (
      build_config['v8'] == 'false' or javascript_disabled) else 'enabled'
  keys['xfa_runtime'] = 'disabled' if (build_config['xfa'] == 'false' or
                                       javascript_disabled or
                                       xfa_disabled) else 'enabled'

  additional_args = ['--gold_key', _dict_to_str(keys)]
  if javascript_disabled:
    additional_args.append('--disable-javascript')
  if xfa_disabled:
    additional_args.append('--disable-xfa')

  return additional_args


def _dict_to_str(props):
  """Returns the given dictionary as a string of space
     separated key/value pairs sorted by keys.
  """
  ret = []
  for k in sorted(props.keys()):
    ret += [k, props[k]]
  return ' '.join(ret)


def _gold_build_config(args):
  """Extracts key value pairs from the arguments handed to 'gn gen'
  and returns them as a dictionary. Since these are used as
  parameters in Gold we strip common prefixes and disregard
  some arguments. i.e. 'use_goma' since we don't care about how
  a binary was built.  Only arguments that follow the
  'key=value' pattern are considered.
  """
  exclude_list = ['use_goma', 'goma_dir', 'use_sysroot', 'is_component_build']
  strip_prefixes = ['is_', 'pdf_enable_', 'pdf_use_', 'pdf_']
  build_config = {}
  for arg in args:
    # Catch multiple k/v pairs separated by spaces.
    parts = arg.split()
    for p in parts:
      kv = [x.strip() for x in p.split('=')]
      if len(kv) == 2:
        k, v = kv
        if k not in exclude_list:
          for prefix in strip_prefixes:
            if k.startswith(prefix):
              k = k[len(prefix):]
              break
          build_config[k] = v
  return build_config


def _gen_ci_build(api, builder):
  return api.buildbucket.ci_build(
      project='pdfium',
      builder=builder,
      build_number=1234,
      git_repo='https://pdfium.googlesource.com/pdfium',
  )


def RunSteps(api, memory_tool, skia, skia_paths, xfa, v8, target_cpu, clang,
             msvc, rel, component, skip_test, target_os, selected_tests_only):
  revision = _checkout_step(api, target_os)

  out_dir = _generate_out_path(memory_tool, skia, skia_paths, xfa, v8, clang,
                               msvc, rel, component)

  with api.osx_sdk('mac'):
    build_config = _gn_gen_builds(api, memory_tool, skia, skia_paths, xfa, v8,
                                  target_cpu, clang, msvc, rel, component,
                                  target_os, out_dir)
    _build_steps(api, clang, msvc, out_dir)

    if skip_test:
      return

    _run_tests(api, memory_tool, v8, xfa, out_dir, build_config, revision,
               selected_tests_only)


def GenTests(api):
  yield api.test(
      'win',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_slave'),
      _gen_ci_build(api, 'windows'),
  )
  yield api.test(
      'linux',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_slave'),
      _gen_ci_build(api, 'linux'),
  )
  yield api.test(
      'mac',
      api.platform('mac', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_slave'),
      _gen_ci_build(api, 'mac'),
  )

  yield api.test(
      'win_no_v8',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(v8=False, bot_id='test_slave'),
      _gen_ci_build(api, 'windows_no_v8'),
  )
  yield api.test(
      'linux_no_v8',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(v8=False, bot_id='test_slave'),
      _gen_ci_build(api, 'linux_no_v8'),
  )
  yield api.test(
      'mac_no_v8',
      api.platform('mac', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(v8=False, bot_id='test_slave'),
      _gen_ci_build(api, 'mac_no_v8'),
  )

  yield api.test(
      'win_component',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(component=True, xfa=True, bot_id='test_slave'),
      _gen_ci_build(api, 'win_component'),
  )

  yield api.test(
      'win_skia',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          skia=True, xfa=True, selected_tests_only=True, bot_id='test_slave'),
      _gen_ci_build(api, 'windows_skia'),
  )

  yield api.test(
      'win_skia_paths',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          skia_paths=True,
          xfa=True,
          selected_tests_only=True,
          bot_id='test_slave'),
      _gen_ci_build(api, 'windows_skia_paths'),
  )

  yield api.test(
      'win_xfa_32',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, target_cpu='x86', bot_id='test_slave'),
      _gen_ci_build(api, 'windows_xfa_32'),
  )

  yield api.test(
      'win_xfa',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, bot_id='test_slave'),
      _gen_ci_build(api, 'windows_xfa'),
  )

  yield api.test(
      'win_xfa_rel',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, rel=True, bot_id='test_slave'),
      _gen_ci_build(api, 'windows_xfa_rel'),
  )

  yield api.test(
      'win_xfa_msvc_32',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          xfa=True, msvc=True, target_cpu='x86', bot_id='test_slave'),
      _gen_ci_build(api, 'windows_xfa_msvc_32'),
  )

  yield api.test(
      'win_xfa_msvc',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, msvc=True, bot_id='test_slave'),
      _gen_ci_build(api, 'windows_xfa_msvc'),
  )

  yield api.test(
      'linux_component',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(component=True, xfa=True, bot_id='test_slave'),
      _gen_ci_build(api, 'linux_component'),
  )

  yield api.test(
      'linux_skia',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          skia=True, xfa=True, selected_tests_only=True, bot_id='test_slave'),
      _gen_ci_build(api, 'linux_skia'),
  )

  yield api.test(
      'linux_skia_paths',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          skia_paths=True,
          xfa=True,
          selected_tests_only=True,
          bot_id='test_slave'),
      _gen_ci_build(api, 'linux_skia_paths'),
  )

  yield api.test(
      'linux_xfa',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, bot_id='test_slave'),
      _gen_ci_build(api, 'linux_xfa'),
  )

  yield api.test(
      'linux_xfa_rel',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, rel=True, bot_id='test_slave'),
      _gen_ci_build(api, 'linux_xfa_rel'),
  )

  yield api.test(
      'mac_component',
      api.platform('mac', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(component=True, xfa=True, bot_id='test_slave'),
      _gen_ci_build(api, 'mac_component'),
  )

  yield api.test(
      'mac_skia',
      api.platform('mac', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          skia=True, xfa=True, selected_tests_only=True, bot_id='test_slave'),
      _gen_ci_build(api, 'mac_skia'),
  )

  yield api.test(
      'mac_skia_paths',
      api.platform('mac', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          skia_paths=True,
          xfa=True,
          selected_tests_only=True,
          bot_id='test_slave'),
      _gen_ci_build(api, 'mac_skia_paths'),
  )

  yield api.test(
      'mac_xfa',
      api.platform('mac', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, bot_id='test_slave'),
      _gen_ci_build(api, 'mac_xfa'),
  )

  yield api.test(
      'mac_xfa_rel',
      api.platform('mac', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, rel=True, bot_id='test_slave'),
      _gen_ci_build(api, 'mac_xfa_rel'),
  )

  yield api.test(
      'linux_asan_lsan',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(memory_tool='asan', bot_id='test_slave'),
      _gen_ci_build(api, 'linux_asan_lsan'),
  )

  yield api.test(
      'linux_msan',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(memory_tool='msan', rel=True, bot_id='test_slave'),
      _gen_ci_build(api, 'linux_msan'),
  )

  yield api.test(
      'linux_ubsan',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(memory_tool='ubsan', rel=True, bot_id='test_slave'),
      _gen_ci_build(api, 'linux_ubsan'),
  )

  yield api.test(
      'linux_xfa_asan_lsan',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(memory_tool='asan', xfa=True, bot_id='test_slave'),
      _gen_ci_build(api, 'linux_xfa_asan_lsan'),
  )

  yield api.test(
      'linux_xfa_msan',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          memory_tool='msan', rel=True, xfa=True, bot_id='test_slave'),
      _gen_ci_build(api, 'linux_xfa_msan'),
  )

  yield api.test(
      'linux_xfa_ubsan',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          memory_tool='ubsan', rel=True, xfa=True, bot_id='test_slave'),
      _gen_ci_build(api, 'linux_xfa_ubsan'),
  )

  yield api.test(
      'win_asan',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          clang=True, memory_tool='asan', rel=True, bot_id='test_slave'),
      _gen_ci_build(api, 'windows_asan'),
  )

  yield api.test(
      'win_xfa_asan',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          clang=True,
          memory_tool='asan',
          rel=True,
          xfa=True,
          bot_id='test_slave'),
      _gen_ci_build(api, 'windows_xfa_asan'),
  )

  yield api.test(
      'try-linux-gerrit_xfa_asan_lsan',
      api.buildbucket.try_build(
          project='pdfium', builder='linux_xfa_asan_lsan', build_number=1234),
      api.platform('linux', 64),
      api.builder_group.for_current('tryserver.client.pdfium'),
      api.properties(xfa=True, memory_tool='asan'),
  )

  yield api.test(
      'android',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_slave', target_os='android', skip_test=True),
      _gen_ci_build(api, 'android'),
  )

  yield api.test(
      'fail-unittests',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_slave'),
      _gen_ci_build(api, 'linux'),
      api.step_data('unittests', retcode=1),
  )

  yield api.test(
      'fail-unittests-selected-tests-only',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_slave', selected_tests_only=True),
      _gen_ci_build(api, 'linux'),
      api.step_data('unittests', retcode=1),
  )

  yield api.test(
      'fail-embeddertests',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_slave'),
      _gen_ci_build(api, 'linux'),
      api.step_data('embeddertests', retcode=1),
  )

  yield api.test(
      'fail-embeddertests-selected-tests-only',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_slave', selected_tests_only=True),
      _gen_ci_build(api, 'linux'),
      api.step_data('embeddertests', retcode=1),
  )

  yield api.test(
      'fail-javascript-tests',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_slave'),
      _gen_ci_build(api, 'linux'),
      api.step_data('javascript tests', retcode=1),
  )

  yield api.test(
      'fail-javascript-tests-javascript-disabled',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_slave'),
      _gen_ci_build(api, 'linux'),
      api.step_data('javascript tests (javascript disabled)', retcode=1),
  )

  yield api.test(
      'fail-javascript-tests-xfa-disabled',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, bot_id='test_slave'),
      _gen_ci_build(api, 'linux'),
      api.step_data('javascript tests (xfa disabled)', retcode=1),
  )

  yield api.test(
      'fail-pixel-tests',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_slave'),
      _gen_ci_build(api, 'linux'),
      api.step_data('pixel tests', retcode=1),
  )

  yield api.test(
      'fail-pixel-tests-javascript-disabled',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_slave'),
      _gen_ci_build(api, 'linux'),
      api.step_data('pixel tests (javascript disabled)', retcode=1),
  )

  yield api.test(
      'fail-pixel-tests-xfa-disabled',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, bot_id='test_slave'),
      _gen_ci_build(api, 'linux'),
      api.step_data('pixel tests (xfa disabled)', retcode=1),
  )

  yield api.test(
      'fail-corpus-tests',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_slave'),
      _gen_ci_build(api, 'linux'),
      api.step_data('corpus tests', retcode=1),
  )

  yield api.test(
      'fail-corpus-tests-javascript-disabled',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_slave'),
      _gen_ci_build(api, 'linux'),
      api.step_data('corpus tests (javascript disabled)', retcode=1),
  )

  yield api.test(
      'fail-corpus-tests-xfa-disabled',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, bot_id='test_slave'),
      _gen_ci_build(api, 'linux'),
      api.step_data('corpus tests (xfa disabled)', retcode=1),
  )
