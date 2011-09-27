# Copyright (c) 2011 The Chromium Authors. All rights reserved.
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

  black_list = input_api.DEFAULT_BLACK_LIST + (
      r'.*slave/.*/build.*/.*', r'.*depot_tools/.*', r'.*unittests/.*',
      r'.*scripts/release/.*')

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

  if input_api.is_committing:
    output.extend(input_api.canned_checks.PanProjectChecks(
      input_api, output_api, excluded_paths=black_list))
  return output


def RunTests(input_api, output_api):
  tests = [
      input_api.os_path.join('test', 'masters_test.py'),
      # TODO(maruel): Broken.
      #input_api.os_path.join(
      #  'scripts', 'slave', 'chromium', 'archive_build_unittest.py'),
      # TODO(maruel): Throws, needing 'mock'.
      #input_api.os_path.join(
      #  'scripts', 'master', 'unittests', 'runtests.py'),
  ]
  internal_path = input_api.os_path.join(
      '..', 'build_internal', 'test', 'internal_masters_test.py')
  if input_api.os_path.isfile(internal_path):
    tests.append(internal_path)
  return input_api.canned_checks.RunUnitTests(input_api, output_api, tests)


def CheckChangeOnUpload(input_api, output_api):
  return CommonChecks(input_api, output_api)


def CheckChangeOnCommit(input_api, output_api):
  output = []
  output.extend(CommonChecks(input_api, output_api))
  output.extend(RunTests(input_api, output_api))
  return output
