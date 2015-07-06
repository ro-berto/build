# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import re
import time

from . import parse_metric


def _set_output_dir(command, output_dir):  # pragma: no cover
  new_arg = '--output-dir=' + output_dir
  if not '--output-dir' in command:
    return '%s %s' % (command, new_arg)
  else:
    out_dir_regex = re.compile(
        r"--output-dir[= ](?P<path>([\"'][^\"']+[\"']|\S+))")
    return out_dir_regex.sub(new_arg, command)

def run_perf_test(api, test_config):
  """Runs the command N times and parses a metric from the output."""
  limit = time.time() + test_config['timeout_seconds']
  values = []
  metric = test_config['metric'].split('/')
  retcodes = []
  command = test_config['command']
  use_chartjson = bool('chartjson' in command)
  output_for_all_runs = []
  temp_dir = None
  for i in range(test_config['repeat_count']):
    if time.time() < limit:
      if use_chartjson:  # pragma: no cover
        temp_dir = api.m.path.mkdtemp('perf-test-output')
        command = _set_output_dir(command, str(temp_dir))
        results_path = temp_dir.join('results-chart.json')

      command_name = "Performance Test %d/%d" % (i + 1,
                                                 test_config['repeat_count'])
      if api.m.platform.is_linux:
        os.environ['CHROME_DEVEL_SANDBOX'] = api.m.path.join(
            '/opt', 'chromium', 'chrome_sandbox')
      out, err, retcode = _run_command(api, command, command_name)

      if out is None and err is None:
        # dummy value when running test TODO: replace with a mock
        values.append(0)
        retcodes.append(retcode)
      else:  # pragma: no cover
        if use_chartjson:
          file_contents = api.m.file.read('Reading chartjson results',
                                          results_path)
          valid_value, value, result = parse_metric.parse_chartjson_metric(
              file_contents, metric)
          output_for_all_runs.append(result)
        else:
          valid_value, value = parse_metric.parse_metric(out, err, metric)
          output_for_all_runs.append(out)
        retcodes.append(retcode)
        if valid_value:
          values.extend(value)
    else:  # pragma: no cover
      break
  return values, output_for_all_runs, retcodes


def truncate_and_aggregate(api, values, truncate_percent):
  if not values: #pragma: no cover
    return {'error': 'No values to aggregate.'}
  truncate_proportion = truncate_percent / 100.0
  mean = api.m.math_utils.truncated_mean(values, truncate_proportion)
  std_err = api.m.math_utils.standard_error(values)
  return {'mean': mean, 'std_err': std_err, 'values': values}


def _run_command(api, command, command_name):

  # TODO(robertocn): Reevaluate this approach when adding support for non-perf
  # tests and non-linux platforms.
  if api.m.platform.is_linux and 'xvfb' not in command:
    command = 'xvfb-run -a ' + command
  command_parts = command.split()
  stdout = api.m.raw_io.output()
  stderr = api.m.raw_io.output()
  try:
    step_result = api.m.step(
        command_name,
        command_parts,
        stdout=stdout,
        stderr=stderr)
  except api.m.step.StepFailure as sf:
    return sf.result.stdout, sf.result.stderr, sf.result.retcode
  return step_result.stdout, step_result.stderr, step_result.retcode
