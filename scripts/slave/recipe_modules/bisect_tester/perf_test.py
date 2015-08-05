# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import re
import time

from . import parse_metric


def _set_output_dir(command, output_dir):  # pragma: no cover
  placeholder = "OUTPUTDIRGOESHERE"
  new_arg = '--output-dir=' + output_dir
  if not '--output-dir' in command:
    return '%s %s' % (command, new_arg)
  else:
    out_dir_regex = re.compile(
        r"--output-dir[= ](?P<path>([\"'][^\"']+[\"']|\S+))")
    # Backslash escape sequences in the replacement string given to |re.sub| are
    # processed -- that is, \t is converted to a tab character, etc. Hence we
    # use a placeholder with no backslashes and later replace with str.replace.
    command = out_dir_regex.sub(placeholder, command)
    return command.replace(placeholder, new_arg)


def _is_telemetry_command(command):
  """Attempts to discern whether or not a given command is running telemetry."""
  return 'run_benchmark' in command


def run_perf_test(api, test_config, **kwargs):
  """Runs the command N times and parses a metric from the output."""
  # TODO(prasadv):  Consider extracting out the body of the for loop into
  # a helper method, or extract the metric-extraction to make this more cleaner.
  limit = test_config['max_time_minutes'] * kwargs.get('time_multiplier', 1)
  values = []
  metric = test_config.get('metric')
  retcodes = []
  output_for_all_runs = []
  temp_dir = None
  repeat_cnt = test_config['repeat_count']

  command = test_config['command']
  use_chartjson = bool('chartjson' in command)
  is_telemetry = _is_telemetry_command(command)
  start_time = time.time()
  for i in range(repeat_cnt):
    elapsed_minutes = (time.time() - start_time) / 60.0
    if elapsed_minutes >= limit:  # pragma: no cover
      break
    if is_telemetry:
      if i == 0 and kwargs.get('reset_on_first_run'):
        command += ' --reset-results'
      if i == repeat_cnt - 1 and kwargs.get('upload_on_last_run'):
        command += ' --upload-results'
      if kwargs.get('results_label'):
        command += ' --results-label=%s' % kwargs.get('results_label')
    if use_chartjson:  # pragma: no cover
      temp_dir = api.m.path.mkdtemp('perf-test-output')
      command = _set_output_dir(command, str(temp_dir))
      results_path = temp_dir.join('results-chart.json')

    step_name = "Performance Test%s %d/%d" % (
        ' (%s)' % kwargs['name'] if 'name' in kwargs else '', i + 1, repeat_cnt)
    if api.m.platform.is_linux:
      os.environ['CHROME_DEVEL_SANDBOX'] = api.m.path.join(
          '/opt', 'chromium', 'chrome_sandbox')
    out, err, retcode = _run_command(api, command, step_name)

    if out is None and err is None:
      # dummy value when running test TODO: replace with a mock
      values.append(0)
    elif metric:  # pragma: no cover
      if use_chartjson:
        file_contents = api.m.file.read(
            'Reading chartjson results', results_path)
        valid_value, value, result = parse_metric.parse_chartjson_metric(
            file_contents, metric)
      else:
        valid_value, value = parse_metric.parse_metric(
            out, err, metric.split('/'))
      output_for_all_runs.append(out)
      if valid_value:
        values.extend(value)
    else:
      output_for_all_runs.append(out)
    retcodes.append(retcode)

  return values, output_for_all_runs, retcodes


def truncate_and_aggregate(api, values, truncate_percent):
  if not values:  # pragma: no cover
    return {'error': 'No values to aggregate.'}
  truncate_proportion = truncate_percent / 100.0
  mean = api.m.math_utils.truncated_mean(values, truncate_proportion)
  std_err = api.m.math_utils.standard_error(values)
  return {'mean': mean, 'std_err': std_err, 'values': values}


def _run_command(api, command, step_name):
  # TODO(robertocn): Reevaluate this approach when adding support for non-perf
  # tests and non-linux platforms.
  if api.m.platform.is_linux and 'xvfb' not in command:
    command = 'xvfb-run -a ' + command
  command_parts = command.split()
  stdout = api.m.raw_io.output()
  stderr = api.m.raw_io.output()
  try:
    step_result = api.m.step(
        step_name,
        command_parts,
        stdout=stdout,
        stderr=stderr)
  except api.m.step.StepFailure as sf:
    return sf.result.stdout, sf.result.stderr, sf.result.retcode
  return step_result.stdout, step_result.stderr, step_result.retcode
