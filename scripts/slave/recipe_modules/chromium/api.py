# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api
from slave import recipe_util


class TestLauncherFilterFileInputPlaceholder(recipe_util.Placeholder):
  def __init__(self, api, tests):
    self.raw = api.m.raw_io.input('\n'.join(tests))
    super(TestLauncherFilterFileInputPlaceholder, self).__init__()

  def render(self, test):
    result = self.raw.render(test)
    if not test.enabled:  # pragma: no cover
      result[0] = '--test-launcher-filter-file=%s' % result[0]
    return result

  def result(self, presentation, test):
    return self.raw.result(presentation, test)


class ChromiumApi(recipe_api.RecipeApi):
  def get_config_defaults(self):
    return {
      'HOST_PLATFORM': self.m.platform.name,
      'HOST_ARCH': self.m.platform.arch,
      'HOST_BITS': self.m.platform.bits,

      'TARGET_PLATFORM': self.m.platform.name,
      'TARGET_ARCH': self.m.platform.arch,

      # NOTE: This is replicating logic which lives in
      # chrome/trunk/src/build/common.gypi, which is undesirable. The desired
      # end-state is that all the configuration logic lives in one place
      # (in chromium/config.py), and the buildside gypfiles are as dumb as
      # possible. However, since the recipes need to accurately contain
      # {TARGET,HOST}_{BITS,ARCH,PLATFORM}, for use across many tools (of which
      # gyp is one tool), we're taking a small risk and replicating the logic
      # here.
      'TARGET_BITS': (
        32 if self.m.platform.name in ('mac', 'win')
        else self.m.platform.bits),

      'BUILD_CONFIG': self.m.properties.get('build_config', 'Release')
    }

  def compile(self, targets=None, name=None, abort_on_failure=True, **kwargs):
    """Return a compile.py invocation."""
    targets = targets or self.c.compile_py.default_targets.as_jsonish()
    assert isinstance(targets, (list, tuple))

    args = [
      '--target', self.c.build_config_fs,
      '--build-dir', self.c.build_dir,
      '--src-dir', self.m.path.checkout,
    ]
    if self.c.compile_py.build_tool:
      args += ['--build-tool', self.c.compile_py.build_tool]
    if self.c.compile_py.compiler:
      args += ['--compiler', self.c.compile_py.compiler]
    if self.m.properties.get('clobber') is not None:
      args.append('--clobber')
    args.append('--')
    args.extend(targets)
    return self.m.python(name or 'compile',
                         self.m.path.build('scripts', 'slave', 'compile.py'),
                         args, abort_on_failure=abort_on_failure, **kwargs)

  @recipe_util.returns_placeholder
  def test_launcher_filter(self, tests):
    return TestLauncherFilterFileInputPlaceholder(self, tests)

  def runtest(self, test, args=None, xvfb=False, name=None, annotate=None,
              results_url=None, perf_dashboard_id=None, test_type=None,
              generate_json_file=False, results_directory=None,
              build_number=None, builder_name=None, python_mode=False,
              spawn_dbus=True, parallel=False, **kwargs):
    """Return a runtest.py invocation."""
    args = args or []
    assert isinstance(args, list)

    t_name, ext = self.m.path.splitext(self.m.path.basename(test))
    if not python_mode and self.m.platform.is_win and ext == '':
      test += '.exe'

    full_args = [
      '--target', self.c.build_config_fs,
      '--build-dir', self.c.build_dir
    ]
    if self.m.platform.is_linux:
      full_args.append('--xvfb' if xvfb else '--no-xvfb')
    full_args += self.m.json.property_args()

    if annotate:
      full_args.append('--annotate=%s' % annotate)
      kwargs['allow_subannotations'] = True
    if results_url:
      full_args.append('--results-url=%s' % results_url)
    if perf_dashboard_id:
      full_args.append('--perf-dashboard-id=%s' % perf_dashboard_id)
    # This replaces the step_name that used to be sent via factory_properties.
    if test_type:
      full_args.append('--test-type=%s' % test_type)
    if generate_json_file:
      full_args.append('--generate-json-file')
    if results_directory:
      full_args.append('--results-directory=%s' % results_directory)
    if build_number:
      full_args.append('--build-number=%s' % build_number)
    if builder_name:
      full_args.append('--builder-name=%s' % builder_name)
    if ext == '.py' or python_mode:
      full_args.append('--run-python-script')
    if not spawn_dbus:
      full_args.append('--no-spawn-dbus')
    if parallel:
      full_args.append('--parallel')
    full_args.append(test)
    full_args.extend(args)

    # By default, always run the tests.
    kwargs.setdefault('always_run', True)

    return self.m.python(
      name or t_name,
      self.m.path.build('scripts', 'slave', 'runtest.py'),
      full_args,
      **kwargs
    )

  @property
  def is_release_build(self):
    return self.c.BUILD_CONFIG == 'Release'

  def run_telemetry_test(self, runner, test, name='', args=None,
                         prefix_args=None, results_directory='',
                         spawn_dbus=False):
    """Runs a Telemetry based test with 'runner' as the executable.
    Automatically passes certain flags like --output-format=gtest to the
    test runner. 'prefix_args' are passed before the built-in arguments and
    'args'."""
    # Choose a reasonable default for the location of the sandbox binary
    # on the bots.
    env = {}
    if self.m.platform.is_linux:
      env['CHROME_DEVEL_SANDBOX'] = self.m.path.join(
          '/opt', 'chromium', 'chrome_sandbox')

    if not name:
      name = test

    # The step name must end in 'test' or 'tests' in order for the results to
    # automatically show up on the flakiness dashboard.
    if not (name.endswith('test') or name.endswith('tests')):
      name = '%s_tests' % name

    test_args = []
    if prefix_args:
      test_args.extend(prefix_args)
    test_args.extend([test,
                      '--show-stdout',
                      '--output-format=gtest',
                      '--browser=%s' % self.c.BUILD_CONFIG.lower()])
    if args:
      test_args.extend(args)

    if not results_directory:
      results_directory = self.m.path.slave_build('gtest-results', name)

    return self.runtest(
        runner,
        test_args,
        annotate='gtest',
        name=name,
        test_type=name,
        generate_json_file=True,
        results_directory=results_directory,
        build_number=self.m.properties['buildnumber'],
        builder_name=self.m.properties['buildername'],
        python_mode=True,
        spawn_dbus=spawn_dbus,
        env=env)

  def runhooks(self, **kwargs):
    """Run the build-configuration hooks for chromium."""
    env = kwargs.get('env', {})
    env.update(self.c.gyp_env.as_jsonish())
    kwargs['env'] = env
    return self.m.gclient.runhooks(**kwargs)

  def cleanup_temp(self):
    return self.m.python(
      'cleanup_temp',
      self.m.path.build('scripts', 'slave', 'cleanup_temp.py'))

  def checkdeps(self, suffix=None, **kwargs):
    name = 'checkdeps'
    if suffix:
      name += ' (%s)' % suffix
    return self.m.python(
        name,
        self.m.path.checkout('tools', 'checkdeps', 'checkdeps.py'),
        args=['--json', self.m.json.output()],
        **kwargs)

  def deps2git(self, suffix=None, **kwargs):
    name = 'deps2git'
    if suffix:
      name += ' (%s)' % suffix
    return self.m.python(
        name,
        self.m.path.checkout('tools', 'deps2git', 'deps2git.py'),
        args=['-d', self.m.path.checkout('DEPS'),
              '-o', self.m.path.checkout('.DEPS.git'),
              '--verify',
              '--json', self.m.json.output()],
        **kwargs)

  def deps2submodules(self, **kwargs):
    return self.m.python(
        'deps2submodules',
        self.m.path.checkout('tools', 'deps2git', 'deps2submodules.py'),
        args=['--gitless', self.m.path.checkout('.DEPS.git')],
        **kwargs)
