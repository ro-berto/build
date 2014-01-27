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
    config.gyp_env.GYP_DEFINES['test_isolation_mode'] = 'archive'
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
    run. These come either from the incoming swarm_hashes build property,
    or from calling manifest_to_hash, above, at some point during the run."""
    return self.m.properties.get('swarm_hashes', self._manifest_hashes)

  @property
  def run_isolated_path(self):
    """Returns the path to run_isolated.py."""
    return self.m.path.checkout('tools', 'swarming_client', 'run_isolated.py')

  def runtest_args_list(self, test, args=None):
    """Returns the array of arguments for running the given test which has
    been previously uploaded to the isolate server. Expects to find the
    test 'test' as a key in the manifest_hashes dictionary."""
    isolate_hash = self.manifest_hashes[test]

    full_args = [
      '-H',
      isolate_hash,
      '-I',
      ISOLATE_SERVER
    ]
    if args:
      full_args.append('--')
      full_args.extend(args)
    return full_args

  def runtest(self, test, args=None, name=None, **runtest_kwargs):
    """Runs a test which has previously been uploaded to the isolate server.
    Uses runtest_args_list, above, and delegates to api.chromium.runtest."""
    return self.m.chromium.runtest(
      self.run_isolated_path,
      args=self.runtest_args_list(test, args),
      # We must use the name of the test as the name in order to avoid
      # duplicate steps called "run_isolated".
      name=name or test,
      **runtest_kwargs)

  def run_telemetry_test(self, isolate_name, test,
                         args=None, name=None, **runtest_kwargs):
    """Runs a Telemetry test which has previously been uploaded to the
    isolate server. Uses runtest_args_list, above, and delegates to
    api.chromium.run_telemetry_test."""
    return self.m.chromium.run_telemetry_test(
      self.run_isolated_path,
      test,
      # When running the Telemetry test via an isolate we need to tell
      # run_isolated.py the hash and isolate server first, and then give
      # the isolate the test name and other arguments separately.
      prefix_args=self.runtest_args_list(isolate_name) + ['--'],
      args=args,
      name=name,
      **runtest_kwargs)
