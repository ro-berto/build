# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

ISOLATE_SERVER = 'https://isolateserver.appspot.com'

class IsolateApi(recipe_api.RecipeApi):
  """APIs for interacting with isolates."""

  def __init__(self, **kwargs):
    super(IsolateApi, self).__init__(**kwargs)
    self._manifest_hashes = {}

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
      self._manifest_hashes = step_result.json.output
      step_result.presentation.properties['swarm_hashes'] = (
        self._manifest_hashes)
    return self.m.python(
      'manifest_to_hash',
      self.m.path.build('scripts', 'slave', 'swarming', 'manifest_to_hash.py'),
      ['--target', self.m.chromium.c.build_config_fs,
       '--output-json', self.m.json.output(),
      ] + targets,
      followup_fn=followup_fn)

  @property
  def manifest_hashes(self):
    """Returns the dictionary of hashes that have been produced during this
    run. These come either from the incoming swarm_hashes factory property,
    or from calling manifest_to_hash, above, at some point during the
    run."""
    return self.m.properties.get('swarm_hashes', self._manifest_hashes)

  def run_isolate_test(self, test, args=None, name=None, **runtest_kwargs):
    """Runs a test which has previously been uploaded to the isolate server.
    Expects to find the test 'test' as a key in the manifest_hashes
    dictionary. Delegates to api.chromium.runtests; see that method for a
    more complete description of the supported arguments."""
    isolate_hash = self.manifest_hashes[test]

    name = name or test

    # TODO(kbr): will need this later. Comment out for now for code coverage.
    # The step name must end in 'test' or 'tests' in order for the results to
    # automatically show up on the flakiness dashboard.
    # if not (name.endswith('test') or name.endswith('tests')):
    #   name = '%s_tests' % name

    if not args:
      args = []

    full_args = [
      '-H',
      isolate_hash,
      '-I',
      ISOLATE_SERVER
    ] + args

    return self.m.chromium.runtests(
      self.m.path.checkout('tools', 'swarming_client', 'run_isolated.py'),
      args=full_args,
      name=name,
      **runtest_kwargs)
