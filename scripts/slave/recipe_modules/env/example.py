# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'env',
  'step',
]

def GenSteps(api):
  yield api.step('step 0', ['command', '0'])

  if api.env.get('ENV_VAR_1'):
    yield api.step('step 1', ['command', '1'])

  if api.env.get('ENV_VAR_2'):
    yield api.step('step 2', ['command', '2'])

def GenTests(api):
  yield (
    api.test('basic') 
  )

  yield (
    api.test('env_var_1') +
    api.env(ENV_VAR_1=True)
  )

  yield (
    api.test('env_var_2') +
    api.env(ENV_VAR_2=True)
  )

  yield (
    api.test('env_var_1_and_2') +
    api.env(ENV_VAR_1=True, ENV_VAR_2=True)
  )
