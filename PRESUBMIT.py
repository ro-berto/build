# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Top-level presubmit script for buildbot.

See http://dev.chromium.org/developers/how-tos/depottools/presubmit-scripts for
details on the presubmit API built into git cl.
"""

import contextlib
import os
import re
import sys


@contextlib.contextmanager
def pythonpath(path):
  orig = sys.path
  try:
    sys.path = path
    yield
  finally:
    sys.path = orig


def GetBlackList(input_api):
  return list(input_api.DEFAULT_BLACK_LIST) + [
      r'.*slave/.*/build.*/.*',
      r'.*slave/.*/isolate.*/.*',
      r'.*depot_tools/.*',
      r'.*goma/.*',
      r'.*scripts/tools/buildbot_tool_templates/.*',
      r'.*scripts/release/.*',
      r'.*scripts/slave/recipes.py$',
      r'.*scripts/slave/recipes/.*_autogen.py$',
      r'.*scripts/slave/recipe_modules/[^/]*/[^/]*.py$',
      r'.*scripts/gsd_generate_index/.*',
      r'.*masters/.*/templates/.*\.html$',
      r'.*masters/.*/templates/.*\.css$',
      r'.*masters/.*/public_html/.*\.html$',
      r'.*masters/.*/public_html/.*\.css$',
      # These gitpoller directories are working directories for
      # master.client.drmemory and master.client.dynamorio and do not contain
      # checked-in code.
      r'.*masters/.*/gitpoller/.*',

      # Exclude all "...recipe_deps" directories.
      #
      # These directories are created by tests in "tests/", and by recipe
      # engine. Each is an independent recipe checkout. If Pylint is run on
      # these, it will hang forever, so we must exclude them.
      r'^(.*/)?\..*recipe_deps/.*',
  ]


def CommonChecks(input_api, output_api):
  def join(*args):
    return input_api.os_path.join(input_api.PresubmitLocalPath(), *args)

  output = []

  infra_path = input_api.subprocess.check_output(
      ['python', 'scripts/common/env.py', 'print']).split()
  test_sys_path = infra_path + [
      # Initially, a separate run was done for unit tests but now that
      # pylint is fetched in memory with setuptools, it seems it caches
      # sys.path so modifications to sys.path aren't kept.
      join('scripts', 'master', 'unittests'),
      join('scripts', 'slave', 'unittests'),
      join('tests'),
  ] + sys.path
  with pythonpath(test_sys_path):
    disabled_warnings = [
      'C0301',  # Line too long (NN/80)
      'C0321',  # More than one statement on a single line
      'W0613',  # Unused argument
    ]
    output.extend(input_api.canned_checks.RunPylint(
        input_api,
        output_api,
        black_list=GetBlackList(input_api),
        disabled_warnings=disabled_warnings))

  output.extend(CheckExternalBuildersPylMastersAreInSync(input_api, output_api))

  return output


def CommitChecks(input_api, output_api):
  def join(*args):
    return input_api.os_path.join(input_api.PresubmitLocalPath(), *args)
  tests = []

  infra_path = input_api.subprocess.check_output(
      ['python', 'scripts/common/env.py', 'print']).split()

  whitelist = [r'.+_test\.py$']
  blacklist = [r'bot_update_test.py$', r'masters_test.py$']
  tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
      input_api, output_api, 'tests', whitelist=whitelist,
      blacklist=blacklist))
  tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join('scripts', 'master', 'unittests'),
      whitelist))
  tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join('scripts', 'slave', 'unittests'),
      whitelist))
  tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join('scripts', 'common', 'unittests'),
      whitelist))
  tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join('scripts', 'tools', 'unittests'),
      whitelist))
  tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join(
        'scripts', 'master', 'buildbucket', 'unittests'),
      whitelist))


  recipe_modules_tests = input_api.glob(
      join('scripts', 'slave', 'recipe_modules', '*', 'unittests'))
  for path in recipe_modules_tests:
    tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
        input_api,
        output_api,
        path,
        whitelist))

  test_env = os.environ.copy()
  test_env['PYTHONPATH'] = os.pathsep.join(infra_path)
  tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join('slave', 'tests'),
      whitelist,
      env=test_env))

  with pythonpath(infra_path + sys.path):
    import common.master_cfg_utils  # pylint: disable=F0401
    # Fetch recipe dependencies once in serial so that we don't hit a race
    # condition where multiple tests are trying to fetch at once.
    output = input_api.RunTests([input_api.Command(
        name='recipes fetch',
        cmd=[input_api.python_executable,
             input_api.os_path.join('scripts', 'slave', 'recipes.py'), 'fetch'],
        kwargs={},
        message=output_api.PresubmitError,
    )])
    # Run the tests.
    with common.master_cfg_utils.TemporaryMasterPasswords():
      output.extend(input_api.RunTests(tests))

    output.extend(input_api.canned_checks.PanProjectChecks(
        input_api, output_api, excluded_paths=GetBlackList(input_api)))
    return output


def ConditionalChecks(input_api, output_api):
  """Pre-commit tests only to be run if specific files have changed.

  Typically, this is used to avoid running lengthy tests when possible.
  """
  tests_to_run = []
  conditional_tests = {
      'tests/masters_test.py': [
          r'^masters/.*',
          r'^scripts/common/.*',
          r'^scripts/master/.*',
          r'^third_party/buildbot_8_4p1/.*',
          r'^third_party/twisted_10_2/.*',
      ],
      'tests/bot_update_test.py': [
          r'^scripts/slave/bot_update.py$',
      ],
  }
  affected_files = set([
      f.LocalPath() for f in input_api.change.AffectedFiles()])
  for test, regexes in conditional_tests.iteritems():
    for path in affected_files:
      if any(re.match(r, path) for r in regexes):
        tests_to_run.append(test)
        break

  return input_api.RunTests(input_api.canned_checks.GetUnitTests(
      input_api, output_api, tests_to_run))

def BuildInternalCheck(output, input_api, output_api):
  if output:
    b_i = input_api.os_path.join(input_api.PresubmitLocalPath(), '..',
                                 'build_internal')
    if input_api.os_path.exists(b_i):
      return [output_api.PresubmitNotifyResult(
          'You have a build_internal checkout. '
          'Updating it may resolve some issues.')]
  return []

def CheckExternalBuildersPylMastersAreInSync(input_api, output_api):
  script_path = input_api.os_path.join('scripts', 'tools', 'buildbot-tool')
  proc = input_api.subprocess.Popen([
      script_path,
      'check',
      '--external-only'
      ], stdout=input_api.subprocess.PIPE, stderr=input_api.subprocess.STDOUT)
  out, _ = proc.communicate()
  if proc.returncode or out:
    return [output_api.PresubmitError('`scripts/tools/buildbot-tool '
                                      'check --external-only` returned '
                                      '%d:\n%s\n' % (proc.returncode, out))]
  return []

def CheckChangeOnUpload(input_api, output_api):
  return CommonChecks(input_api, output_api)


def CheckChangeOnCommit(input_api, output_api):
  output = CommonChecks(input_api, output_api)
  output.extend(CommitChecks(input_api, output_api))
  output.extend(ConditionalChecks(input_api, output_api))
  output.extend(BuildInternalCheck(output, input_api, output_api))
  return output
