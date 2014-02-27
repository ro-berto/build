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
    self._using_separate_swarming_client = False

  @staticmethod
  def set_isolate_environment(config):
    """Modifies the passed Config (which should generally be api.chromium.c)
    to set up the appropriate GYP_DEFINES to upload isolates to the isolate
    server during the build. This must be called early in your recipe;
    definitely before the checkout and runhooks steps."""
    assert config.gyp_env.GYP_DEFINES['component'] != 'shared_library', (
      "isolates don't work with the component build yet; see crbug.com/333473")
    config.gyp_env.GYP_DEFINES['test_isolation_mode'] = 'archive'
    config.gyp_env.GYP_DEFINES['test_isolation_outdir'] = ISOLATE_SERVER

  def checkout_swarming_client(self):
    """Returns a step which checks out the swarming_client tools into a
    separate directory from the Chromium checkout. Ordinarily this is
    checked out via DEPS into src/tools/swarming_client. Configures this
    recipe module to use this separate checkout.

    This requires the build property 'parent_got_swarming_client_revision'
    to be present, and raises an exception otherwise. Fail-fast behavior is
    used because if machines silently fell back to checking out the entire
    workspace, that would cause dramatic increases in cycle time if a
    misconfiguration were made and it were no longer possible for the bot
    to check out swarming_client separately."""
    # If the following line throws an exception, it either means the
    # bot is misconfigured, or, if you're testing locally, that you
    # need to pass in some recent legal revision for this property.
    swarming_client_rev = self.m.properties[
      'parent_got_swarming_client_revision']
    self._using_separate_swarming_client = True
    return self.m.git.checkout(
      'https://chromium.googlesource.com/external/swarming.client.git',
      swarming_client_rev)

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
      followup_fn=followup_fn,
      step_test_data=lambda: (self.test_api.output_json(targets)))

  @property
  def manifest_hashes(self):
    """Returns the dictionary of hashes that have been produced during this
    run. These come either from the incoming swarm_hashes build property,
    or from calling manifest_to_hash, above, at some point during the run."""
    return self.m.properties.get('swarm_hashes', self._manifest_hashes)

  @property
  def _run_isolated_path(self):
    """Returns the path to run_isolated.py."""
    if self._using_separate_swarming_client:
      return self.m.path.checkout('run_isolated.py')
    else:
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

  def runtest(self, test, revision, webkit_revision, args=None, name=None,
              master_class_name=None, **runtest_kwargs):
    """Runs a test which has previously been uploaded to the isolate server.
    Uses runtest_args_list, above, and delegates to api.chromium.runtest."""
    return self.m.chromium.runtest(
      self._run_isolated_path,
      args=self.runtest_args_list(test, args),
      # We must use the name of the test as the name in order to avoid
      # duplicate steps called "run_isolated".
      name=name or test,
      revision=revision,
      webkit_revision=webkit_revision,
      master_class_name=master_class_name,
      **runtest_kwargs)

  def run_telemetry_test(self, isolate_name, test,
                         revision, webkit_revision,
                         args=None, name=None, master_class_name=None,
                         **runtest_kwargs):
    """Runs a Telemetry test which has previously been uploaded to the
    isolate server. Uses runtest_args_list, above, and delegates to
    api.chromium.run_telemetry_test."""
    return self.m.chromium.run_telemetry_test(
      self._run_isolated_path,
      test,
      # When running the Telemetry test via an isolate we need to tell
      # run_isolated.py the hash and isolate server first, and then give
      # the isolate the test name and other arguments separately.
      prefix_args=self.runtest_args_list(isolate_name) + ['--'],
      args=args,
      name=name,
      revision=revision,
      webkit_revision=webkit_revision,
      master_class_name=master_class_name,
      **runtest_kwargs)
