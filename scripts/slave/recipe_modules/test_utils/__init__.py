from recipe_engine.recipe_api import Property

DEPS = [
  'build',
  'chromium',
  'traceback',
  'depot_tools/tryserver',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
]

PROPERTIES = {
  'max_reported_gtest_failures': Property(default=30, kind=int),
}

# TODO(phajdan.jr): provide coverage (http://crbug.com/693058).
DISABLE_STRICT_COVERAGE = True
