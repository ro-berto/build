# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Local presubmit script for the auto_bisect_staging recipe module directory.

See http://dev.chromium.org/developers/how-tos/depottools/presubmit-scripts.
"""

import os


def CommonChecks(input_api, output_api):  # pragma: no cover
  results = []
  results.extend(input_api.canned_checks.RunPylint(input_api, output_api))
  results.extend(
      input_api.canned_checks.RunUnitTestsInDirectory(
          input_api, output_api,
          input_api.PresubmitLocalPath(),
          whitelist=[r'.+_test\.py$']))
  results.extend(
      input_api.canned_checks.RunUnitTestsInDirectory(
          input_api, output_api,
          os.path.join(input_api.PresubmitLocalPath(), 'resources'),
          whitelist=[r'.+_test\.py$']))
  return results


def CheckChangeOnUpload(input_api, output_api):  # pragma: no cover
  return CommonChecks(input_api, output_api)


def CheckChangeOnCommit(input_api, output_api):  # pragma: no cover
  return CommonChecks(input_api, output_api)
