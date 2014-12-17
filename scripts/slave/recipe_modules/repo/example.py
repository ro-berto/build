# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'repo'
]


def GenSteps(api):
  api.repo.init('http://manifest_url')
  api.repo.init('http://manifest_url/manifest', '-b', 'branch')
  api.repo.reset()
  api.repo.clean()
  api.repo.clean('-x')
  api.repo.sync()


def GenTests(api):
  yield api.test('setup_repo')
