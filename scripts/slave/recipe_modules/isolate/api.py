# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools
import sys
from recipe_engine import recipe_api


class IsolateApi(recipe_api.RecipeApi):
  """APIs for interacting with isolates."""

  def __init__(self, **kwargs):
    super(IsolateApi, self).__init__(**kwargs)
    self._isolate_server = 'https://isolateserver.appspot.com'
    self._isolated_tests = {}
    self._service_account_json = None

  @property
  def isolate_server(self):
    """URL of Isolate server to use, default is a production one."""
    return self._isolate_server

  @isolate_server.setter
  def isolate_server(self, value):
    """Changes URL of Isolate server to use."""
    self._isolate_server = value

  @property
  def service_account_json(self):
    """Service account json to use."""
    return self._service_account_json

  @service_account_json.setter
  def service_account_json(self, value):
    """Service account json to use."""
    self._service_account_json = value

  def clean_isolated_files(self, build_dir):
    """Cleans out all *.isolated files from the build directory in
    preparation for the compile. Needed in order to ensure isolates
    are rebuilt properly because their dependencies are currently not
    completely described to gyp.
    """
    self.m.python(
      'clean isolated files',
      self.resource('find_isolated_tests.py'),
      [
        '--build-dir', build_dir,
        '--clean-isolated-files'
      ])

  def find_isolated_tests(self, build_dir, targets=None, **kwargs):
    """Returns a step which finds all *.isolated files in a build directory.

    Useful only with 'archive' isolation mode.
    In 'prepare' mode use 'isolate_tests' instead.

    Assigns the dict {target name -> *.isolated file hash} to the swarm_hashes
    build property. This implies this step can currently only be run once
    per recipe.

    If |targets| is None, the step will use all *.isolated files it finds.
    Otherwise, it will verify that all |targets| are found and will use only
    them. If some expected targets are missing, will abort the build.
    """
    step_result = self.m.python(
      'find isolated tests',
      self.resource('find_isolated_tests.py'),
      [
        '--build-dir', build_dir,
        '--output-json', self.m.json.output(),
      ],
      step_test_data=lambda: (self.test_api.output_json(targets)),
      **kwargs)

    assert isinstance(step_result.json.output, dict)
    self._isolated_tests = step_result.json.output
    if targets is not None and (
            step_result.presentation.status != self.m.step.FAILURE):
      found = set(step_result.json.output)
      expected = set(targets)
      if found >= expected:  # pragma: no cover
        # Limit result only to |expected|.
        self._isolated_tests = {
          target: step_result.json.output[target] for target in expected
        }
      else:
        # Some expected targets are missing? Fail the step.
        step_result.presentation.status = self.m.step.FAILURE
        step_result.presentation.logs['missing.isolates'] = (
            ['Failed to find *.isolated files:'] + list(expected - found))
    step_result.presentation.properties['swarm_hashes'] = self._isolated_tests
    # No isolated files found? That looks suspicious, emit warning.
    if (not self._isolated_tests and
        step_result.presentation.status != self.m.step.FAILURE):
      step_result.presentation.status = self.m.step.WARNING

  def isolate_tests(self, build_dir, targets=None, verbose=False,
                    set_swarm_hashes=True, use_exparchive=False,
                    **kwargs):
    """Archives prepared tests in |build_dir| to isolate server.

    src/tools/mb/mb.py is invoked to produce *.isolated.gen.json files that
    describe how to archive tests.

    This step then uses *.isolated.gen.json files to actually performs the
    archival. By archiving all tests at once it is able to reduce the total
    amount of work. Tests share many common files, and such files are processed
    only once.

    Args:
        targets: List of targets to use instead of finding .isolated.gen.json
            files.
        verbose (bool): Isolate command should be verbose in output.
        set_swarm_hashes (bool): On true, assigns the dict
            {target name -> *.isolated file hash} to the swarm_hashes build
            property (also accessible as 'isolated_tests' property). This
            implies this step can currently only be run once per recipe.
        use_exparchive (bool, int, float, long): Provide a boolean to
            enable/disable exparchive, or provide a number (between 0 and 100)
            to have n% of builds run with exparchive. IGNORED (deprecated).
    """
    # TODO(tansell): Make all steps in this function nested under one overall
    # 'isolate tests' master step.


    # TODO(vadimsh): Always require |targets| to be passed explicitly. Currently
    # chromium_trybot, blink_trybot and swarming/canary recipes rely on targets
    # autodiscovery. The code path in chromium_trybot that needs it is being
    # deprecated in favor of to *_ng builders, that pass targets explicitly.
    if targets is None:
      # mb generates <target>.isolated.gen.json files.
      paths = self.m.file.glob_paths(
          'find isolated targets',
          build_dir, '*.isolated.gen.json',
          test_data=['dummy_target_%d.isolated.gen.json' % i for i in (1, 2)])
      targets = []
      for p in paths:
        name = self.m.path.basename(p)
        assert name.endswith('.isolated.gen.json'), name
        targets.append(name[:-len('.isolated.gen.json')])

    # No isolated tests found.
    if not targets:  # pragma: no cover
      return

    batch_targets = []
    archive_targets = []
    for t in targets:
      if t.endswith('_exparchive'):
        archive_targets.append(t)
      else:
        batch_targets.append(t)

    isolate_steps = []
    try:
      args = [
          self.m.swarming_client.path,
          'archive',
          '--dump-json', self.m.json.output(),
          '--isolate-server', self._isolate_server,
          '--eventlog-endpoint', 'prod',
      ] + (['--verbose'] if verbose else [])

      if self.service_account_json:
        args.extend(['--service-account-json', self.service_account_json])

      for target in archive_targets:
        isolate_steps.append(
            self.m.python(
                'isolate %s' % target,
                self.resource('isolate.py'),
                args + [
                    '--isolate', build_dir.join('%s.isolate' % target),
                    '--isolated', build_dir.join('%s.isolated' % target),
                ],
                step_test_data=lambda: self.test_api.output_json([target]),
                **kwargs))

      if batch_targets:
        # TODO(vadimsh): Differentiate between bad *.isolate and upload errors.
        # Raise InfraFailure on upload errors.
        args = [
            self.m.swarming_client.path,
            'batcharchive',
            '--dump-json', self.m.json.output(),
            '--isolate-server', self._isolate_server,
            '--eventlog-endpoint', 'prod',
        ] + (['--verbose'] if verbose else [])

        if self.service_account_json:
          args.extend(['--service-account-json', self.service_account_json])

        args.extend([
            build_dir.join('%s.isolated.gen.json' % t) for t in batch_targets])

        isolate_steps.append(
            self.m.python(
                'isolate tests', self.resource('isolate.py'), args,
                step_test_data=lambda: self.test_api.output_json(batch_targets),
                **kwargs))

      # TODO(tansell): Change this to return a dummy "isolate results" or the
      # top level master step.
      return isolate_steps[-1]
    finally:
      step_result = self.m.step.active_result
      swarm_hashes = {}
      for step in isolate_steps:
        if not step.json.output:
          continue  # pragma: no cover

        for k, v in step.json.output.iteritems():
          # TODO(tansell): Raise an error here when it can't clobber an
          # existing error. This code is currently inside a finally block,
          # meaning it could be executed when an existing error is occurring.
          # See https://chromium-review.googlesource.com/c/437024/
          #assert k not in swarm_hashes or swarm_hashes[k] == v, (
          #    "Duplicate hash for target %s was found at step %s."
          #    "Existing hash: %s, New hash: %s") % (
          #        k, step, swarm_hashes[k], v)
          swarm_hashes[k] = v

      if swarm_hashes:
        self._isolated_tests = swarm_hashes

      if set_swarm_hashes:
        step_result.presentation.properties['swarm_hashes'] = swarm_hashes

      missing = sorted(
          t for t, h in self._isolated_tests.iteritems() if not h)
      if missing:
        step_result.presentation.logs['failed to isolate'] = (
            ['Failed to isolate following targets:'] +
            missing +
            ['', 'See logs for more information.']
        )
        for k in missing:
          self._isolated_tests.pop(k)

  @property
  def isolated_tests(self):
    """The dictionary of 'target name -> isolated hash' for this run.

    These come either from the incoming swarm_hashes build property,
    or from calling find_isolated_tests, above, at some point during the run.
    """
    hashes = self.m.properties.get('swarm_hashes', self._isolated_tests)
    # Be robust in the case where swarm_hashes is an empty string
    # instead of an empty dictionary, or similar.
    if not hashes:
      return {} # pragma: no covergae
    return {
      k.encode('ascii'): v.encode('ascii')
      for k, v in hashes.iteritems()
    }

  @property
  def _run_isolated_path(self):
    """Returns the path to run_isolated.py."""
    return self.m.swarming_client.path.join('run_isolated.py')

  def run_isolated(self, name, isolate_hash, args=None, **kwargs):
    """Runs an isolated test."""
    cmd = [
        '--isolated', isolate_hash,
        '-I', self.isolate_server,
        '--verbose',
    ]
    if args:
      cmd.append('--')
      cmd.extend(args)
    self.m.python(name, self._run_isolated_path, cmd, **kwargs)

  def remove_build_metadata(self):
    """Removes the build metadata embedded in the build artifacts."""
    args = [
        '--build-dir', self.m.chromium.output_dir,
    ]
    # Turn the failures during this step into warnings, it's a best effort step
    # that shouldn't break the build for now.
    try:
      with self.m.context(cwd=self.m.path['start_dir']):
        self.m.python('remove_build_metadata',
                      self.m.path.join(self.m.path['checkout'],
                                       'tools',
                                       'determinism',
                                       'remove_build_metadata.py'),
                      args=args)
    except self.m.step.StepFailure:
      step_result = self.m.step.active_result
      step_result.presentation.status = self.m.step.WARNING

  def archive_differences(self, first_dir, second_dir, values):
    """Archive different files of 2 builds."""
    GS_BUCKET = 'chrome-determinism'
    TARBALL_NAME = 'deterministic_build_diffs.tgz'

    diffs = list(itertools.chain.from_iterable(values.itervalues()))
    if not diffs:  # pragma: no cover
      return

    with self.m.tempfile.temp_dir('deterministic_build') as t:
      output = self.m.path.join(t, TARBALL_NAME)
      self.m.python('create tarball',
                    script=self.m.path.join(self.m.path['checkout'],
                                            'tools',
                                            'determinism',
                                            'create_diffs_tarball.py'),
                    args=[
                        '--first-build-dir', first_dir,
                        '--second-build-dir', second_dir,
                        '--json-input', self.m.json.input(diffs),
                        '--output', output,
                    ])
      self.m.gsutil.upload(output,
                           GS_BUCKET,
                           self.m.path.join(
                               self.m.properties['buildername'],
                               self.m.properties['buildnumber'],
                               TARBALL_NAME))

  def compare_build_artifacts(self, first_dir, second_dir):
    """Compare the artifacts from 2 builds."""
    args = [
        '--first-build-dir', first_dir,
        '--second-build-dir', second_dir,
        '--target-platform', self.m.chromium.c.TARGET_PLATFORM,
        '--json-output', self.m.json.output(),
    ]
    try:
      with self.m.context(cwd=self.m.path['start_dir']):
        step_result = self.m.python(
            'compare_build_artifacts',
            self.m.path.join(self.m.path['checkout'],
                             'tools',
                             'determinism',
                             'compare_build_artifacts.py'),
            args=args,
            step_test_data=(lambda: self.m.json.test_api.output({
                'expected_diffs': ['flatc'],
                'unexpected_diffs': ['base_unittest'],
            })))
      self.archive_differences(first_dir, second_dir, step_result.json.output)
    except self.m.step.StepFailure as e:
      step_result = self.m.step.active_result
      self.archive_differences(first_dir, second_dir, step_result.json.output)
      raise e
