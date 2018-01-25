# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import ast
import contextlib
import datetime
import difflib
import itertools
import random
import re
import urllib

from builders import TestStepConfig, iter_builder_set
from recipe_engine.types import freeze
from recipe_engine import recipe_api
from . import bisection
from . import builders
from . import testing


CBE_URL = 'http://chrome-build-extract.appspot.com'
V8_URL = 'https://chromium.googlesource.com/v8/v8'

COMMIT_TEMPLATE = '%s/+/%%s' % V8_URL

# Regular expressions for v8 branch names.
RELEASE_BRANCH_RE = re.compile(r'^\d+\.\d+$')

# With more than 23 letters, labels are to big for buildbot's popup boxes.
MAX_LABEL_SIZE = 23

# Make sure that a step is not flooded with log lines.
MAX_FAILURE_LOGS = 10

# Factor by which the considered failure for bisection must be faster than the
# ongoing build's total.
BISECT_DURATION_FACTOR = 5

MIPS_TOOLCHAIN = ('Codescape.GNU.Tools.Package.2015.01-7.for.MIPS.MTI.Linux'
                  '.CentOS-5.x86_64.tar.gz')
MIPS_DIR = 'mips-mti-linux-gnu/2015.01-7'

TEST_RUNNER_PARSER = argparse.ArgumentParser()
TEST_RUNNER_PARSER.add_argument('--extra-flags')

VERSION_LINE_RE = r'^#define %s\s+(\d*)$'
VERSION_LINE_REPLACEMENT = '#define %s %s'
V8_MAJOR = 'V8_MAJOR_VERSION'
V8_MINOR = 'V8_MINOR_VERSION'
V8_BUILD = 'V8_BUILD_NUMBER'
V8_PATCH = 'V8_PATCH_LEVEL'

BBUCKET_SERVICE_ACCOUNT = 'v8-bot'


class V8Version(object):
  """A v8 version as used for tagging (with patch level), e.g. '3.4.5.1'."""

  def __init__(self, major, minor, build, patch):
    self.major = major
    self.minor = minor
    self.build = build
    self.patch = patch

  def __eq__(self, other):
    return (self.major == other.major and
            self.minor == other.minor and
            self.build == other.build and
            self.patch == other.patch)

  def __str__(self):
    patch_str = '.%s' % self.patch if self.patch and self.patch != '0' else ''
    return '%s.%s.%s%s' % (self.major, self.minor, self.build, patch_str)

  def with_incremented_patch(self):
    return V8Version(
        self.major, self.minor, self.build, str(int(self.patch) + 1))

  def update_version_file_blob(self, blob):
    """Takes a version file's text and returns it with this object's version.
    """
    def sub(label, value, text):
      return re.sub(
          VERSION_LINE_RE % label,
          VERSION_LINE_REPLACEMENT % (label, value),
          text,
          flags=re.M,
      )
    blob = sub(V8_MAJOR, self.major, blob)
    blob = sub(V8_MINOR, self.minor, blob)
    blob = sub(V8_BUILD, self.build, blob)
    return sub(V8_PATCH, self.patch, blob)


def isolate_targets_from_tests(tests):
  """Returns the isolated targets associated with a list of tests.

  Args:
    tests: A list of builders.TestStepConfig objects.
  """
  targets = []
  for test in tests:
    if not test.swarming:  # pragma: no cover
      # Skip tests that explicitly disable swarming.
      continue
    config = testing.TEST_CONFIGS.get(test.name) or {}

    # Tests either define an explicit isolate target or use the test
    # names for convenience.
    if config.get('isolated_target'):
      targets.append(config['isolated_target'])
    elif config.get('tests'):
      targets.extend(config['tests'])
  return targets


