# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Top-level presubmit script for the tools/build repo.

See http://dev.chromium.org/developers/how-tos/depottools/presubmit-scripts for
details on the presubmit API built into git cl.
"""

import re


def GetFilesToSkip(input_api):
  return list(input_api.DEFAULT_FILES_TO_SKIP) + [
      r'.*recipes/.*/build.*/.',
      r'.*recipes/.*/isolate.*/.',
      r'.*depot_tools/.*',
      r'.*goma/.*',
      r'.*scripts/release/.*',
      r'.*recipes/recipes.py$',
      r'.*recipes/recipes/.*_autogen.py$',
      r'.*scripts/gsd_generate_index/.*',
      r'.*masters/.*/templates/.*\.html$',
      r'.*masters/.*/templates/.*\.css$',
      r'.*masters/.*/public_html/.*\.html$',
      r'.*masters/.*/public_html/.*\.css$',

      # Exclude all "...recipe_deps" directories.
      #
      # These directories are created by recipe engine.
      # Each is an independent recipe checkout. If Pylint is run on
      # these, it will hang forever, so we must exclude them.
      r'^(.*/)?\..*recipe_deps/.*',
  ]


def CommitChecks(input_api, output_api):
  def join(*args):
    return input_api.os_path.join(input_api.PresubmitLocalPath(), *args)

  output = []

  # Run pylint.
  vpython = 'vpython.bat' if input_api.is_windows else 'vpython'
  infra_path = input_api.subprocess.check_output(
      [vpython, 'scripts/common/env.py', 'print']).split()
  disabled_warnings = [
    'C0321',  # More than one statement on a single line
    'W0613',  # Unused argument
  ]
  output.extend(input_api.canned_checks.RunPylint(
      input_api,
      output_api,
      files_to_skip=GetFilesToSkip(input_api),
      disabled_warnings=disabled_warnings,
      extra_paths_list=infra_path + [
        # Initially, a separate run was done for unit tests but now that
        # pylint is fetched in memory with setuptools, it seems it caches
        # sys.path so modifications to sys.path aren't kept.
        join('scripts', 'master', 'unittests'),
        join('recipes', 'unittests'),
        join('tests'),
      ]))

  tests = []

  files_to_check = [r'.+_test\.py$']
  tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join('recipes', 'unittests'),
      files_to_check=files_to_check))
  tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join('scripts', 'common', 'unittests'),
      files_to_check=files_to_check))

  recipe_modules_tests = (
      input_api.glob(
          join('recipes', 'recipe_modules', '*', 'unittests')
      ) + input_api.glob(
          join('recipes', 'recipe_modules', '*', 'resources')
      )
  )
  for path in recipe_modules_tests:
    tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
        input_api,
        output_api,
        path,
        files_to_check=files_to_check))

  recipes_resources = (
      input_api.glob(join('recipes', 'recipes', '*.resources')) +
      input_api.glob(join('recipes', 'recipes', '*', '*.resources')))
  for path in recipes_resources:
    tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
        input_api,
        output_api,
        path,
        files_to_check=files_to_check))

  # Fetch recipe dependencies once in serial so that we don't hit a race
  # condition where multiple tests are trying to fetch at once.
  output.extend(input_api.RunTests([input_api.Command(
      name='recipes fetch',
      cmd=[input_api.python_executable,
           input_api.os_path.join('recipes', 'recipes.py'), 'fetch'],
      kwargs={},
      message=output_api.PresubmitError,
  )]))
  # Run the tests.
  output.extend(input_api.RunTests(tests))

  output.extend(input_api.canned_checks.PanProjectChecks(
      input_api, output_api, excluded_paths=GetFilesToSkip(input_api)))
  return output


def BuildInternalCheck(output, input_api, output_api):
  if output:
    b_i = input_api.os_path.join(input_api.PresubmitLocalPath(), '..',
                                 'build_internal')
    if input_api.os_path.exists(b_i):
      return [output_api.PresubmitNotifyResult(
          'You have a build_internal checkout. '
          'Updating it may resolve some issues.')]
  return []


def CheckChangeOnUpload(input_api, output_api):
  output = []
  # TODO(https://crbug.com/979330) If clang-format is fixed for non-chromium
  # repos, remove check_clang_format=False so that proto files can be formatted
  output.extend(
      input_api.canned_checks.CheckPatchFormatted(
          input_api, output_api, check_clang_format=False
      )
  )
  return output


def CheckChangeOnCommit(input_api, output_api):
  output = CommitChecks(input_api, output_api)
  output.extend(BuildInternalCheck(output, input_api, output_api))
  output.extend(CheckChangeOnUpload(input_api, output_api))
  return output
