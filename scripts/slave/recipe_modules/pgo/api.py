# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

# List of the benchmark that we run during the profiling step.
#
# TODO(sebmarchand): Move this into a BenchmarkSuite in telemetry, this way
# only have to run one benchmark.
_BENCHMARKS_TO_RUN = {
  'dromaeo.domcoreattr',
  'dromaeo.domcoremodify',
  'dromaeo.domcorequery',
  'dromaeo.domcoretraverse',
  'dromaeo.jslibattrjquery',
  'dromaeo.jslibattrprototype',
  'dromaeo.jslibeventjquery',
  'dromaeo.jslibeventprototype',
  'dromaeo.jslibmodifyjquery',
  'dromaeo.jslibmodifyprototype',
  'dromaeo.jslibstylejquery',
  'dromaeo.jslibstyleprototype',
  'dromaeo.jslibtraversejquery',
  'dromaeo.jslibtraverseprototype',
  'sunspider',
}


class PGOApi(recipe_api.RecipeApi):
  """
  PGOApi encapsulate the various step involved in a PGO build.
  """

  def __init__(self, **kwargs):
    super(PGOApi, self).__init__(**kwargs)


  def _compile_instrumented_image(self, recipe_config):
    """
    Generates the instrumented version of the binaries.
    """
    self.m.chromium.set_config(recipe_config['chromium_config_instrument'],
                            **recipe_config.get('chromium_config_kwargs'))
    self.m.chromium.runhooks(name='Runhooks: Instrumentation phase.')
    # Remove the profile files from the previous builds.
    self.m.path.rmwildcard('*.pg[cd]', str(self.m.chromium.output_dir))
    self.m.chromium.compile(name='Compile: Instrumentation phase.')


  def _run_pgo_benchmarks(self):
    """
    Run a suite of telemetry benchmarks to generate some profiling data.
    """
    pgosweep_path = self.m.path['depot_tools'].join(
        'win_toolchain', 'vs2013_files', 'VC', 'bin')
    pgo_env = {'PATH': '%s;%s' % (pgosweep_path, '%(PATH)s')}
    pgo_args = ['--profiler=win_pgo_profiler', '--use-live-sites']

    for benchmark in _BENCHMARKS_TO_RUN:
      try:
        self.m.chromium.run_telemetry_benchmark(benchmark_name=benchmark,
                                                cmd_args=pgo_args,
                                                env=pgo_env)
      except self.m.step.StepFailure:
        # Turn the failures into warning, we shouldn't stop the build for a
        # benchmark.
        step_result = self.m.step.active_result
        step_result.presentation.status = self.m.step.WARNING


  def _compile_optimized_image(self, recipe_config):
    """
    Generates the optimized version of the binaries.
    """
    self.m.chromium.set_config(recipe_config['chromium_config_optimize'],
                            **recipe_config.get('chromium_config_kwargs'))
    self.m.chromium.runhooks(name='Runhooks: Optimization phase.')
    self.m.chromium.compile(name='Compile: Optimization phase.')


  def compile_pgo(self):
    """
    Do a PGO build. This takes care of building an instrumented image, profiling
    it and then compiling the optimized version of it.
    """
    buildername = self.m.properties['buildername']
    mastername = self.m.properties['mastername']
    master_dict = self.m.chromium.builders.get(mastername, {})
    recipe_config = master_dict.get('builders', {}).get(buildername)

    self.m.gclient.set_config(recipe_config['gclient_config'])

    # Augment the solution if needed.
    self.m.gclient.c.solutions[0].url += recipe_config.get('url_suffix', '')

    if self.m.properties.get('slavename') != 'fake_slave':
      self.m.chromium.taskkill()

    self.m.bot_update.ensure_checkout(
        patch_root=recipe_config.get('patch_root', None))

    # First step: compilation of the instrumented build.
    self._compile_instrumented_image(recipe_config)

    # Second step: profiling of the instrumented build.
    self._run_pgo_benchmarks()

    # Increase the stack size of pgomgr.exe.
    #
    # TODO(sebmarchand): Remove this once the bug has been fixed.
    self.m.python('increase pgomgr.exe stack size',
        self.resource('increase_pgomgr_stack_size.py'),
        args=[self.m.path['depot_tools'].join(
            'win_toolchain', 'vs2013_files', 'VC', 'bin', 'amd64_x86')],
        cwd=self.m.path['slave_build'])

    # Third step: Compilation of the optimized build, this will use the profile
    #     data files produced by the previous step.
    self._compile_optimized_image(recipe_config)
