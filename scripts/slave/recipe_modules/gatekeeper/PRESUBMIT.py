# Copyright (c) 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Local presubmit script for the gatekeeper recipe module directory.

See http://dev.chromium.org/developers/how-tos/depottools/presubmit-scripts.
"""

import os


def CheckChangeOnCommit(input_api, output_api):
  # Run unit tests for the scripts in resources/.
  return input_api.canned_checks.RunUnitTestsInDirectory(
      input_api,
      output_api,
      os.path.join(input_api.PresubmitLocalPath(), 'resources'),
      # TODO(crbug.com/991689): Add more gatekeeper tests as they are fixed.
      whitelist=[r'build_scan_test\.py$'])
