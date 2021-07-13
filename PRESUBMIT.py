# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Top-level presubmit script for the tools/build repo.

See http://dev.chromium.org/developers/how-tos/depottools/presubmit-scripts for
details on the presubmit API built into git cl.
"""

PRESUBMIT_VERSION = '2.0.0'


def GetFilesToSkip(input_api):
  return list(input_api.DEFAULT_FILES_TO_SKIP) + [
      r'.*recipes/.*/build.*/.',
      r'.*recipes/.*/isolate.*/.',
      r'.*depot_tools/.*',
      r'.*goma/.*',
      r'.*scripts/release/.*',
      r'.*recipes/recipes.py$',
      r'.*recipes/recipes/.*_autogen.py$',

      # Exclude all "...recipe_deps" directories.
      #
      # These directories are created by recipe engine.
      # Each is an independent recipe checkout. If Pylint is run on
      # these, it will hang forever, so we must exclude them.
      r'^(.*/)?\..*recipe_deps/.*',
  ]


def join(input_api, *args):
  return input_api.os_path.join(input_api.PresubmitLocalPath(), *args)


def CheckPylintOnCommit(input_api, output_api):
  vpython = 'vpython.bat' if input_api.is_windows else 'vpython'
  infra_path = input_api.subprocess.check_output(
      [vpython, 'scripts/common/env.py', 'print']).split()
  disabled_warnings = [
      'C0321',  # More than one statement on a single line
      'W0613',  # Unused argument
      'W0403',  # Relative import. TODO(crbug.com/1095510): remove this
  ]
  return input_api.canned_checks.RunPylint(
      input_api,
      output_api,
      files_to_skip=GetFilesToSkip(input_api),
      disabled_warnings=disabled_warnings,
      extra_paths_list=infra_path + [
          # Initially, a separate run was done for unit tests but now that
          # pylint is fetched in memory with setuptools, it seems it caches
          # sys.path so modifications to sys.path aren't kept.
          join(input_api, 'recipes', 'unittests'),
          join(input_api, 'tests'),
      ]
  )


def CheckTestsOnCommit(input_api, output_api):
  tests = []

  for dir_glob in (
      ('recipes', 'unittests'),
      ('scripts', 'common', 'unittests'),
      ('recipes', 'recipe_modules', '*', 'unittests'),
      ('recipes', 'recipe_modules', '*', 'resources'),
      ('recipes', 'recipes', '*.resources'),
      ('recipes', 'recipes', '*', '*.resources'),
  ):
    glob = dir_glob + ('*_test.py',)
    test_files = input_api.glob(join(input_api, *glob))
    tests.extend(
        input_api.canned_checks.GetUnitTests(input_api, output_api, test_files)
    )

  # Fetch recipe dependencies once in serial so that we don't hit a race
  # condition where multiple tests are trying to fetch at once.
  output = input_api.RunTests([
      input_api.Command(
          name='recipes fetch',
          cmd=[
              input_api.python_executable,
              input_api.os_path.join('recipes', 'recipes.py'), 'fetch'
          ],
          kwargs={},
          message=output_api.PresubmitError,
      )
  ])
  # Run the tests.
  output.extend(input_api.RunTests(tests))

  return output


def CheckPanProjectChecksOnCommit(input_api, output_api):
  return input_api.canned_checks.PanProjectChecks(
      input_api,
      output_api,
      excluded_paths=GetFilesToSkip(input_api),
      owners_check=False
  )


def CheckConfigFilesParse(input_api, output_api):
  file_filter = lambda x: x.LocalPath() == 'infra/config/recipes.cfg'
  return input_api.canned_checks.CheckJsonParses(
      input_api, output_api, file_filter=file_filter
  )


def CheckPatchFormatted(input_api, output_api):
  # TODO(https://crbug.com/979330) If clang-format is fixed for non-chromium
  # repos, remove check_clang_format=False so that proto files can be formatted
  return input_api.canned_checks.CheckPatchFormatted(
      input_api, output_api, check_clang_format=False
  )
