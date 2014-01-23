# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

ISOLATE_SERVER = 'https://isolateserver.appspot.com'

class IsolateApi(recipe_api.RecipeApi):
  """APIs for interacting with isolates."""

  def set_isolate_environment(self, config):
    """Modifies the passed Config (which should generally be api.chromium.c)
    to set up the appropriate GYP_DEFINES to upload isolates to the isolate
    server during the build. This must be called early in your recipe;
    definitely before the checkout and runhooks steps."""
    assert config.gyp_env.GYP_DEFINES['component'] != 'shared_library', (
      "isolates don't work with the component build yet; see crbug.com/333473")
    config.gyp_env.GYP_DEFINES['test_isolation_mode'] = 'hashtable'
    config.gyp_env.GYP_DEFINES['test_isolation_outdir'] = ISOLATE_SERVER

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
