# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from copy import deepcopy
from recipe_engine import recipe_test_api

class iOSTestApi(recipe_test_api.RecipeTestApi):
  @recipe_test_api.mod_test_data
  @staticmethod
  def build_config(config):
    return deepcopy(config)

  def make_test_build_config(self, config):
    return self.build_config(config)

  @recipe_test_api.mod_test_data
  @staticmethod
  def parent_build_config(config):
    return deepcopy(config)

  def make_test_build_config_for_parent(self, config):
    return self.parent_build_config(config)

  @recipe_test_api.mod_test_data
  @staticmethod
  def child_build_configs(configs):
    return deepcopy(configs)

  def make_test_build_configs_for_children(self, configs):
    return self.child_build_configs(configs)

  def generate_test_results_placeholder(
      self, failure=False, swarming_number=10000):
    summary_contents = {
      'logs': {
        'passed tests': ['PASSED_TEST'],
      },
      'step_text': 'dummy step text'
    }
    if failure:
      summary_contents['logs']['failed tests'] = ['FAILED_TEST']

    summary_path = str(swarming_number) + '/summary.json'
    return self.m.raw_io.output_dir(
        {summary_path: json.dumps(summary_contents)})
