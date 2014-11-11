# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'file',
  'gclient',
  'path',
  'platform',
  'properties',
  'python',
  'step',
]


# List of the benchmark that we run during the profiling step.
_BENCHMARKS_TO_RUN = {
  'peacekeeper.dom',
  'peacekeeper.array',
  'peacekeeper.html5',
  'peacekeeper.string',
  'peacekeeper.render',
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
  'jsgamebench',
}


# Run the profiling benchmarks.
def RunBenchmarks(api):
  pgosweep_path = api.path['depot_tools'].join(
      'win_toolchain', 'vs2013_files', 'VC', 'bin')
  pgo_env = {'PATH': '%s;%s' % (pgosweep_path, '%(PATH)s')}
  pgo_args = ['--profiler=win_pgo_profiler', '--use-live-sites']

  for benchmark in _BENCHMARKS_TO_RUN:
    api.chromium.run_telemetry_benchmark(benchmark_name=benchmark,
                                         cmd_args=pgo_args,
                                         env=pgo_env)


def GenSteps(api):
  api.step.auto_resolve_conflicts = True
  api.chromium.set_config('chromium_pgo_instrument', BUILD_CONFIG='Release')
  api.gclient.set_config('chromium_lkgr')

  api.chromium.taskkill()
  api.bot_update.ensure_checkout()

  api.chromium.runhooks()

  # Remove the profile files from the previous builds.
  api.path.rmwildcard('*.pg[cd]', str(api.chromium.output_dir))

  # First step: compilation of the instrumented build.
  api.chromium.compile()

  # Second step: profiling of the instrumented build.
  RunBenchmarks(api)

  # Third step: Compilation of the optimized build, this will use the profile
  #     data files produced by the previous step.
  api.chromium.set_config('chromium_pgo_optimize', BUILD_CONFIG='Release')
  api.chromium.runhooks()
  api.chromium.compile()


def GenTests(api):
  mastername = 'chromium.fyi'
  buildername = 'Chromium Win PGO Builder'

  def _sanitize_nonalpha(text):
    return ''.join(c if c.isalnum() else '_' for c in text)

  yield (
    api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                             _sanitize_nonalpha(buildername))) +
    api.properties.generic(mastername=mastername, buildername=buildername) +
    api.platform('win', 32)
  )
