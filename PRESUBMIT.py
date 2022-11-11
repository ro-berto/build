# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Top-level presubmit script for the tools/build repo.

See http://dev.chromium.org/developers/how-tos/depottools/presubmit-scripts for
details on the presubmit API built into git cl.
"""

PRESUBMIT_VERSION = '2.0.0'

USE_PYTHON3 = True

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
    'recipes/zip_build.py',
    'recipes/extract_build.py',
    'recipes/recipes/flakiness/generate_builder_test_data.resources/query.py',
    (
        'recipes/recipes/flakiness/generate_builder_test_data.resources/'
        'query_test.py'
    ),
    'recipes/recipe_modules/archive/resources/filter_build_files.py',
    'recipes/recipe_modules/archive/resources/zip_archive.py',
    'recipes/recipe_modules/chromium/resources/ninja_wrapper.py',
    'recipes/recipe_modules/chromium/resources/ninja_wrapper_test.py',
    'recipes/recipe_modules/chromium_android/resources/archive_build.py',
    (
        'recipes/recipe_modules/chromium_android/resources/'
        'archive_build_unittest.py'
    ),
    'recipes/recipe_modules/chromium_tests_builder_config/PRESUBMIT.py',
    (
        'recipes/recipe_modules/chromium_tests_builder_config/migration/'
        'scripts/buildozer_wrapper.py'
    ),
    (
        'recipes/recipe_modules/chromium_tests_builder_config/migration/'
        'scripts/generate_groupings.py'
    ),
    (
        'recipes/recipe_modules/chromium_tests_builder_config/migration/'
        'scripts/migrate.py'
    ),
    (
        'recipes/recipe_modules/chromium_tests_builder_config/migration/'
        'scripts/tests/buildozer_wrapper_unit_test.py'
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
        'recipes/recipe_modules/chromium_tests_builder_config/migration/'
        'scripts/tests/migrate_integration_test.py'
    ),
    (
        'recipes/recipe_modules/chromium_tests_builder_config/migration/'
        'scripts/tests/migrate_unit_test.py'
    ),
    'recipes/recipe_modules/cronet/resources/clear_landmines.py',
    'recipes/recipe_modules/tar/resources/tar_test.py',
    (
        'recipes/recipe_modules/tricium_clang_tidy/resources/'
        'tricium_clang_tidy_script.py'
    ),
    (
        'recipes/recipe_modules/tricium_clang_tidy/resources/'
        'tricium_clang_tidy_test.py'
    ),
    'recipes/recipe_modules/test_utils/unittests/query_cq_flakes_test.py',
    'recipes/recipe_modules/code_coverage/unittests/aggregation_util_test.py',
    (
        'recipes/recipe_modules/code_coverage/unittests/'
        'combine_jacoco_reports_test.py'
    ),
    'recipes/recipe_modules/code_coverage/unittests/constants_test.py',
    'recipes/recipe_modules/code_coverage/unittests/diff_util_test.py',
    (
        'recipes/recipe_modules/code_coverage/unittests/'
        'generate_coverage_metadata_for_javascript_test.py'
    ),
    (
        'recipes/recipe_modules/code_coverage/unittests/'
        'generate_coverage_metadata_for_java_test.py'
    ),
    (
        'recipes/recipe_modules/code_coverage/unittests/'
        'generate_coverage_metadata_test.py'
    ),
    'recipes/recipe_modules/code_coverage/unittests/gerrit_util_test.py',
    (
        'recipes/recipe_modules/code_coverage/unittests/'
        'get_unstripped_paths_test.py'
    ),
    'recipes/recipe_modules/code_coverage/unittests/make_report_test.py',
    (
        'recipes/recipe_modules/code_coverage/unittests/'
        'rebase_line_number_from_bot_to_gerrit_test.py'
    ),
    'recipes/recipe_modules/code_coverage/unittests/repository_util_test.py',
    'recipes/recipe_modules/code_coverage/unittests/write_paths_test.py',
    'recipes/unittests/extract_build_unittest.py',
    'recipes/unittests/zip_build_unittest.py',
    'scripts/common/unittests/chromium_utils_test.py',
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
  return input_api.os_path.normpath(
      input_api.os_path.join(input_api.PresubmitLocalPath(), *args)
  )


def CheckPylintOnCommit(input_api, output_api):
  disabled_warnings = [
      'C0321',  # More than one statement on a single line
      'W0613',  # Unused argument
      'W0403',  # Relative import. TODO(crbug.com/1095510): remove this

      # Below warnings are disabled for pylint version update, but better to
      # remove if possible.
      'C0201',  # consider-iterating-dictionary
      'C0301',  # line-too-long
      'C0415',  # import-outside-toplevel
      'E0001',  # syntax-error
      'E0012',  # bad-option-value
      'E0702',  # raising-bad-type
      'E1101',  # no-member
      'E1120',  # no-value-for-parameter
      'E1137',  # unsupported-assignment-operation
      'R0205',  # useless-object-inheritance
      'R1701',  # consider-merging-isinstance
      'R1704',  # redefined-argument-from-local
      'R1705',  # no-else-return
      'R1706',  # consider-using-ternary
      'R1707',  # trailing-comma-tuple
      'R1710',  # inconsistent-return-statements
      'R1711',  # useless-return
      'R1714',  # consider-using-in
      'R1716',  # chained-comparison
      'R1718',  # consider-using-set-comprehension
      'R1720',  # no-else-raise
      'R1721',  # unnecessary-comprehension
      'R1723',  # no-else-break
      'R1725',  # super-with-arguments
      'R1729',  # use-a-generator
      'W0104',  # pointless-statement
      'W0106',  # expression-not-assigned
      'W0107',  # unnecessary-pass
      'W0221',  # arguments-differ
      'W0235',  # useless-super-delegation
      'W0621',  # redefined-outer-name
      'W0622',  # redefined-builtin
      'W0707',  # raise-missing-from
      'W0715',  # raising-format-tuple
      'W1113',  # keyword-arg-before-vararg
      'W1404',  # implicit-str-concat
  ]
  extra_paths_list = [
      join(input_api, 'recipes'),
      join(input_api, 'scripts'),
      # Initially, a separate run was done for unit tests but now that
      # pylint is fetched in memory with setuptools, it seems it caches
      # sys.path so modifications to sys.path aren't kept.
      join(input_api, 'recipes', 'unittests'),
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


def _GetTests(input_api, output_api, test_files):
  python3_only_files = set(join(input_api, f) for f in PYTHON3_ONLY_FILES)
  non_python3_test_files = []
  python3_test_files = []
  for t in sorted(test_files):
    if t in python3_only_files:
      python3_test_files.append(t)
    else:
      non_python3_test_files.append(t)

  tests = []
  tests.extend(
      input_api.canned_checks.GetUnitTests(
          input_api,
          output_api,
          non_python3_test_files,
      )
  )
  tests.extend(
      input_api.canned_checks.GetUnitTests(
          input_api,
          output_api,
          python3_test_files,
          run_on_python2=False,
          run_on_python3=True,
          skip_shebang_check=True,
      )
  )
  return tests


# The following tests invoke recipes.py which isn't safe in parallel, so they'll
# be run in a separate check function that runs them sequentially
RECIPES_PY_TESTS = [
    'recipes/unittests/recipe_test.py',
    (
        'recipes/recipe_modules/chromium_tests_builder_config/migration/'
        'scripts/tests/generate_groupings_integration_test.py'
    ),
    (
        'recipes/recipe_modules/chromium_tests_builder_config/migration/'
        'scripts/tests/migrate_integration_test.py'
    ),
]


def _RecipesPyTestFiles(input_api):
  return [join(input_api, f) for f in RECIPES_PY_TESTS]


def CheckRecipesPyTestsOnCommit(input_api, output_api):
  tests = _GetTests(input_api, output_api, _RecipesPyTestFiles(input_api))
  return input_api.RunTests(tests, parallel=False)


def CheckTestsOnCommit(input_api, output_api):
  excluded_test_files = set(_RecipesPyTestFiles(input_api))

  test_files = []
  for dir_glob in (
      ('recipes', 'unittests'),
      ('recipes', 'recipe_modules', '*', 'unittests'),
      ('recipes', 'recipe_modules', '*', 'resources'),
      ('recipes', 'recipe_modules', 'chromium_tests_builder_config',
       'migration', 'scripts', 'tests'),
      ('recipes', 'recipes', '*.resources'),
      ('recipes', 'recipes', '*', '*.resources'),
      ('scripts', 'common', 'unittests'),
  ):
    glob = dir_glob + ('*_test.py',)
    test_files.extend(
        x for x in input_api.glob(join(input_api, *glob))
        if x not in excluded_test_files
    )

  tests = _GetTests(input_api, output_api, test_files)
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
