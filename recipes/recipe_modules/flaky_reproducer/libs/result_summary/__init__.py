# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .gtest_result_summary import GTestTestResultSummary


def create_result_summary_from_output_json(json):
  """Factory method for TestResultSummary(s) that distinguish and create the
  correct TestResultSummary object."""
  return GTestTestResultSummary()
