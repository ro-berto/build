# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gerrit',
  'depot_tools/git',
  'depot_tools/infra_paths',
  'depot_tools/presubmit',
  'depot_tools/tryserver',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/runtime',
  'recipe_engine/step',
]


def _RunStepsInternal(api):
  repo_name = api.properties.get('repo_name')

  gclient_config = None
  if repo_name:
    api.gclient.set_config(repo_name)
  else:
    gclient_config = api.gclient.make_config()
    solution = gclient_config.solutions.add()
    solution.url = api.tryserver.gerrit_change_repo_url
    solution.name = api.properties['solution_name']
    gclient_config.got_revision_mapping[solution.name] = 'got_revision'

  bot_update_step = api.bot_update.ensure_checkout(
      gclient_config=gclient_config)
  relative_root = api.gclient.get_gerrit_patch_root(
      gclient_config=gclient_config).rstrip('/')
  got_revision_properties = api.bot_update.get_project_revision_properties(
      relative_root, gclient_config or api.gclient.c)
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
    '--issue', str(api.tryserver.gerrit_change.change),
    '--patchset', str(api.tryserver.gerrit_change.patchset),
    '--gerrit_url', 'https://%s' % api.tryserver.gerrit_change.host,
    '--gerrit_fetch',
  ]
  if api.properties.get('dry_run'):
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
      api.presubmit(*presubmit_args, venv=venv, timeout=8 * 60)
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
  safe_buildername = ''.join(
      c if c.isalnum() else '_' for c in api.buildbucket.builder_name)
  # HACK to avoid invalidating caches when PRESUBMIT running
  # on special infra/config branch, which is typically orphan.
  if api.tryserver.gerrit_change_target_ref == 'refs/heads/infra/config':
    safe_buildername += '_infra_config'
  if api.runtime.is_luci:
    cwd = api.path['cache'].join('builder', safe_buildername)
    api.file.ensure_directory('ensure builder cache dir', cwd)
  else:
    # TODO(machenbach): Remove this case when all builders using this recipe
    # migrated to LUCI, hard deadline being March 1st 2019.
    cwd = api.path['start_dir']
  with api.context(cwd=cwd):
    with api.tryserver.set_failure_hash():
      return _RunStepsInternal(api)


def GenTests(api):
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
      api.buildbucket.try_build(
          project=repo_name, builder='%s_presubmit' % repo_name) +
      api.properties(repo_name=repo_name) +
      api.step_data('presubmit', api.json.output([['%s_presubmit' % repo_name,
                                                   ['compile']]]))
    )

  yield (
    api.test('chromium_timeout') +
    api.buildbucket.try_build(
        project='chromium', builder='chromium_presubmit',
        git_repo='https://chromium.googlesource.com/chromium/src') +
    api.properties(repo_name='chromium') +
    api.step_data('presubmit', api.json.output(
        [['chromium_presubmit', ['compile']]]), times_out_after=60*20)
  )

  yield (
    api.test('chromium_dry_run') +
    api.buildbucket.try_build(
        project='chromium', builder='chromium_presubmit',
        git_repo='https://chromium.googlesource.com/chromium/src') +
    api.properties(
        repo_name='chromium',
        dry_run=True) +
    api.step_data('presubmit', api.json.output([['chromium_presubmit',
                                                 ['compile']]]))
  )

  yield (
    api.test('infra_with_runhooks') +
    api.buildbucket.try_build(
        project='infra', builder='infra_presubmit',
        git_repo='https://chromium.googlesource.com/infra/infra') +
    api.properties(
        repo_name='infra',
        runhooks=True) +
    api.step_data('presubmit', api.json.output([['infra_presubmit',
                                                 ['compile']]]))
  )

  yield (
    api.test('recipes-py') +
    api.buildbucket.try_build(
        project='infra', builder='recipes_presubmit',
        git_repo='https://chromium.googlesource.com/infra/luci/recipes-py') +
    api.properties(
        repo_name='recipes_py',
        runhooks=True) +
    api.step_data('presubmit', api.json.output([['recipes_presubmit',
                                                 ['compile']]]))
  )

  yield (
    api.test('luci-py') +
    api.buildbucket.try_build(
        project='infra', builder='luci_py_presubmit',
        git_repo='https://chromium.googlesource.com/infra/luci/luci-py') +
    api.properties(repo_name='luci_py') +
    api.step_data('presubmit', api.json.output([['recipes_presubmit',
                                                 ['compile']]]))
  )


  yield (
    api.test('presubmit-failure') +
    api.buildbucket.try_build(
        project='chromium', builder='chromium_presubmit',
        git_repo='https://chromium.googlesource.com/chromium/src') +
    api.properties(repo_name='chromium') +
    api.step_data('presubmit', api.json.output({}, retcode=1))
  )

  yield (
    api.test('presubmit-infra-failure') +
    api.buildbucket.try_build(
        project='chromium', builder='chromium_presubmit',
        git_repo='https://chromium.googlesource.com/chromium/src') +
    api.properties(repo_name='chromium') +
    api.step_data('presubmit', api.json.output({}, retcode=2))
  )

  yield (
    api.test('by_solution') +
    api.buildbucket.try_build(
        project='skia', builder='skia_presubmit',
        git_repo='https://skia.googlesource.com/skia.git') +
    api.properties(solution_name='skia') +
    api.step_data('presubmit', api.json.output([['chromium_presubmit',
                                                 ['compile']]]))
  )

  yield (
    api.test('v8_with_cache') +
    api.buildbucket.try_build(
        project='v8', builder='v8_presubmit',
        git_repo='https://chromium.googlesource.com/v8/v8') +
    api.properties(repo_name='v8') +
    api.runtime(is_luci=True, is_experimental=False)
  )

  yield (
    api.test('v8_with_cache_infra_config_branch') +
    api.buildbucket.try_build(
        project='v8', builder='v8_presubmit',
        git_repo='https://chromium.googlesource.com/v8/v8') +
    api.properties(repo_name='v8') +
    api.runtime(is_luci=True, is_experimental=False) +
    api.tryserver.gerrit_change_target_ref('refs/heads/infra/config')
  )
