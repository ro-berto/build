# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Python version used to run the recipe itself.
# Separately, python command used to run the steps in the recipe.
PYTHON_CMD = ['vpython3', '-u']

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
    'recipe_engine/resultdb',
    'recipe_engine/step',
    'recipe_engine/time',
]

from dataclasses import dataclass

from recipe_engine.recipe_api import Property

PROPERTIES = {
    'clang': Property(default=False, kind=bool),
    'component': Property(default=False, kind=bool),
    'memory_tool': Property(default=None, kind=str),
    'msvc': Property(default=False, kind=bool),
    'rel': Property(default=False, kind=bool),
    'run_skia_gold': Property(default=True, kind=bool),
    'selected_tests_only': Property(default=False, kind=bool),
    'skia': Property(default=False, kind=bool),
    'skip_test': Property(default=False, kind=bool),
    'target_cpu': Property(default=None, kind=str),
    'target_os': Property(default=None, kind=str),
    'v8': Property(default=True, kind=bool),
    'xfa': Property(default=False, kind=bool),
}

# test_runner.py test types.
_CORPUS_TEST_TYPE = 'corpus'
_JAVASCRIPT_TEST_TYPE = 'javascript'
_PIXEL_TEST_TYPE = 'pixel'

# Renderer types.
_AGG_RENDERER = 'agg'
_SKIA_RENDERER = 'skia'


@dataclass
class _DefaultOption:
  """Base class for test_runner.py test options. Returns default options."""

  # The name of the option, as displayed in the test step.
  name: str = ''

  # The suffix used in test suite names, with underscores, not spaces.
  test_suite_suffix: str = ''

  # Additional command line argument to run tests with.
  additional_arg: str = ''

  # Whether this option disables JavaScript or not.
  disable_javascript: bool = False

  # Whether this option disables XFA or not.
  disable_xfa: bool = False


@dataclass
class _JavascriptDisabledOption(_DefaultOption):
  """A test_runner.py test option to disable JavaScript."""

  name: str = 'javascript disabled'
  test_suite_suffix: str = 'javascript_disabled'
  additional_arg: str = '--disable-javascript'
  disable_javascript: bool = True


@dataclass
class _XfaDisabledOption(_DefaultOption):
  """A test_runner.py test option to disable XFA."""

  name: str = 'xfa disabled'
  test_suite_suffix: str = 'xfa_disabled'
  additional_arg: str = '--disable-xfa'
  disable_xfa: bool = True


@dataclass
class _OneshotOption(_DefaultOption):
  """A test_runner.py test option to enable one-shot rendering."""

  name: str = 'oneshot rendering enabled'
  test_suite_suffix: str = 'oneshot'
  additional_arg: str = '--render-oneshot'


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


def _generate_out_path(memory_tool, skia, xfa, v8, clang, msvc, rel, component):
  out_dir = 'release' if rel else 'debug'

  if skia:
    out_dir += '_skia'
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
def _gn_gen_builds(api, memory_tool, skia, xfa, v8, target_cpu, clang, msvc,
                   rel, component, target_os, out_dir):
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
  if target_cpu:
    args.append('target_cpu="%s"' % target_cpu)

  with api.context(cwd=checkout):
    api.step(
        'gn gen', PYTHON_CMD + [
            gn_cmd, '--check', '--root=' + str(checkout), 'gen',
            '//out/' + out_dir, '--args=' + ' '.join(args)
        ])

  # convert the arguments to key values pairs for gold usage.
  return _gold_build_config(args)


def _build_steps(api, clang, msvc, out_dir):
  enable_goma = _is_goma_enabled(msvc)
  debug_path = api.path['checkout'].join('out', out_dir)
  ninja_path = api.path['checkout'].join('third_party', 'ninja', 'ninja')
  ninja_cmd = [ninja_path, '-C', debug_path]
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


