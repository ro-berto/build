# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

DEPS = [
    'commit_position',
    'properties',
    'step',
    ]

VALID_CP = 'refs/heads/master@{#12345}'
INVALID_CP_BAD_FORMAT = 'foo/var@{missing-hash}'
INVALID_CP_NON_NUMERIC = 'refs/heads/master@{#foo}'

def GenSteps(api):
  cp = api.properties['cp']
  expect_revision = api.properties.get('revision')
  expect_branch = api.properties.get('branch')

  # Parse a valid commit position (branch).
  try:
    branch = api.commit_position.parse_branch(cp)
  except ValueError:
    raise recipe_api.StepFailure("Failed to parse branch from: %s" % (cp,))
  api.step('test branch parse', ['/bin/echo', branch])
  assert branch == expect_branch, "Invalid parsed branch: %s" % (branch,)

  # Parse a valid commit position (revision).
  revision = api.commit_position.parse_revision(cp)
  api.step('test revision parse', ['/bin/echo', revision])
  assert revision == expect_revision, "Invalid parsed revision: %s" % (
      revision,)

  # Construct a commit position.
  value = api.commit_position.construct(branch, revision)
  api.step('test construction', ['/bin/echo', value])
  assert value == cp, "Construction failed: %s" % (value,)


def GenTests(api):
  yield (
      api.test('valid') +
      api.properties(
        cp=VALID_CP,
        revision=12345,
        branch='refs/heads/master',))

  yield (
      api.test('invalid_bad_format') +
      api.properties(
        cp=INVALID_CP_BAD_FORMAT))

  yield (
      api.test('invalid_non_numeric') +
      api.properties(
        cp=INVALID_CP_NON_NUMERIC))
