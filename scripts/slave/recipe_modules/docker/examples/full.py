# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'docker',
]

def RunSteps(api):
  api.docker('version')
  api.docker.login()
  api.docker.run(
      'testimage', cmd_args=['test', 'cmd'], dir_mapping=[('/foo', '/bar')])
  api.docker(
      'push', 'gcr.io/chromium-container-registry/image:2018-11-16-01-25')


def GenTests(api):
  yield api.test('example')