# TODO(https://crbug.com/pdfium/11): `selected_tests_only` currently enables
# all tests except for corpus tests for the bots. Remove this parameter once
# corpus tests can pass with Skia enabled.
def _run_tests(api, memory_tool, v8, xfa, skia, out_dir, build_config, revision,
               run_skia_gold, selected_tests_only):
  """Runs the tests and uploads the results to Gold."""
  resultdb = _ResultDb(
      api, base_variant={
          'builder': api.buildbucket.builder_name,
      })
  test_runner = _TestRunner(api, memory_tool, resultdb, out_dir, build_config,
                            revision, run_skia_gold)

  # This variable swallows the exception raised by a failed step. The step
  # will still show up as failed, but processing will continue.
  test_exception = None

  # pdfium_unittests:
  try:
    test_runner.run_unit_tests()
  except api.step.StepFailure as e:
    test_exception = e

  # pdfium_embeddertests:
  if skia:
    try:
      test_runner.run_embedder_tests(_AGG_RENDERER)
    except api.step.StepFailure as e:
      test_exception = e

    try:
      test_runner.run_embedder_tests(_SKIA_RENDERER)
    except api.step.StepFailure as e:
      test_exception = e
  else:
    try:
      test_runner.run_embedder_tests()
    except api.step.StepFailure as e:
      test_exception = e

  # run_javascript_tests.py:
  if v8:
    try:
      test_runner.run_javascript_tests(_DefaultOption)
    except api.step.StepFailure as e:
      test_exception = e

    try:
      test_runner.run_javascript_tests(_JavascriptDisabledOption)
    except api.step.StepFailure as e:
      test_exception = e

    if xfa:
      try:
        test_runner.run_javascript_tests(_XfaDisabledOption)
      except api.step.StepFailure as e:
        test_exception = e

  # run_pixel_tests.py:
  try:
    test_runner.run_pixel_tests(_DefaultOption)
  except api.step.StepFailure as e:
    test_exception = e

  try:
    test_runner.run_pixel_tests(_OneshotOption)
  except api.step.StepFailure as e:
    test_exception = e

  if v8:
    try:
      test_runner.run_pixel_tests(_JavascriptDisabledOption)
    except api.step.StepFailure as e:
      test_exception = e

    if xfa:
      try:
        test_runner.run_pixel_tests(_XfaDisabledOption)
      except api.step.StepFailure as e:
        test_exception = e

  if selected_tests_only:
    if test_exception:
      raise test_exception  # pylint: disable=E0702
    return

  # run_corpus_tests.py:
  try:
    test_runner.run_corpus_tests(_DefaultOption)
  except api.step.StepFailure as e:
    test_exception = e

  try:
    test_runner.run_corpus_tests(_OneshotOption)
  except api.step.StepFailure as e:
    test_exception = e

  if v8:
    try:
      test_runner.run_corpus_tests(_JavascriptDisabledOption)
    except api.step.StepFailure as e:
      test_exception = e

    if xfa:
      try:
        test_runner.run_corpus_tests(_XfaDisabledOption)
      except api.step.StepFailure as e:
        test_exception = e

  if test_exception:
    raise test_exception  # pylint: disable=E0702


class _ResultDb:

  def __init__(self, api, *, base_variant):
    self.api = api
    self.base_variant = base_variant

    self.api.resultdb.assert_enabled()

    self.result_adapter_path = str(self.api.path['checkout'].join(
        'tools', 'resultdb', 'result_adapter'))
    if self.api.platform.is_win:
      self.result_adapter_path += '.exe'

  def wrap(self,
           command,
           *,
           test_id_prefix='',
           base_variant=None,
           base_tags=None):
    """Wraps an invocation with native ResultSink support."""
    variant = dict(self.base_variant)
    variant.update(base_variant or {})

    tags = set(base_tags or [])

    return self.api.resultdb.wrap(
        command,
        test_id_prefix=test_id_prefix,
        base_variant=variant,
        base_tags=list(tags),
    )

  def wrap_gtest(self, gtest_command, **kwargs):
    """Wraps an invocation of a GoogleTest test runner."""
    result_file_path = self.api.path.mkstemp()
    artifact_directory_path = self.api.path.dirname(result_file_path)
    return self.wrap([
        self.result_adapter_path,
        'gtest_json',
        '-artifact-directory',
        artifact_directory_path,
        '-result-file',
        result_file_path,
        '--',
    ] + gtest_command + [
        f'--gtest_output=json:{result_file_path}',
    ], **kwargs)


