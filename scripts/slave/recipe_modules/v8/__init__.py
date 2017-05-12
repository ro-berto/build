DEPS = [
  'archive',
  'depot_tools/bot_update',
  'chromium',
  'commit_position',
  'file',
  'depot_tools/gclient',
  'depot_tools/gitiles',
  'depot_tools/gsutil',
  'isolate',
  'perf_dashboard',
  'recipe_engine/context',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/shutil',
  'recipe_engine/step',
  'swarming',
  'swarming_client',
  'test_utils',
  'recipe_engine/tempfile',
  'recipe_engine/time',
  'trigger',
  'depot_tools/tryserver',
]


# TODO(phajdan.jr): provide coverage (http://crbug.com/693058).
DISABLE_STRICT_COVERAGE = True
