# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'recipe_engine/raw_io',
    'repo',
    'recipe_engine/step',
]


REPO_LIST_OUTPUT = """\
src/foo : foo
src/bar : bar
badline
"""


def RunSteps(api):
  api.repo.init('http://manifest_url')
  api.repo.init('http://manifest_url/manifest', '-b', 'branch')
  api.repo.reset()
  api.repo.clean()
  api.repo.clean('-x')
  api.repo.sync()
  api.repo.manifest()

  repos = api.repo.list()
  assert repos == [('src/foo', 'foo'), ('src/bar', 'bar')]
  api.step('repo list echo', ['echo', str(repos)])


def GenTests(api):
  yield api.test(
      'setup_repo',
      api.step_data('repo list', api.raw_io.stream_output(REPO_LIST_OUTPUT)),
  )