class _TestRunner:

  def __init__(self, api, memory_tool, resultdb, out_dir, build_config,
               revision, run_skia_gold):
    self.api = api
    self.resultdb = resultdb
    self.out_dir = self.api.path['checkout'].join('out', out_dir)
    self.build_config = build_config
    self.env = self._create_sanitizer_envionment(memory_tool)

    self.test_runner_py_args = [
        '--build-dir',
        self.api.path.join('out', out_dir),
    ]

    # Add Skia Gold flags if the "run_skia_gold" property is true.
    if run_skia_gold:
      self.test_runner_py_args.extend([
          '--gold_output_dir',
          self.out_dir.join('gold_output'),
          '--run-skia-gold',
          '--git-revision',
          revision,
          '--buildbucket-id',
          str(self.api.buildbucket.build.id),
      ])

      # Add the trybot information if this is a trybot run.
      if self.api.tryserver.gerrit_change:
        self.test_runner_py_args.extend([
            '--gerrit-issue',
            str(self.api.tryserver.gerrit_change.change),
            '--gerrit-patchset',
            str(self.api.tryserver.gerrit_change.patchset),
        ])

  def _create_sanitizer_envionment(self, memory_tool):
    """Sets environment variables required by sanitizer tools."""
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
      if not self.api.platform.is_win:
        options.extend(COMMON_UNIX_SANITIZER_OPTIONS)
      env.update({'ASAN_OPTIONS': ' '.join(options)})
    elif memory_tool == 'msan':
      assert not self.api.platform.is_win
      options = []
      options.extend(COMMON_SANITIZER_OPTIONS)
      options.extend(COMMON_UNIX_SANITIZER_OPTIONS)
      env.update({'MSAN_OPTIONS': ' '.join(options)})
    elif memory_tool == 'ubsan':
      assert not self.api.platform.is_win
      options = []
      options.extend(COMMON_SANITIZER_OPTIONS)
      options.extend(COMMON_UNIX_SANITIZER_OPTIONS)
      env.update({'UBSAN_OPTIONS': ' '.join(options)})

    return env

  def run_unit_tests(self):
    with self.api.context(cwd=self.api.path['checkout'], env=self.env):
      self._run_gtest('unittests', target=('', 'pdfium_unittests'))

  def run_embedder_tests(self, renderer=None):
    test_name = 'embeddertests'
    args = []
    if renderer:
      test_name = f'{test_name} ({renderer})'
      args.append(f'--use-renderer={renderer}')

    with self.api.context(cwd=self.api.path['checkout'], env=self.env):
      self._run_gtest(
          test_name,
          target=('', 'pdfium_embeddertests'),
          args=args,
          test_suite_suffix=renderer)

  def run_javascript_tests(self, option):
    self._run_python_tests(_JAVASCRIPT_TEST_TYPE, option)

  def run_pixel_tests(self, option):
    self._run_python_tests(_PIXEL_TEST_TYPE, option)

  def run_corpus_tests(self, option):
    self._run_python_tests(_CORPUS_TEST_TYPE, option)

  def _run_python_tests(self, test_type, option):
    test_name = f'{test_type} tests'
    if option.name:
      test_name = f'{test_name} ({option.name})'

    with self.api.context(cwd=self.api.path['checkout'], env=self.env):
      self._run_test_runner_py(
          test_name,
          test_type=test_type,
          args=_get_modifiable_script_args(self.api, self.build_config, option),
          test_suite_suffix=option.test_suite_suffix)

  def _run_gtest(self, step_name, *, target, args=None, test_suite_suffix=None):
    target_path, target_name = target

    test_path = str(self.out_dir.join(target_name))
    if self.api.platform.is_win:
      test_path += '.exe'

    variant = {
        'test_suite': _get_test_suite(target_name, test_suite_suffix),
    }

    tags = [
        ('step_name', step_name),
    ]

    self.api.step(
        step_name,
        self.resultdb.wrap_gtest(
            [test_path] + (args or []),
            test_id_prefix=f'ninja://{target_path}:{target_name}/',
            base_variant=variant,
            base_tags=tags))

  def _run_test_runner_py(self, step_name, *, test_type, args,
                          test_suite_suffix):
    test_path = self.api.path['checkout'].join('testing', 'tools',
                                               f'run_{test_type}_tests.py')

    variant = {
        'test_suite': _get_test_suite(test_type, test_suite_suffix),
    }

    tags = [
        ('step_name', step_name),
    ]

    self.api.step(
        step_name,
        self.resultdb.wrap(
            PYTHON_CMD + [test_path] + self.test_runner_py_args + args,
            test_id_prefix=f'ninja://testing/tools:run_{test_type}_tests/',
            base_variant=variant,
            base_tags=tags))


