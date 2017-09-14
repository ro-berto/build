DEPS = [
  'dart',
  'recipe_engine/properties',
  'recipe_engine/step',
  'recipe_engine/platform'
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
  tasks = api.dart.shard('vm_tests', isolate_hash, test_args)
  api.dart.collect(tasks)

  with api.step.defer_results():
    api.step('Print Hello World', ['echo', 'hello', 'world'])
    api.dart.read_result_file('print result', 'result.log')

  api.dart.kill_tasks()
  api.dart.read_debug_log()

def GenTests(api):
  yield (
    api.test('basic') +
    api.properties(shards='2')
  )

  yield (
    api.test('basic-win') + api.platform('win', 64) +
    api.properties(shards='1')
  )
