# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'gclient',
  'git',
  'path',
  'properties',
  'raw_io',
  'step',
]

BASE_URL = 'https://chromium.googlesource.com'
REPO = BASE_URL + '/v8/v8'
V8_DEPS = {
  'v8/tools/clang': BASE_URL + '/chromium/src/tools/clang.git',
}


def GenSteps(api):
  api.step.auto_resolve_conflicts = True

  api.gclient.set_config('v8')
  api.bot_update.ensure_checkout(force=True, no_shallow=True)

  # Enforce a clean state.
  api.git(
      'checkout', '-f', 'origin/master',
      cwd=api.path['checkout'],
  )
  api.git(
      'branch', '-D', 'roll',
      ok_ret=any,
      cwd=api.path['checkout'],
  )
  api.git(
      'clean', '-ffd',
      cwd=api.path['checkout'],
  )
  api.git(
      'new-branch', 'roll',
      cwd=api.path['checkout'],
  )

  # Lookup the heads of all deps and roll them into v8's DEPS.
  for name, deps in V8_DEPS.iteritems():
    step_result = api.git(
        'ls-remote', deps, 'HEAD',
        name='look up %s' % name,
        stdout=api.raw_io.output(),
    )
    revision = step_result.stdout.strip().split('\t')[0]
    step_result.presentation.step_text = revision
    api.step(
        'roll dependency',
        ['roll-dep', name, revision],
        cwd=api.path['checkout'],
    )

  # Check for a difference. If the no deps changed, the diff is empty.
  step_result = api.git(
      'diff',
      stdout=api.raw_io.output(),
      cwd=api.path['checkout'],
  )
  diff = step_result.stdout.strip()
  step_result.presentation.logs['diff'] = diff.splitlines()

  # Commit deps change and send to CQ.
  if diff:
    api.git(
        'commit', '-a',
        '-m', 'Update V8 DEPS.',
        '-m', 'TBR=machenbach@chromium.org',
        stdout=api.raw_io.output(),
        cwd=api.path['checkout'],
    )
    api.git(
        'cl', 'upload', '-f', '--use-commit-queue', '--bypass-hooks',
        '--email', 'v8-autoroll@chromium.org', '--send-mail',
        cwd=api.path['checkout'],
    )


def GenTests(api):
  test = (
      api.test('roll') +
      api.properties.generic(mastername='client.v8',
                             buildername='Auto-roll - v8 deps') +
      api.override_step_data(
          'git diff',
          api.raw_io.stream_output('some difference', stream='stdout'),
      )
  )

  for name in V8_DEPS:
    test += api.override_step_data(
        'look up %s' % name,
        api.raw_io.stream_output('deadbeaf\tHEAD', stream='stdout'),
    )

  yield test
