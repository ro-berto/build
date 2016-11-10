# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os

from recipe_engine import recipe_api
from . import perf_test

BUCKET = 'chrome-perf'
RESULTS_GS_DIR = 'bisect-results'


class BisectTesterApi(recipe_api.RecipeApi):
  """A module for the bisect tester bot using the chromium recipe."""

  def __init__(self, **kwargs):
    super(BisectTesterApi, self).__init__(**kwargs)
    self._device_to_test = None

  @property
  def device_to_test(self):
    return self._device_to_test

  @device_to_test.setter
  def device_to_test(self, value):
    self._device_to_test = value

  def load_config_from_dict(self, bisect_config):
    """Copies the required configuration keys to a new dict."""
    return {
        'command': bisect_config['command'],
        'metric': bisect_config.get('metric'),
        'repeat_count': int(bisect_config.get('repeat_count', 20)),
        # The default is to NOT timeout, hence 0.
        'max_time_minutes': float(bisect_config.get('max_time_minutes', 0)),
        'test_type': bisect_config.get('test_type', 'perf')
    }

  def run_test(self, test_config, **kwargs):
    """Exposes perf tests implementation."""
    return perf_test.run_perf_test(self, test_config, **kwargs)
