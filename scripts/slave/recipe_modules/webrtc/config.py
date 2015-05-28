# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import Static


def BaseConfig(PERF_ID=None, PERF_CONFIG=None, TEST_SUITE=None, **_kwargs):
  return ConfigGroup(
    PERF_ID = Static(PERF_ID),
    PERF_CONFIG = Static(PERF_CONFIG),
    TEST_SUITE = Static(TEST_SUITE),
  )

VAR_TEST_MAP = {
  'PERF_ID': (None, 'perf-id'),
  'PERF_CONFIG': (None, '{}', '{"a_default_rev": "r_webrtc_rev"}'),
}

def TEST_NAME_FORMAT(kwargs):
  return 'webrtc'  # pragma: no cover

config_ctx = config_item_context(BaseConfig, VAR_TEST_MAP, TEST_NAME_FORMAT)

# Only exists to be able to set the PERF_ID and PERF_CONFIG configurations.
@config_ctx()
def webrtc(c):
  pass
