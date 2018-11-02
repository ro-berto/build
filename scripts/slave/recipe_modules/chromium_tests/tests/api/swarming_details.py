from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/properties',
]

def RunSteps(api):
  api.chromium.set_config('chromium_clang')
  for c in api.properties.get('chromium_apply_config', []):
    api.chromium.apply_config(c)
  for attr, expected_value in api.properties.get('expected'):
    value = getattr(api.chromium_tests, attr)
    if isinstance(expected_value, tuple):
      expected_value = list(expected_value)
    assert value == expected_value, (
      ('runtests_spec.%s does not have expected value\n'
       '  expected: %r\n'
       '  actual: %r') % (attr, expected_value, value))

def _expected(swarming_tags=frozenset(), swarming_extra_args=()):
  return [
      ('swarming_extra_args', swarming_extra_args),
  ]

def GenTests(api):
  yield (
      api.test('basic')
      + api.properties(expected=_expected())
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('combined')
      + api.properties(
          chromium_apply_config=['asan', 'lsan', 'msan', 'tsan2'],
          expected=_expected(swarming_extra_args=['--lsan=1']))
      + api.post_process(post_process.DropExpectation)
  )
