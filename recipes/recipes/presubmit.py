# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from PB.recipe_engine import result as result_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2

from recipe_engine import post_process
import textwrap

DEPS = [
    'depot_tools/gclient',
    'depot_tools/presubmit',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/cq',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'depot_tools/tryserver',
    # The following recipe modules are not used here,
    # but apparently set spooky gclient configs,
    # which get used by this recipe through "api.gclient.set_config".
    'angle',
    'v8',
    'webrtc',
]


def RunSteps(api):
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
    api.gclient.c = gclient_config

  safe_buildername = ''.join(
      c if c.isalnum() else '_' for c in api.buildbucket.builder_name)
  # HACK to avoid invalidating caches when PRESUBMIT running
  # on special infra/config branch, which is typically orphan.
  if api.tryserver.gerrit_change_target_ref == 'refs/heads/infra/config':
    safe_buildername += '_infra_config'
  cwd = api.path['cache'].join('builder', safe_buildername)
  api.file.ensure_directory('ensure builder cache dir', cwd)

  skip_owners = False
  # TODO(crbug.com/1046950): Make this check stricter.
  if (api.tryserver.gerrit_change.host == 'chromium-review.googlesource.com' and
      api.tryserver.gerrit_change.project == 'chromium/src' and
      api.tryserver.gerrit_change_target_ref.startswith('refs/branch-heads/')):
    skip_owners = True

  if api.cq.active:
    api.cq.allow_reuse_for(api.cq.DRY_RUN, api.cq.QUICK_DRY_RUN)

  with api.context(cwd=cwd):
    bot_update_step = api.presubmit.prepare()
    return api.presubmit.execute(bot_update_step, skip_owners)


def GenTests(api):
  yield api.test(
      'expected_tryjob',
      api.buildbucket.try_build(
          project='chromium',
          bucket='try',
          builder='chromium_presubmit',
          git_repo='https://chromium.googlesource.com/chromium/src'),
      api.cq(run_mode=api.cq.DRY_RUN),
      api.step_data('presubmit', api.json.output({})),
      api.step_data('presubmit py3', api.json.output({})),
  )

  REPO_NAMES = [
      'angle',
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
    yield api.test(
        repo_name,
        api.properties.tryserver(
            buildername='%s_presubmit' % repo_name,
            repo_name=repo_name,
            gerrit_project=repo_name),
        api.properties(**{'$depot_tools/presubmit': {
            'timeout_s': 654
        }}),
        api.step_data(
            'presubmit',
            api.json.output({
                'errors': [],
                'notifications': [],
                'warnings': []
            })),
    )

  yield api.test(
      'repository_url_with_solution_name',
      api.properties.tryserver(
          buildername='chromium_presubmit',
          repository_url='https://skia.googlesource.com/skia.git',
          gerrit_project='skia',
          solution_name='skia'),
      api.properties(**{'$depot_tools/presubmit': {
          'timeout_s': 654
      }}),
      api.step_data(
          'presubmit',
          api.json.output({
              'errors': [],
              'notifications': [],
              'warnings': []
          })),
  )

  yield api.test(
      'v8_with_cache',
      api.properties.tryserver(
          buildername='v8_presubmit',
          repo_name='v8',
          gerrit_project='v8/v8',
          runhooks=True),
      api.properties(**{'$depot_tools/presubmit': {
          'timeout_s': 654
      }}),
  )

  yield api.test(
      'v8_with_cache_infra_config_branch',
      api.properties.tryserver(
          buildername='v8_presubmit',
          repo_name='v8',
          gerrit_project='v8/v8',
          runhooks=True),
      api.properties(**{'$depot_tools/presubmit': {
          'timeout_s': 654
      }}),
      api.tryserver.gerrit_change_target_ref('refs/heads/infra/config'),
  )

  yield api.test(
      'branch_presubmit',
      api.buildbucket.try_build(
          project='chromium',
          bucket='try',
          builder='chromium_presubmit',
          git_repo='https://chromium.googlesource.com/chromium/src'),
      api.step_data('presubmit', api.json.output({})),
      api.tryserver.gerrit_change_target_ref('refs/branch-heads/3987'),
  )
