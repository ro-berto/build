# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64

DEPS = [
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gerrit',
  'depot_tools/git',
  'depot_tools/gitiles',
  'recipe_engine/context',
  'recipe_engine/json',
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

TEST_DEPS_FILE = """
vars = {
  'chromium_git': 'https://chromium.googlesource.com',
  'v8_revision': '%s',
}

deps = {
  'src/v8':
    Var('chromium_git') + '/v8/v8.git' + '@' +  Var('v8_revision'),
}
"""

# Location of the infra-python package's run script.
_RUN_PY = '/opt/infra-python/run.py'


def V8RevisionFrom(deps):
  Var = lambda var: '%s'  # pylint: disable=W0612
  exec(deps)
  return vars['v8_revision']

def RunSteps(api):
  monitoring_state = 'failure'
  try:
    api.gclient.set_config('chromium')
    api.gclient.apply_config('v8_tot')

    # We need a full V8 checkout as well in order to checkout V8 DEPS, which
    # includes pinned depot_tools used by release scripts that we invoke below.
    api.gclient.apply_config('v8_bare')

    output = api.url.get_text(
        'https://v8-roll.appspot.com/status',
        step_name='check roll status',
        default_test_data='1',
    ).output
    api.step.active_result.presentation.logs['stdout'] = output.splitlines()
    if output.strip() != '1':
      api.step.active_result.presentation.step_text = 'Rolling deactivated'
      monitoring_state = 'deactivated'
      return
    else:
      api.step.active_result.presentation.step_text = 'Rolling activated'

    # Check for an open auto-roller CL. There should be at most one CL in the
    # chromium project, which is the last roll.
    push_account = (
        # TODO(sergiyb): Replace with api.service_account.default().get_email()
        # when https://crbug.com/846923 is resolved.
        'v8-ci-autoroll-builder@chops-service-accounts.iam.gserviceaccount.com'
        if api.runtime.is_luci else 'v8-autoroll@chromium.org')
    commits = api.gerrit.get_changes(
        'https://chromium-review.googlesource.com',
      query_params=[
        ('project', 'chromium/src'),
        ('owner', push_account),
        ('status', 'open'),
      ],
      limit=1,
    )

    if commits:
      cq_commits = api.gerrit.get_changes(
        'https://chromium-review.googlesource.com/a',
        query_params=[
          ('change', commits[0]['_number']),
          ('label', 'Commit-Queue>=1'),
        ],
        limit=1,
      )

      if not cq_commits:
        api.v8.checkout()
        dt_path = api.path['checkout'].join('third_party', 'depot_tools')
        with api.context(
            cwd=api.path['checkout'], env_prefixes={'PATH': [dt_path]}):
          if api.runtime.is_experimental:
            api.step('fake resubmit to CQ', cmd=None)
          else:
            api.git('cl', 'set-commit', '--gerrit', '-i', commits[0]['_number'])
          api.step.active_result.presentation.step_text = (
            'Stale roll found. Resubmitted to CQ.')
          monitoring_state = 'stale_roll'
      else:
        assert cq_commits[0]['_number'] == commits[0]['_number']
        api.step.active_result.presentation.step_text = 'Active rolls found.'
        monitoring_state = 'active_roll'

      return

    # Make it more likely to avoid inconsistencies when hitting different
    # mirrors.
    api.python.inline(
        'wait for consistency',
        'import time; time.sleep(20)',
    )

    api.v8.checkout()

    # Get deps file from gitiles.
    gitiles_deps = api.gitiles.download_file(
        'https://chromium.googlesource.com/chromium/src',
        'DEPS',
        branch='refs/heads/master',
        step_test_data= lambda: api.json.test_api.output({
          'value': base64.b64encode(TEST_DEPS_FILE % 'deadbeef'),
        }),
    )

    # Get the deps file used by the auto roller.
    local_deps = api.git(
        'cat-file', 'blob', 'HEAD:DEPS',
        stdout=api.raw_io.output_text(),
        step_test_data= lambda: api.raw_io.test_api.stream_output(
            TEST_DEPS_FILE % 'deadbeef'),
    ).stdout

    # Require both HEADs to be consistent before proceeding.
    if V8RevisionFrom(gitiles_deps) != V8RevisionFrom(local_deps):
      api.step('Local checkout is lagging behind.', cmd=None)
      api.step.active_result.presentation.status = api.step.WARNING
      monitoring_state = 'inconsistent'
      return

    with api.context(cwd=api.path['checkout'].join('v8')):
      safe_buildername = ''.join(
        c if c.isalnum() else '_' for c in api.properties['buildername'])
      if api.runtime.is_experimental:
        api.step('fake roll deps', cmd=None)
      else:
        result = api.python(
            'roll deps',
            api.v8.checkout_root.join(
                'v8', 'tools', 'release', 'auto_roll.py'),
            ['--chromium', api.path['checkout'],
             '--author', push_account,
             '--reviewer',
             'hablich@chromium.org,machenbach@chromium.org,'
             'kozyatinskiy@chromium.org,sergiyb@chromium.org',
             '--roll',
             '--json-output', api.json.output(),
             '--work-dir', api.path['cache'].join(safe_buildername, 'workdir')],
            step_test_data=lambda: api.json.test_api.output(
                {'monitoring_state': 'success'}),
        )
        monitoring_state = result.json.output['monitoring_state']
  finally:
    if not api.runtime.is_experimental:
      counter_config = {
        'name': '/v8/autoroller/count',
        'project': 'v8-roll',
        'result': monitoring_state,
        'value': 1,
      }
      api.python(
          'upload stats',
          _RUN_PY,
          [
            'infra.tools.send_ts_mon_values',
            '--ts-mon-target-type', 'task',
            '--ts-mon-task-service-name', 'auto-roll',
            '--ts-mon-task-job-name', 'roll',
            '--counter', api.json.dumps(counter_config),
          ],
      )


def GenTests(api):
  yield (api.test('standard') + api.properties.generic(
      mastername='client.v8.fyi', path_config='kitchen') +
      api.override_step_data('gerrit changes', api.json.output([]))
    )
  yield (api.test('rolling_deactivated') +
      api.properties.generic(mastername='client.v8', path_config='kitchen') +
      api.url.text('check roll status', '0')
    )
  yield (api.test('active_roll') +
      api.properties.generic(mastername='client.v8', path_config='kitchen') +
      api.override_step_data(
          'gerrit changes', api.json.output([{'_number': '123'}])) +
      api.override_step_data(
          'gerrit changes (2)', api.json.output([{'_number': '123'}]))
    )
  yield (api.test('stale_roll') +
      api.properties.generic(mastername='client.v8', path_config='kitchen') +
      api.override_step_data(
          'gerrit changes', api.json.output([{'_number': '123'}])) +
      api.override_step_data('gerrit changes (2)', api.json.output([]))
    )
  yield (api.test('inconsistent_state') +
      api.properties.generic(mastername='client.v8', path_config='kitchen') +
      api.override_step_data('gerrit changes', api.json.output([])) +
      api.override_step_data(
          'git cat-file', api.raw_io.stream_output(
              TEST_DEPS_FILE % 'beefdead'))
    )
  yield (api.test('standard_experimental') + api.properties.generic(
      mastername='client.v8.fyi', path_config='kitchen') +
      api.override_step_data('gerrit changes', api.json.output([])) +
      api.runtime(is_luci=True, is_experimental=True)
    )
  yield (api.test('stale_roll_experimental') +
      api.properties.generic(mastername='client.v8', path_config='kitchen') +
      api.override_step_data(
          'gerrit changes', api.json.output([{'_number': '123'}])) +
      api.override_step_data('gerrit changes (2)', api.json.output([])) +
      api.runtime(is_luci=True, is_experimental=True)
    )