class V8Api(recipe_api.RecipeApi):
  BUILDERS = builders.BUILDERS

  # Map of GS archive names to urls.
  GS_ARCHIVES = {
    'android_arm_rel_archive': 'gs://chromium-v8/v8-android-arm-rel',
    'android_arm64_rel_archive': 'gs://chromium-v8/v8-android-arm64-rel',
    'arm_rel_archive': 'gs://chromium-v8/v8-arm-rel',
    'arm_dbg_archive': 'gs://chromium-v8/v8-arm-dbg',
    'linux_rel_archive': 'gs://chromium-v8/v8-linux-rel',
    'linux_dbg_archive': 'gs://chromium-v8/v8-linux-dbg',
    'linux_nosnap_rel_archive': 'gs://chromium-v8/v8-linux-nosnap-rel',
    'linux_nosnap_dbg_archive': 'gs://chromium-v8/v8-linux-nosnap-dbg',
    'linux_swarming_staging_archive':
        'gs://chromium-v8/v8-linux-swarming-staging',
    'linux64_rel_archive': 'gs://chromium-v8/v8-linux64-rel',
    'linux64_dbg_archive': 'gs://chromium-v8/v8-linux64-dbg',
    'linux64_custom_snapshot_dbg_archive':
        'gs://chromium-v8/v8-linux64-custom-snapshot-dbg',
    'mips_rel_archive': 'gs://chromium-v8/v8-mips-rel',
    'mipsel_sim_rel_archive': 'gs://chromium-v8/v8-mipsel-sim-rel',
    'mips64el_sim_rel_archive': 'gs://chromium-v8/v8-mips64el-sim-rel',
    'win32_rel_archive': 'gs://chromium-v8/v8-win32-rel',
    'win32_dbg_archive': 'gs://chromium-v8/v8-win32-dbg',
    'v8_for_dart_archive': 'gs://chromium-v8/v8-for-dart-rel',
  }

  VERSION_FILE = 'include/v8-version.h'

  def apply_bot_config(self, builders, tryserver_check=True):
    """Entry method for using the v8 api.

    Requires the presence of a bot_config dict for any master/builder pair.
    This bot_config will be used to refine other api methods.
    """

    mastername = self.m.properties.get('mastername')
    buildername = self.m.properties.get('buildername')
    master_dict = builders.get(mastername, {})
    self.bot_config = master_dict.get('builders', {}).get(buildername)
    assert self.bot_config, (
        'Unrecognized builder name %r for master %r.' % (
            buildername, mastername))

    kwargs = self.bot_config.get('v8_config_kwargs', {})
    self.set_config('v8', optional=True, **kwargs)
    self.m.chromium.set_config('v8', **kwargs)
    self.m.gclient.set_config('v8', **kwargs)

    for c in self.bot_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)
    for c in self.bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)
    if tryserver_check and self.m.tryserver.is_tryserver:
      # TODO(machenbach): This sets the trybot flavor only for gyp. GN
      # is controlled through MB. Unfortunately also the v8 test driver
      # reads this and passes e.g. --dcheck-always-on flag. This should
      # be untangled.
      self.init_tryserver()
    for c in self.bot_config.get('v8_apply_config', []):
      self.apply_config(c)

    if self.bot_config.get('enable_swarming'):
      self.m.gclient.c.got_revision_reverse_mapping[
          'got_swarming_client_revision'] = ('v8/tools/swarming_client')

    # FIXME(machenbach): Use a context object that stores the state for each
    # test process. Otherwise it's easy to introduce bugs with multiple test
    # processes and stale context data. E.g. during bisection these values
    # change for tests on rerun.

    # Default failure retry.
    self.rerun_failures_count = 2

    # If tests are run, this value will be set to their total duration.
    self.test_duration_sec = 0

    # Allow overriding the isolate hashes during bisection with the ones that
    # correspond to the build of a bisect step.
    self._isolated_tests_override = None

    # Cache to compute isolated targets only once.
    self._isolate_targets_cached = []

    # This is inferred from the run_mb step or from the parent bot. If mb is
    # run multiple times, it is overwritten. It contains either gyp or gn
    # properties.
    self.build_environment = self.m.properties.get(
        'parent_build_environment', {})

  @property
  def isolated_tests(self):
    # During bisection, the isolated hashes will be updated with hashes that
    # correspond to the bisect step.
    # TODO(machenbach): Remove pragma as soon as rerun is implemented for
    # swarming.
    if self._isolated_tests_override is not None:  # pragma: no cover
      return self._isolated_tests_override
    return self.m.isolate.isolated_tests

  def testing_random_seed(self):
    """Return a random seed suitable for v8 testing.

    If there are isolate hashes, build a random seed based on the hashes.
    Otherwise use the system's PRNG. This uses a deterministic seed for
    recipe simulation.
    """
    r = random.Random()
    if self.isolated_tests:
      r.seed(tuple(self.isolated_tests))
    elif self._test_data.enabled:
      r.seed(12345)

    seed = 0
    while not seed:
      # Avoid 0 because v8 switches off usage of random seeds when
      # passing 0 and creates a new one.
      seed = r.randint(-2147483648, 2147483647)
    return seed

  def init_tryserver(self):
    if self.m.chromium.c.BUILD_CONFIG != 'Debug':
      # TODO(machenbach): This is only for passing --dchecks-always-on to
      # the test driver. All real build flags are passed by MB on the V8 side.
      # This can be removed after the GN switch is complete as the test
      # driver auto-detects it for GN.
      self.m.chromium.apply_config('trybot_flavor')

  def checkout(self, revision=None, **kwargs):
    # Set revision for bot_update.
    revision = revision or self.m.properties.get(
        'parent_got_revision', self.m.properties.get('revision', 'HEAD'))
    solution = self.m.gclient.c.solutions[0]
    branch = self.m.properties.get('branch', 'master')
    needs_branch_heads = False
    if RELEASE_BRANCH_RE.match(branch):
      revision = 'refs/branch-heads/%s:%s' % (branch, revision)
      needs_branch_heads = True
    solution.revision = revision

    try:
      safe_buildername = ''.join(
          c if c.isalnum() else '_' for c in self.m.properties['buildername'])
      self.checkout_root = self.m.path['builder_cache'].join(safe_buildername)
      self.m.file.ensure_directory(
          'ensure builder cache dir', self.checkout_root)
    except KeyError:
      # No explicit builder cache directory defined. Use the "start_dir"
      # directory.
      # TODO(machenbach): Remove this case when all builders using this recipe
      # migrated to LUCI.
      self.checkout_root = self.m.path['start_dir']
    with self.m.context(cwd=self.checkout_root):
      update_step = self.m.bot_update.ensure_checkout(
          no_shallow=True,
          with_branch_heads=needs_branch_heads,
          **kwargs)

    assert update_step.json.output['did_run']

    # Bot_update maintains the properties independent of the UI
    # presentation.
    self.revision = self.m.bot_update.last_returned_properties['got_revision']

    # Note, a commit position might not be available on feature branches.
    self.revision_cp = (
        self.m.bot_update.last_returned_properties.get('got_revision_cp'))
    self.revision_number = None
    if self.revision_cp:
      self.revision_number = str(self.m.commit_position.parse_revision(
          self.revision_cp))

    return update_step

  def calculate_patch_base_gerrit(self):
    """Calculates the commit hash a gerrit patch was branched off."""
    commits, _ = self.m.gitiles.log(
        url=V8_URL,
        ref='master..%s' % self.m.properties['patch_ref'],
        limit=100,
        step_name='Get patches',
        step_test_data=lambda: self.test_api.example_patch_range(),
    )
    # There'll be at least one commit with the patch. Maybe more for dependent
    # CLs.
    assert len(commits) >= 1
    # We don't support merges.
    assert len(commits[-1]['parents']) == 1
    return commits[-1]['parents'][0]

  def set_up_swarming(self):
    if self.bot_config.get('enable_swarming'):
      self.m.swarming.check_client_version()

    self.m.swarming.set_default_dimension('pool', 'Chrome')
    self.m.swarming.set_default_dimension('os', 'Ubuntu-14.04')
    # TODO(machenbach): Investigate if this is causing a priority inversion
    # with tasks not specifying cores=8. See http://crbug.com/735388
    # self.m.swarming.set_default_dimension('cores', '8')
    self.m.swarming.add_default_tag('project:v8')
    self.m.swarming.default_hard_timeout = 45 * 60

    self.m.swarming.default_idempotent = True

    if self.m.properties['mastername'] == 'tryserver.v8':
      self.m.swarming.add_default_tag('purpose:pre-commit')
      requester = self.m.properties.get('requester')
      if requester == 'commit-bot@chromium.org':
        self.m.swarming.default_priority = 30
        self.m.swarming.add_default_tag('purpose:CQ')
        blamelist = self.m.properties.get('blamelist')
        if len(blamelist) == 1:
          requester = blamelist[0]
      else:
        self.m.swarming.default_priority = 28
        self.m.swarming.add_default_tag('purpose:ManualTS')
      self.m.swarming.default_user = requester

      patch_project = self.m.properties.get('patch_project')
      if patch_project:
        self.m.swarming.add_default_tag('patch_project:%s' % patch_project)
    else:
      if self.m.properties['mastername'] in ['client.v8', 'client.v8.ports']:
        self.m.swarming.default_priority = 25
      else:
        # This should be lower than the CQ.
        self.m.swarming.default_priority = 35
      self.m.swarming.add_default_tag('purpose:post-commit')
      self.m.swarming.add_default_tag('purpose:CI')

    # Overwrite defaults with per-bot settings.
    for key, value in self.bot_config.get(
        'swarming_properties', {}).iteritems():
      setattr(self.m.swarming, key, value)

  def runhooks(self, **kwargs):
    if (self.m.chromium.c.compile_py.compiler and
        self.m.chromium.c.compile_py.compiler.startswith('goma')):
      # Only ensure goma if we want to use it. Otherwise it might break bots
      # that don't support the goma executables.
      self.m.chromium.ensure_goma()
    env = {}
    # TODO(machenbach): Remove this after mb migration.
    if self.c.gyp_env.AR:
      env['AR'] = self.c.gyp_env.AR
    if self.c.gyp_env.CC:
      env['CC'] = self.c.gyp_env.CC
    if self.c.gyp_env.CXX:
      env['CXX'] = self.c.gyp_env.CXX
    if self.c.gyp_env.LINK:
      env['LINK'] = self.c.gyp_env.LINK
    if self.c.gyp_env.RANLIB:
      env['RANLIB'] = self.c.gyp_env.RANLIB
    if self.m.chromium.c.project_generator.tool != 'gyp':
      env['GYP_CHROMIUM_NO_ACTION'] = 1
    else:
      env['GYP_CHROMIUM_NO_ACTION'] = 0
    self.m.chromium.runhooks(env=env, **kwargs)

  def setup_mips_toolchain(self):
    # TODO(machenbach): Deprecate this before migrating to LUCI.
    mips_dir = self.m.path['start_dir'].join(MIPS_DIR, 'bin')
    if not self.m.path.exists(mips_dir):
      self.m.gsutil.download_url(
          'gs://chromium-v8/%s' % MIPS_TOOLCHAIN,
          self.m.path['start_dir'],
          name='bootstrapping mips toolchain')
      with self.m.context(cwd=self.m.path['start_dir']):
        self.m.step('unzipping', ['tar', 'xf', MIPS_TOOLCHAIN])

    self.c.gyp_env.CC = self.m.path.join(mips_dir, 'mips-mti-linux-gnu-gcc')
    self.c.gyp_env.CXX = self.m.path.join(mips_dir, 'mips-mti-linux-gnu-g++')
    self.c.gyp_env.AR = self.m.path.join(mips_dir, 'mips-mti-linux-gnu-ar')
    self.c.gyp_env.RANLIB = self.m.path.join(
        mips_dir, 'mips-mti-linux-gnu-ranlib')
    self.c.gyp_env.LINK = self.m.path.join(mips_dir, 'mips-mti-linux-gnu-g++')

  @property
  def bot_type(self):
    return self.bot_config.get('bot_type', 'builder_tester')

  @property
  def should_build(self):
    return self.bot_type in ['builder', 'builder_tester']

  @property
  def should_test(self):
    return self.bot_type in ['tester', 'builder_tester']

  @property
  def should_upload_build(self):
    return (self.bot_type == 'builder' and
            not self.bot_config.get('slim_swarming_builder'))

  @property
  def should_download_build(self):
    return self.bot_type == 'tester'

  @property
  def relative_path_to_d8(self):
    return self.m.path.join('out', self.m.chromium.c.build_config_fs, 'd8')

  def _test_spec_to_properties(self, buildername, test_spec):
    """Packs a test spec and returns it as a properties dict to be passed to
    another builder.

    This method is the counterpart to the method below.
    """
    packed_spec = [t.pack() for t in (test_spec or {}).get(buildername, [])]
    # TODO(machenbach): Remove this restriction post-buildbot.
    assert len(self.m.json.dumps(packed_spec)) < 1024
    if packed_spec:
      return {'parent_test_spec': packed_spec}
    return {}

  def _test_spec_from_properties(self):
    """Unpacks a test spec provided by another builder via properties.

    This method is the counterpart to the method above.
    """
    return [
      TestStepConfig.unpack(packed_spec)
      for packed_spec in self.m.properties.get('parent_test_spec', [])
    ]

  def extra_tests_from_properties(self):
    """Returns runnable testing.BaseTest objects for each extra test specified
    by parent_test_spec property.

    The parent_test_spec property is expected to contain a list of packed
    builders.TestStepConfig objects.
    """
    return [
      testing.create_test(test, self.m)
      for test in self._test_spec_from_properties()
    ]

  def extra_tests_from_test_spec(self, test_spec):
    """Returns runnable testing.BaseTest objects for each extra test specified
    in the test spec of the current builder.
    """
    return [
      testing.create_test(test, self.m)
      for test in test_spec.get(self.m.properties['buildername'], [])
    ]

  def read_test_spec(self):
    """Reads a test specification file under v8/infra/testing/<mastername>.pyl.

    Returns: Test spec, filtered by interesting builders (current builder and
        all its triggered testers). The format is a mapping of builder name
        to list of builders.TestStepConfig objects. The test-step configs
        can be used by the V8 api to create runnable test steps.
    """
    mastername = self.m.properties['mastername']
    buildername = self.m.properties['buildername']
    test_spec_file = self.m.path['checkout'].join(
        'infra', 'testing', mastername + '.pyl')

    # Source-side test spec is opt-in. Just ignore it if the file doesn't
    # exist for the current master.
    if not self.m.path.exists(test_spec_file):
      return {}

    try:
      # Eval python literal file.
      full_test_spec = ast.literal_eval(self.m.file.read_text(
          'read test spec',
          test_spec_file,
          test_data='{}',
      ))
    except SyntaxError as e:  # pragma: no cover
      raise self.m.step.InfraFailure(
          'Failed to parse test specification "%s": %s' % (test_spec_file, e))

    # Iterate over the current builder and all its triggered testers. Transform
    # the pyl structure into a test-step configuration with TestStepConfig
    # objects for all builders that apply.
    test_spec = {}
    for iter_buildername, _ in iter_builder_set(mastername, buildername):
      if full_test_spec.get(iter_buildername):
        test_spec[iter_buildername] = [
          TestStepConfig.from_test_spec(t)
          for t in full_test_spec[iter_buildername]
        ]

    # Log test spec for debuggability.
    log = []
    for builder, tests in sorted(test_spec.iteritems()):
      log.append(builder)
      for test in tests:
        log.append('  ' + str(test))
    self.m.step.active_result.presentation.logs['test_spec'] = log
    return test_spec

  @property
  def isolate_targets(self):
    if self._isolate_targets_cached:
      return self._isolate_targets_cached

    if self.bot_config.get('enable_swarming'):
      mastername = self.m.properties['mastername']
      buildername = self.m.properties['buildername']

      # Find tests to isolate on builders (requires builder and tester on same
      # master).
      for _, bot_config in iter_builder_set(mastername, buildername):
        self._isolate_targets_cached.extend(
            isolate_targets_from_tests(bot_config.get('tests', [])))

      # Add the performance-tests isolate everywhere, where the perf-bot proxy
      # is triggered.
      if self.bot_config.get('triggers_proxy', False):
        self._isolate_targets_cached.append('perf')

    self._isolate_targets_cached = sorted(list(set(
        self._isolate_targets_cached)))
    return self._isolate_targets_cached

  def isolate_tests(self, extra_targets=None):
    """Upload isolated tests to isolate server.

    Args:
      extra_targets: More targets to isolate.
    """
    isolate_targets = sorted(list(set(
        self.isolate_targets + (extra_targets or []))))
    if isolate_targets:
      self.m.isolate.isolate_tests(
          self.m.chromium.output_dir,
          targets=isolate_targets,
          verbose=True,
          set_swarm_hashes=False,
      )
      self.upload_isolated_json()

  def _update_build_environment(self, mb_output):
    """Sets the build_environment property based on gyp or gn properties in mb
    output.
    """
    self.build_environment = {}
    # Get the client's gyp flags from MB's output. Group 1 captures with posix,
    # group 2 with windows output semantics.
    #
    # Posix:
    # GYP_DEFINES='foo=1 path=a/b/c'
    #
    # Windows:
    # set GYP_DEFINES=foo=1 path='a/b/c'
    # TODO(machenbach): Remove the gyp case after gyp is deprecated.
    for match in re.finditer('^(?:set )?GYP_([^=]*)=(?:(?:\'(.*)\')|(?:(.*)))$',
                             mb_output, re.M):  # pragma: no cover
      # Yield the property name (e.g. GYP_DEFINES) and the value. Either the
      # windows or the posix group matches.
      self.build_environment['GYP_' + match.group(1)] = (
          match.group(2) or match.group(3))

    if 'GYP_DEFINES' in self.build_environment:  # pragma: no cover
      # Filter out gomadir.
      self.build_environment['GYP_DEFINES'] = ' '.join(
          d for d in self.build_environment['GYP_DEFINES'].split()
          if not d.startswith('gomadir')
      )

    # Check if the output looks like gn. Space-join all gn args, except
    # goma_dir.
    # TODO(machenbach): Instead of scanning the output, we could also read
    # the gn.args file that was written.
    match = re.search(r'Writing """\\?\s*(.*)""" to ', mb_output, re.S)
    if match:
      self.build_environment['gn_args'] = ' '.join(
        l for l in match.group(1).strip().splitlines()
        if not l.startswith('goma_dir'))

  def _upload_build_dependencies(self, deps):
    values = {
      'ext_h_avg_deps': deps['by_extension']['h']['avg_deps'],
      'ext_h_top100_avg_deps': deps['by_extension']['h']['top100_avg_deps'],
      'ext_h_top200_avg_deps': deps['by_extension']['h']['top200_avg_deps'],
      'ext_h_top500_avg_deps': deps['by_extension']['h']['top500_avg_deps'],
    }
    points = []
    root = '/'.join([
      'v8.infra',
      'build_dependencies',
      '',
    ])
    for k, v in values.iteritems():
      p = self.m.perf_dashboard.get_skeleton_point(
          root + k, self.revision_number, str(v))
      p['units'] = 'count'
      p['supplemental_columns'] = {
        'a_default_rev': 'r_v8_git',
        'r_v8_git': self.revision,
      }
      points.append(p)
    if points:
      self.m.perf_dashboard.add_point(points)

  def _track_binary_size(self, path_pieces_list, category):
    """Track and upload binary size of configured binaries.

    Args:
      path_pieces_list: List of path pieces to be joined to the build output
          folder respectively. Each path should point to a binary to track.
      category: ChromePerf category for qualifying the graph names, e.g.
          linux32 or linux64.
    """
    files = [
      self.m.chromium.c.build_dir.join(
          *([self.m.chromium.c.build_config_fs] + list(path_pieces)))
      for path_pieces in path_pieces_list
    ]

    sizes = self.m.file.filesizes('Check binary size', files)

    point_defaults = {
      'units': 'bytes',
      'supplemental_columns': {
        'a_default_rev': 'r_v8_git',
        'r_v8_git': self.revision,
      },
    }
    trace_prefix = ['v8.infra', 'binary_size']

    points = []
    for path_pieces, size in zip(path_pieces_list, sizes):
      p = self.m.perf_dashboard.get_skeleton_point(
          '/'.join(trace_prefix + [path_pieces[-1]]),
          self.revision_number,
          str(size),
          bot=category,
      )
      p.update(point_defaults)
      points.append(p)
    self.m.perf_dashboard.add_point(points)

  def compile(self, test_spec=None, **kwargs):
    """Compile all desired targets and isolate tests.

    Args:
      test_spec: Optional test specification in the format returned by
          read_test_spec(). Expected to contain only specifications for the
          current builder and all triggered builders. All corrensponding extra
          targets will also be isolated.
    """
    use_goma = (self.m.chromium.c.compile_py.compiler and
                'goma' in self.m.chromium.c.compile_py.compiler)
    if self.m.chromium.c.project_generator.tool == 'mb':
      def step_test_data():
        # Fake MB output with GN flags.
        return self.m.raw_io.test_api.stream_output(
            'Writing """\\\n'
            'goma_dir = "/b/build/slave/cache/goma_client"\n'
            'target_cpu = "x86"\n'
            'use_goma = true\n'
            '""" to /b/build/slave/linux-builder/build/v8/out/Release/args.gn\n'
            'moar text'
        )
      try:
        self.m.chromium.run_mb(
            self.m.properties['mastername'],
            self.m.properties['buildername'],
            use_goma=use_goma,
            mb_config_path=self.m.path['checkout'].join(
                'infra', 'mb', 'mb_config.pyl'),
            isolated_targets=self.isolate_targets,
            gyp_script=self.m.path.join('gypfiles', 'gyp_v8'),
            stdout=self.m.raw_io.output_text(),
            step_test_data=step_test_data,
        )
      finally:
        # Log captured output. We call log below 'captured_stdout' instead of
        # simply 'stdout' to differentiate it from the default 'stdout' log that
        # is added to all steps. The latter log will actually contain no real
        # output because it is captured by the raw_io module.
        self.m.step.active_result.presentation.logs['captured_stdout'] = (
          self.m.step.active_result.stdout.splitlines())

      # Update the build environment dictionary, which is printed to the
      # user on test failures for easier build reproduction.
      self._update_build_environment(self.m.step.active_result.stdout)

      # Create logs surfacing GN arguments and GYP environment. This information
      # is critical to developers for reproducing failures locally.
      if 'gn_args' in self.build_environment:
        self.m.step.active_result.presentation.logs['gn_args'] = (
            self.build_environment['gn_args'].splitlines())
    elif self.m.chromium.c.project_generator.tool == 'gn':
      self.m.chromium.run_gn(use_goma=use_goma)

    if self.m.properties['buildername'] != 'V8 Mips - builder':
      kwargs['use_goma_module'] = True
    self.m.chromium.compile(**kwargs)

    if self.bot_config.get('track_build_dependencies', False):
      deps = self.m.python(
          name='track build dependencies (fyi)',
          script=self.resource('build-dep-stats.py'),
          args=[
            '-C', self.m.chromium.c.build_dir.join(
                self.m.chromium.c.build_config_fs),
            '-x', '/third_party/',
            '-o', self.m.json.output(),
          ],
          step_test_data=lambda: self.test_api.example_build_dependencies(),
          ok_ret='any',
      ).json.output
      if deps:
        self._upload_build_dependencies(deps)

    # Track binary size if specified.
    tracking_config = self.bot_config.get('binary_size_tracking', {})
    if tracking_config:
      self._track_binary_size(
        tracking_config['path_pieces_list'],
        tracking_config['category'],
      )

    # Calculate extra targets to isolate from V8-side test specification. The
    # test_spec contains extra TestStepConfig objects for the current builder
    # and all its triggered builders.
    extra_targets = isolate_targets_from_tests(
        itertools.chain(*(test_spec or {}).values()))
    self.isolate_tests(extra_targets)

  # TODO(machenbach): This should move to a dynamorio module as soon as one
  # exists.
  def dr_compile(self):
    # TODO(machenbach): Figure out where to put this before the corresponding
    # bot migrates to LUCI.
    self.m.file.ensure_directory(
      'Create Build Dir',
      self.m.path['start_dir'].join('dynamorio', 'build'))
    with self.m.context(
        cwd=self.m.path['start_dir'].join('dynamorio', 'build')):
      self.m.step(
        'Configure Release x64 DynamoRIO',
        ['cmake', '..', '-DDEBUG=OFF'],
      )
      self.m.step(
        'Compile Release x64 DynamoRIO',
        ['make', '-j5'],
      )

  @property
  def run_dynamorio(self):
    return self.m.gclient.c.solutions[-1].name == 'dynamorio'

  def upload_build(self, name_suffix='', archive=None):
    archive = archive or self.GS_ARCHIVES[self.bot_config['build_gs_archive']]
    self.m.archive.zip_and_upload_build(
          'package build' + name_suffix,
          self.m.chromium.c.build_config_fs,
          archive,
          src_dir=self.checkout_root.join('v8'))

  @property
  def isolated_archive_path(self):
    buildername = (self.m.properties.get('parent_buildername') or
                   self.m.properties['buildername'])
    return 'chromium-v8/isolated/%s/%s' % (
        self.m.properties['mastername'],
        buildername,
    )

  def upload_isolated_json(self):
    self.m.gsutil.upload(
        self.m.json.input(self.m.isolate.isolated_tests),
        self.isolated_archive_path,
        '%s.json' % self.revision,
        args=['-a', 'public-read'],
    )

  def maybe_create_clusterfuzz_archive(self, update_step):
    if self.bot_config.get('cf_archive_build', False):
      self.m.archive.clusterfuzz_archive(
          revision_dir='v8',
          build_dir=self.m.chromium.c.build_dir.join(
              self.m.chromium.c.build_config_fs),
          update_properties=update_step.presentation.properties,
          gs_bucket=self.bot_config.get('cf_gs_bucket'),
          gs_acl=self.bot_config.get('cf_gs_acl'),
          archive_prefix=self.bot_config.get('cf_archive_name'),
      )

  def download_build(self, name_suffix='', archive=None):
    self.m.file.rmtree(
          'build directory' + name_suffix,
          self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs))

    archive = archive or self.GS_ARCHIVES[self.bot_config['build_gs_archive']]
    self.m.archive.download_and_unzip_build(
          'extract build' + name_suffix,
          self.m.chromium.c.build_config_fs,
          archive,
          src_dir='v8')

  def download_isolated_json(self, revision):
    archive = 'gs://' + self.isolated_archive_path + '/%s.json' % revision
    self.m.gsutil.download_url(
        archive,
        self.m.json.output(),
        name='download isolated json',
        step_test_data=lambda: self.m.json.test_api.output(
            {'bot_default': '[dummy hash for bisection]'}),
    )
    step_result = self.m.step.active_result
    self._isolated_tests_override = step_result.json.output

  @property
  def build_output_dir(self):
    return self.m.path.join(
        self.m.chromium.c.build_dir,
        self.m.chromium.c.build_config_fs,
    )

  @property
  def generate_gcov_coverage(self):
    return bool(self.bot_config.get('gcov_coverage_folder'))

  def init_gcov_coverage(self):
    """Delete all gcov counter files."""
    self.m.step(
        'lcov zero counters',
        ['lcov', '--directory', self.build_output_dir, '--zerocounters'],
    )

  def upload_gcov_coverage_report(self):
    """Capture coverage data and upload a report."""
    coverage_dir = self.m.path.mkdtemp('gcov_coverage')
    report_dir = self.m.path.mkdtemp('gcov_coverage_html')
    output_file = self.m.path.join(coverage_dir, 'app.info')

    # Capture data from gcda and gcno files.
    self.m.step(
        'lcov capture',
        [
          'lcov',
          '--directory', self.build_output_dir,
          '--capture',
          '--output-file', output_file,
        ],
    )

    # Remove unwanted data.
    self.m.step(
        'lcov remove',
        [
          'lcov',
          '--directory', self.build_output_dir,
          '--remove', output_file,
          'third_party/*',
          'testing/gtest/*',
          'testing/gmock/*',
          '/usr/include/*',
          '--output-file', output_file,
        ],
    )

    # Generate html report into a temp folder.
    self.m.step(
        'genhtml',
        [
          'genhtml',
          '--output-directory', report_dir,
          output_file,
        ],
    )

    # Upload report to google storage.
    dest = '%s/%s' % (self.bot_config['gcov_coverage_folder'], self.revision)
    result = self.m.gsutil(
        [
          '-m', 'cp', '-a', 'public-read', '-R', report_dir,
          'gs://chromium-v8/%s' % dest,
        ],
        'coverage report',
    )
    result.presentation.links['report'] = (
      'https://storage.googleapis.com/chromium-v8/%s/index.html' % dest)

  @property
  def generate_sanitizer_coverage(self):
    return bool(self.bot_config.get('sanitizer_coverage_folder'))

  def create_coverage_context(self):
    if self.generate_sanitizer_coverage:
      return testing.SanitizerCoverageContext(self.m)
    else:
      return testing.NULL_COVERAGE

  def create_test(self, test):
    """Wrapper that allows to shortcut common tests with their names.

    Returns: A runnable test instance.
    """
    return testing.create_test(test, self.m)

  def create_tests(self):
    return [self.create_test(t) for t in self.bot_config.get('tests', [])]

  def is_pure_swarming_tester(self, tests):
    return (self.bot_type == 'tester' and
            self.bot_config.get('enable_swarming') and
            all(map(lambda x: x.uses_swarming, tests)))

  def runtests(self, tests):
    if self.extra_flags:
      result = self.m.step('Customized run with extra flags', cmd=None)
      result.presentation.step_text += ' '.join(self.extra_flags)
      assert all(re.match(r'[\w\-]*', x) for x in self.extra_flags), (
          'no special characters allowed in extra flags')

    start_time_sec = self.m.time.time()
    test_results = testing.TestResults.empty()

    # Apply test filter.
    # TODO(machenbach): Track also the number of tests that ran and throw an
    # error if the overall number of tests from all steps was zero.
    tests = [t for t in tests if t.apply_filter()]

    swarming_tests = [t for t in tests if t.uses_swarming]
    non_swarming_tests = [t for t in tests if not t.uses_swarming]
    failed_tests = []

    # Creates a coverage context if coverage is tracked. Null object otherwise.
    coverage_context = self.create_coverage_context()

    # Make sure swarming triggers come first.
    # TODO(machenbach): Port this for rerun for bisection.
    for t in swarming_tests + non_swarming_tests:
      try:
        t.pre_run(coverage_context=coverage_context)
      except self.m.step.InfraFailure:  # pragma: no cover
        raise
      except self.m.step.StepFailure:  # pragma: no cover
        failed_tests.append(t)

    # Setup initial zero coverage after all swarming jobs are triggered.
    coverage_context.setup()

    # Make sure non-swarming tests are run before swarming results are
    # collected.
    for t in non_swarming_tests + swarming_tests:
      try:
        test_results += t.run(coverage_context=coverage_context)
      except self.m.step.InfraFailure:  # pragma: no cover
        raise
      except self.m.step.StepFailure:  # pragma: no cover
        failed_tests.append(t)

    # Upload accumulated coverage data.
    coverage_context.maybe_upload()

    if failed_tests:
      failed_tests_names = [t.name for t in failed_tests]
      raise self.m.step.StepFailure(
          '%d tests failed: %r' % (len(failed_tests), failed_tests_names))
    self.test_duration_sec = self.m.time.time() - start_time_sec
    return test_results

  def maybe_bisect(self, test_results):
    """Build-local bisection for one failure."""
    # Don't activate for branch or fyi bots.
    if self.m.properties['mastername'] not in ['client.v8', 'client.v8.ports']:
      return

    if self.bot_config.get('disable_auto_bisect'):  # pragma: no cover
      return

    # Only bisect over failures not flakes. Rerun only the fastest test.
    try:
      failure = min(test_results.failures, key=lambda r: r.duration)
    except ValueError:
      return

    # Only bisect if the fastest failure is significantly faster than the
    # ongoing build's total.
    duration_factor = self.m.properties.get(
        'bisect_duration_factor', BISECT_DURATION_FACTOR)
    if (failure.duration * duration_factor > self.test_duration_sec):
      step_result = self.m.step(
          'Bisection disabled - test too slow', cmd=None)
      return

    # Don't retry failures during bisection.
    self.rerun_failures_count = 0

    # Suppress using shards to be able to rerun single tests.
    self.c.testing.may_shard = False

    # Only rebuild the target of the test to retry. Works only with ninja.
    targets = None
    if 'ninja' in self.m.chromium.c.gyp_env.GYP_GENERATORS:
      targets = [failure.failure_dict.get('target_name', 'All')]

    test = self.create_test(failure.test_step_config)
    def test_func(revision):
      return test.rerun(failure_dict=failure.failure_dict)

    def is_bad(revision):
      with self.m.step.nest('Bisect ' + revision[:8]):
        if not self.is_pure_swarming_tester([test]):
          self.checkout(revision, update_presentation=False)
        if self.bot_type == 'builder_tester':
          self.runhooks()
          self.compile(targets=targets)
        elif self.bot_type == 'tester':
          if test.uses_swarming:
            self.download_isolated_json(revision)
          else:  # pragma: no cover
            raise self.m.step.InfraFailure('Swarming required for bisect.')
        else:  # pragma: no cover
          raise self.m.step.InfraFailure(
              'Bot type %s not supported.' % self.bot_type)
        result = test_func(revision)
        if result.infra_failures:  # pragma: no cover
          raise self.m.step.InfraFailure(
              'Cannot continue bisection due to infra failures.')
        return result.failures

    with self.m.step.nest('Bisect'):
      # Setup bisection range ("from" exclusive).
      latest_previous, bisect_range = self.get_change_range()
      if len(bisect_range) <= 1:
        self.m.step('disabled - less than two changes', cmd=None)
        return

      if self.bot_type == 'tester':
        # Filter the bisect range to the revisions for which isolate hashes or
        # archived builds are available, depending on whether swarming is used
        # or not.
        available_bisect_range = self.get_available_range(
            bisect_range, test.uses_swarming)
      else:
        available_bisect_range = bisect_range

    if is_bad(latest_previous):
      # If latest_previous is already "bad", the test failed before the current
      # build's change range, i.e. it is a recurring failure.
      # TODO: Try to be smarter here, fetch the build data from the previous
      # one or two builds and check if the failure happened in revision
      # latest_previous. Otherwise, the cost of calling is_bad is as much as
      # one bisect step.
      step_result = self.m.step(
          'Bisection disabled - recurring failure', cmd=None)
      step_result.presentation.status = self.m.step.WARNING
      return

    # Log available revisions to ease debugging.
    self.log_available_range(available_bisect_range)

    culprit = bisection.keyed_bisect(available_bisect_range, is_bad)
    culprit_range = self.calc_missing_values_in_sequence(
        bisect_range,
        available_bisect_range,
        culprit,
    )
    self.report_culprits(culprit_range)

  @staticmethod
  def format_duration(duration_in_seconds):
    duration = datetime.timedelta(seconds=duration_in_seconds)
    time = (datetime.datetime.min + duration).time()
    return time.strftime('%M:%S:') + '%03i' % int(time.microsecond / 1000)

  def _command_results_text(self, results, flaky):
    """Returns log lines for all results of a unique command."""
    assert results
    lines = []

    # Add common description for multiple runs.
    flaky_suffix = ' (flaky in a repeated run)' if flaky else ''
    lines.append('Test: %s%s' % (results[0]['name'], flaky_suffix))
    lines.append('Flags: %s' % ' '.join(results[0]['flags']))
    lines.append('Command: %s' % results[0]['command'])
    lines.append('')
    lines.append('Build environment:')
    build_environment = self.build_environment
    if build_environment is None:
      lines.append(
          'Not available. Please look up the builder\'s configuration.')
    else:
      for key in sorted(build_environment):
        lines.append(' %s: %s' % (key, build_environment[key]))
    lines.append('')

    # Add results for each run of a command.
    for result in sorted(results, key=lambda r: int(r['run'])):
      lines.append('Run #%d' % int(result['run']))
      lines.append('Exit code: %s' % result['exit_code'])
      lines.append('Result: %s' % result['result'])
      if result.get('expected'):
        lines.append('Expected outcomes: %s' % ", ".join(result['expected']))
      lines.append('Duration: %s' % V8Api.format_duration(result['duration']))
      lines.append('')
      if result['stdout']:
        lines.append('Stdout:')
        lines.extend(result['stdout'].splitlines())
        lines.append('')
      if result['stderr']:
        lines.append('Stderr:')
        lines.extend(result['stderr'].splitlines())
        lines.append('')
    return lines

  def _duration_results_text(self, test):
    return [
      'Test: %s' % test['name'],
      'Flags: %s' % ' '.join(test['flags']),
      'Command: %s' % test['command'],
      'Duration: %s' % V8Api.format_duration(test['duration']),
    ]

  def _update_durations(self, output, presentation):
    # Slowest tests duration summary.
    lines = []
    for test in output['slowest_tests']:
      suffix = ''
      if test.get('marked_slow') is False:
        suffix = ' *'
      lines.append(
          '%s %s%s' % (V8Api.format_duration(test['duration']),
                       test['name'], suffix))

    # Slowest tests duration details.
    lines.extend(['', 'Details:', ''])
    for test in output['slowest_tests']:
      lines.extend(self._duration_results_text(test))
    presentation.logs['durations'] = lines

  def _get_failure_logs(self, output, failure_factory):
    def all_same(items):
      return all(x == items[0] for x in items)

    if not output['results']:
      return {}, [], {}, []

    unique_results = {}
    for result in output['results']:
      # Use test base name as UI label (without suite and directory names).
      label = result['name'].split('/')[-1]
      # Truncate the label if it is still too long.
      if len(label) > MAX_LABEL_SIZE:
        label = label[:MAX_LABEL_SIZE - 2] + '..'
      # Group tests with the same label (usually the same test that ran under
      # different configurations).
      unique_results.setdefault(label, []).append(result)

    failure_log = {}
    flake_log = {}
    failures = []
    flakes = []
    for label in sorted(unique_results.keys()[:MAX_FAILURE_LOGS]):
      failure_lines = []
      flake_lines = []

      # Group results by command. The same command might have run multiple
      # times to detect flakes.
      results_per_command = {}
      for result in unique_results[label]:
        results_per_command.setdefault(result['command'], []).append(result)

      for command in results_per_command:
        # Determine flakiness. A test is flaky if not all results from a unique
        # command are the same (e.g. all 'FAIL').
        if all_same(map(lambda x: x['result'], results_per_command[command])):
          # This is a failure. Only add the data of the first run to the final
          # test results, as rerun data is not important for bisection.
          failure = results_per_command[command][0]
          failures.append(failure_factory(failure, failure['duration']))
          failure_lines += self._command_results_text(
              results_per_command[command], False)
        else:
          # This is a flake. Only add the data of the first run to the final
          # test results, as rerun data is not important for bisection.
          flake = results_per_command[command][0]
          flakes.append(failure_factory(flake, flake['duration']))
          flake_lines += self._command_results_text(
              results_per_command[command], True)

      if failure_lines:
        failure_log[label] = failure_lines
      if flake_lines:
        flake_log[label] = flake_lines

    return failure_log, failures, flake_log, flakes

  def _update_failure_presentation(self, log, failures, presentation):
    for label in sorted(log):
      presentation.logs[label] = log[label]

    if failures:
      # Number of failures.
      presentation.step_text += ('failures: %d<br/>' % len(failures))

  @property
  def extra_flags(self):
    extra_flags = self.m.properties.get('extra_flags', '')
    if isinstance(extra_flags, basestring):
      extra_flags = extra_flags.split()
    assert isinstance(extra_flags, list) or isinstance(extra_flags, tuple)
    return list(extra_flags)

  def _with_extra_flags(self, args):
    """Returns: the arguments with additional extra flags inserted.

    Extends a possibly existing extra flags option.
    """
    if not self.extra_flags:
      return args

    options, args = TEST_RUNNER_PARSER.parse_known_args(args)

    if options.extra_flags:
      new_flags = [options.extra_flags] + self.extra_flags
    else:
      new_flags = self.extra_flags

    args.extend(['--extra-flags', ' '.join(new_flags)])
    return args

  @property
  def test_filter(self):
    return [f for f in self.m.properties.get('testfilter', [])
            if f != 'defaulttests']

  def _applied_test_filter(self, test):
    """Returns: the list of test filters that match a test configuration."""
    # V8 test filters always include the full suite name, followed
    # by more specific paths and possibly ending with a glob, e.g.:
    # 'mjsunit/regression/prefix*'.
    return [f for f in self.test_filter
              for t in test.get('suite_mapping', test['tests'])
              if f.startswith(t)]

  def _setup_test_runner(self, test, applied_test_filter, test_step_config):
    env = {}
    full_args = [
      '--progress=verbose',
      '--mode', self.m.chromium.c.build_config_fs,
      '--outdir', self.m.path.split(self.m.chromium.c.build_dir)[-1],
      '--buildbot',
      '--timeout=200',
    ]

    # On reruns, there's a fixed random seed set in the test configuration.
    if '--random-seed' not in test.get('test_args', []):
      full_args.append('--random-seed=%d' % self.testing_random_seed())

    # Either run tests as specified by the filter (trybots only) or as
    # specified by the test configuration.
    if applied_test_filter:
      full_args += applied_test_filter
    else:
      full_args += list(test.get('tests', []))

    # Add test-specific test arguments.
    full_args += test.get('test_args', [])

    # Add builder-specific test arguments.
    full_args += self.c.testing.test_args

    # Add builder-, test- and step-specific variants.
    full_args += testing.test_args_from_variants(
        self.bot_config.get('variants'),
        test.get('variants'),
        test_step_config.variants,
    )

    # Add step-specific test arguments.
    full_args += test_step_config.test_args

    full_args = self._with_extra_flags(full_args)

    if self.run_dynamorio:
      # TODO(machenbach): Needs to use cache for LUCI migration.
      drrun = self.m.path['start_dir'].join(
          'dynamorio', 'build', 'bin64', 'drrun')
      full_args += [
        '--command_prefix',
        '%s -reset_every_nth_pending 0 --' % drrun,
      ]

    full_args += [
      '--rerun-failures-count=%d' % self.rerun_failures_count,
    ]

    # TODO(machenbach): This is temporary code for rolling out the new test
    # runner. It should be removed after the roll-out. We skip the branches
    # waterfall, as it runs older versions of the V8 side.
    if self.m.properties['mastername'] != 'client.v8.branches':
      full_args += [
        '--mastername', self.m.properties['mastername'],
        '--buildername', self.m.properties['buildername'],
      ]

    return full_args, env

  @staticmethod
  def _copy_property(src, dest, key):
    if key in src:
      dest[key] = src[key]

  def maybe_trigger(self, test_spec=None, **additional_properties):
    triggers = self.bot_config.get('triggers', [])
    triggers_proxy = self.bot_config.get('triggers_proxy', False)
    if triggers or triggers_proxy:
      # Careful! Before adding new properties, note the following:
      # Triggered bots on CQ will either need new properties to be explicitly
      # whitelisted or their name should be prefixed with 'parent_'.
      properties = {
        'parent_got_revision': self.revision,
      }
      if self.revision_cp:
        properties['parent_got_revision_cp'] = self.revision_cp
      if self.m.tryserver.is_tryserver:
        properties.update(
          category=self.m.properties.get('category', 'manual_ts'),
          reason=str(self.m.properties.get('reason', 'ManualTS')),
          # On tryservers, set revision to the same as on the current bot,
          # as CQ expects builders and testers to match the revision field.
          revision=str(self.m.properties.get('revision', 'HEAD')),
        )
        for p in ['issue', 'master', 'patch_gerrit_url', 'patch_git_url',
                  'patch_issue', 'patch_project', 'patch_ref',
                  'patch_repository_url', 'patch_set', 'patch_storage',
                  'patchset', 'requester', 'rietveld']:
          try:
            properties[p] = str(self.m.properties[p])
          except KeyError:
            pass
      else:
        # On non-tryservers, we can set the revision to whatever the
        # triggering builder checked out.
        properties['revision'] = self.revision

      if self.m.properties.get('testfilter'):
        properties.update(testfilter=list(self.m.properties['testfilter']))
      self._copy_property(self.m.properties, properties, 'extra_flags')

      # TODO(machenbach): Also set meaningful buildbucket tags of triggering
      # parent.

      # Pass build environment to testers if it doesn't exceed buildbot's
      # limits.
      # TODO(machenbach): Remove the check in the after-buildbot age.
      if len(self.m.json.dumps(self.build_environment)) < 1024:
        properties['parent_build_environment'] = self.build_environment

      swarm_hashes = self.m.isolate.isolated_tests
      if swarm_hashes:
        properties['swarm_hashes'] = swarm_hashes
      properties.update(**additional_properties)

      if self.m.tryserver.is_tryserver:
        if triggers:
          trigger_props = {}
          self._copy_property(self.m.properties, trigger_props, 'git_revision')
          self._copy_property(self.m.properties, trigger_props, 'revision')
          trigger_props['parent_buildername'] = self.m.properties['buildername']
          if 'build_id' in self.m.properties:
            trigger_props['parent_build_id'] = self.m.properties['build_id']
          if 'buildnumber' in self.m.properties:
            trigger_props['parent_buildnumber'] = (
                self.m.properties['buildnumber'])
          trigger_props.update(properties)
          try:
            bucket_name = self.m.buildbucket.properties['build']['bucket']
          except (TypeError, KeyError) as e:
            bucket_name = 'master.%s' % self.m.properties['mastername']
          if not self.m.runtime.is_luci:
            service_account = self.m.puppet_service_account.get_key_path(
                BBUCKET_SERVICE_ACCOUNT)
          else:
            # LUCI builders are automatically using service account from
            # swarming env, which is specified in the cr-buildbucket.cfg.
            service_account = None
          step_result = self.m.buildbucket.put(
              [
                {
                  'bucket': bucket_name,
                  'parameters': {
                    'builder_name': builder_name,
                    # Attach additional builder-specific test-spec properties.
                    'properties': dict(
                        trigger_props,
                        **self._test_spec_to_properties(builder_name, test_spec)
                    ),
                    # Generate a list of fake changes from the blamelist
                    # property to have correct blamelist displayed on the child
                    # build. Unfortunately, this only copies author names, but
                    # additional details about the list of changes associated
                    # with the build are currently not accessible from the
                    # recipe code.
                    'changes': [
                      {
                        'author': {
                          'email': author,
                        },
                      }
                      for author in self.m.properties.get('blamelist', [])
                    ],
                  },
                }
                for builder_name in triggers
              ],
              service_account,
              name='trigger',
              step_test_data=lambda: self.m.json.test_api.output_stream({}),
          )
      else:
        self.m.trigger(*[{
          'builder_name': builder_name,
          # Attach additional builder-specific test-spec properties.
          'properties': dict(
              properties,
              **self._test_spec_to_properties(builder_name, test_spec)
          ),
        } for builder_name in triggers])

      if triggers_proxy:
        proxy_properties = {
          'archive': self.GS_ARCHIVES[self.bot_config['build_gs_archive']],
        }
        proxy_properties.update(properties)
        self.m.trigger(*[{
          'builder_name': 'v8_trigger_proxy',
          'bucket': 'master.internal.client.v8',
          'properties': proxy_properties,
          'buildbot_changes': [{
            'author': 'trigger_proxy',
            'revision': self.revision,
          }]
        }])

  def get_change_range(self):
    if self.m.properties.get('override_changes'):
      # This can be used for manual testing or on a staging builder that
      # simulates a change range.
      changes = self.m.properties['override_changes']
      step_result = self.m.step('Override changes', cmd=None)
      step_result.presentation.logs['changes'] = self.m.json.dumps(
        changes, indent=2).splitlines()
    else:
      url = '%s/p/%s/builders/%s/builds/%s?json=1' % (
          CBE_URL,
          self.m.properties['mastername'],
          urllib.quote(self.m.properties['buildername']),
          str(self.m.properties['buildnumber']),
      )
      change_json = self.m.url.get_json(
          url,
          step_name='Fetch changes',
          default_test_data=self.test_api.example_buildbot_changes(),
      ).output
      changes = change_json['sourceStamp']['changes']

    assert changes
    first_change = changes[0]['revision']
    last_change = changes[-1]['revision']

    # Commits is a list of gitiles commit dicts in reverse chronological order.
    commits, _ = self.m.gitiles.log(
        url=V8_URL,
        ref='%s~2..%s' % (first_change, last_change),
        limit=100,
        step_name='Get change range',
        step_test_data=lambda: self.test_api.example_bisection_range()
    )

    # We get minimum two commits when the first and last commit are equal (i.e.
    # there was only one commit C). Commits will contain the latest previous
    # commit and C.
    assert len(commits) > 1

    return (
        # Latest previous.
        commits[-1]['commit'],
        # List of commits oldest -> newest, without the latest previous.
        [commit['commit'] for commit in reversed(commits[:-1])],
    )

  def get_available_range(self, bisect_range, use_swarming=False):
    assert self.bot_type == 'tester'
    archive_url_pattern = 'gs://' + self.isolated_archive_path + '/%s.json'
    # TODO(machenbach): Maybe parallelize this in a wrapper script.
    args = ['ls']
    available_range = []
    # Check all builds except the last as we already know it is "bad".
    for r in bisect_range[:-1]:
      step_result = self.m.gsutil(
          args + [archive_url_pattern % r],
          name='check build %s' % r[:8],
          # Allow failures, as the tool will formally fail for any absent file.
          ok_ret='any',
          stdout=self.m.raw_io.output_text(),
          step_test_data=lambda: self.test_api.example_available_builds(r),
      )
      if r in step_result.stdout.strip():
        available_range.append(r)

    # Always keep the latest revision in the range. The latest build is
    # assumed to be "bad" and won't be tested again.
    available_range.append(bisect_range[-1])
    return available_range

  def calc_missing_values_in_sequence(
        self, sequence, subsequence, value):
    """Calculate a list of missing values from a subsequence.

    Args:
      sequence: The complete sequence including all values.
      subsequence: A subsequence from the sequence above.
      value: An element from subsequence.
    Returns: A subsequence from sequence [a..b], where b is the value and
             for all x in a..b-1 holds x not in subsequence. Also
             a-1 is either in subsequence or value was the first
             element in subsequence.
    """
    from_index = 0
    to_index = sequence.index(value) + 1
    index_on_subsequence = subsequence.index(value)
    if index_on_subsequence > 0:
      # Value is not the first element in subsequence.
      previous = subsequence[index_on_subsequence - 1]
      from_index = sequence.index(previous) + 1
    return sequence[from_index:to_index]

  def log_available_range(self, available_bisect_range):
    step_result = self.m.step('Available range', cmd=None)
    for revision in available_bisect_range:
      step_result.presentation.links[revision[:8]] = COMMIT_TEMPLATE % revision

  def report_culprits(self, culprit_range):
    assert culprit_range
    if len(culprit_range) > 1:
      text = 'Suspecting multiple commits'
    else:
      text = 'Suspecting %s' % culprit_range[0][:8]

    step_result = self.m.step(text, cmd=None)
    for culprit in culprit_range:
      step_result.presentation.links[culprit[:8]] = COMMIT_TEMPLATE % culprit

  def read_version_file(self, ref, step_name_desc):
    """Read and return the version-file content at a paricular ref."""
    with self.m.context(cwd=self.m.path['checkout']):
      return self.m.git(
          'show', '%s:%s' % (ref, self.VERSION_FILE),
          name='Check %s version file' % step_name_desc,
          stdout=self.m.raw_io.output_text(),
      ).stdout

  def read_version_from_ref(self, ref, step_name_desc):
    """Read and return the version at a paricular ref."""
    return V8Api.version_from_file(self.read_version_file(ref, step_name_desc))

  @staticmethod
  def version_from_file(blob):
    major = re.search(VERSION_LINE_RE % V8_MAJOR, blob, re.M).group(1)
    minor = re.search(VERSION_LINE_RE % V8_MINOR, blob, re.M).group(1)
    build = re.search(VERSION_LINE_RE % V8_BUILD, blob, re.M).group(1)
    patch = re.search(VERSION_LINE_RE % V8_PATCH, blob, re.M).group(1)
    return V8Version(major, minor, build, patch)
