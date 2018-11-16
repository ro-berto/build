# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Log parsing for non-Telemetry tests that output data in HistogramSets.

This is specifically not meant for Telemetry tests, as those should all be using
the src-side scripts for dashboard uploading via the "merge script"
functionality. This is a temporary solution for non-Telemetry tests that still
use the build-side code for dashboard uploading.

This is based off telemetry_utils.TelemetryResultsProcessor.
"""

import json
import logging
import os
import shutil

class HistogramResultsParser(object):

  def __init__(self, filename, is_ref, cleanup_parent_dir):
    self._histogram_filename = filename
    self._is_reference_build = is_ref
    self._cleanup_parent_dir = cleanup_parent_dir

  def HistogramSet(self):
    try:
      with open(self._histogram_filename) as f:
        return json.load(f)
    except (IOError, ValueError) as e:
      logging.error('Error reading histogram results from %s',
          self._histogram_filename)
      logging.error('Given error is %s', e)
    return None

  def Cleanup(self):
    try:
      os.remove(self._histogram_filename)
    except OSError as e:
      logging.error('Unable to remove HistogramSet output file %s',
          self._histogram_filename)
      logging.error('Given error is %s', e)
    if self._cleanup_parent_dir:
      try:
        shutil.rmtree(os.path.dirname(self._histogram_filename))
      except OSError as e:
        logging.error('Unable to remve output directory %s',
            os.path.dirname(self._histogram_filename))
        logging.error('Given error is %s', e)

  def IsChartJson(self):
    """This is not the deprecated ChartJSON format."""
    return False

  def IsHistogramSet(self):
    """This is the newer HistogramSet format that replaces ChartJSON."""
    return True

  def HistogramFilename(self):
    return self._histogram_filename

  def IsReferenceBuild(self):
    return self._is_reference_build

  def ProcessLine(self, line):
    pass

  def FailedTests(self):
    return []

  def MemoryToolReportHashes(self):
    return []

  def ParsingErrors(self):
    return []

  def PerformanceSummary(self):
    return []
