# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'adb',
    'build',
    'chromium',
    'chromium_android',
    'chromium_swarming',
    'chromium_tests',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/gitiles',
    'depot_tools/gsutil',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/commit_position',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/legacy_annotation',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'recipe_engine/raw_io',
    'recipe_engine/runtime',
    'test_results',
    'test_utils',
]


def get_component_revision_from_deps(api, component, project, repository_url,
                                     branch):
  deps = api.gitiles.download_file(
      repository_url,
      'DEPS',
      branch=branch,
      step_name='fetch %s DEPS' % project)
  deps_file = api.path.mkdtemp(project).join('DEPS')
  api.file.write_text('snapshot %s DEPS' % project, deps_file, deps)
  revision = api.gclient(
      'get %s_revision' % component,
      ['getdep',
       '--var=%s_revision' % component,
       '--deps-file=%s' % deps_file],
      stdout=api.raw_io.output_text(add_output_log=True),
  ).stdout.strip()
  return revision


def RunSteps(api):
  _, builder_config = api.chromium_tests_builder_config.lookup_builder()
  is_angle_tot = 'angle_top_of_tree' in builder_config.gclient_apply_config
  if is_angle_tot:
    angle_revision = 'refs/heads/master'
  else:
    angle_revision = get_component_revision_from_deps(
        api, 'angle', 'Chromium',
        'https://chromium.googlesource.com/chromium/src', 'refs/heads/master')

  chromium_revision = get_component_revision_from_deps(
      api, 'chromium', 'ANGLE', 'https://chromium.googlesource.com/angle/angle',
      angle_revision)

  with api.chromium.chromium_layout():
    return api.chromium_tests.main_waterfall_steps(
        root_solution_revision=chromium_revision)


def GenTests(api):
  return []
