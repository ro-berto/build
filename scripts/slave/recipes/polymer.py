# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

def GetSteps(api):
  tmp_path = api.checkout_path('.tmp')
  test_prefix = ['xvfb-run'] if api.IsLinux else []
  return (
    api.git_checkout(api.properties['repository'] + '.git', recursive=True),
    api.step('mktmp', ['mkdir', tmp_path]),
    api.step('update-install', ['npm', 'install', '--tmp', tmp_path],
             cwd=api.checkout_path()),
    api.step('test', test_prefix+['grunt', 'test-buildbot'],
             cwd=api.checkout_path(), allow_subannotations=True)
  )
