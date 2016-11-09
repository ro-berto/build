# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import re
import shlex
import time

from . import parse_metric


class Metric(object):  # pragma: no cover
  OLD_STYLE_DELIMITER = '-'
  NEW_STYLE_DELIMITER = '@@'

  def __init__(self, metric_string):
    parts = metric_string.split('/')
    self.chart_name = None
    self.interaction_record_name = None
    self.trace_name = None

    if len(parts) == 3:
      # chart/interaction/trace
      self.chart_name = parts[0]
      self.interaction_record_name = parts[1]
      self.trace_name = parts[2]

    if len(parts) == 2:
      self.chart_name = parts[0]
      if parts[0] != parts[1]:
        self.trace_name = parts[1]

  def as_pair(self, delimiter=NEW_STYLE_DELIMITER):
    """Returns a pair of strings which represents a metric.

    The first part is the chart part, which may contain an interaction record
    name if applicable. The second part is the trace part, which is the same
    as the first part if we want to get the summary result.

    Args:
      delimiter: The separator between interaction name and chart name.

    Returns:
      A pair of strings, or (None, None) if the metric is invalid.
    """
    first_part = self.chart_name
    if self.interaction_record_name is not None:
      first_part = self.interaction_record_name + delimiter + self.chart_name
    if self.trace_name is not None:
      second_part = self.trace_name
    else:
      second_part = first_part
    return (first_part, second_part)


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
  # a helper method, or extract the metric-extraction to make this more
  # cleaner.
  limit = test_config['max_time_minutes'] * kwargs.get('time_multiplier', 1)
  run_results = {'measured_values': [], 'errors': set()}
  values = run_results['measured_values']
  metric = test_config.get('metric')
  retcodes = []
  output_for_all_runs = []
  temp_dir = None
  repeat_cnt = test_config['repeat_count']

  command = test_config['command']
  use_chartjson = bool('chartjson' in command)
  is_telemetry = _is_telemetry_command(command)
  start_time = time.time()

  if api.m.chromium.c.TARGET_PLATFORM == 'android' and is_telemetry:
    device_serial_number = api.device_to_test;
    if device_serial_number:
      command += ' --device ' + device_serial_number # pragma: no cover

  for i in range(repeat_cnt):
    elapsed_minutes = (time.time() - start_time) / 60.0
    # A limit of 0 means 'no timeout set'.
    if limit and elapsed_minutes >= limit:  # pragma: no cover
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

    step_name = "Performance Test%s %d of %d" % (
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
        step_result = api.m.json.read(
            'Reading chartjson results', results_path)
        has_valid_value, value = find_values(
            step_result.json.output, Metric(metric))
      else:
        has_valid_value, value = parse_metric.parse_metric(
            out, err, metric.split('/'))
      output_for_all_runs.append(out)
      if has_valid_value:
        values.extend(value)
      else:
        # This means the metric was not found in the output.
        if not retcode:
          # If all tests passed, but the metric was not found, this means that
          # something changed on the test, or the given metric name was
          # incorrect, we need to surface this on the bisector.
          run_results['errors'].add('MISSING_METRIC')
    else:
      output_for_all_runs.append(out)
    retcodes.append(retcode)

  return run_results, output_for_all_runs, retcodes


def find_values(results, metric):  # pragma: no cover
  """Tries to extract the given metric from the given results.

  This method tries several different possible chart names depending
  on the given metric.

  Args:
    results: The chartjson dict.
    metric: A Metric instance.

  Returns:
    A pair (has_valid_value, value), where has_valid_value is a boolean,
    and value is the value(s) extracted from the results.
  """
  has_valid_value, value, _ = parse_metric.parse_chartjson_metric(
      results, metric.as_pair())
  if has_valid_value:
    return True, value

  # TODO(eakuefner): Get rid of this fallback when bisect uses ToT Telemetry.
  has_valid_value, value, _ = parse_metric.parse_chartjson_metric(
        results, metric.as_pair(Metric.OLD_STYLE_DELIMITER))
  if has_valid_value:
    return True, value

  # If we still haven't found a valid value, it's possible that the metric was
  # specified as interaction-chart/trace or interaction-chart/interaction-chart,
  # and the chartjson chart names use @@ as the separator between interaction
  # and chart names.
  if Metric.OLD_STYLE_DELIMITER not in metric.chart_name:
    return False, []  # Give up; no results found.
  interaction, chart = metric.chart_name.split(Metric.OLD_STYLE_DELIMITER, 1)
  metric.interaction_record_name = interaction
  metric.chart_name = chart
  has_valid_value, value, _ = parse_metric.parse_chartjson_metric(
      results, metric.as_pair())
  return has_valid_value, value

def _rebase_path(api, file_path):
  """Attempts to make an absolute path for the command.

  We want to pass to runtest.py an absolute path if possible.
  """
  if (file_path.startswith('src/') or file_path.startswith('./src/')):
    return api.m.path['checkout'].join(
        *file_path.split('src', 1)[1].split('/')[1:])
  elif (file_path.startswith('src\\') or
        file_path.startswith('.\\src\\')):  # pragma: no cover
    return api.m.path['checkout'].join(
        *file_path.split('src', 1)[1].split('\\')[1:])
  return file_path

def _run_command(api, command, step_name):
  command_parts = shlex.split(command)
  stdout = api.m.raw_io.output()
  stderr = api.m.raw_io.output()

  # TODO(prasadv): Remove this once bisect runs are no longer running
  # against revisions from February 2016 or earlier.
  kwargs = {}
  if 'android-chrome' in command:  # pragma: no cover
    kwargs['env'] = {'CHROMIUM_OUTPUT_DIR': api.m.chromium.output_dir}

  # By default, we assume that the test to run is an executable binary. In the
  # case of python scripts, runtest.py will guess based on the extension.
  python_mode = False
  if command_parts[0] == 'python':  # pragma: no cover
    # Dashboard prepends the command with 'python' when on windows, however, it
    # is not necessary to pass this along to the runtest.py invocation.
    # TODO(robertocn): Remove this clause when dashboard stops sending python as
    # part of the command.
    # https://github.com/catapult-project/catapult/issues/2283
    command_parts = command_parts[1:]
    python_mode = True
  elif _is_telemetry_command(command):
    # run_benchmark is a python script without an extension, hence we force
    # python mode.
    python_mode = True
  try:
    step_result = api.m.chromium.runtest(
        test=_rebase_path(api, command_parts[0]),
        args=command_parts[1:],
        xvfb=True,
        name=step_name,
        python_mode=python_mode,
        stdout=stdout,
        stderr=stderr,
        **kwargs)
    step_result.presentation.logs['Captured Output'] = (
        step_result.stdout or '').splitlines()
  except api.m.step.StepFailure as sf:
    sf.result.presentation.logs['Failure Output'] = (
        sf.result.stdout or '').splitlines()
    if sf.result.stderr:  # pragma: no cover
      sf.result.presentation.logs['stderr'] = (
        sf.result.stderr).splitlines()
    return sf.result.stdout, sf.result.stderr, sf.result.retcode
  return step_result.stdout, step_result.stderr, step_result.retcode
