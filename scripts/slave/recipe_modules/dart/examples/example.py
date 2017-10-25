DEPS = [
  'dart',
  'recipe_engine/properties',
  'recipe_engine/step',
  'recipe_engine/platform',
  'recipe_engine/raw_io'
]

TEST_MATRIX = {
  "filesets": {
    "fileset1": "[]"
  },
  "configurations": [
    {
      "builders": [
        "dart2js-win10-debug-x64-ff-try",
        "analyzer-linux-release-be"
      ],
      "meta": {},
      "steps": [{
        "name": "Build",
        "script": "tools/build.py",
        "arguments": ["foo", "--bar"]
      }, {
        "name": "Test-step 1",
        "script": "tools/test.py",
        "arguments": ["foo", "--bar"],
        "tests": ["language_2"],
        "exclude_tests": ["co19"],
        "shards": 1,
        "fileset": "fileset1"
      }, {
        "name": "Test-step 2",
        "arguments": ["foo", "--bar"],
        "tests": []
      },{
        "name": "Test-step 3",
        "arguments": ["foo", "--bar"]
      }]
    },
    {
      "builders": [
        "dart2js-linux-release-chrome-try"
      ],
      "meta": {},
      "steps": [{
        "name": "Test-step 1",
        "script": "tools/test.py",
        "arguments": ["foo", "--bar"],
        "tests": ["-e co19, language_2"],
        "shards": 2,
        "fileset": "fileset1"
      }, {
        "name": "Test-step custom",
        "script": "tools/custom_thing.py",
        "arguments": ["foo", "--bar"]
      }, {
        "name": "Test-step 2",
        "arguments": ["foo", "--bar"],
        "tests": ["co19"]
      }]
    }
  ]
}

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

  api.dart.test(test_data=TEST_MATRIX)


def GenTests(api):
  yield (api.test('basic') + api.properties(
      shards='2', buildername='dart2js-linux-release-chrome-try') +
      api.step_data('upload testing fileset fileset1',
                    stdout=api.raw_io.output('test isolate hash')))

  yield (api.test('basic-missing-name') + api.properties(
      shards='1', buildername='this-name-does-not-exists-in-test-matrix'))

  yield (api.test('basic-win') + api.platform('win', 64) + api.properties(
      shards='1', buildername='dart2js-win10-debug-x64-ff-try') +
      api.step_data('upload testing fileset fileset1',
                    stdout=api.raw_io.output('test isolate hash')))
