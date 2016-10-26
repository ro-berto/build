# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/git',
  'depot_tools/presubmit',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'depot_tools/tryserver',
  'depot_tools/rietveld',
  'v8',
  'webrtc',
]


def _RunStepsInternal(api):
  repo_name = api.properties['repo_name']
  codereview_auth = api.properties.get('codereview_auth', False)
  patch_storage = api.properties.get('patch_storage', 'rietveld')

  api.gclient.set_config(repo_name)

  kwargs = {}
  bot_update_step = api.bot_update.ensure_checkout(
      patch_oauth2=codereview_auth,
      **kwargs)
  relative_root = api.gclient.calculate_patch_root(
      api.properties['patch_project']).rstrip('/')
  got_revision_property = api.gclient.c.got_revision_mapping[relative_root]
  upstream = bot_update_step.json.output['properties'].get(
      got_revision_property)

  abs_root = api.path['slave_build'].join(relative_root)
  # TODO(hinoka): Extract email/name from issue?
  api.git('-c', 'user.email=commit-bot@chromium.org',
          '-c', 'user.name=The Commit Bot',
          'commit', '-a', '-m', 'Committed patch',
          name='commit git patch', cwd=abs_root)

  if api.properties.get('runhooks'):
    api.gclient.runhooks()

  if patch_storage == 'rietveld':
    presubmit_args = [
      '--issue', api.properties['issue'],
      '--patchset', api.properties['patchset'],
      '--rietveld_url', api.properties['rietveld'],
      '--rietveld_fetch',
    ]
    if codereview_auth:
      presubmit_args.extend([
          '--rietveld_email_file',
          api.path['build'].join('site_config', '.rietveld_client_email')])
      presubmit_args.extend([
          '--rietveld_private_key_file',
          api.path['build'].join('site_config', '.rietveld_secret_key')])
    else:
      presubmit_args.extend(['--rietveld_email', ''])  # activate anonymous mode
  elif patch_storage == 'gerrit':
    gerrit_url = api.properties.get('patch_gerrit_url')
    if not gerrit_url:
      # TODO(tandrii): clean up old Gerrit patch properties.
      # Field event.patchSet.ref looks like 'refs/changes/11/338811/4'
      issue, patchset = api.properties['event.patchSet.ref'].split('/')[-2:]
      gerrit_url = api.properties['gerrit']
    else:
      issue = api.properties.get('patch_issue')
      patchset = api.properties.get('patch_set')
    presubmit_args = [
      '--issue', issue,
      '--patchset', patchset,
      '--gerrit_url', gerrit_url,
      '--gerrit_fetch',
    ]
  else:  # pragma: no cover
    assert False, 'patch_storage %s is not supported' % patch_storage
  if api.properties.get('dry_run'):
    presubmit_args.append('--dry_run')

  presubmit_args.extend([
    '--root', abs_root,
    '--commit',
    '--verbose', '--verbose',
    '--skip_canned', 'CheckRietveldTryJobExecution',
    '--skip_canned', 'CheckTreeIsOpen',
    '--skip_canned', 'CheckBuildbotPendingBuilds',
    '--upstream', upstream,  # '' if not in bot_update mode.
  ])


  env = {}
  if repo_name in ['build', 'build_internal', 'build_internal_scripts_slave']:
    # This should overwrite the existing pythonpath which includes references to
    # the local build checkout (but the presubmit scripts should only pick up
    # the scripts from presubmit_build checkout).
    env['PYTHONPATH'] = ''

  try:
    api.presubmit(*presubmit_args, env=env)
  except api.step.StepFailure as step_failure:
    if step_failure.result and step_failure.result.retcode == 1:
      api.tryserver.set_test_failure_tryjob_result()
    else:
      # Script presubmit_support.py returns 2 on infra failures, but if we get
      # something else or nothing at all, then it's also an infra failure.
      api.tryserver.set_invalid_test_results_tryjob_result()
    raise


def RunSteps(api):
  with api.tryserver.set_failure_hash():
    return _RunStepsInternal(api)


def GenTests(api):
  # TODO(machenbach): This uses the same tryserver for all repos, which doesn't
  # reflect reality (cosmetical problem only).
  for repo_name in ['chromium', 'v8', 'nacl', 'webports', 'gyp',
                    'build', 'build_internal', 'build_internal_scripts_slave',
                    'master_deps', 'slave_deps', 'internal_deps',
                    'depot_tools', 'skia', 'chrome_golo', 'webrtc', 'catapult']:
    yield (
      api.test(repo_name) +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='%s_presubmit' % repo_name,
          repo_name=repo_name,
          patch_project=repo_name) +
      api.step_data('presubmit', api.json.output([['%s_presubmit' % repo_name,
                                                   ['compile']]]))
    )

  yield (
    api.test('chromium_dry_run') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='chromium_presubmit',
        repo_name='chromium',
        patch_project='chromium',
        dry_run=True) +
    api.step_data('presubmit', api.json.output([['chromium_presubmit',
                                                 ['compile']]]))
  )

  yield (
    api.test('chromium_with_auth') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='chromium_presubmit',
        repo_name='chromium',
        codereview_auth=True,
        patch_project='chromium') +
    api.step_data('presubmit', api.json.output([['chromium_presubmit',
                                                 ['compile']]]))
  )

  yield (
    api.test('infra_with_runhooks') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='infra_presubmit',
        repo_name='infra',
        patch_project='infra',
        runhooks=True) +
    api.step_data('presubmit', api.json.output([['infra_presubmit',
                                                 ['compile']]]))
  )

  yield (
    api.test('infra_with_runhooks_and_gerrit_deprecated') +
    api.properties.tryserver_gerrit(
        full_project_name='infra/infra',
        repo_name='infra',
        mastername='tryserver.infra',
        buildername='infra_presubmit',
        runhooks=True) +
    api.step_data('presubmit', api.json.output([['infra_presubmit',
                                                 ['compile']]]))
  )

  yield (
    api.test('infra_with_runhooks_and_gerrit') +
    api.properties.tryserver(
        gerrit_project='infra/infra',
        repo_name='infra',
        mastername='tryserver.infra',
        buildername='infra_presubmit',
        runhooks=True) +
    api.step_data('presubmit', api.json.output([['infra_presubmit',
                                                 ['compile']]]))
  )

  yield (
    api.test('depot_tools_and_gerrit') +
    api.properties.tryserver(
        gerrit_project='chromium/tools/depot_tools',
        repo_name='depot_tools',
        mastername='tryserver.infra',
        buildername='presubmit_depot_tools',
        runhooks=True) +
    api.step_data('presubmit', api.json.output([['depot_tools_presubmit',
                                                 ['test']]]))
  )

  yield (
    api.test('recipes-py') +
    api.properties.tryserver(
        mastername='tryserver.infra',
        buildername='infra_presubmit',
        repo_name='recipes_py',
        patch_project='recipes-py',
        runhooks=True) +
    api.step_data('presubmit', api.json.output([['infra_presubmit',
                                                 ['compile']]]))
  )

  yield (
    api.test('presubmit-failure') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='chromium_presubmit',
        repo_name='chromium',
        patch_project='chromium') +
    api.step_data('presubmit', api.json.output({}, retcode=1))
  )

  yield (
    api.test('presubmit-infra-failure') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='chromium_presubmit',
        repo_name='chromium',
        patch_project='chromium') +
    api.step_data('presubmit', api.json.output({}, retcode=2))
  )
