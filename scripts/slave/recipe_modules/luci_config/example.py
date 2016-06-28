# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property

DEPS = [
  'luci_config',
  'recipe_engine/properties',
  'recipe_engine/step'
]

PROPERTIES = {
  'auth_token': Property(default=None),
  'protobuf': Property(default=None),
}

def RunSteps(api, auth_token, protobuf):
  if auth_token:
    api.luci_config.c.auth_token = auth_token

  if protobuf:
    result = api.luci_config.parse_textproto(api.luci_config.get_project_config(
        'build', 'recipes.cfg')['content'].split('\n'))
    api.step('checkit', ['echo', str(result)])
    return

  api.luci_config.get_project_config('build', 'recipes.cfg')
  api.luci_config.get_project_metadata('build')



def GenTests(api):
  yield (
      api.test('basic') +
      api.luci_config.get_projects(['build']) +
      api.luci_config.get_project_config('build', 'recipes.cfg', 'testcontent')
  )

  yield (
      api.test('auth_token') +
      api.properties(auth_token='ya2930948320948203480=') +
      api.luci_config.get_projects(['build']) +
      api.luci_config.get_project_config('build', 'recipes.cfg', 'testcontent')
  )

  protobuf_lines = """
    foo: 1
    bar: "hi"
    baz {
      the_thing: "hi"
    }
  """

  yield (
      api.test('protobuf') +
      api.luci_config.get_project_config(
          'build', 'recipes.cfg', protobuf_lines) +
      api.properties(protobuf=True)
  )