def _get_test_suite(base_name, suffix=None):
  return f'{base_name}_{suffix}' if suffix else base_name


def _get_modifiable_script_args(api, build_config, option):
  """Get the list of additional arguments for Python-based tests that can be
  further modified based on test options.
  Returns a list that can be concatenated with the other script arguments.
  """
  additional_args = []

  # Add Skia Gold keys if `build_config` is non-empty.
  if build_config:
    # Add the os from the builder name to the set of unique identifers.
    keys = build_config.copy()
    builder_name = api.m.buildbucket.builder_name.strip()
    keys['os'] = builder_name.split('_')[0]
    keys['javascript_runtime'] = 'disabled' if (
        build_config['v8'] == 'false' or
        option.disable_javascript) else 'enabled'
    keys['xfa_runtime'] = 'disabled' if (build_config['xfa'] == 'false' or
                                         option.disable_javascript or
                                         option.disable_xfa) else 'enabled'
    additional_args.extend(['--gold_key', _dict_to_str(keys)])

  if option.additional_arg:
    additional_args.append(option.additional_arg)

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


def RunSteps(api, memory_tool, skia, xfa, v8, target_cpu, clang, msvc, rel,
             run_skia_gold, component, skip_test, target_os,
             selected_tests_only):
  revision = _checkout_step(api, target_os)

  out_dir = _generate_out_path(memory_tool, skia, xfa, v8, clang, msvc, rel,
                               component)

  with api.osx_sdk('mac'):
    # buildbot sets 'clobber' to the empty string which evaluates to false if
    # checked directly. Instead, check using the 'in' keyword.
    if 'clobber' in api.properties:
      api.file.rmtree('clobber', api.path['checkout'].join('out', out_dir))

    build_config = _gn_gen_builds(api, memory_tool, skia, xfa, v8, target_cpu,
                                  clang, msvc, rel, component, target_os,
                                  out_dir)
    if not run_skia_gold:
      build_config = {}
    _build_steps(api, clang, msvc, out_dir)

    if skip_test:
      return

    _run_tests(api, memory_tool, v8, xfa, skia, out_dir, build_config, revision,
               run_skia_gold, selected_tests_only)


