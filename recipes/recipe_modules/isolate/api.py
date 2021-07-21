# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools
import sys

from recipe_engine import recipe_api


# Only surface up to these many isolate hashes via properties, to avoid
# overflowing the field for a build.
# This arbitrary number was selected to be the least surprising value that
# is likely to work for the purpose above.
_MAX_SWARM_HASHES_PROPERTY_LENGTH = 200


# Take revision from
# https://ci.chromium.org/p/infra-internal/g/infra-packagers/console
_LUCI_GO_REVISION = 'git_revision:9ee8b1d719c0d3c268e0e19282351ca78024af2d'


class IsolateApi(recipe_api.RecipeApi):
  """APIs for interacting with isolates."""

  def __init__(self, **kwargs):
    super(IsolateApi, self).__init__(**kwargs)
    # TODO(maruel): Delete this recipe and use upstream isolated instead.
    # https://crbug.com/944904
    # TODO(crbug.com/1143123): remove this.
    self._isolate_server = 'https://isolateserver.appspot.com'
    self._isolated_tests = {}

  @property
  def isolate_server(self):
    """URL of Isolate server to use, default is a production one."""
    return self._isolate_server

  @isolate_server.setter
  def isolate_server(self, value):
    """Changes URL of Isolate server to use."""
    self._isolate_server = value

  def check_swarm_hashes(self, targets):
    """Asserts that all the targets in the passed list are present as keys in
    the 'swarm_hashes' property.

    This is just an optional early check that all the isolated targets that are
    needed throughout the build are present. Without this step, the build would
    just fail later, on a 'trigger' step. But the main usefulness of this is
    that it automatically populates the 'swarm_hashes' property in testing
    context, so that it doesn't need to be manually specified through test_api.
    """
    with self.m.step.nest('check swarm_hashes'):
      if self._test_data.enabled:
        self._isolated_tests = {
          target: '[dummy hash for %s/1]' % target for target in targets}

      isolated_tests = self.isolated_tests
      missing = [t for t in targets if not isolated_tests.get(t)]
      if missing:
        raise self.m.step.InfraFailure(
          'Missing isolated target(s) %s in swarm_hashes' % ', '.join(missing))

  def isolate_tests(
      self,
      build_dir,
      targets,
      verbose=False,
      swarm_hashes_property_name='swarm_hashes',
      step_name=None,
      suffix='',
      # TODO(crbug.com/chrome-operations/49): remove this after
      # isolate server shutdown.
      use_cas=True,
      **kwargs):
    """Archives prepared tests in |build_dir| to isolate server.

    src/tools/mb/mb.py is invoked to produce *.isolated.gen.json files that
    describe how to archive tests.

    This step then uses *.isolated.gen.json files to actually performs the
    archival. By archiving all tests at once it is able to reduce the total
    amount of work. Tests share many common files, and such files are processed
    only once.

    Args:
        targets: List of targets to use.
        verbose (bool): Isolate command should be verbose in output.
        swarm_hashes_property_name (str): If set, assigns the dict
            {target name -> *.isolated file hash} to the named build
            property. If this needs to be run more than once per recipe run,
            make sure to pass different propery names for each invocation.
        suffix: suffix of isolate_tests step.
            e.g. ' (with patch)', ' (without patch)'.
        use_cas: whether upload files to RBE-CAS or not.
    """

    # No isolated tests found.
    if not targets:  # pragma: no cover
      return

    version = _LUCI_GO_REVISION
    if self._test_data.enabled:
      version = 'git_revision:dummy_version'
    exe = self.m.cipd.ensure_tool('infra/tools/luci/isolate/${platform}',
                                  version)

    # FIXME: Differentiate between bad *.isolate and upload errors.
    # Raise InfraFailure on upload errors.
    args = [
        exe,
        'batcharchive',
        '--dump-json',
        self.m.json.output(),
    ] + (['--verbose'] if verbose else [])

    if use_cas:
      args.extend(['-cas-instance', self.m.cas.instance])

      # TODO(b/187913980): this is for investigation of upload failures.
      args.extend(['-log-level', 'debug'])

      if ("chromium.isolate.use_new_lib" in
          self.m.buildbucket.build.input.experiments or
          self.m.platform.is_linux):
        # TODO(crbug.com/1225524): remove this after migration.
        args.extend(['-use-new-lib'])
    else:
      args.extend(['--isolate-server', self._isolate_server])

    args.extend([
        build_dir.join('%s.isolated.gen.json' % t)
        for t in sorted(set(targets))
    ])

    step_result = self.m.step(
        step_name or ('isolate tests%s' % suffix),
        args,
        step_test_data=lambda: self.test_api.output_json(
            targets, use_cas=use_cas),
        **kwargs)

    swarm_hashes = {}
    if step_result.json.output:
      for k, v in step_result.json.output.iteritems():
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
      self.set_isolated_tests(swarm_hashes)

    if not use_cas:
      step_result.presentation.properties['isolate_server'] = self._isolate_server

    if (swarm_hashes_property_name and
        len(swarm_hashes) <= _MAX_SWARM_HASHES_PROPERTY_LENGTH):
      step_result.presentation.properties[
          swarm_hashes_property_name] = swarm_hashes

    missing = sorted(t for t, h in self._isolated_tests.iteritems() if not h)
    if missing:
      step_result.presentation.logs['failed to isolate'] = (
          ['Failed to isolate following targets:'] + missing +
          ['', 'See logs for more information.'])
      for k in missing:
        self._isolated_tests.pop(k)

    return step_result

  def set_isolated_tests(self, swarm_hashes):
    """Allows recipes to set their own swarm_hashes when they are not already
    set as a build property.
    Args:
        swarm_hashes: Dict of target name -> isolated hash
    """
    assert isinstance(swarm_hashes, dict)

    self._isolated_tests = swarm_hashes

  @property
  def isolated_tests(self):
    """The dictionary of 'target name -> isolated hash' for this run.

    These come either from the incoming swarm_hashes build property,
    or from calling isolate_tests, above, at some point during the run.
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

  def run_isolated(self,
                   name,
                   isolated_input,
                   args=None,
                   pre_args=None,
                   **kwargs):
    """Runs an isolated test."""
    cmd = [
        '--verbose',
    ]

    if '/' in isolated_input:
      cmd.extend([
          '--cas-instance',
          self.m.cas.instance,
          '--cas-digest',
          isolated_input,
      ])
    else:
      # TODO(crbug.com/1143122): remove this after migration
      cmd.extend([
          '-I',
          self.isolate_server,
          '--isolated',
          isolated_input,
      ])

    if 'env' in kwargs and isinstance(kwargs['env'], dict):
      for k, v in sorted(kwargs.pop('env').iteritems()):
        cmd.extend(['--env', '%s=%s' % (k, v)])
    cmd.extend(pre_args or [])
    if args:
      cmd.append('--')
      cmd.extend(args)
    self.m.build.python(name, self._run_isolated_path, cmd, **kwargs)

  def archive_differences(self, first_dir, second_dir, values):
    """Archive different files of 2 builds."""
    GS_BUCKET = 'chrome-determinism'
    TARBALL_NAME = 'deterministic_build_diffs.tgz'

    # compare_build_artifacts.py --json-output produces a json object that
    # looks like
    # {
    #   'expected_diffs': [ ...filenames... ],
    #   'unexpected_diffs': [ ...filenames... ],
    #   'deps_diff': [ ...filenames... ],
    # }
    # Join all three filename lists in the values into a single list.
    diffs = list(itertools.chain.from_iterable(values.itervalues()))
    if not diffs:  # pragma: no cover
      return

    # args.gn won't be different, but it's useful to have it in the archive:
    # It's tiny, contains useful information, and compare_build_artifacts.py
    # reads it to check if this is a component build. So having this in the
    # archive makes running compare_build_artifacts.py locally easier.
    diffs.append('args.gn')

    # TODO(thakis): Temporary, for debugging https://crbug.com/1031993
    # Consider comparing all generated files?
    diffs.append('gen/third_party/blink/renderer/core/style/computed_style_base.h')

    t = self.m.path.mkdtemp('deterministic_build')
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
        '--ninja-path', self.m.depot_tools.ninja_path,
        '--use-isolate-files'
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
