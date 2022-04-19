# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.depot_tools.gclient import (api as gclient, CONFIG_CTX as
                                                GCLIENT_CONFIG_CTX)

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium_checkout',
    'depot_tools/gclient',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
]


@GCLIENT_CONFIG_CTX()
def revision_resolver(c):
  s = c.solutions.add()
  s.name = 'src'
  c.revisions['src-internal'] = gclient.RevisionFallbackChain('refs/heads/main')


def RunSteps(api):
  api.gclient.set_config(api.properties.get('gclient_config', 'chromium'))

  api.chromium_checkout.ensure_checkout()

  api.step('details', [])
  api.step.active_result.presentation.logs['details'] = [
    'affected_files: %r' % (
        api.chromium_checkout.get_files_affected_by_patch(),),
  ]


def GenTests(api):
  yield api.test(
      'full',
      api.platform('linux', 64),
      api.buildbucket.generic_build(),
  )

  def verify_checkout_dir(check, step_odict, expected_path):
    step = step_odict['git diff to analyze patch']
    expected_path = str(expected_path)
    check(step.cwd == expected_path)
    return {}

  yield api.test(
      'win',
      api.buildbucket.try_build(),
      api.platform('win', 64),
      api.post_process(verify_checkout_dir,
                       api.path['cache'].join('builder', 'src')),
  )

  yield api.test(
      'linux',
      api.buildbucket.try_build(),
      api.platform('linux', 64),
      api.post_process(verify_checkout_dir,
                       api.path['cache'].join('builder', 'src')),
  )

  def verify_revision_resolver_in_log(check, steps, expected):
    gclient_config = api.json.loads(steps["gclient config"].logs["config"])
    check(gclient_config["revisions"]["src-internal"] == expected)

  yield api.test(
      'revision-resolver',
      api.properties(gclient_config='revision_resolver'),
      api.post_check(verify_revision_resolver_in_log,
                     "*RevisionFallbackChain*"),
      api.post_process(post_process.DropExpectation),
  )
