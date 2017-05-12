# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


DEPS = [
  'recipe_engine/context',
  'recipe_engine/step',
]


def RunSteps(api):
  with api.context(
      env={'mood': 'excellent', 'climate': 'sunny'},
      name_prefix='grandparent'):
    with api.context(env={'climate': 'rainy'}, name_prefix='mom'):
      api.step("child", ["echo", "billy"])
    with api.context(env={'climate': 'cloudy'}, name_prefix='dad'):
      api.step("child", ["echo", "sam"])
    api.step("aunt", ["echo", "testb"])


def GenTests(api):
  yield api.test('basic')
