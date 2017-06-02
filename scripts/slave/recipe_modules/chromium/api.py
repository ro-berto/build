# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import contextlib
import functools
import re

from recipe_engine import recipe_api
from recipe_engine import util as recipe_util

class TestLauncherFilterFileInputPlaceholder(recipe_util.InputPlaceholder):
  def __init__(self, api, tests):
    self.raw = api.m.raw_io.input_text('\n'.join(tests))
    super(TestLauncherFilterFileInputPlaceholder, self).__init__()

  def render(self, test):
    result = self.raw.render(test)
    if not test.enabled:  # pragma: no cover
      result[0] = '--test-launcher-filter-file=%s' % result[0]
    return result

  def cleanup(self, test_enabled):
    self.raw.cleanup(test_enabled)


class ChromiumApi(recipe_api.RecipeApi):

  Layout = collections.namedtuple('Layout', ('env',))

  def __init__(self, *args, **kwargs):
    super(ChromiumApi, self).__init__(*args, **kwargs)
    self._build_properties = None
    self._layout = None

  def ensure_chromium_layout(self):
    """Ensures that Chromium build layout is installed.

    Note: the layout must be installed into the engine context. The
    "chromium_layout" context manager is probably a better way to access this.

    Returns (ChromiumApi.Layout): The configured Chromium build layout.
    """
    env = {
        # CHROME_HEADLESS makes sure that running 'gclient runhooks' and other
        # tools don't require user interaction.
        'CHROME_HEADLESS': '1',
    }

    return self.Layout(
        env=env,
    )

  @contextlib.contextmanager
  def chromium_layout(self):
    """Context manager that must be entered prior to performing any Chromium
    recipe operations. This is responsible for basic enviornment initialization.

    See "ensure_chromium_layout" for more information.
    """
    with self.m.context(env=self.ensure_chromium_layout().env):
      yield

  def _with_chromium_layout(fn):
    """Decorator which applies "ensure_chromium_layout" to bound ChromiumApi
    functions.

    This is an INTERNAL method, and specifically decorates ChromiumApi member
    functions. DO NOT USE this outside of this class and module.
    """
    @functools.wraps(fn)
    def inner(self, *args, **kwargs):
      with self.chromium_layout():
        return fn(self, *args, **kwargs)
    return inner

  def get_config_defaults(self):
    defaults = {
      'HOST_PLATFORM': self.m.platform.name,
      'HOST_ARCH': self.m.platform.arch,
      'HOST_BITS': self.m.platform.bits,

      'TARGET_PLATFORM': self.m.platform.name,
      'TARGET_ARCH': self.m.platform.arch,
      'TARGET_CROS_BOARD': None,

      # NOTE: This is replicating logic which lives in
      # chrome/trunk/src/build/common.gypi, which is undesirable. The desired
      # end-state is that all the configuration logic lives in one place
      # (in chromium/config.py), and the buildside gypfiles are as dumb as
      # possible. However, since the recipes need to accurately contain
      # {TARGET,HOST}_{BITS,ARCH,PLATFORM}, for use across many tools (of which
      # gyp is one tool), we're taking a small risk and replicating the logic
      # here.
      'TARGET_BITS': (
        32 if self.m.platform.name == 'win'
        else self.m.platform.bits),

      'BUILD_CONFIG': self.m.properties.get('build_config', 'Release'),

      'CHECKOUT_PATH': self.m.path['checkout'],
    }

    # TODO(phajdan.jr): get rid of the need for BUILD_PATH in config.
    defaults['BUILD_PATH'] = self.package_repo_resource()
    return defaults

  def get_env(self):
    ret = {}
    if self.c.env.PATH:
      ret['PATH'] = self.m.path.pathsep.join(
          map(str, self.c.env.PATH) + ['%(PATH)s'])
    if self.c.env.ADB_VENDOR_KEYS:
      ret['ADB_VENDOR_KEYS'] = self.c.env.ADB_VENDOR_KEYS
    if self.c.env.LLVM_FORCE_HEAD_REVISION:
      ret['LLVM_FORCE_HEAD_REVISION'] = self.c.env.LLVM_FORCE_HEAD_REVISION
    if self.c.env.GOMA_STUBBY_PROXY_IP_ADDRESS:
      ret['GOMA_STUBBY_PROXY_IP_ADDRESS'] = \
        self.c.env.GOMA_STUBBY_PROXY_IP_ADDRESS
    ret['GOMA_SERVICE_ACCOUNT_JSON_FILE'] = \
        self.m.goma.service_account_json_path
    if self.c.env.FORCE_MAC_TOOLCHAIN:
      ret['FORCE_MAC_TOOLCHAIN'] = self.c.env.FORCE_MAC_TOOLCHAIN
    if self.c.env.FORCE_MAC_TOOLCHAIN_REVISION_OVERRIDE:
      ret['MAC_TOOLCHAIN_REVISION'] = \
          self.c.env.FORCE_MAC_TOOLCHAIN_REVISION_OVERRIDE
    return ret

  @property
  def build_properties(self):
    return self._build_properties

  @property
  def output_dir(self):
    """Return the path to the built executable directory."""
    return self.c.build_dir.join(self.c.build_config_fs)

  @property
  def version(self):
    """Returns a version dictionary (after get_version()), e.g.

    { 'MAJOR'": '51', 'MINOR': '0', 'BUILD': '2704', 'PATCH': '0' }
    """
    text = self._version
    output = {}
    for line in text.splitlines():
      [k,v] = line.split('=', 1)
      output[k] = v
    return output

  def get_version(self):
    self._version = self.m.file.read(
        'get version',
        self.m.path['checkout'].join('chrome', 'VERSION'),
        test_data=("MAJOR=51\nMINOR=0\nBUILD=2704\nPATCH=0\n"))
    return self.version

  def set_build_properties(self, props):
    self._build_properties = props

  def configure_bot(self, builders_dict, additional_configs=None):
    """Sets up the configurations and gclient to be ready for bot update.

    builders_dict is a dict of mastername -> 'builders' -> buildername ->
        bot_config.

    The current mastername and buildername are looked up from the
    build properties; we then apply the configs specified in bot_config
    as appropriate.

    Returns a tuple of (buildername, bot_config) for subsequent use in
       the recipe.
    """
    additional_configs = additional_configs or []

    # TODO: crbug.com/358481 . The build_config should probably be a property
    # passed in from the slave config, but that doesn't exist today, so we
    # need a lookup mechanism to map bot name to build_config.
    mastername = self.m.properties.get('mastername')
    buildername = self.m.properties.get('buildername')
    master_dict = builders_dict.get(mastername, {})
    bot_config = master_dict.get('builders', {}).get(buildername)

    self.set_config(bot_config.get('chromium_config', 'chromium'),
                    **bot_config.get('chromium_config_kwargs', {}))

    for c in bot_config.get('chromium_apply_config', []):
      self.apply_config(c)

    for c in additional_configs:
      self.apply_config(c)

    # Note that we have to call gclient.set_config() and apply_config() *after*
    # calling chromium.set_config(), above, because otherwise the chromium
    # call would reset the gclient config to its defaults.
    self.m.gclient.set_config(
        'chromium',
        PATCH_PROJECT=self.m.properties.get('patch_project'))
    for c in bot_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)

    return (buildername, bot_config)

  def _run_ninja(self, ninja_command, name=None, ninja_env=None,
                 ninja_confirm_noop=False, **kwargs):
    """
    Run ninja with given command and env.

    Args:
      ninja_command: Command used for build.
                     This is sent as part of log.
                     (e.g. ['ninja', '-C', 'out/Release'])
      name: Name of compile step.
      ninja_env: Environment for ninja.
      ninja_confirm_noop (bool):
        If this is True, check that ninja does nothing in second build.

    Raises:
      StepFailure or InfraFailure if it fails to build or
      occurs something failure on goma steps.
    """

    with self.m.context(env=ninja_env):
      self.m.step(name or 'compile', ninja_command, **kwargs)

    if not ninja_confirm_noop:
      return

    ninja_command_explain = ninja_command + ['-d', 'explain', '-n']

    ninja_no_work = 'ninja: no work to do.'

    with self.m.context(env=ninja_env):
      step_result = self.m.step(
          (name or 'compile') + ' confirm no-op',
          ninja_command_explain,
          stdout=self.m.raw_io.output_text(),
          step_test_data=(
              lambda: self.m.raw_io.test_api.stream_output(
                  ninja_no_work
              )))

    if ninja_no_work not in step_result.stdout:
      step_result.presentation.status = self.m.step.FAILURE
      step_result.presentation.step_text = (
          "This should have been a no-op, but it wasn't.")
      raise self.m.step.StepFailure(
          """Failing build because ninja reported work to do.
          This means that after completing a compile, another was run and
          it resulted in still having work to do (that is, a no-op build
          wasn't a no-op). Consult the first "ninja explain:" line for a
          likely culprit.""")


  def _run_ninja_with_goma(self, ninja_command, name=None,
                           ninja_log_outdir=None, ninja_log_compiler=None,
                           goma_env=None, ninja_env=None,
                           ninja_confirm_noop=False, **kwargs):
    """
    Run ninja with goma.
    This function start goma, call _run_ninja and stop goma using goma module.

    Args:
      ninja_command: Command used for build.
                     This is sent as part of log.
                     (e.g. ['ninja', '-C', 'out/Release'])
      name: Name of compile step.
      ninja_log_outdir: Directory of ninja log. (e.g. "out/Release")
      ninja_log_compiler: Compiler used in ninja. (e.g. "clang")
      goma_env: Environment controlling goma behavior.
      ninja_env: Environment for ninja.
      ninja_confirm_noop (bool):
        If this is True, check that ninja does nothing in second build.

    Raises:
      StepFailure or InfraFailure if it fails to build or
      occurs something failure on goma steps.
    """

    ninja_log_exit_status = None

    self.m.goma.start(goma_env)

    try:
      self._run_ninja(ninja_command, name, ninja_env,
                      ninja_confirm_noop, **kwargs)
      ninja_log_exit_status = 0
    except self.m.step.StepFailure as e:
      ninja_log_exit_status = e.retcode
      raise e

    finally:
      self.m.goma.stop(ninja_log_outdir=ninja_log_outdir,
                       ninja_log_compiler=ninja_log_compiler,
                       ninja_log_command=ninja_command,
                       ninja_log_exit_status=ninja_log_exit_status)

  # TODO(tikuta): Remove use_goma_module.
  # Decrease the number of ways configuring with or without goma.
  @_with_chromium_layout
  def compile(self, targets=None, name=None, out_dir=None,
              target=None, use_goma_module=False, **kwargs):
    """Return a compile.py invocation."""
    targets = targets or self.c.compile_py.default_targets.as_jsonish()
    assert isinstance(targets, (list, tuple))

    if self.c.gyp_env.GYP_DEFINES.get('clang', 0) == 1:
      # Get the Clang revision before compiling.
      self._clang_version = self.get_clang_version()

    goma_env = self.get_env()
    goma_env.update(self.m.context.env)
    ninja_env = goma_env.copy()

    # Set the ninja status so we can see where the compile time is going.
    ninja_env['NINJA_STATUS'] = (
        '%%e [%%s/%%t %%p - %%r running, current %%c p/s, overall %%o p/s] ')

    goma_env['GOMA_CACHE_DIR'] = self.m.goma.default_cache_path

    # Enable goma DepsCache
    goma_env['GOMA_DEPS_CACHE_FILE'] = "goma_deps_cache"

    if self.c.compile_py.mode:
      if (self.c.compile_py.mode == 'google_chrome' or
          self.c.compile_py.mode == 'official'):
        ninja_env['CHROMIUM_BUILD'] = '_google_chrome'

      if self.c.compile_py.mode == 'official':
        # Official builds are always Google Chrome.
        ninja_env['CHROME_BUILD_TYPE'] = '_official'

    if self.c.compile_py.goma_hermetic:
      goma_env['GOMA_HERMETIC'] = self.c.compile_py.goma_hermetic
    if self.c.compile_py.goma_enable_localoutputcache:
      # Use per-slave cache. LocalOutputCache could use a lot of disks.
      # To run GC for older caches, we should share the same build
      # among builders.
      goma_env['GOMA_LOCAL_OUTPUT_CACHE_DIR'] = (
          self.m.path.join(self.m.goma.default_cache_path_per_slave,
                           "localoutputcache"))
    if self.c.compile_py.goma_max_active_fail_fallback_tasks:
      goma_env['GOMA_MAX_ACTIVE_FAIL_FALLBACK_TASKS'] = (
          self.c.compile_py.goma_max_active_fail_fallback_tasks)
    if (self.m.tryserver.is_tryserver or
        self.c.compile_py.goma_failfast):
      # We rely on goma to meet cycle time goals on the tryserver. It's better
      # to fail early.
      goma_env['GOMA_FAIL_FAST'] = 'true'
    else:
      goma_env['GOMA_ALLOWED_NETWORK_ERROR_DURATION'] = '1800'

    if self.c.TARGET_CROS_BOARD:
      # Wrap 'compile' through 'cros chrome-sdk'
      kwargs['wrapper'] = self.get_cros_chrome_sdk_wrapper()

    if self.m.platform.is_linux and self.c.TARGET_CROS_BOARD:
      out_dir = 'out_%s' % self.c.TARGET_CROS_BOARD
    elif out_dir is None:
      out_dir = 'out'

    target_output_dir = self.m.path.abspath(
        self.m.path.join(self.m.path['checkout'], out_dir,
                         target or self.c.build_config_fs))

    command = [str(self.m.depot_tools.ninja_path), '-w', 'dupbuild=err',
               '-C', target_output_dir]

    if self.c.compile_py.show_ninja_stats:
      command.extend(['-d', 'stats'])

    if self.c.compile_py.build_args:
      command.extend(self.c.compile_py.build_args)

    # TODO(tikuta): Remove this and let goma module set '-j'
    #               inside build_with_goma.
    if use_goma_module:
      # Set -j just before 'with self.m.goma.build_with_goma('
      # for ninja_log_command being set correctly if starting goma
      # fails.
      if self.c.compile_py.goma_high_parallel:
        # This flag is set for experiment.
        command += ['-j', 3 * self.m.goma.recommended_goma_jobs]
      else:
        command += ['-j', self.m.goma.recommended_goma_jobs]

    if targets is not None:
      # Add build targets to command ('All', 'chrome' etc).
      command += targets

    assert 'env' not in kwargs

    assert 'cwd' not in kwargs


    if not use_goma_module:
      compile_exit_status = 1
      try:
        with self.m.context(cwd=self.m.context.cwd or self.m.path['checkout']):
          self._run_ninja(ninja_command=command,
                          name=name or 'compile',
                          ninja_env=ninja_env,
                          ninja_confirm_noop=self.c.compile_py.ninja_confirm_noop,
                          **kwargs)
        compile_exit_status = 0
      except self.m.step.StepFailure as e:
        compile_exit_status = e.retcode
        raise e
      finally:
        upload_ninja_log_args = [
            '--gsutil-py-path', self.m.depot_tools.gsutil_py_path,
            '--skip-sendgomatsmon',
            '--ninja-log-outdir', target_output_dir,
            '--ninja-log-command', str(command),
            '--ninja-log-exit-status', compile_exit_status,
            '--ninja-log-compiler', self.c.compile_py.compiler or 'unknown'
        ]
        self.m.build.python(
            name='upload_ninja_log',
            script=self.package_repo_resource(
                'scripts', 'slave', 'upload_goma_logs.py'),
            args=upload_ninja_log_args)

      return

    try:
      with self.m.context(cwd=self.m.context.cwd or self.m.path['checkout']):
        self._run_ninja_with_goma(
            name=name or 'compile',
            ninja_command=command,
            ninja_env=ninja_env,
            goma_env=goma_env,
            ninja_log_outdir=target_output_dir,
            ninja_log_compiler=self.c.compile_py.compiler or 'goma',
            ninja_confirm_noop=self.c.compile_py.ninja_confirm_noop,
            **kwargs)
    except self.m.step.StepFailure as e:
      # Handle failures caused by goma.
      step_result = self.m.step.active_result
      failure_result_code = ''

      json_status = self.m.goma.jsonstatus['notice'][0]

      if (not json_status.get('infra_status')):
        failure_result_code = 'GOMA_SETUP_FAILURE'
      elif json_status['infra_status']['ping_status_code'] != 200:
        failure_result_code = 'GOMA_PING_FAILURE'
      elif json_status['infra_status'].get('num_user_error', 0) > 0:
        failure_result_code = 'GOMA_BUILD_ERROR'

      if failure_result_code:
        assert len(failure_result_code) <= 20
        properties = self.m.step.active_result.presentation.properties
        if not properties.get('extra_result_code'):
          properties['extra_result_code'] = []
        properties['extra_result_code'].append(failure_result_code)
        raise self.m.step.InfraFailure('Infra compile failure: %s' % e)

      raise e

  @recipe_util.returns_placeholder
  def test_launcher_filter(self, tests):
    return TestLauncherFilterFileInputPlaceholder(self, tests)

  @_with_chromium_layout
  def runtest(self, test, args=None, xvfb=False, name=None, annotate=None,
              results_url=None, perf_dashboard_id=None, test_type=None,
              python_mode=False, parallel=False,
              point_id=None, revision=None, webkit_revision=None,
              test_launcher_summary_output=None, flakiness_dash=None,
              perf_id=None, perf_config=None, chartjson_file=False,
              disable_src_side_runtest_py=False, tee_stdout_file=None,
              **kwargs):
    """Return a runtest.py invocation."""
    args = args or []
    assert isinstance(args, list)

    t_name, ext = self.m.path.splitext(self.m.path.basename(test))
    if not python_mode and self.m.platform.is_win and ext == '':
      test += '.exe'

    full_args = ['--target', self.c.build_config_fs]
    if self.c.TARGET_PLATFORM == 'android':
      full_args.extend(['--test-platform', 'android'])
    if self.m.platform.is_linux:
      full_args.append('--xvfb' if xvfb else '--no-xvfb')

    properties_json = self.m.json.dumps(self.m.properties.legacy())
    full_args.extend(['--factory-properties', properties_json,
                      '--build-properties', properties_json])

    if annotate:
      full_args.append('--annotate=%s' % annotate)
      kwargs['allow_subannotations'] = True

    if annotate != 'gtest':
      assert not flakiness_dash

    if results_url:
      full_args.append('--results-url=%s' % results_url)
    if perf_dashboard_id:
      full_args.append('--perf-dashboard-id=%s' % perf_dashboard_id)
    if perf_id:
      full_args.append('--perf-id=%s' % perf_id)
    if perf_config:
      full_args.extend(['--perf-config', self.m.json.dumps(perf_config)])
    # This replaces the step_name that used to be sent via factory_properties.
    if test_type:
      full_args.append('--test-type=%s' % test_type)
    step_name = name or t_name
    full_args.append('--step-name=%s' % step_name)
    if chartjson_file:
      full_args.append('--chartjson-file')
      full_args.append(self.m.json.output())
      if 'step_test_data' not in kwargs:
        kwargs['step_test_data'] = lambda: self.m.json.test_api.output([])
    if test_launcher_summary_output:
      full_args.extend([
        '--test-launcher-summary-output',
        test_launcher_summary_output
      ])
    if flakiness_dash:
      full_args.extend([
        '--generate-json-file',
        '-o', 'gtest-results/%s' % test,
      ])
      # The flakiness dashboard needs the buildnumber, so we assert it here.
      assert self.m.properties.get('buildnumber') is not None

    # These properties are specified on every bot, so pass them down
    # unconditionally.
    full_args.append('--builder-name=%s' % self.m.properties['buildername'])
    full_args.append('--slave-name=%s' % self.m.properties['bot_id'])
    # A couple of the recipes contain tests which don't specify a buildnumber,
    # so make this optional.
    if self.m.properties.get('buildnumber') is not None:
      full_args.append('--build-number=%s' % self.m.properties['buildnumber'])
    if ext == '.py' or python_mode:
      full_args.append('--run-python-script')
    if point_id:
      full_args.append('--point-id=%d' % point_id)
    if revision:
      full_args.append('--revision=%s' % revision)
    if webkit_revision:
      # TODO(kbr): figure out how to cover this line of code with
      # tests after the removal of the GPU recipe. crbug.com/584469
      full_args.append(
          '--webkit-revision=%s' % webkit_revision)  # pragma: no cover

    if (self.c.gyp_env.GYP_DEFINES.get('asan', 0) == 1 or
        self.c.runtests.run_asan_test):
      full_args.append('--enable-asan')
    if self.c.runtests.enable_lsan:
      full_args.append('--enable-lsan')
    if self.c.gyp_env.GYP_DEFINES.get('msan', 0) == 1:
      full_args.append('--enable-msan')
    if self.c.gyp_env.GYP_DEFINES.get('tsan', 0) == 1:
      full_args.append('--enable-tsan')
    if self.c.runtests.enable_memcheck:
      full_args.extend([
        '--pass-build-dir',
        '--pass-target',
        '--run-shell-script',
        self.c.runtests.memory_tests_runner,
        '--test', t_name,
        '--tool', 'memcheck',
      ])
    else:
      full_args.append(test)

    full_args.extend(self.c.runtests.test_args)
    full_args.extend(args)

    runtest_path = self.package_repo_resource('scripts', 'slave', 'runtest.py')
    if self.c.runtest_py.src_side and not disable_src_side_runtest_py:
      runtest_path = self.m.path['checkout'].join(
          'infra', 'scripts', 'runtest_wrapper.py')
      # Note that -- is needed since full_args are not indended
      # for wrapper script but for real runtest.py .
      full_args = ['--'] + full_args
    if tee_stdout_file:
      full_args = [tee_stdout_file, '--', 'python', runtest_path] + full_args
      runtest_path = self.package_repo_resource(
          'scripts', 'slave', 'tee.py')
    with self.m.build.gsutil_py_env():
      return self.m.build.python(
        step_name,
        runtest_path,
        args=full_args,
        **kwargs
      )

  @_with_chromium_layout
  def sizes(self, results_url=None, perf_id=None, platform=None, **kwargs):
    """Return a sizes.py invocation.
    This uses runtests.py to upload the results to the perf dashboard."""
    sizes_script = self.package_repo_resource(
        'scripts', 'slave', 'chromium', 'sizes.py')
    sizes_args = ['--target', self.c.build_config_fs]
    if platform:
      sizes_args.extend(['--platform', platform])
    else:
      sizes_args.extend(['--platform', self.c.TARGET_PLATFORM])

    run_tests_args = ['--target', self.c.build_config_fs,
                      '--no-xvfb']
    properties_json = self.m.json.dumps(self.m.properties.legacy())
    run_tests_args.extend(['--factory-properties', properties_json,
                           '--build-properties', properties_json])
    run_tests_args.extend(['--test-type=sizes',
                           '--builder-name=%s' % self.m.properties['buildername'],
                           '--slave-name=%s' % self.m.properties['bot_id'],
                           '--build-number=%s' % self.m.properties['buildnumber'],
                           '--run-python-script'])

    if perf_id:
      assert results_url is not None
      run_tests_args.extend(['--annotate=graphing',
                             '--results-url=%s' % results_url,
                             '--perf-dashboard-id=sizes',
                             '--perf-id=%s' % perf_id])

      # If we have a clang revision, add that to the perf data point.
      # TODO(hans): We want this for all perf data, not just sizes.
      if hasattr(self, '_clang_version'):
        clang_rev = re.match(r'(\d+)(-\d+)?', self._clang_version).group(1)
        run_tests_args.append(
            "--perf-config={'r_clang_rev': '%s'}" % clang_rev)

    full_args = run_tests_args + [sizes_script] + sizes_args

    return self.m.build.python(
        'sizes', self.package_repo_resource('scripts', 'slave', 'runtest.py'),
        full_args, allow_subannotations=True, **kwargs)

  @_with_chromium_layout
  def get_clang_version(self, **kwargs):
    with self.m.context(env=self.get_env()):
      step_result = self.m.build.python(
          'clang_revision',
          self.package_repo_resource('scripts', 'slave', 'clang_revision.py'),
          args=['--src-dir', self.m.path['checkout'],
                '--output-json', self.m.json.output()],
          step_test_data=lambda:
              self.m.json.test_api.output({'clang_revision': '123456-7'}),
          allow_subannotations=True,
          **kwargs)
    return step_result.json.output['clang_revision']

  def get_cros_chrome_sdk_wrapper(self, clean=False):
    """Returns: a wrapper command for 'cros chrome-sdk'

    Args:
      external: (bool) If True, force the wrapper to prefer external board
          configurations over internal ones, even if the latter is available.
      clean: (bool) If True, instruct the wrapper to clean any previous
          state data.
    """
    assert self.c.TARGET_CROS_BOARD
    wrapper = [
        self.m.depot_tools.cros_path, 'chrome-sdk',
        '--board=%s' % (self.c.TARGET_CROS_BOARD,),
        '--nocolor',]
    wrapper += self.c.cros_sdk.args
    if self.c.cros_sdk.external:
      wrapper += ['--use-external-config']
    if clean:
      wrapper += ['--clear-sdk-cache']
    if self.c.compile_py.goma_dir:
      wrapper += ['--gomadir', self.c.compile_py.goma_dir]
      # Since we are very sure api.chromium.compile starts compiler_proxy,
      # and starting compiler_proxy here make it difficult for us to
      # investigate the compiler_proxy start-up failure reason,
      # let me stop starting compiler_proxy. (crbug.com/639432)
      wrapper += ['--nostart-goma']
    # NOTE: --fastbuild is no longer supported in 'cros chrome-sdk'.
    wrapper += ['--']
    return wrapper

  def ensure_goma(self, canary=False):
    no_goma_compiler = self.c.compile_py.compiler or ''
    if no_goma_compiler == 'goma-clang':
      no_goma_compiler = 'clang'
    elif no_goma_compiler == 'goma':
      no_goma_compiler = None

    if ('use_goma' in self.c.gyp_env.GYP_DEFINES and
        self.c.gyp_env.GYP_DEFINES['use_goma'] == 0):
      self.c.compile_py.compiler = no_goma_compiler
      return

    goma_dir = self.m.goma.ensure_goma(canary=canary)

    self.c.gyp_env.GYP_DEFINES['gomadir'] = goma_dir
    self.c.gyp_env.GYP_DEFINES['use_goma'] = 1
    self.c.compile_py.goma_dir = goma_dir

  def clobber_if_needed(self):
    """Add an explicit clobber step if requested."""
    # clobber_before_runhooks is true for bots that apply the 'clobber' config,
    # that is for bots that do clobber bots on every build.
    # properties.get('clobber') is true on bots that normally don't clobber,
    # when the "Clobber" button in the buildbot UI is pressed.
    if (self.c.clobber_before_runhooks or
        self.m.properties.get('clobber') is not None):
      self.m.file.rmtree('clobber', self.output_dir)

  @_with_chromium_layout
  def runhooks(self, env=None, **kwargs):
    """Run the build-configuration hooks for chromium."""

    # runhooks might write things into the output directory, so clobber before
    # that.
    self.clobber_if_needed()

    runhooks_env = self.get_env()
    runhooks_env.update(self.m.context.env)
    runhooks_env.update(env or {})

    # CrOS "chrome_sdk" builds fully override GYP_DEFINES in the wrapper. Zero
    # it to not show confusing information in the build logs.
    if not self.c.TARGET_CROS_BOARD:
      # TODO(sbc): Ideally we would not need gyp_env set during runhooks when
      # we are not running gyp, but there are some hooks (such as sysroot
      # installation that peek at GYP_DEFINES and modify thier behaviour
      # accordingly.
      runhooks_env.update(self.c.gyp_env.as_jsonish())

    if self.c.project_generator.tool != 'gyp':
      runhooks_env['GYP_CHROMIUM_NO_ACTION'] = 1
    if self.c.TARGET_CROS_BOARD:
      # Wrap 'runhooks' through 'cros chrome-sdk'
      kwargs['wrapper'] = self.get_cros_chrome_sdk_wrapper(clean=True)
    with self.m.context(env=runhooks_env):
      self.m.gclient.runhooks(**kwargs)

  # No cover because internal recipes use this.
  @_with_chromium_layout
  def run_gyp_chromium(self): # pragma: no cover
    gyp_chromium_path = self.m.path['checkout'].join('build', 'gyp_chromium.py')
    env = self.get_env()
    env.update(self.c.gyp_env.as_jsonish())
    with self.m.context(env=env):
      self.m.python(name='gyp_chromium', script=gyp_chromium_path)

  @_with_chromium_layout
  def run_gn(self, use_goma=False, gn_path=None, build_dir=None, **kwargs):
    if not gn_path:
      gn_path = self.m.depot_tools.gn_py_path

    gn_args = list(self.c.gn_args)

    # TODO(dpranke): Figure out if we should use the '_x64' thing to
    # consistent w/ GYP, or drop it to be consistent w/ the other platforms.
    build_dir = build_dir or '//out/%s' % self.c.build_config_fs

    if self.c.BUILD_CONFIG == 'Debug':
      gn_args.append('is_debug=true')
    if self.c.BUILD_CONFIG == 'Release':
      gn_args.append('is_debug=false')

    if self.c.TARGET_PLATFORM == 'android':
      gn_args.append('target_os="android"')
    elif self.c.TARGET_PLATFORM in ('mac', 'win'):
      assert self.c.TARGET_ARCH == 'intel'
    elif self.c.TARGET_PLATFORM == 'linux':
      assert self.c.TARGET_ARCH in ('arm', 'intel')

    gn_cpu = {
      ('intel', 32): 'x86',
      ('intel', 64): 'x64',
      ('arm',   32): 'arm',
      ('arm',   64): 'arm64',
      ('mipsel',  32): 'mipsel',
    }.get((self.c.TARGET_ARCH, self.c.TARGET_BITS))
    if gn_cpu:
      gn_args.append('target_cpu="%s"' % gn_cpu)

    # TODO: crbug.com/395784.
    # Consider getting the flags to use via the project_generator config
    # and/or modifying the goma config to modify the gn flags directly,
    # rather than setting the gn_args flags via a parameter passed to
    # run_gn(). We shouldn't have *three* different mechanisms to control
    # what args to use.
    if use_goma:
      gn_args.append('use_goma=true')
      gn_args.append('goma_dir="%s"' % self.c.compile_py.goma_dir)
    gn_args.extend(self.c.project_generator.args)

    # TODO(jbudorick): Change this s.t. no clients use gn.py.
    step_args = [
        '--root=%s' % str(self.m.path['checkout']),
        'gen',
        build_dir,
        '--args=%s' % ' '.join(gn_args),
    ]
    with self.m.context(cwd=kwargs.get('cwd', self.m.path['checkout'])):
      if str(gn_path).endswith('.py'):
        self.m.python(name='gn', script=gn_path, args=step_args, **kwargs)
      else:
        self.m.step(name='gn', cmd=[gn_path] + step_args, **kwargs)

  @_with_chromium_layout
  def run_mb(self, mastername, buildername, use_goma=True, mb_path=None,
             mb_config_path=None, isolated_targets=None, name=None,
             build_dir=None, android_version_code=None,
             android_version_name=None, gyp_script=None, phase=None,
             **kwargs):
    mb_path = mb_path or self.m.path['checkout'].join('tools', 'mb')
    mb_config_path = mb_config_path or mb_path.join('mb_config.pyl')
    isolated_targets = isolated_targets or []

    out_dir = 'out'
    if self.c.TARGET_CROS_BOARD:
      out_dir += '_%s' % self.c.TARGET_CROS_BOARD

    build_dir = build_dir or '//%s/%s' % (out_dir, self.c.build_config_fs)

    args=[
        'gen',
        '-m', mastername,
        '-b', buildername,
        '--config-file', mb_config_path,
    ]

    if phase is not None:
      args += [ '--phase', str(phase) ]

    if use_goma:
      goma_dir = self.c.compile_py.goma_dir
      # TODO(phajdan.jr): remove this weird goma fallback or cover it
      if not goma_dir:  # pragma: no cover
        # This method defaults to use_goma=True, which doesn't necessarily
        # match build-side configuration. However, MB is configured
        # src-side, and so it might be actually using goma.
        self.ensure_goma()
        goma_dir = self.c.compile_py.goma_dir
      if goma_dir:
        args += ['--goma-dir', goma_dir]

    if isolated_targets:
      sorted_isolated_targets = sorted(set(isolated_targets))
      # TODO(dpranke): Change the MB flag to '--isolate-targets-file', maybe?
      data = '\n'.join(sorted_isolated_targets) + '\n'
      args += ['--swarming-targets-file', self.m.raw_io.input_text(data)]

    if android_version_code:
      args += ['--android-version-code=%s' % android_version_code]
    if android_version_name:
      args += ['--android-version-name=%s' % android_version_name]

    if gyp_script:
      args += ['--gyp-script=%s' % gyp_script]

    args += [build_dir]

    # This runs with an almost-bare env being passed along, so we get a clean
    # environment without any GYP_DEFINES being present to cause confusion.
    env = {
      'GOMA_SERVICE_ACCOUNT_JSON_FILE': self.m.goma.service_account_json_path,
    }
    env.update(self.m.context.env)
    step_kwargs = {
      'name': name or 'generate_build_files',
      'script': mb_path.join('mb.py'),
      'args': args,
    }

    if self.c.env.FORCE_MAC_TOOLCHAIN:
      env['FORCE_MAC_TOOLCHAIN'] = self.c.env.FORCE_MAC_TOOLCHAIN

    if self.c.gyp_env.GYP_MSVS_VERSION:
      # TODO(machenbach): Remove this as soon as it's not read anymore by
      # vs_toolchain.py (currently called by gn).
      env['GYP_MSVS_VERSION'] = self.c.gyp_env.GYP_MSVS_VERSION

    if self.c.TARGET_CROS_BOARD:
      # Wrap 'runhooks' through 'cros chrome-sdk'
      step_kwargs['wrapper'] = self.get_cros_chrome_sdk_wrapper(clean=True)

    step_kwargs.update(kwargs)
    with self.m.context(
        # TODO(phajdan.jr): get cwd from context, not kwargs.
        cwd=kwargs.get('cwd', self.m.path['checkout']),
        env=env):
      self.m.python(**step_kwargs)

    # Comes after self.m.python so the log appears in the correct step result.
    result = self.m.step.active_result
    if isolated_targets and result:
      result.presentation.logs['swarming-targets-file.txt'] = (
          sorted_isolated_targets)


  @_with_chromium_layout
  def update_clang(self):
    # The hooks in DEPS call `update.py --if-needed`, which updates clang by
    # default on Mac and Linux, or if clang=1 is in GYP_DEFINES.  This step
    # is only needed on bots that use clang but where --if-needed doesn't update
    # clang. (In practice, this means on Windows when using gn, not gyp.)
    self.m.python(name='update_clang',
                  script=self.m.path['checkout'].join('tools', 'clang',
                                                      'scripts', 'update.py'))

  def taskkill(self):
    self.m.build.python(
      'taskkill',
      self.package_repo_resource('scripts', 'slave', 'kill_processes.py'),
      infra_step=True)

  def process_dumps(self, **kwargs):
    # Dumps are especially useful when other steps (e.g. tests) are failing.
    try:
      self.m.build.python(
          'process_dumps',
          self.package_repo_resource('scripts', 'slave', 'process_dumps.py'),
          ['--target', self.c.build_config_fs],
          infra_step=True,
          **kwargs)
    except self.m.step.InfraFailure:
      pass

  @_with_chromium_layout
  def apply_syzyasan(self):
    args = [
        '--src-dir', self.m.path['checkout'],
        '--target', self.c.BUILD_CONFIG,
    ]
    self.m.build.python(
      'apply_syzyasan',
      self.package_repo_resource(
          'scripts', 'slave', 'chromium', 'win_apply_syzyasan.py'),
      args)

  @_with_chromium_layout
  def archive_build(self, step_name, gs_bucket, gs_acl=None, mode=None,
                    **kwargs):
    """Returns a step invoking archive_build.py to archive a Chromium build."""

    # archive_build.py insists on inspecting factory properties. For now just
    # provide these options in the format it expects.
    fake_factory_properties = {
        'gclient_env': self.c.gyp_env.as_jsonish(),
        'gs_bucket': 'gs://%s' % gs_bucket,
    }
    if gs_acl is not None:
      fake_factory_properties['gs_acl'] = gs_acl
    if self.c.TARGET_PLATFORM == 'android':
      fake_factory_properties['target_os'] = 'android'

    sanitized_buildername = ''.join(
        c if c.isalnum() else '_' for c in self.m.properties['buildername'])

    args = [
        '--src-dir', self.m.path['checkout'],
        '--build-name', sanitized_buildername,
        '--staging-dir', self.m.path['cache'].join('chrome_staging'),
        '--target', self.c.build_config_fs,
        '--factory-properties', self.m.json.dumps(fake_factory_properties),
    ]
    args += self.m.build.slave_utils_args
    if self.build_properties:
      args += [
        '--build-properties', self.m.json.dumps(self.build_properties),
      ]
    if mode:
      args.extend(['--mode', mode])
    self.m.build.python(
      step_name,
      self.package_repo_resource(
          'scripts', 'slave', 'chromium', 'archive_build.py'),
      args,
      infra_step=True,
      **kwargs)

  @_with_chromium_layout
  def list_perf_tests(self, browser, num_shards, device=None):
    args = ['list', '--browser', browser, '--json-output',
            self.m.json.output(), '--num-shards', num_shards]
    if device:
      args += ['--device', device]

    return self.m.python(
      'List Perf Tests',
      self.m.path['checkout'].join('tools', 'perf', 'run_benchmark'),
      args,
      step_test_data=lambda: self.m.json.test_api.output({
        "steps": {
          "blink_perf.all.release": {
            "cmd": "/usr/bin/python /path/to/run_benchmark --a=1 -v --b=2",
            "perf_dashboard_id": "blink_perf.all",
            "device_affinity": 0
          },
          "blink_perf.all.exact": {
            "cmd": "/usr/bin/python /path/to/run_benchmark --a=1 -v --b=2",
            "perf_dashboard_id": "blink_perf.all",
            "device_affinity": 1 % num_shards
          },
          "blink_perf.dom": {
            "cmd": "/path/to/run_benchmark -v --upload-results blink_perf.dom",
            "perf_dashboard_id": "blink_perf.dom",
            "device_affinity": 1 % num_shards
          },
          "dromaeo.cssqueryjquery.release": {
            "cmd": "/path/to/run_benchmark",
            "perf_dashboard_id": "dromaeo.cssqueryjquery",
            "device_affinity": 11 % num_shards
          },
          "dromaeo.cssqueryjquery": {
            "cmd": "/path/to/run_benchmark",
            "device_affinity": 13 % num_shards
          },
        },
        "version": 2,
      }))

  def get_annotate_by_test_name(self, test_name):
    return 'graphing'

  @_with_chromium_layout
  def download_lto_plugin(self):
    return self.m.python(
        name='download LTO plugin',
        script=self.m.path['checkout'].join(
            'build', 'download_gold_plugin.py'))
