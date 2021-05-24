# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from RECIPE_MODULES.depot_tools.gclient import (api as gclient, CONFIG_CTX as
                                                GCLIENT_CONFIG_CTX)

DEPS = [
    'chromium',
    'chromium_checkout',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/step',
]


@GCLIENT_CONFIG_CTX()
def revision_resolver(c):
  s = c.solutions.add()
  s.name = 'src'
  c.revisions['src-internal'] = gclient.RevisionFallbackChain('refs/heads/main')


def RunSteps(api):
  _, builder_config = api.chromium_tests_builder_config.lookup_builder()

  api.chromium_tests.configure_build(builder_config)

  api.chromium_checkout.ensure_checkout(builder_config)

  api.step('details', [])
  api.step.active_result.presentation.logs['details'] = [
    'working_dir: %r' % (api.chromium_checkout.working_dir,),
    'affected_files: %r' % (
        api.chromium_checkout.get_files_affected_by_patch(),),
  ]


def GenTests(api):
  yield api.test(
      'full',
      api.chromium_tests_builder_config.generic_build(),
  )

  def verify_checkout_dir(check, step_odict, expected_path):
    step = step_odict['git diff to analyze patch']
    expected_path = str(expected_path)
    check(step.cwd == expected_path)
    return {}

  yield api.test(
      'win',
      api.chromium_tests_builder_config.try_build(
          builder_group='tryserver.chromium.win',
          builder='win10_chromium_x64_rel_ng',
      ),
      api.post_process(verify_checkout_dir,
                       api.path['cache'].join('builder', 'src')),
  )

  yield api.test(
      'linux',
      api.chromium_tests_builder_config.try_build(
          builder_group='tryserver.chromium.linux',
          builder='linux-rel',
      ),
      api.post_process(verify_checkout_dir,
                       api.path['cache'].join('builder', 'src')),
  )

  def verify_revision_resolver_in_log(check, steps, expected):
    gclient_config = json.loads(steps["gclient config"].logs["config"])
    check(gclient_config["revisions"]["src-internal"] == expected)

  yield api.test(
      'revision-resolver',
      api.chromium_tests_builder_config.generic_build(
          builder_group='fake-group',
          builder='fake-builder',
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-builder':
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='revision_resolver',
                      ),
              },
          }),
      ),
      api.post_check(verify_revision_resolver_in_log,
                     "*RevisionFallbackChain*"),
      api.post_process(post_process.DropExpectation),
  )
