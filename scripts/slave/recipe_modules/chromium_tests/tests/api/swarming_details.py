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
      ('swarming_tags', swarming_tags),
      ('swarming_extra_args', swarming_extra_args),
  ]

def GenTests(api):
  yield (
      api.test('basic')
      + api.properties(expected=_expected())
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('asan')
      + api.properties(
          chromium_apply_config=['asan'],
          expected=_expected(swarming_tags={'asan:1'}))
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('lsan')
      + api.properties(
          chromium_apply_config=['lsan'],
          expected=_expected(swarming_tags={'lsan:1'},
                             swarming_extra_args=['--lsan=1']))
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('msan')
      + api.properties(
          chromium_apply_config=['msan'],
          expected=_expected(swarming_tags={'msan:1'}))
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('tsan')
      + api.properties(
          chromium_apply_config=['tsan2'],
          expected=_expected(swarming_tags={'tsan:1'}))
      + api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('combined')
      + api.properties(
          chromium_apply_config=['asan', 'lsan', 'msan', 'tsan2'],
          expected=_expected(swarming_tags={'asan:1', 'lsan:1',
                                            'msan:1', 'tsan:1'},
                             swarming_extra_args=['--lsan=1']))
      + api.post_process(post_process.DropExpectation)
  )
