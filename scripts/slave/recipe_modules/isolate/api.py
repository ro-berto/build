# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class IsolateApi(recipe_api.RecipeApi):
  """APIs for interacting with isolates."""

  @recipe_api.inject_test_data
  def manifest_to_hash(self, targets):
    """Returns a step which runs manifest_to_hash.py against the given array
    of targets. Assigns the result to the swarm_hashes factory property.
    (This implies this step can currently only be run once per recipe.)"""
    def followup_fn(step_result):
      step_result.presentation.properties['swarm_hashes'] = (
        step_result.json.output)
    return self.m.python(
      'manifest_to_hash',
      self.m.path.build('scripts', 'slave', 'swarming', 'manifest_to_hash.py'),
      ['--target', self.m.chromium.c.build_config_fs,
       '--output-json', self.m.json.output(),
      ] + targets,
      followup_fn=followup_fn)
