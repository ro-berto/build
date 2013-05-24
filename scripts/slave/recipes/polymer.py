# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

def GetSteps(api, _factory_properties, build_properties):
  steps = api.Steps(build_properties)
  tmp_path = api.checkout_path('.tmp')
  test_prefix = ['xvfb-run'] if api.IsLinux() else []
  return (
    steps.git_checkout(build_properties['repository'] + '.git', recursive=True),
    steps.step('mktmp', ['mkdir', tmp_path]),
    steps.step('update-install', ['npm', 'install', '--tmp', tmp_path],
               cwd=api.checkout_path()),
    steps.step('test', test_prefix+['grunt', 'test-buildbot'],
               cwd=api.checkout_path(), allow_subannotations=True)
  )
