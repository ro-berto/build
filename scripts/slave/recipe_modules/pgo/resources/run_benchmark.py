#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Run a profiling benchmark for a PGO build.

This wrapper script is required so we can find the path to pgosweep.exe.
"""

import json
import optparse
import os
import subprocess
import sys


def find_pgosweep(chrome_checkout_dir, target_bits):
  """Find the directory containing pgosweep.exe."""
  win_toolchain_json_file = os.path.join(chrome_checkout_dir, 'build',
      'win_toolchain.json')
  if not os.path.exists(win_toolchain_json_file):
    print 'The toolchain JSON file is missing.'
    return
  with open(win_toolchain_json_file) as temp_f:
    toolchain_data = json.load(temp_f)
  if not os.path.isdir(toolchain_data['path']):
    print 'The toolchain JSON file is invalid.'
    return

  pgo_sweep_dir = os.path.join(toolchain_data['path'], 'VC', 'bin')
  if target_bits == 64:
    pgo_sweep_dir = os.path.join(pgo_sweep_dir, 'amd64')

  if not os.path.exists(os.path.join(pgo_sweep_dir, 'pgosweep.exe')):
    print 'pgosweep.exe is missing from %s.' % pgo_sweep_dir
    return

  return pgo_sweep_dir


def main():
  parser = optparse.OptionParser(usage='%prog [options]')
  parser.add_option(
       '--checkout-dir', help='The Chrome checkout directory.')
  parser.add_option(
      '--browser-type', help='The browser type (to be passed to Telemetry\'s '
                              'benchmark runner).')
  parser.add_option('--target-bits', help='The target\'s bitness.', type=int)
  parser.add_option('--benchmark', help='The benchmark to run.')
  parser.add_option('--build-dir', help='Chrome build directory.')
  options, _ = parser.parse_args()

  if not options.checkout_dir:
    parser.error('--checkout-dir is required')
  if not options.browser_type:
    parser.error('--browser-type is required')
  if not options.target_bits:
    parser.error('--target-bits is required')
  if not options.benchmark:
    parser.error('--benchmark is required')
  if not options.build_dir:
    parser.error('--build-dir is required')

  # Starts by finding the directory containing pgosweep.exe
  pgo_sweep_dir = find_pgosweep(options.checkout_dir, options.target_bits)
  if not pgo_sweep_dir:
    return 1

  # Then find the run_benchmark script.
  chrome_run_benchmark_script = os.path.join(options.checkout_dir, 'tools',
                                             'perf', 'run_benchmark')
  if not os.path.exists(chrome_run_benchmark_script):
    print ('Unable to find the run_benchmark script (%s doesn\'t exist) ' %
           chrome_run_benchmark_script)
    return 1

  # Augment the PATH to make sure that the benchmarking script can find
  # pgosweep.exe and its runtime libraries.
  env = os.environ.copy()
  env['PATH'] = str(os.pathsep.join([pgo_sweep_dir, options.build_dir,
                                     os.environ['PATH']]))
  env['PogoSafeMode'] = '1'
  # Apply a scaling factor of 0.5 to the PGO profiling buffers for the 32-bit
  # builds, without this the buffers will be too large and the process will
  # fail to start. See crbug.com/632864#c22.
  if options.target_bits == 32:
    env['VCPROFILE_ALLOC_SCALE'] = '0.5'

  benchmark_command = [
      sys.executable,
      chrome_run_benchmark_script,
      '--browser', options.browser_type,
      '--profiler', 'win_pgo_profiler',
      options.benchmark
    ]
  return subprocess.call(benchmark_command, env=env)


if __name__ == '__main__':
  sys.exit(main())
