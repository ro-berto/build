# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'git',
  'path',
  'platform',
  'properties',
  'step',
]

def GenSteps(api):
  yield api.git.checkout(api.properties['repository'] + '.git', recursive=True)

  tmp_path = api.path.checkout('.tmp')
  yield api.step('mktmp', ['mkdir', tmp_path])
  yield api.step('update-install', ['npm', 'install', '--tmp', tmp_path],
             cwd=api.path.checkout())

  test_prefix = ['xvfb-run'] if api.platform.is_linux else []
  yield api.step('test', test_prefix+['grunt', 'test-buildbot'],
             cwd=api.path.checkout(), allow_subannotations=True)


def GenTests(api):
  yield 'basic', {
    'properties': api.properties_scheduled(
        repository='https://github.com/Polymer/polymer'),
  }
