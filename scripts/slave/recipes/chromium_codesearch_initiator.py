# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A recipe for picking a stable HEAD revision for chromium/src.

This recipe picks a commit at HEAD, and then triggers the other codesearch
recipes with the chosen commit hash as a parameter. This ensures that codesearch
index packs (used to generate xrefs) are all generated from the same revision.
"""

from datetime import datetime

DEPS = [
  'recipe_engine/buildbucket',
  'recipe_engine/json',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'recipe_engine/scheduler',
  'recipe_engine/step',
  'recipe_engine/time',
  'recipe_engine/url',
]

BUILDERS = [
    'codesearch-gen-chromium-chromiumos',
    'codesearch-gen-chromium-linux',
    'codesearch-gen-chromium-android',
    'codesearch-gen-chromium-win',
]

GERRIT_TEST_DATA = {
    'commit': 'deadbeef',
    'committer': {
        'time': 'Wed Jul 18 04:22:39 2018'
    }
}

GERRIT_TEST_DATA_NO_COMMIT = {}

GERRIT_TEST_DATA_NO_TIMESTAMP = {
    'commit': 'deadbeef',
}

GERRIT_TEST_DATA_BAD_TIMESTAMP = {
    'commit': 'deadbeef',
    'committer': {
        'time': 'Jul 18 04:22:39 2018'
    }
}

GERRIT_URL = 'https://chromium.googlesource.com/chromium/src/+show/master?format=JSON'
GERRIT_DATETIME_FORMAT = '%a %b %d %H:%M:%S %Y'

def RunSteps(api):
  master_ref_json = api.url.get_json(
      GERRIT_URL,
      step_name='Get hash of HEAD commit on master',
      strip_prefix=api.url.GERRIT_JSON_PREFIX,
      default_test_data=GERRIT_TEST_DATA).output

  formatted_time = master_ref_json.get('committer', {}).get('time', '')
  try:
    time_since_epoch = datetime.strptime(
        formatted_time, GERRIT_DATETIME_FORMAT) - datetime(1970, 1, 1)
    unix_timestamp = time_since_epoch.total_seconds()
  except ValueError as e:
    api.step.active_result.presentation.step_text = str(e)
    api.step.active_result.presentation.status = api.step.WARNING
    # If we failed to extract the time, use the current time as an
    # approximation.
    unix_timestamp = api.time.time()

  commit_hash = master_ref_json.get('commit', 'HEAD')

  # Trigger the chromium_codesearch builders.
  properties = {
      'root_solution_revision': commit_hash,
      'root_solution_revision_timestamp': unix_timestamp
  }
  api.scheduler.emit_trigger(
      api.scheduler.BuildbucketTrigger(properties=properties),
      project='infra', jobs=BUILDERS)

def GenTests(api):
  yield api.test('basic') + api.runtime(is_luci=True, is_experimental=False)
  yield (
      api.test('missing_commit') +
      api.runtime(is_luci=True, is_experimental=False) +
      api.url.json('Get hash of HEAD commit on master', GERRIT_TEST_DATA_NO_COMMIT)
  )
  yield (
      api.test('missing_timestamp') +
      api.runtime(is_luci=True, is_experimental=False) +
      api.url.json('Get hash of HEAD commit on master', GERRIT_TEST_DATA_NO_TIMESTAMP)
  )
  yield (
      api.test('bad_timestamp') +
      api.runtime(is_luci=True, is_experimental=False) +
      api.url.json('Get hash of HEAD commit on master', GERRIT_TEST_DATA_BAD_TIMESTAMP)
  )
