# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Recipe for archiving officially tagged v8 builds.
"""

from recipe_engine.post_process import DoesNotRun, DropExpectation, MustRun

DEPS = [
  'depot_tools/gclient',
  'depot_tools/git',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'v8',
]


def RunSteps(api):
  api.v8.apply_bot_config(api.v8.BUILDERS)
  api.v8.checkout()

  head_version = api.v8.read_version_from_ref(api.v8.revision, 'head')
  tags = set(x.strip() for x in api.git(
      'describe', '--tags', 'HEAD',
      stdout=api.raw_io.output_text(),
  ).stdout.strip().splitlines())

  if str(head_version) not in tags:
    api.step('Skipping build due to missing tag.', cmd=None)
    return

  api.step('Here comes a new shiny archiving recipe!', cmd=None)


def GenTests(api):
  def check_bot_update(check, steps):
    check('v8@refs/branch-heads/3.4:deadbeef' in steps['bot_update']['cmd'])

  for mastername, _, buildername, _ in api.v8.iter_builders('v8/archive'):
    yield (
        api.test(api.v8.test_name(mastername, buildername)) +
        api.properties.generic(mastername='client.v8.official',
                               buildername='V8 Linux64',
                               branch='3.4',
                               revision='deadbeef') +
        api.v8.version_file(17, 'head') +
        api.override_step_data(
            'git describe', api.raw_io.stream_output('3.4.3.17')) +
        api.post_process(DoesNotRun, 'Skipping build due to missing tag.') +
        api.post_process(MustRun, 'Here comes a new shiny archiving recipe!') +
        api.post_process(check_bot_update) +
        api.post_process(DropExpectation)
    )

  # Test bailout on missing tag.
  mastername = 'client.v8.official'
  buildername = 'V8 Linux64'
  yield (
      api.test(api.v8.test_name(mastername, buildername, 'no_tag')) +
      api.properties.generic(mastername=mastername,
                             buildername=buildername,
                             branch='3.4',
                             revision='deadbeef') +
      api.v8.version_file(17, 'head') +
      api.override_step_data(
          'git describe', api.raw_io.stream_output('3.4.3.17-blabla')) +
      api.post_process(MustRun, 'Skipping build due to missing tag.') +
      api.post_process(DoesNotRun, 'Here comes a new shiny archiving recipe!') +
      api.post_process(DropExpectation)
  )
