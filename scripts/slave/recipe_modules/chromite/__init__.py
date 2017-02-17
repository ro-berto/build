DEPS = [
  'buildbucket',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/git',
  'gitiles',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'repo',
  'recipe_engine/step',
]


# TODO(phajdan.jr): provide coverage (http://crbug.com/693058).
DISABLE_STRICT_COVERAGE = True
