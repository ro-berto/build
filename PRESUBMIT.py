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

  black_list = list(input_api.DEFAULT_BLACK_LIST) + [
      r'.*slave/.*/build.*/.*', r'.*depot_tools/.*', r'.*unittests/.*',
      r'.*scripts/release/.*', r'.+_bb7\.py$']

  sys_path_backup = sys.path
  try:
    sys.path = [
        join('third_party'),
        join('third_party', 'buildbot_8_4p1'),
        join('third_party', 'decorator_3_3_1'),
        join('third_party', 'jinja2'),
        join('third_party', 'mock-0.6.0'),
        join('third_party', 'sqlalchemy_0_7_1'),
        join('third_party', 'sqlalchemy_migrate_0_7_1'),
        join('third_party', 'tempita_0_5'),
        join('third_party', 'twisted_10_2'),
        join('scripts'),
        join('site_config'),
        join('test'),
    ] + sys.path

    output.extend(input_api.canned_checks.RunPylint(
        input_api,
        output_api,
        black_list=black_list))

    # Do a separate run with unit tests.
    black_list.remove(r'.*unittests/.*')
    white_list = (r'.*unittests/.+\.py$',)
    sys.path.append(join('scripts', 'master', 'unittests'))
    output.extend(input_api.canned_checks.RunPylint(
        input_api,
        output_api,
        black_list=black_list,
        white_list=white_list))
  finally:
    sys.path = sys_path_backup

  if input_api.is_committing:
    output.extend(input_api.canned_checks.PanProjectChecks(
      input_api, output_api, excluded_paths=black_list))
  return output


def RunTests(input_api, output_api):
  out = []
  whitelist = [r'.+_test\.py$']
  out.extend(input_api.canned_checks.RunUnitTestsInDirectory(
      input_api, output_api, 'test', whitelist))
  out.extend(input_api.canned_checks.RunUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join('scripts', 'master', 'unittests'),
      whitelist))
  internal_path = input_api.os_path.join('..', 'build_internal', 'test')
  if input_api.os_path.isfile(internal_path):
    out.extend(input_api.canned_checks.RunUnitTestsInDirectory(
        input_api, output_api, internal_path, whitelist))
  return out


def CheckChangeOnUpload(input_api, output_api):
  return CommonChecks(input_api, output_api)


def CheckChangeOnCommit(input_api, output_api):
  output = []
  output.extend(CommonChecks(input_api, output_api))
  output.extend(RunTests(input_api, output_api))
  return output
