#! /usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=R0201

"""Log parsing for telemetry tests."""

import json
import logging
import os
import tempfile


class TelemetryResultsProcessor(object):

  def __init__(self):
    self._chart_filename = None
    self._ref_chart_filename = None

  def GetArguments(self):
    if not self._chart_filename:
      handle = tempfile.NamedTemporaryFile(delete=False)
      self._chart_filename = handle.name
      handle.close()
    if not self._ref_chart_filename:
      handle = tempfile.NamedTemporaryFile(delete=False)
      self._ref_chart_filename = handle.name
      handle.close()
    return (['--chart-output-filename', self._chart_filename,
             '--ref-output-filename', self._ref_chart_filename])

  def _GetFileJson(self, filename):
    try:
      return json.load(open(filename))
    except (IOError, ValueError):
      logging.error('Error reading telemetry results from %s', filename)
      return None

  def ChartJson(self):
    return self._GetFileJson(self._chart_filename)

  def RefChartJson(self):
    return self._GetFileJson(self._ref_chart_filename)

  def Cleanup(self):
    try:
      os.remove(self._chart_filename)
    except OSError:
      logging.error('Unable to remove telemetry output file %s',
                    self._chart_filename)
    try:
      os.remove(self._ref_chart_filename)
    except OSError:
      logging.error('Unable to remove telemetry ref output file %s',
                    self._ref_chart_filename)

  def IsChartJson(self):
    """This is the new telemetry --chartjson output format."""
    return True

  def ProcessLine(self, line):
    pass

  def FailedTests(self):
    return []

  def SuppressionHashes(self):  # pylint: disable=R0201
    return []

  def ParsingErrors(self):  # pylint: disable=R0201
    return []

  def PerformanceSummary(self):
    return ''
