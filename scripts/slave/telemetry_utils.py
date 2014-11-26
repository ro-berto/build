#! /usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=R0201

"""Log parsing for telemetry tests.

The TelemetryResultsProcessor loads and contains results that were output in
JSON format from Telemetry. It can be used as a replacement for the classes in
the performance_log_processor module.
"""

import json
import logging
import os

from slave.performance_log_processor import _FormatHumanReadable


class TelemetryResultsProcessor(object):

  def __init__(self, filename, is_ref):
    self._chart_filename = filename
    self._is_reference_build = is_ref

  def ChartJson(self):
    try:
      return json.load(open(self._chart_filename))
    except (IOError, ValueError):
      logging.error('Error reading telemetry results from %s',
                    self._chart_filename)
    return None

  def Cleanup(self):
    try:
      os.remove(self._chart_filename)
    except OSError:
      logging.error('Unable to remove telemetry output file %s',
                    self._chart_filename)
    try:
      os.rmdir(os.path.dirname(self._chart_filename))
    except OSError:
      logging.error('Unable to remove telemetry output dir %s',
                    os.path.dirname(self._chart_filename))

  def IsChartJson(self):
    """This is the new telemetry --chartjson output format."""
    return True

  def IsReferenceBuild(self):
    return self._is_reference_build

  def ProcessLine(self, line):
    pass

  def FailedTests(self):
    return []

  def SuppressionHashes(self):  # pylint: disable=R0201
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

    results = []
    for chart_name, chart_values in self.ChartJson()['charts'].iteritems():
      if 'summary' in chart_values:
        summary = chart_values['summary']
        if summary['important']:
          mean = sum(summary['values']) / float(len(summary['values']))
          display = '%s: %s' % (chart_name, _FormatHumanReadable(mean))
          results.append(display)
    return results
