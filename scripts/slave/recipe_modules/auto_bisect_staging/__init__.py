DEPS = [
    'adb',
    'bisect_tester_staging',
    'buildbucket',
    'chromium',
    'chromium_android',
    'chromium_checkout',
    'chromium_swarming',
    'chromium_tests',
    'commit_position',
    'crrev',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/git',
    'depot_tools/gitiles',
    'depot_tools/gsutil',
    'depot_tools/tryserver',
    'goma',
    'halt',
    'math_utils',
    'perf_dashboard',
    'perf_try_staging',
    'puppet_service_account',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'test_utils',
    'trigger',
]


# TODO(phajdan.jr): provide coverage (http://crbug.com/693058).
DISABLE_STRICT_COVERAGE = True
