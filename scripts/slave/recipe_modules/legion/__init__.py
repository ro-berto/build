DEPS = [
  'isolate',
  'recipe_engine/path',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'swarming',
  'swarming_client',
]


# TODO(phajdan.jr): provide coverage (http://crbug.com/693058).
DISABLE_STRICT_COVERAGE = True
