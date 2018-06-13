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
}


def RunSteps(api, auth_token):
  if auth_token:
    api.luci_config.c.auth_token = auth_token

  api.luci_config.get_ref_config('chromium', 'refs/heads/master', 'cq.cfg')
  api.luci_config.get_project_metadata('build')


def GenTests(api):
  yield (
      api.test('basic') +
      api.luci_config.get_projects(['build']) +
      api.luci_config.get_ref_config(
        'chromium', 'refs/heads/master', 'cq.cfg',
        'cq.cfg content',
        found_at_path='infra/config/branch/')
  )

  yield (
      api.test('auth_token') +
      api.properties(auth_token='ya2930948320948203480=') +
      api.luci_config.get_projects(['build']) +
      api.luci_config.get_ref_config(
        'chromium', 'refs/heads/master', 'cq.cfg',
        'cq.cfg content',
        found_at_path='infra/config/branch/')
  )
