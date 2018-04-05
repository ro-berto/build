# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A recipe for picking a stable HEAD revision for chromium/src.

This recipe picks a commit at HEAD, and then triggers the other codesearch
recipes with the chosen commit hash as a parameter. This ensures that codesearch
index packs (used to generate xrefs) are all generated from the same revision.
"""

DEPS = [
  'recipe_engine/buildbucket',
  'recipe_engine/properties',
  'recipe_engine/step',
  'recipe_engine/url',
  'trigger',
]

def RunSteps(api):
  url = 'https://chromium.googlesource.com/chromium/src/+refs/heads/master?format=JSON'

  master_ref_json = api.url.get_json(
      url,
      step_name='Get hash of HEAD commit on master',
      strip_prefix=api.url.GERRIT_JSON_PREFIX,
      default_test_data={'refs/heads/master': {'value': 'deadbeef'}}).output
  commit_hash = master_ref_json.get(
      'refs/heads/master', {}).get('value', 'HEAD')
  api.step('Print revision', ['echo', commit_hash])

  # Trigger the chromium_codesearch builders.
  api.trigger(
      {
          'builder_name': 'codesearch-gen-chromium-chromiumos',
          'properties': {
              'root_solution_revision': commit_hash,
          },
      },
      {
          'builder_name': 'codesearch-gen-chromium-linux',
          'properties': {
              'root_solution_revision': commit_hash,
          },
      },
      {
          'builder_name': 'codesearch-gen-chromium-android',
          'properties': {
              'root_solution_revision': commit_hash,
          },
      },
  )

def GenTests(api):
  yield api.test('basic')
