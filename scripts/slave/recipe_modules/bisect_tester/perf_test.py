# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import re
import time
import uuid


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

def _is_gtest_with_buildbot_output(command):
  """Attempts to discern whether or not a given command is an old style gtest
  that generates buildbot output."""
  GTESTS_WITH_BUILDBOT_OUTPUT = [
      'angle_perftests', 'cc_perftests', 'idb_perf',
      'performance_browser_tests', 'load_library_perf_tests', 'media_perftests'
  ]
  return any([t in command for t in GTESTS_WITH_BUILDBOT_OUTPUT])

def _make_results_dir(api):
  new_dir = 'dummy' if api._test_data.enabled else str(uuid.uuid4())
  full_path = api.m.path['bisect_results'].join(new_dir)
  api.m.file.ensure_directory('results directory', full_path)
  return full_path

def run_perf_test(api, test_config, **kwargs):
  """Runs the command N times and parses a metric from the output."""
  # TODO(prasadv):  Consider extracting out the body of the for loop into
  # a helper method, or extract the metric-extraction to make this more
  # cleaner.
  limit = test_config['max_time_minutes'] * kwargs.get('time_multiplier', 1)
  results = {'valueset_paths': [], 'chartjson_paths': [], 'errors': set(),
             'retcodes': [], 'stdout_paths': [], 'output': []}
  metric = test_config.get('metric')
  temp_dir = None
  repeat_count = test_config['repeat_count']

  command = test_config['command']
  use_chartjson = bool('chartjson' in command)
  use_valueset = bool('valueset' in command)
  use_buildbot = _is_gtest_with_buildbot_output(command)
  is_telemetry = _is_telemetry_command(command)
  start_time = time.time()

  if api.m.chromium.c.TARGET_PLATFORM == 'android' and is_telemetry:
    device_serial_number = api.device_to_test;
    if device_serial_number:
      command += ' --device ' + device_serial_number # pragma: no cover

  for i in range(repeat_count):
    elapsed_minutes = (time.time() - start_time) / 60.0
    # A limit of 0 means 'no timeout set'.
    if limit and elapsed_minutes >= limit:  # pragma: no cover
      break
    if is_telemetry:
      if i == 0 and kwargs.get('reset_on_first_run'):
        command += ' --reset-results'
      if i == repeat_count - 1 and kwargs.get('upload_on_last_run'):
        command += ' --upload-results'
      if kwargs.get('results_label'):
        command += ' --results-label=%s' % kwargs.get('results_label')
    temp_dir = _make_results_dir(api)
    if use_chartjson or use_valueset:  # pragma: no cover
      command = _set_output_dir(command, str(temp_dir))
      chartjson_path = temp_dir.join('results-chart.json')
      valueset_path = temp_dir.join('results-valueset.json')

      if '{CHROMIUM_OUTPUT_DIR}' in command:
        command = command.replace(
            '{CHROMIUM_OUTPUT_DIR}', str(api.m.chromium.output_dir))

    step_name = "Performance Test%s %d of %d" % (
        ' (%s)' % kwargs['name'] if 'name' in kwargs else '',
        i + 1, repeat_count)
    if api.m.platform.is_linux:
      os.environ['CHROME_DEVEL_SANDBOX'] = api.m.path.join(
          '/opt', 'chromium', 'chrome_sandbox')
    out, _, retcode = _run_command(api, command, step_name, **kwargs)
    results['output'].append(out or '')
    if out:
      # Write stdout to a local temp location for possible buildbot parsing
      stdout_path = temp_dir.join('results.txt')
      api.m.file.write_text('write buildbot output to disk', stdout_path, out)

      if use_buildbot:
        results['stdout_paths'].append(stdout_path)

    if metric:
      if use_chartjson:
        try:
          step_result = api.m.json.read(
              'Reading chartjson results', chartjson_path)
        except api.m.step.StepFailure:  # pragma: no cover
          pass
        else:
          if step_result.json.output:  # pragma: no cover
            results['chartjson_paths'].append(chartjson_path)
      if use_valueset:
        try:
          step_result = api.m.json.read(
              'Reading valueset results', valueset_path,
              step_test_data=lambda: api.m.json.test_api.output(
                  {'dummy':'dict'}))
        except api.m.step.StepFailure:  # pragma: no cover
          pass
        else:
          if step_result.json.output:
            results['valueset_paths'].append(valueset_path)
    results['retcodes'].append(retcode)
  return results

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

def _run_command(api, command, step_name, **kwargs):
  command_parts = command.split()
  stdout_proxy = api.m.raw_io.output_text(name='stdout_proxy')
  stderr = api.m.raw_io.output_text()

  inner_kwargs = {}
  if 'step_test_data' in kwargs:
    inner_kwargs['step_test_data'] = (
        lambda: kwargs['step_test_data']() +
                api.m.raw_io.test_api.output_text('benchmark text',
                                             name='stdout_proxy'))
  else:
    inner_kwargs['step_test_data'] = (
        lambda: api.m.raw_io.test_api.output_text('', name='stdout_proxy'))
  # TODO(prasadv): Remove this once bisect runs are no longer running
  # against revisions from February 2016 or earlier.
  env = {}
  if 'android-chrome' in command:
    env = {'CHROMIUM_OUTPUT_DIR': api.m.chromium.output_dir}

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
    with api.m.context(env=env):
      step_result = api.m.chromium.runtest(
          test=_rebase_path(api, command_parts[0]),
          args=command_parts[1:],
          xvfb=True,
          name=step_name,
          python_mode=python_mode,
          tee_stdout_file=stdout_proxy,
          stderr=stderr,
          **inner_kwargs)
    step_result.presentation.logs['Captured Output'] = (
        step_result.raw_io.output_texts.get('stdout_proxy', '')).splitlines()
  except api.m.step.StepFailure as sf:
    sf.result.presentation.status = api.m.step.WARNING
    sf.result.presentation.logs['Failure Output'] = (
        sf.result.raw_io.output_texts.get('stdout_proxy')).splitlines()
    if sf.result.stderr:  # pragma: no cover
      sf.result.presentation.logs['stderr'] = (
        sf.result.stderr).splitlines()
    return (
        sf.result.raw_io.output_texts.get('stdout_proxy'),
        sf.result.stderr, sf.result.retcode)
  return (step_result.raw_io.output_texts.get('stdout_proxy'),
          step_result.stderr, step_result.retcode)
