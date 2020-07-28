# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Top-level presubmit script for buildbot.
See http://dev.chromium.org/developers/how-tos/depottools/presubmit-scripts for
details on the presubmit API built into gcl.
"""
# TODO(crbug.com/1109980): Remove this once the production freeze is over, which
# is expected to be on August 3rd.
def CheckChangeOnUpload(input_api, output_api):
  del input_api, output_api
  return []


def CheckChangeOnCommit(input_api, output_api):
  footers = input_api.change.GitFootersFromDescription()
  with open("tmp.txt", 'w') as f:
    f.write(str(footers))
  if footers.get('Ignore-Cq-Freeze'):
    return []

  message = """
  Your change is modifying files which may impact the Chromium CQ. The Chromium
  CQ is currently in a production freeze. Please get a review from someone in
  the //scripts/slave/recipe_modules/chromium_tests/CHROMIUM_TESTS_OWNERS file
  (preferably a trooper), and then add the 'Ignore-CQ-Freeze' git footer to
  your CL. See https://crbug.com/1109980 for more details.
  """
  return [output_api.PresubmitError(message)]
