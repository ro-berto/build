# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Top-level presubmit script for buildbot.

See http://dev.chromium.org/developers/how-tos/depottools/presubmit-scripts for
details on the presubmit API built into gcl.
"""

import sys

def CommonChecks(input_api, output_api):
  output = []

  def join(*args):
    return input_api.os_path.join(input_api.PresubmitLocalPath(), *args)

  black_list = list(input_api.DEFAULT_BLACK_LIST) + [
      r'.*slave/.*/build/.*', r'.*depot_tools/.*', r'.*unittests/.*']

  sys_path_backup = sys.path
  try:
    sys.path = [
        join('third_party'),
        join('third_party', 'buildbot_7_12'),
        join('third_party', 'twisted_8_1'),
        #join('third_party', 'buildbot_8_3p1', 'buildbot'),
        #join('third_party', 'twisted_10_2'),
        join('scripts'),
        join('site_config'),
    ] + sys.path

    output.extend(input_api.canned_checks.RunPylint(
        input_api,
        output_api,
        black_list=black_list))
  finally:
    sys.path = sys_path_backup
  return output


def CheckChangeOnUpload(input_api, output_api):
  return CommonChecks(input_api, output_api)


def CheckChangeOnCommit(input_api, output_api):
  return CommonChecks(input_api, output_api)
