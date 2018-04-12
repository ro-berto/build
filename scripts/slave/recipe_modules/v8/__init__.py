DEPS = [
  'archive',
  'build',
  'chromium',
  'commit_position',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/git',
  'depot_tools/gitiles',
  'depot_tools/gsutil',
  'depot_tools/tryserver',
  'docker',
  'isolate',
  'perf_dashboard',
  # TODO(sergiyb): Module puppet_service_account is not LUCI-ready because it
  # requires puppet configuration to be used. We need to migrate to
  # recipe_engine/service_account once buildbucket module supports passing
  # access_token instead of path to JSON file containing credentials.
  'puppet_service_account',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'recipe_engine/scheduler',
  'recipe_engine/tempfile',
  'recipe_engine/time',
  'recipe_engine/url',
  'swarming',
  'swarming_client',
  'test_utils',
  'trigger',
]


# TODO(phajdan.jr): provide coverage (http://crbug.com/693058).
DISABLE_STRICT_COVERAGE = True
