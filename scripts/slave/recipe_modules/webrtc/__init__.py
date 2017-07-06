DEPS = [
  'adb',
  'archive',
  'depot_tools/bot_update',
  'chromium',
  'chromium_android',
  'chromium_checkout',
  'chromium_swarming',
  'chromium_tests',
  'commit_position',
  'depot_tools/gsutil',
  'depot_tools/gclient',
  'depot_tools/git',
  'isolate',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'swarming',
  'test_utils',
  'test_results',
  'trigger',
  'depot_tools/tryserver',
  'zip',
]


# TODO(phajdan.jr): provide coverage (http://crbug.com/693058).
DISABLE_STRICT_COVERAGE = True
