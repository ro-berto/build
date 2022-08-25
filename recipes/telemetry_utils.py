#! /usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=R0201

"""Log parsing for telemetry tests.

The TelemetryResultsProcessor loads and contains results that were output in
JSON format from Telemetry.
"""

import json
import logging
import os


def _FormatHumanReadable(number):
  """Formats a float into three significant figures, using metric suffixes.

  Only m, k, and M prefixes (for 1/1000, 1000, and 1,000,000) are used.
  Examples:
    0.0387    => 38.7m
    1.1234    => 1.12
    10866     => 10.8k
    682851200 => 683M
  """
  metric_prefixes = {-3: 'm', 0: '', 3: 'k', 6: 'M'}
  scientific = '%.2e' % float(number)  # 6.83e+005
  e_idx = scientific.find('e')  # 4, or 5 if negative
  digits = float(scientific[:e_idx])  # 6.83
  exponent = int(scientific[e_idx + 1:])  # int('+005') = 5
  while exponent % 3:
    digits *= 10
    exponent -= 1
  while exponent > 6:
    digits *= 10
    exponent -= 1
  while exponent < -3:
    digits /= 10
    exponent += 1
  if digits >= 100:
    # Don't append a meaningless '.0' to an integer number.
    digits = int(digits)
  # Exponent is now divisible by 3, between -3 and 6 inclusive: (-3, 0, 3, 6).
  return '%s%s' % (digits, metric_prefixes[exponent])


class TelemetryResultsProcessor(object):

  def __init__(self, filename, is_ref, cleanup_parent_dir):
    self._chart_filename = filename
    self._is_reference_build = is_ref
    self._cleanup_parent_dir = cleanup_parent_dir

  def ChartJson(self):
    try:
      with open(self._chart_filename) as f:
        return json.load(f)
    except (IOError, ValueError):
      logging.error(
          'Error reading telemetry results from %s', self._chart_filename
      )
      logging.error(
          'This usually means that telemetry did not run, so it could'
          ' not generate the file. Please check the device running the test.'
      )
    return None

  def Cleanup(self):
    try:
      os.remove(self._chart_filename)
    except OSError:
      logging.error(
          'Unable to remove telemetry output file %s', self._chart_filename
      )
    if self._cleanup_parent_dir:
      try:
        os.rmdir(os.path.dirname(self._chart_filename))
      except OSError:
        logging.error(
            'Unable to remove telemetry output dir %s',
            os.path.dirname(self._chart_filename)
        )

  def IsChartJson(self):
    """This is the new telemetry --chartjson output format."""
    return True

  def IsHistogramSet(self):
    """This is not the newer HistogramSet format that replaces ChartJSON."""
    return False

  def IsReferenceBuild(self):
    return self._is_reference_build

  def ProcessLine(self, line):
    pass

  def FailedTests(self):
    return []

  def MemoryToolReportHashes(self):  # pylint: disable=R0201
    return []

  def ParsingErrors(self):  # pylint: disable=R0201
    return []

  def PerformanceSummary(self):
    """Writes the waterfall display text.

    The waterfall contains lines for each important trace, in the form
      tracename: value< (refvalue)>
    """
    if self._is_reference_build:
      return []

    chartjson_data = self.ChartJson()
    if not chartjson_data:
      return []

    charts = chartjson_data.get('charts')
    if not charts:
      return []

    def _summary_to_string(chart_name, chart_values):
      summary = chart_values.get('summary')
      if not summary:
        return None

      important = summary.get('important')
      if not important:
        return None

      value_type = summary.get('type')
      if value_type == 'list_of_scalar_values':
        values = summary.get('values')
        if not values or None in values:
          return '%s: %s' % (chart_name, 'NaN')
        else:
          mean = sum(values) / float(len(values))
          return '%s: %s' % (chart_name, _FormatHumanReadable(mean))
      elif value_type == 'scalar':
        value = summary.get('value')
        if value is None:
          return '%s: %s' % (chart_name, 'NaN')
        else:
          return '%s: %s' % (chart_name, _FormatHumanReadable(value))
      return None

    gen = (
        _summary_to_string(chart_name, chart_values)
        for chart_name, chart_values in sorted(charts.iteritems())
    )
    return [i for i in gen if i]
