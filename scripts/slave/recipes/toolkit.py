# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

def GetSteps(api, _factory_properties, build_properties):
  steps = api.Steps(build_properties)
  return (
    steps.git_checkout(build_properties['repository'] + '.git', recursive=True),
    steps.generator_script(api.checkout_path('buildbot', 'gen_steps.py'))
  )
