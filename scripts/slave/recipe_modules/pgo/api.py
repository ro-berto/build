# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


# List of the benchmark that we run during the profiling step.
#
# TODO(sebmarchand): Move this into a BenchmarkSuite in telemetry, this way
# only have to run one benchmark.
_BENCHMARKS_TO_RUN = {
  'blink_perf.bindings',
  'blink_perf.canvas',
  'blink_perf.css',
  'blink_perf.dom',
  'blink_perf.paint',
  'blink_perf.svg',
  'blink_style.top_25',
  'dromaeo.cssqueryjquery',
  'dromaeo.domcoreattr',
  'dromaeo.domcoremodify',
  'dromaeo.domcorequery',
  'dromaeo.domcoretraverse',
  'dromaeo.jslibattrprototype',
  'dromaeo.jslibeventprototype',
  'dromaeo.jslibmodifyprototype',
  'dromaeo.jslibstyleprototype',
  'dromaeo.jslibtraversejquery',
  'dromaeo.jslibtraverseprototype',
  'indexeddb_perf',
  'media.tough_video_cases',
  'octane',
  'smoothness.top_25_smooth',
  'speedometer',
  'sunspider',
}


class PGOApi(recipe_api.RecipeApi):
  """
  PGOApi encapsulate the various step involved in a PGO build.
  """

  def __init__(self, **kwargs):
    super(PGOApi, self).__init__(**kwargs)

  def _compile_instrumented_image(self, bot_config):
    """
    Generates the instrumented version of the binaries.
    """
    self.m.chromium.set_config(bot_config['chromium_config_instrument'],
                               **bot_config.get('chromium_config_kwargs'))
    self.m.chromium.runhooks(name='Runhooks: Instrumentation phase.')
    self.m.chromium.run_mb(
        self.m.properties['mastername'],
        self.m.properties['buildername'],
        use_goma=False,
        phase=1)
    # Remove the profile files from the previous builds.
    self.m.file.rmwildcard('*.pg[cd]', str(self.m.chromium.output_dir))
    self.m.chromium.compile(name='Compile: Instrumentation phase.')

  def _run_pgo_benchmarks(self):
    """
    Run a suite of telemetry benchmarks to generate some profiling data.
    """
    args = [
        '--browser-type', self.m.chromium.c.build_config_fs.lower(),
        '--target-cpu', self.m.chromium.c.gyp_env.GYP_DEFINES['target_arch'],
        '--build-dir', self.m.chromium.output_dir,
    ]
    self.m.python(
        'Profiling benchmarks.',
        self.m.path['checkout'].join('build', 'win',
                                     'run_pgo_profiling_benchmarks.py'),
        args)

  def _compile_optimized_image(self, bot_config):
    """
    Generates the optimized version of the binaries.
    """
    self.m.chromium.set_config(bot_config['chromium_config_optimize'],
                               **bot_config.get('chromium_config_kwargs'))
    self.m.chromium.runhooks(name='Runhooks: Optimization phase.')
    self.m.chromium.run_mb(
        self.m.properties['mastername'],
        self.m.properties['buildername'],
        use_goma=False,
        phase=2)
    self.m.chromium.compile(name='Compile: Optimization phase.')

  def compile_pgo(self, bot_config):
    """
    Do a PGO build. This takes care of building an instrumented image, profiling
    it and then compiling the optimized version of it.
    """
    self.m.gclient.set_config(bot_config['gclient_config'])

    # Augment the DEPS path if needed.
    if '%s' in self.m.gclient.c.solutions[0].deps_file:  # pragma: no cover
      self.m.gclient.c.solutions[0].deps_file = (
        self.m.gclient.c.solutions[0].deps_file % bot_config['bucket'])

    if self.m.properties.get('slavename') != 'fake_slave':
      self.m.chromium.taskkill()

    self.m.bot_update.ensure_checkout()
    if bot_config.get('patch_root'):
      self.m.path['checkout'] = self.m.path['slave_build'].join(
          bot_config.get('patch_root'))

    # First step: compilation of the instrumented build.
    self._compile_instrumented_image(bot_config)

    # Second step: profiling of the instrumented build.
    self._run_pgo_benchmarks()

    # Third step: Compilation of the optimized build, this will use the
    #     profile data files produced by the previous step.
    self._compile_optimized_image(bot_config)
