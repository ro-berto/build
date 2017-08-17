DEPS = [
  'dart',
  'recipe_engine/properties',
]

def RunSteps(api):
  channel = 'try'
  api.dart.checkout(channel, True)
  channel = 'release'
  api.dart.checkout(channel, False)

  build_args = ['--super-fast']
  api.dart.build(build_args)
  isolate_hash = api.dart.build(build_args, 'dart_tests')

  test_args = ['--all']
  api.dart.shard('vm_tests', isolate_hash, test_args)

  api.dart.kill_tasks()

def GenTests(api):
  yield (
    api.test('basic') +
    api.properties(shards='6'))
