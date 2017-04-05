# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from recipe_engine import recipe_test_api

DEPS = [
    'gitiles',
]

class ChromiteTestApi(recipe_test_api.RecipeTestApi):
  def seed_chromite_config(self, data):
    """Seeds step data for the Chromite configuration fetch.
    """
    return self.m.step.step_data('read chromite config',
        self.m.json.output(data))

  def add_chromite_config(self, config_name, build_type=None):
    d = {
        config_name: {
          'build_type': build_type,
        },
    }
    return self.seed_chromite_config(d)
