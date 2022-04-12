# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Top-level presubmit script for the tools/build repo.

See http://dev.chromium.org/developers/how-tos/depottools/presubmit-scripts for
details on the presubmit API built into git cl.
"""

PRESUBMIT_VERSION = '2.0.0'

_IGNORE_FREEZE_FOOTER = 'Ignore-Freeze'

# The time module's handling of timezones is abysmal, so the boundaries are
# precomputed in UNIX time
_FREEZE_START = 1639641600  # 2021/12/16 00:00 -0800
_FREEZE_END = 1641196800  # 2022/01/03 00:00 -0800


def CheckFreeze(input_api, output_api):
  if _FREEZE_START <= input_api.time.time() < _FREEZE_END:
    footers = input_api.change.GitFootersFromDescription()
    if _IGNORE_FREEZE_FOOTER not in footers:

      def convert(t):
        ts = input_api.time.localtime(t)
        return input_api.time.strftime('%Y/%m/%d %H:%M %z', ts)

      return [
          output_api.PresubmitError(
              'There is a prod freeze in effect from {} until {}'.format(
                  convert(_FREEZE_START), convert(_FREEZE_END)
              )
          )
      ]

  return []


# A list of files that are _only_ compatible with python3. Tests for these are
# only run under vpython3, and lints are performed with pylint 2.7. The
# expectation is that these will become the defaults over time.
PYTHON3_ONLY_FILES = (
    'PRESUBMIT_test.py',
    'recipes/recipes/flakiness/generate_builder_test_data.resources/query.py',
    (
        'recipes/recipes/flakiness/generate_builder_test_data.resources/'
        'query_test.py'
    ),
    'recipes/recipe_modules/chromium_tests_builder_config/PRESUBMIT.py',
    (
        'recipes/recipe_modules/chromium_tests_builder_config/migration/'
        'scripts/generate_groupings.py'
    ),
    (
        'recipes/recipe_modules/chromium_tests_builder_config/migration/'
        'scripts/tests/generate_groupings_integration_test.py'
    ),
    (
        'recipes/recipe_modules/chromium_tests_builder_config/migration/'
        'scripts/tests/generate_groupings_unit_test.py'
    ),
    (
        'recipes/recipe_modules/tricium_clang_tidy/resources/'
        'tricium_clang_tidy_script.py'
    ),
    (
        'recipes/recipe_modules/tricium_clang_tidy/resources/'
        'tricium_clang_tidy_test.py'
    ),
)


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
  infra_path = input_api.subprocess.check_output([
      vpython, 'scripts/common/env.py', 'print'
  ]).split()
  disabled_warnings = [
      'C0321',  # More than one statement on a single line
      'W0613',  # Unused argument
      'W0403',  # Relative import. TODO(crbug.com/1095510): remove this
  ]
  extra_paths_list = infra_path + [
      # Initially, a separate run was done for unit tests but now that
      # pylint is fetched in memory with setuptools, it seems it caches
      # sys.path so modifications to sys.path aren't kept.
      join(input_api, 'recipes', 'unittests'),
      join(input_api, 'tests'),
  ]
  lints = input_api.canned_checks.RunPylint(
      input_api,
      output_api,
      files_to_skip=GetFilesToSkip(input_api) + list(PYTHON3_ONLY_FILES),
      disabled_warnings=disabled_warnings,
      extra_paths_list=extra_paths_list,
  )
  if PYTHON3_ONLY_FILES:
    lints.extend(
        input_api.canned_checks.RunPylint(
            input_api,
            output_api,
            files_to_check=PYTHON3_ONLY_FILES,
            disabled_warnings=disabled_warnings,
            extra_paths_list=extra_paths_list,
            version='2.7',
        )
    )
  return lints


def CheckTestsOnCommit(input_api, output_api):
  tests = []

  test_suffix = '_test.py'
  python3_only_tests = set(
      join(input_api, f) for f in PYTHON3_ONLY_FILES if f.endswith(test_suffix)
  )
  for dir_glob in (
      ('recipes', 'unittests'),
      ('scripts', 'common', 'unittests'),
      ('recipes', 'recipe_modules', '*', 'unittests'),
      ('recipes', 'recipe_modules', '*', 'resources'),
      ('recipes', 'recipe_modules', 'chromium_tests_builder_config',
       'migration', 'scripts', 'tests'),
      ('recipes', 'recipes', '*.resources'),
      ('recipes', 'recipes', '*', '*.resources'),
  ):
    glob = dir_glob + ('*' + test_suffix,)
    test_files = [
        x for x in input_api.glob(join(input_api, *glob))
        if x not in python3_only_tests
    ]
    tests.extend(
        input_api.canned_checks.GetUnitTests(input_api, output_api, test_files)
    )

  if python3_only_tests:
    tests.extend(
        input_api.canned_checks.GetUnitTests(
            input_api,
            output_api,
            sorted(python3_only_tests),
            run_on_python2=False,
            run_on_python3=True,
            skip_shebang_check=True,
        )
    )

  return input_api.RunTests(tests)


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
