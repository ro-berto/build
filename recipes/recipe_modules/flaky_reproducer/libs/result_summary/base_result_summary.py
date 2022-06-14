# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


class BaseResultSummary:
  """
  Collection of all test results within a run.

  Attributes:
    results (TestResult): A list of TestResult.
  """
  pass


class BaseTestResult:
  """
  A result of a test case.
  Often a single test case is executed multiple times and has multiple results.

  Attributes:
    [TBD]
  """
  pass
