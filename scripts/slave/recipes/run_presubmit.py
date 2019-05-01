# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/git',
  'depot_tools/presubmit',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/cq',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'depot_tools/tryserver',
  # The following two recipe modules are not used here,
  # but apparently set spooky gclient configs,
  # which get used by this recipe through "api.gclient.set_config".
  'v8',
  'webrtc',
]


def _RunStepsInternal(api):
  repo_name = api.properties.get('repo_name')

  # TODO(nodir): remove repo_name and repository_url properties.
  # They are redundant with api.tryserver.gerrit_change_repo_url.
  gclient_config = None
  if repo_name:
    api.gclient.set_config(repo_name)
  else:
    gclient_config = api.gclient.make_config()
    solution = gclient_config.solutions.add()
    solution.url = api.properties.get(
        'repository_url', api.tryserver.gerrit_change_repo_url)
    # Solution name shouldn't matter for most users, particularly if there is no
    # DEPS file, but if someone wants to override it, fine.
    solution.name = api.properties.get('solution_name', 's')
    gclient_config.got_revision_mapping[solution.name] = 'got_revision'

  bot_update_step = api.bot_update.ensure_checkout(
      gclient_config=gclient_config)
  relative_root = api.gclient.get_gerrit_patch_root(
      gclient_config=gclient_config).rstrip('/')
  got_revision_properties = api.bot_update.get_project_revision_properties(
      # Replace path.sep with '/', since most recipes are written assuming '/'
      # as the delimiter. This breaks on windows otherwise.
      relative_root.replace(api.path.sep, '/'), gclient_config or api.gclient.c)
  upstream = bot_update_step.json.output['properties'].get(
      got_revision_properties[0])

  abs_root = api.context.cwd.join(relative_root)
  with api.context(cwd=abs_root):
    # TODO(hinoka): Extract email/name from issue?
    api.git('-c', 'user.email=commit-bot@chromium.org',
            '-c', 'user.name=The Commit Bot',
            'commit', '-a', '-m', 'Committed patch',
            name='commit-git-patch', infra_step=False)

  if api.properties.get('runhooks'):
    with api.context(cwd=api.path['checkout']):
      api.gclient.runhooks()

  presubmit_args = [
    '--issue', api.tryserver.gerrit_change.change,
    '--patchset', api.tryserver.gerrit_change.patchset,
    '--gerrit_url', 'https://%s' % api.tryserver.gerrit_change.host,
    '--gerrit_fetch',
  ]
  if api.cq.state == api.cq.DRY:
    presubmit_args.append('--dry_run')

  presubmit_args.extend([
    '--root', abs_root,
    '--commit',
    '--verbose', '--verbose',
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

  # Repos that have '.vpython' spec.
  venv = None
  if repo_name == 'luci_py':
    venv = abs_root.join('.vpython')

  try:
    with api.context(env=env):
      # 8 minutes seems like a reasonable upper bound on presubmit timings.
      # According to event mon data we have, it seems like anything longer than
      # this is a bug, and should just instant fail.
      #
      # https://crbug.com/917479 This is a problem on luci-py, bump to 15
      # minutes.
      timeout = 900 if repo_name == 'luci_py' else 480
      api.presubmit(*presubmit_args, venv=venv, timeout=timeout)
  except api.step.StepTimeout:
    raise
  except api.step.StepFailure as step_failure:
    if step_failure.result and step_failure.result.retcode == 1:
      api.tryserver.set_test_failure_tryjob_result()
    else:
      # Script presubmit_support.py returns 2 on infra failures, but if we get
      # something else or nothing at all, then it's also an infra failure.
      api.tryserver.set_invalid_test_results_tryjob_result()
    raise


def RunSteps(api):
  try:
    safe_buildername = ''.join(
        c if c.isalnum() else '_' for c in api.buildbucket.builder_name)
    # HACK to avoid invalidating caches when PRESUBMIT running
    # on special infra/config branch, which is typically orphan.
    if api.tryserver.gerrit_change_target_ref == 'refs/heads/infra/config':
      safe_buildername += '_infra_config'
    cwd = api.path['builder_cache'].join(safe_buildername)
    api.file.ensure_directory('ensure builder cache dir', cwd)
  except KeyError:
    # No explicit builder cache directory defined. Use the "start_dir"
    # directory.
    # TODO(machenbach): Remove this case when all builders using this recipe
    # migrated to LUCI.
    cwd = api.path['start_dir']
  with api.context(cwd=cwd):
    return _RunStepsInternal(api)


def GenTests(api):
  yield (
    api.test('expected_tryjob') +
    api.runtime(is_luci=True, is_experimental=False) +
    api.buildbucket.try_build(
        project='chromium',
        bucket='try',
        builder='chromium_presubmit',
        git_repo='https://chromium.googlesource.com/chromium/src') +
    api.step_data('presubmit',
                  api.json.output([['chromium_presubmit', ['compile']]]))
  )

  # TODO(machenbach): This uses the same tryserver for all repos, which doesn't
  # reflect reality (cosmetical problem only).
  REPO_NAMES = [
      'build',
      'build_internal',
      'build_internal_scripts_slave',
      'catapult',
      'chrome_golo',
      'chromium',
      'depot_tools',
      'gyp',
      'internal_deps',
      'master_deps',
      'nacl',
      'openscreen',
      'pdfium',
      'skia',
      'slave_deps',
      'v8',
      'webports',
      'webrtc',
  ]
  for repo_name in REPO_NAMES:
    yield (
      api.test(repo_name) +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='%s_presubmit' % repo_name,
          repo_name=repo_name,
          gerrit_project=repo_name) +
      api.step_data('presubmit', api.json.output([['%s_presubmit' % repo_name,
                                                   ['compile']]]))
    )

  yield (
    api.test('chromium_timeout') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='chromium_presubmit',
        repo_name='chromium',
        gerrit_project='chromium/src') +
    api.step_data('presubmit', api.json.output(
        [['chromium_presubmit', ['compile']]]), times_out_after=60*20)
  )

  yield (
    api.test('chromium_dry_run') +
    api.cq(dry_run=True) +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='chromium_presubmit',
        repo_name='chromium',
        gerrit_project='chromium/src',
        dry_run=True) +
    api.step_data('presubmit', api.json.output([['chromium_presubmit',
                                                 ['compile']]]))
  )

  yield (
    api.test('infra_with_runhooks') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='infra_presubmit',
        repo_name='infra',
        gerrit_project='infra/infra',
        runhooks=True) +
    api.step_data('presubmit', api.json.output([['infra_presubmit',
                                                 ['compile']]]))
  )

  yield (
    api.test('recipes-py') +
    api.properties.tryserver(
        mastername='tryserver.infra',
        buildername='infra_presubmit',
        repo_name='recipes_py',
        gerrit_project='infra/luci/recipes-py',
        runhooks=True) +
    api.step_data('presubmit', api.json.output([['infra_presubmit',
                                                 ['compile']]]))
  )

  yield (
    api.test('recipes-py-windows') +
    api.properties.tryserver(
        mastername='tryserver.infra',
        buildername='infra_presubmit',
        repo_name='recipes_py',
        gerrit_project='infra/luci/recipes-py',
        runhooks=True) +
    api.platform('win', 64) +
    api.step_data('presubmit', api.json.output([['infra_presubmit',
                                                 ['compile']]]))
  )

  yield (
    api.test('luci-py') +
    api.properties.tryserver(
        mastername='luci.infra.try',
        buildername='Luci-py Presubmit',
        repo_name='luci_py',
        gerrit_project='infra/luci/luci-py') +
    api.step_data('presubmit', api.json.output({}))
  )

  yield (
    api.test('presubmit-failure') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='chromium_presubmit',
        repo_name='chromium',
        gerrit_project='chromium/src') +
    api.step_data('presubmit', api.json.output({}, retcode=1))
  )

  yield (
    api.test('presubmit-infra-failure') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='chromium_presubmit',
        repo_name='chromium',
        gerrit_project='chromium/src') +
    api.step_data('presubmit', api.json.output({}, retcode=2))
  )

  yield (
    api.test('repository_url_with_solution_name') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='chromium_presubmit',
        repository_url='https://skia.googlesource.com/skia.git',
        gerrit_project='skia',
        solution_name='skia') +
    api.step_data('presubmit',
                  api.json.output([['chromium_presubmit', ['compile']]]))
  )

  yield (
    api.test('v8_with_cache') +
    api.properties.tryserver(
        mastername='tryserver.v8',
        buildername='v8_presubmit',
        repo_name='v8',
        gerrit_project='v8/v8',
        runhooks=True,
        path_config='generic')
  )

  yield (
    api.test('v8_with_cache_infra_config_branch') +
    api.properties.tryserver(
        mastername='tryserver.v8',
        buildername='v8_presubmit',
        repo_name='v8',
        gerrit_project='v8/v8',
        runhooks=True,
        path_config='generic') +
    api.tryserver.gerrit_change_target_ref('refs/heads/infra/config')
  )
