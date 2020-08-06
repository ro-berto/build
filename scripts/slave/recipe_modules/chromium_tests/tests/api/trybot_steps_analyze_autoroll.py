# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec, try_spec

DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'test_utils',
]

_TEST_BUILDERS = bot_db.BotDatabase.create({
    'chromium.test': {
        'chromium-rel':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
            ),
        'chromium-test-rel':
            bot_spec.BotSpec.create(gclient_config='chromium',),
    },
})

_TEST_TRYBOTS = try_spec.TryDatabase.create({
    'tryserver.chromium.test': {
        'chromium-rel':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='chromium.test',
                        buildername='chromium-rel',
                        tester='chromium-test-rel',
                    ),
                ],
                analyze_deps_autorolls=True),
    }
})


def RunSteps(api):
  assert api.tryserver.is_tryserver
  raw_result = api.chromium_tests.trybot_steps()
  return raw_result


def GenTests(api):
  deps_changes = '''
13>src/third_party/fake_lib/fake_file
13>src/third_party/fake_lib/fake_file_2
'''
  cl_info = api.json.output([{
      'owner': {
          # chromium-autoroller
          '_account_id': 1302611
      },
      'branch': 'master',
      'revisions': {},
  }])

  yield api.test(
      'analyze deps autorolls success',
      api.chromium.try_build(
          builder_group='tryserver.chromium.test', builder='chromium-rel'),
      api.chromium_tests.builders(_TEST_BUILDERS),
      api.chromium_tests.trybots(_TEST_TRYBOTS),
      api.override_step_data('gerrit fetch current CL info', cl_info),
      api.override_step_data('git diff to analyze patch',
                             api.raw_io.stream_output('DEPS')),
      api.override_step_data('gclient recursively git diff all DEPS',
                             api.raw_io.stream_output(deps_changes)),
  )

  yield api.test(
      'analyze deps autorolls nothing',
      api.chromium.try_build(
          builder_group='tryserver.chromium.test', builder='chromium-rel'),
      api.chromium_tests.builders(_TEST_BUILDERS),
      api.chromium_tests.trybots(_TEST_TRYBOTS),
      api.override_step_data('gerrit fetch current CL info', cl_info),
      api.override_step_data('git diff to analyze patch',
                             api.raw_io.stream_output('DEPS')),
      api.override_step_data('gclient recursively git diff all DEPS',
                             api.raw_io.stream_output('')),
  )
