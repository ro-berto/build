# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gerrit',
  'depot_tools/git',
  'recipe_engine/context',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'webrtc',
]


GERRIT_URL = 'https://webrtc-review.googlesource.com'


def RunSteps(api):
  api.gclient.set_config('webrtc')

  # Make sure the checkout contains all deps for all platforms.
  for os in ['linux', 'android', 'mac', 'ios', 'win', 'unix']:
    api.gclient.c.target_os.add(os)

  step_result = api.python(
        'check roll status',
        api.package_repo_resource('scripts', 'tools', 'pycurl.py'),
        args=['https://webrtc-roll-cr-rev-status.appspot.com/status'],
        stdout=api.raw_io.output_text(),
        step_test_data=lambda: api.raw_io.test_api.stream_output(
            '1', stream='stdout')
  )
  step_result.presentation.logs['stdout'] = step_result.stdout.splitlines()
  if step_result.stdout.strip() != '1':
    step_result.presentation.step_text = 'Rolling deactivated'
    return
  else:
    step_result.presentation.step_text = 'Rolling activated'

  api.webrtc.checkout()
  api.gclient.runhooks()

  with api.context(cwd=api.path['checkout']):
    push_account = (
        # TODO(oprypin): Replace with api.service_account.default().get_email()
        # when https://crbug.com/846923 is resolved.
        'chromium-webrtc-autoroll@webrtc-ci.iam.gserviceaccount.com'
        if api.runtime.is_luci else 'buildbot@webrtc.org')
    commits = api.gerrit.get_changes(
        GERRIT_URL,
        query_params=[
            ('project', 'src'),
            ('owner', push_account),
            ('status', 'open'),
        ],
        limit=1,
    )
    if commits:
      cq_commits = api.gerrit.get_changes(
          GERRIT_URL,
          query_params=[
              ('change', commits[0]['_number']),
              ('label', 'Commit-Queue=2'),
          ],
          limit=1,
      )
      if cq_commits:
        assert cq_commits[0]['_number'] == commits[0]['_number']
        api.step.active_result.presentation.step_text = 'Active rolls found.'
        return
      else:
        with api.context(env={'SKIP_GCE_AUTH_FOR_GIT': '1'}):
          api.git('cl', 'set-close', '--gerrit', '-i', commits[0]['_number'])
          api.step.active_result.presentation.step_text = (
              'Stale roll found. Abandoned.')

    # Enforce a clean state, and discard any local commits from previous runs.
    api.git('checkout', '-f', 'master')
    api.git('pull', 'origin', 'master')
    api.git('clean', '-ffd')

    # Run the roll script. It will take care of branch creation, modifying DEPS,
    # uploading etc. It will also delete any previous roll branch.
    params = ['--clean', '--verbose']
    if api.runtime.is_experimental:
      params.append('--skip-cq')
    else:
      params.append('--cq-over=100')
    api.python(
        'autoroll DEPS',
        api.path['checkout'].join('tools_webrtc', 'autoroller', 'roll_deps.py'),
        params,
    )


def GenTests(api):
  yield (
      api.test('rolling_activated') +
      api.properties.generic(mastername='client.webrtc.fyi',
                             buildername='Auto-roll - WebRTC DEPS') +
      api.override_step_data('gerrit changes', api.json.output([]))
  )
  yield (
      api.test('rolling_activated_luci') +
      api.properties.generic(mastername='client.webrtc.fyi',
                             buildername='Auto-roll - WebRTC DEPS') +
      api.override_step_data('gerrit changes', api.json.output([])) +
      api.runtime(is_luci=True, is_experimental=True)
  )
  yield (
      api.test('rolling_deactivated') +
      api.properties.generic(mastername='client.webrtc.fyi',
                             buildername='Auto-roll - WebRTC DEPS') +
      api.override_step_data('check roll status',
                             api.raw_io.stream_output('0', stream='stdout'))
  )
  yield (
      api.test('stale_roll') +
      api.properties.generic(mastername='client.webrtc.fyi',
                             buildername='Auto-roll - WebRTC DEPS') +
      api.override_step_data(
          'gerrit changes', api.json.output([{'_number': '123'}])) +
      api.override_step_data('gerrit changes (2)', api.json.output([]))
  )
  yield (
      api.test('previous_roll_in_cq') +
      api.properties.generic(mastername='client.webrtc.fyi',
                             buildername='Auto-roll - WebRTC DEPS') +
      api.override_step_data(
          'gerrit changes', api.json.output([{'_number': '123'}])) +
      api.override_step_data(
          'gerrit changes (2)', api.json.output([{'_number': '123'}]))
  )
