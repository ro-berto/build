DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'file',
  'depot_tools/gclient',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]


# TODO(phajdan.jr): provide coverage (http://crbug.com/693058).
DISABLE_STRICT_COVERAGE = True
