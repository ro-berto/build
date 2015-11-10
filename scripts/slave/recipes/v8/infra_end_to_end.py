# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

DEPS = [
  'bot_update',
  'gclient',
  'json',
  'path',
  'properties',
  'python',
  'raw_io',
  'step',
]

TESTS = [
  {
    'name': 'Test auto-bisect on tester',
    'properties': {
      'workdir': '/b/build/slave/linux',
      'repository': 'https://chromium.googlesource.com/v8/v8',
      'buildername': 'V8 Linux - nosnap',
      'parent_buildnumber': 8736,
      'recipe': 'v8',
      'mastername':
      'client.v8',
      'buildbotURL': 'http://build.chromium.org/p/client.v8/',
      'project': 'v8',
      'parent_buildername': 'V8 Linux - nosnap builder',
      'git_revision': '722719fe31fe7fd5bb50be6256b3581bb28a8169',
      'parent_got_revision': '722719fe31fe7fd5bb50be6256b3581bb28a8169',
      'buildnumber': 4816,
      'slavename': 'slave28-c3',
      'blamelist': ['bmeurer@chromium.org', 'yangguo@chromium.org'],
      'branch': 'master',
      'parent_got_revision_cp': 'refs/heads/master@{#31390}',
      'requestedAt': 1445316061,
      'revision': '722719fe31fe7fd5bb50be6256b3581bb28a8169',
      'override_changes': [
        {'revision': '6ed05f44afd2419582a2e843141f4d3c3d06b418'},
        {'revision': '019f9408dc9f4c0306831a4b0fe35c2f58217cdb'},
        {'revision': '722719fe31fe7fd5bb50be6256b3581bb28a8169'},
      ],
      'bisect_duration_factor': 0.5,
      'testfilter': [
        'test262/built-ins/RegExp/prototype/test/y-fail-lastindex-no-write',
      ],
    },
    'ok_ret': [1],
    'verifiers': [
      {
        'name': 'verify suspects',
        'regexp': r'Suspecting multiple commits(?:.|\s)*'
                  r'019f9408(?:.|\s)*722719fe',
      },
    ],
  },
]

def RunSteps(api):
  api.gclient.set_config('build')
  api.bot_update.ensure_checkout(force=True)

  for test in TESTS:
    result = api.python(
        name=test['name'],
        script=api.path['checkout'].join('scripts', 'tools', 'run_recipe.py'),
        args=[
          'v8',
          '--properties-file',
          api.json.input(test['properties'])
        ],
        ok_ret=test['ok_ret'],
        stdout=api.raw_io.output(),
    )

    # Make consumed output visible again.
    result.presentation.logs['stdout'] = result.stdout.splitlines()

    # Assert invariants.
    for verifier in test['verifiers']:
      if not re.search(verifier['regexp'], result.stdout):
        result.presentation.status = api.step.FAILURE
        result.presentation.logs[verifier['name']] = [
            'Regular expression "%s" did not match.' % verifier['regexp']]


def GenTests(api):
  yield (
      api.test('v8-auto-bisect-end-to-end-pass') +
      api.properties.generic(
          mastername='chromium.tools.build',
          buildername='v8-linux-end-to-end',
      ) +
      api.override_step_data(
          'Test auto-bisect on tester',
          api.raw_io.stream_output(
              'Suspecting multiple commits@@\n@@\n@@019f9408@@@\n@@@722719fe',
              stream='stdout',
          ),
          retcode=1,
      )
  )

  yield (
      api.test('v8-auto-bisect-end-to-end-fail') +
      api.properties.generic(
          mastername='chromium.tools.build',
          buildername='v8-linux-end-to-end',
      ) +
      api.override_step_data(
          'Test auto-bisect on tester',
          api.raw_io.stream_output(
              'Suspecting multiple commits\ndeadbeef\ndeadbeef',
              stream='stdout',
          ),
          retcode=1,
      )
  )
