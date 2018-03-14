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
  'recipe_engine/step',
  'recipe_engine/url',
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
    commits = api.gerrit.get_changes(
        'https://chromium-review.googlesource.com',
      query_params=[
        ('project', 'chromium/src'),
        ('owner', 'v8-autoroll@chromium.org'),
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
        api.bot_update.ensure_checkout(no_shallow=True)
        with api.context(cwd=api.path['checkout']):
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

    api.bot_update.ensure_checkout(no_shallow=True)

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
      result = api.python(
          'roll deps',
          api.path['checkout'].join(
              'v8', 'tools', 'release', 'auto_roll.py'),
          ['--chromium', api.path['checkout'],
           '--author', 'v8-autoroll@chromium.org',
           '--reviewer',
           'hablich@chromium.org,machenbach@chromium.org,'
           'kozyatinskiy@chromium.org,sergiyb@chromium.org',
           '--roll',
           '--json-output', api.json.output(),
           '--work-dir', api.path['start_dir'].join('workdir')],
          step_test_data=lambda: api.json.test_api.output(
              {'monitoring_state': 'success'}),
      )
    monitoring_state = result.json.output['monitoring_state']
  finally:
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
      mastername='client.v8.fyi') +
      api.override_step_data('gerrit changes', api.json.output([]))
    )
  yield (api.test('rolling_deactivated') +
      api.properties.generic(mastername='client.v8') +
      api.url.text('check roll status', '0')
    )
  yield (api.test('active_roll') +
      api.properties.generic(mastername='client.v8') +
      api.override_step_data(
          'gerrit changes', api.json.output([{'_number': '123'}])) +
      api.override_step_data(
          'gerrit changes (2)', api.json.output([{'_number': '123'}]))
    )
  yield (api.test('stale_roll') +
      api.properties.generic(mastername='client.v8') +
      api.override_step_data(
          'gerrit changes', api.json.output([{'_number': '123'}])) +
      api.override_step_data('gerrit changes (2)', api.json.output([]))
    )
  yield (api.test('inconsistent_state') +
      api.properties.generic(mastername='client.v8') +
      api.override_step_data('gerrit changes', api.json.output([])) +
      api.override_step_data(
          'git cat-file', api.raw_io.stream_output(
              TEST_DEPS_FILE % 'beefdead'))
    )
