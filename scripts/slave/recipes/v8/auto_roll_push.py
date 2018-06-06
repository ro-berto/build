# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'depot_tools/gclient',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/service_account',
  'recipe_engine/step',
  'recipe_engine/url',
  'v8',
]

def RunSteps(api):
  api.gclient.set_config('v8')
  api.bot_update.ensure_checkout(no_shallow=True)

  output = api.url.get_text(
      'https://v8-roll.appspot.com/status',
      step_name='check roll status',
      default_test_data='1',
    ).output
  api.step.active_result.presentation.logs['stdout'] = output.splitlines()
  if output.strip() != '1':
    api.step.active_result.presentation.step_text = "Pushing deactivated"
    return
  else:
    api.step.active_result.presentation.step_text = "Pushing activated"

  with api.context(cwd=api.path['checkout']):
    safe_buildername = ''.join(
      c if c.isalnum() else '_' for c in api.properties['buildername'])
    push_arg = [] if api.runtime.is_experimental else ['--push']
    push_account = (
        # TODO(sergiyb): Replace with api.service_account.default().get_email()
        # when https://crbug.com/846923 is resolved.
        'v8-ci-autoroll-builder@chops-service-accounts.iam.gserviceaccount.com'
        if api.runtime.is_luci else 'v8-autoroll@chromium.org')
    api.python(
        'push candidate',
        api.path['checkout'].join('tools', 'release', 'auto_push.py'),
        push_arg + [
         '--author', push_account,
         '--reviewer', push_account,
         '--work-dir', api.path['cache'].join(safe_buildername, 'workdir')],
      )


def GenTests(api):
  yield api.test('standard') + api.properties.generic(
      mastername='client.v8.fyi')
  yield (api.test('rolling_deactivated') +
      api.properties.generic(mastername='client.v8.fyi') +
      api.url.text('check roll status', '0'))