def GenTests(api):
  yield api.test(
      'win',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot'),
      _gen_ci_build(api, 'windows'),
  )
  yield api.test(
      'linux',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot'),
      _gen_ci_build(api, 'linux'),
  )
  yield api.test(
      'mac',
      api.platform('mac', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot'),
      _gen_ci_build(api, 'mac'),
  )

  yield api.test(
      'win_no_v8',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(v8=False, bot_id='test_bot'),
      _gen_ci_build(api, 'windows_no_v8'),
  )
  yield api.test(
      'linux_no_v8',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(v8=False, bot_id='test_bot'),
      _gen_ci_build(api, 'linux_no_v8'),
  )
  yield api.test(
      'mac_no_v8',
      api.platform('mac', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(v8=False, bot_id='test_bot'),
      _gen_ci_build(api, 'mac_no_v8'),
  )

  yield api.test(
      'win_component',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(component=True, xfa=True, bot_id='test_bot'),
      _gen_ci_build(api, 'win_component'),
  )

  yield api.test(
      'win_skia',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          skia=True, xfa=True, selected_tests_only=True, bot_id='test_bot'),
      _gen_ci_build(api, 'windows_skia'),
  )

  yield api.test(
      'win_xfa_32',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, target_cpu='x86', bot_id='test_bot'),
      _gen_ci_build(api, 'windows_xfa_32'),
  )

  yield api.test(
      'win_xfa',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, bot_id='test_bot'),
      _gen_ci_build(api, 'windows_xfa'),
  )

  yield api.test(
      'win_xfa_rel',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, rel=True, bot_id='test_bot'),
      _gen_ci_build(api, 'windows_xfa_rel'),
  )

  yield api.test(
      'win_xfa_msvc_32',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, msvc=True, target_cpu='x86', bot_id='test_bot'),
      _gen_ci_build(api, 'windows_xfa_msvc_32'),
  )

  yield api.test(
      'win_xfa_msvc',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, msvc=True, bot_id='test_bot'),
      _gen_ci_build(api, 'windows_xfa_msvc'),
  )

  yield api.test(
      'linux_component',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(component=True, xfa=True, bot_id='test_bot'),
      _gen_ci_build(api, 'linux_component'),
  )

  yield api.test(
      'linux_skia',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          skia=True, xfa=True, selected_tests_only=True, bot_id='test_bot'),
      _gen_ci_build(api, 'linux_skia'),
  )

  yield api.test(
      'linux_xfa',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, bot_id='test_bot'),
      _gen_ci_build(api, 'linux_xfa'),
  )

  yield api.test(
      'linux_xfa_rel',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, rel=True, bot_id='test_bot'),
      _gen_ci_build(api, 'linux_xfa_rel'),
  )

  yield api.test(
      'mac_component',
      api.platform('mac', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(component=True, xfa=True, bot_id='test_bot'),
      _gen_ci_build(api, 'mac_component'),
  )

  yield api.test(
      'mac_skia',
      api.platform('mac', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          skia=True, xfa=True, selected_tests_only=True, bot_id='test_bot'),
      _gen_ci_build(api, 'mac_skia'),
  )

  yield api.test(
      'mac_xfa',
      api.platform('mac', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, bot_id='test_bot'),
      _gen_ci_build(api, 'mac_xfa'),
  )

  yield api.test(
      'mac_xfa_rel',
      api.platform('mac', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, rel=True, bot_id='test_bot'),
      _gen_ci_build(api, 'mac_xfa_rel'),
  )

  yield api.test(
      'linux_asan_lsan',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(memory_tool='asan', bot_id='test_bot'),
      _gen_ci_build(api, 'linux_asan_lsan'),
  )

  yield api.test(
      'linux_msan',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(memory_tool='msan', rel=True, bot_id='test_bot'),
      _gen_ci_build(api, 'linux_msan'),
  )

  yield api.test(
      'linux_ubsan',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(memory_tool='ubsan', rel=True, bot_id='test_bot'),
      _gen_ci_build(api, 'linux_ubsan'),
  )

  yield api.test(
      'linux_xfa_asan_lsan',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(memory_tool='asan', xfa=True, bot_id='test_bot'),
      _gen_ci_build(api, 'linux_xfa_asan_lsan'),
  )

  yield api.test(
      'linux_xfa_msan',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(memory_tool='msan', rel=True, xfa=True, bot_id='test_bot'),
      _gen_ci_build(api, 'linux_xfa_msan'),
  )

  yield api.test(
      'linux_xfa_ubsan',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          memory_tool='ubsan', rel=True, xfa=True, bot_id='test_bot'),
      _gen_ci_build(api, 'linux_xfa_ubsan'),
  )

  yield api.test(
      'win_asan',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          clang=True, memory_tool='asan', rel=True, bot_id='test_bot'),
      _gen_ci_build(api, 'windows_asan'),
  )

  yield api.test(
      'win_xfa_asan',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          clang=True, memory_tool='asan', rel=True, xfa=True,
          bot_id='test_bot'),
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
      api.properties(
          bot_id='test_bot',
          target_os='android',
          target_cpu='arm64',
          skip_test=True),
      _gen_ci_build(api, 'android'),
  )

  yield api.test(
      'android_32',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot', target_os='android', skip_test=True),
      _gen_ci_build(api, 'android'),
  )

  yield api.test(
      'clobber-linux_skia',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          skia=True,
          xfa=True,
          selected_tests_only=True,
          bot_id='test_bot',
          clobber=''),
      _gen_ci_build(api, 'linux_skia'),
  )

  yield api.test(
      'clobber-mac_xfa_rel',
      api.platform('mac', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, rel=True, bot_id='test_bot', clobber=''),
      _gen_ci_build(api, 'mac_xfa_rel'),
  )

  yield api.test(
      'clobber-win_xfa',
      api.platform('win', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, bot_id='test_bot', clobber=''),
      _gen_ci_build(api, 'windows_xfa'),
  )

  yield api.test(
      'fail-unittests',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot'),
      _gen_ci_build(api, 'linux'),
      api.step_data('unittests', retcode=1),
  )

  yield api.test(
      'fail-unittests-selected-tests-only',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot', selected_tests_only=True),
      _gen_ci_build(api, 'linux'),
      api.step_data('unittests', retcode=1),
  )

  yield api.test(
      'fail-embeddertests',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot'),
      _gen_ci_build(api, 'linux'),
      api.step_data('embeddertests', retcode=1),
  )

  yield api.test(
      'fail-embeddertests-selected-tests-only',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot', selected_tests_only=True),
      _gen_ci_build(api, 'linux'),
      api.step_data('embeddertests', retcode=1),
  )

  yield api.test(
      'fail-embeddertests-skia-agg',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          skia=True, xfa=True, selected_tests_only=True, bot_id='test_bot'),
      _gen_ci_build(api, 'linux'),
      api.step_data('embeddertests (agg)', retcode=1),
  )

  yield api.test(
      'fail-embeddertests-skia-skia',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(
          skia=True, xfa=True, selected_tests_only=True, bot_id='test_bot'),
      _gen_ci_build(api, 'linux'),
      api.step_data('embeddertests (skia)', retcode=1),
  )

  yield api.test(
      'fail-javascript-tests',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot'),
      _gen_ci_build(api, 'linux'),
      api.step_data('javascript tests', retcode=1),
  )

  yield api.test(
      'fail-javascript-tests-javascript-disabled',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot'),
      _gen_ci_build(api, 'linux'),
      api.step_data('javascript tests (javascript disabled)', retcode=1),
  )

  yield api.test(
      'fail-javascript-tests-xfa-disabled',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, bot_id='test_bot'),
      _gen_ci_build(api, 'linux'),
      api.step_data('javascript tests (xfa disabled)', retcode=1),
  )

  yield api.test(
      'fail-pixel-tests',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot'),
      _gen_ci_build(api, 'linux'),
      api.step_data('pixel tests', retcode=1),
  )

  yield api.test(
      'fail-pixel-tests-oneshot-rendering-enabled',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot'),
      _gen_ci_build(api, 'linux'),
      api.step_data('pixel tests (oneshot rendering enabled)', retcode=1),
  )

  yield api.test(
      'fail-pixel-tests-javascript-disabled',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot'),
      _gen_ci_build(api, 'linux'),
      api.step_data('pixel tests (javascript disabled)', retcode=1),
  )

  yield api.test(
      'fail-pixel-tests-xfa-disabled',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, bot_id='test_bot'),
      _gen_ci_build(api, 'linux'),
      api.step_data('pixel tests (xfa disabled)', retcode=1),
  )

  yield api.test(
      'fail-corpus-tests',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot'),
      _gen_ci_build(api, 'linux'),
      api.step_data('corpus tests', retcode=1),
  )

  yield api.test(
      'fail-corpus-tests-oneshot-rendering-enabled',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot'),
      _gen_ci_build(api, 'linux'),
      api.step_data('corpus tests (oneshot rendering enabled)', retcode=1),
  )

  yield api.test(
      'fail-corpus-tests-javascript-disabled',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot'),
      _gen_ci_build(api, 'linux'),
      api.step_data('corpus tests (javascript disabled)', retcode=1),
  )

  yield api.test(
      'fail-corpus-tests-xfa-disabled',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(xfa=True, bot_id='test_bot'),
      _gen_ci_build(api, 'linux'),
      api.step_data('corpus tests (xfa disabled)', retcode=1),
  )

  yield api.test(
      'disable-skia-gold-linux',
      api.platform('linux', 64),
      api.builder_group.for_current('client.pdfium'),
      api.properties(bot_id='test_bot', run_skia_gold=False),
      _gen_ci_build(api, 'linux'),
  )
