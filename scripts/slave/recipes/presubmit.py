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
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'depot_tools/tryserver',
  # The following two recipe modules are not used here,
  # but apparently set spooky gclient configs,
  # which get used by this recipe through "api.gclient.set_config".
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
    bot_update_step = api.presubmit.prepare()
    return api.presubmit.execute(bot_update_step)


def GenTests(api):
  yield (
    api.test('expected_tryjob') +
    api.runtime(is_luci=True, is_experimental=False) +
    api.buildbucket.try_build(
        project='chromium',
        bucket='try',
        builder='chromium_presubmit',
        git_repo='https://chromium.googlesource.com/chromium/src') +
    api.step_data('presubmit', api.json.output({}))
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
      api.step_data('presubmit', api.json.output(
        {'errors': [], 'notifications': [], 'warnings': []}
      ))
    )

  yield (
    api.test('repository_url_with_solution_name') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='chromium_presubmit',
        repository_url='https://skia.googlesource.com/skia.git',
        gerrit_project='skia',
        solution_name='skia') +
    api.step_data('presubmit', api.json.output(
      {'errors': [], 'notifications': [], 'warnings': []}
    ))
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
