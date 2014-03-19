# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

ISOLATE_SERVER = 'https://isolateserver.appspot.com'

class IsolateApi(recipe_api.RecipeApi):
  """APIs for interacting with isolates."""

  def __init__(self, **kwargs):
    super(IsolateApi, self).__init__(**kwargs)
    self._isolated_tests = {}
    self._using_separate_swarming_client = False

  @staticmethod
  def set_isolate_environment(config):
    """Modifies the config to include isolate related GYP_DEFINES.

    Modifies the passed Config (which should generally be api.chromium.c)
    to set up the appropriate GYP_DEFINES to upload isolates to the isolate
    server during the build. This must be called early in your recipe;
    definitely before the checkout and runhooks steps.
    """
    assert config.gyp_env.GYP_DEFINES['component'] != 'shared_library', (
      "isolates don't work with the component build yet; see crbug.com/333473")
    config.gyp_env.GYP_DEFINES['test_isolation_mode'] = 'archive'
    config.gyp_env.GYP_DEFINES['test_isolation_outdir'] = ISOLATE_SERVER

  def checkout_swarming_client(self):
    """Returns a step to checkout swarming client into a separate directory.

    Ordinarily swarming client checked out via DEPS into
    src/tools/swarming_client. Configures this recipe module to use this
    separate checkout.

    This requires the build property 'parent_got_swarming_client_revision'
    to be present, and raises an exception otherwise. Fail-fast behavior is
    used because if machines silently fell back to checking out the entire
    workspace, that would cause dramatic increases in cycle time if a
    misconfiguration were made and it were no longer possible for the bot
    to check out swarming_client separately.
    """
    # If the following line throws an exception, it either means the
    # bot is misconfigured, or, if you're testing locally, that you
    # need to pass in some recent legal revision for this property.
    swarming_client_rev = self.m.properties[
      'parent_got_swarming_client_revision']
    self._using_separate_swarming_client = True
    return self.m.git.checkout(
      'https://chromium.googlesource.com/external/swarming.client.git',
      swarming_client_rev)

  def find_isolated_tests(self, build_dir, targets=None):
    """Returns a step which finds all *.isolated files in a build directory.

    Assigns the dict {target name -> *.isolated file hash} to the swarm_hashes
    build property. This implies this step can currently only be run once
    per recipe.

    If |targets| is None, the step will use all *.isolated files it finds.
    Otherwise, it will verify that all |targets| are found and will use only
    them.
    """
    def followup_fn(step_result):
      self._isolated_tests = step_result.json.output
      if targets is not None and step_result.presentation.status != 'FAILURE':
        found = set(step_result.json.output)
        expected = set(targets)
        if found >= expected:
          # Found some extra? Issue warning.
          if found != expected:
            step_result.presentation.status = 'WARNING'
            step_result.presentation.logs['unexpected.isolates'] = (
              ['Found unexpected *.isolated files:'] + list(found - expected))
          # Limit result only to |expected|.
          self._isolated_tests = {
            target: step_result.json.output[target] for target in expected
          }
        else:
          # Some expected targets are missing? Fail the step.
          step_result.presentation.status = 'FAILURE'
          step_result.presentation.logs['missing.isolates'] = (
            ['Failed to find *.isolated files:'] + list(expected - found))
      step_result.presentation.properties['swarm_hashes'] = self._isolated_tests
    return self.m.python(
      'find isolated tests',
      self.resource('find_isolated_tests.py'),
      ['--build-dir', build_dir,
       '--output-json', self.m.json.output(),
      ],
      followup_fn=followup_fn,
      step_test_data=lambda: (self.test_api.output_json(targets)))

  @property
  def isolated_tests(self):
    """The dictionary of 'target name -> isolated hash' for this run.

    These come either from the incoming swarm_hashes build property,
    or from calling find_isolated_tests, above, at some point during the run.
    """
    return self.m.properties.get('swarm_hashes', self._isolated_tests)

  @property
  def _run_isolated_path(self):
    """Returns the path to run_isolated.py."""
    if self._using_separate_swarming_client:
      return self.m.path['checkout'].join('run_isolated.py')
    else:
      return self.m.path['checkout'].join('tools', 'swarming_client',
                                          'run_isolated.py')

  def runtest_args_list(self, test, args=None):
    """Array of arguments for running the given test via run_isolated.py.

    The test should be already uploaded to the isolated server. The method
    expects to find |test| as a key in the isolated_tests dictionary.
    """
    isolate_hash = self.isolated_tests[test]

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
    """Runs a test which has previously been isolated to the server.

    Uses runtest_args_list, above, and delegates to api.chromium.runtest.
    """
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
    """Runs a Telemetry test which has previously isolated to the server.

    Uses runtest_args_list, above, and delegates to
    api.chromium.run_telemetry_test.
    """
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
