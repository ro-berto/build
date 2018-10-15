# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import config_item_context, ConfigGroup, Single

def BaseConfig(**_kwargs):
  return ConfigGroup(
      test_results_server = Single(basestring))


config_ctx = config_item_context(BaseConfig)


@config_ctx(is_root=True)
def BASE(_):
  pass

@config_ctx()
def no_server(c):
  c.test_results_server = None

@config_ctx()
def public_server(c):
  c.test_results_server = 'test-results.appspot.com'

@config_ctx()
def staging_server(c):
  c.test_results_server = 'test-results-test.appspot.com'
