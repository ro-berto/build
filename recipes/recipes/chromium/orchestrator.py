# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Triggers compilator and tests"""

from recipe_engine import post_process
from PB.recipe_modules.build.chromium_orchestrator.properties import (
    InputProperties)
from RECIPE_MODULES.depot_tools.tryserver import api as tryserver

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'chromium',
    'chromium_orchestrator',
    'chromium_tests_builder_config',
    'code_coverage',
    'depot_tools/tryserver',
    'recipe_engine/cas',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/step',
]


def RunSteps(api):
  api.tryserver.require_is_tryserver()

  with api.chromium.chromium_layout():
    return api.chromium_orchestrator.trybot_steps()


def GenTests(api):
  ctbc_api = api.chromium_tests_builder_config

  def ctbc_properties():
    return ctbc_api.properties(
        ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
            builder_group='fake-group',
            builder='fake-builder',
        ).with_mirrored_tester(
            builder_group='fake-group',
            builder='fake-tester',
        ).assemble())

  yield api.test(
      'basic',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.chromium_orchestrator.fake_head_revision(),
      api.post_process(post_process.StepCommandContains, 'bot_update',
                       ['--refs', 'refs/heads/main']),
      api.post_process(post_process.StepCommandContains, 'bot_update',
                       ['--patch_ref']),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.post_process(
          post_process.StepCommandContains,
          'install infra/chromium/compilator_watcher.ensure_installed', [
              '-ensure-file', 'infra/chromium/compilator_watcher/${platform} '
              'git_revision:e841fc'
          ]),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.MustRun, 'browser_tests (with patch)'),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
