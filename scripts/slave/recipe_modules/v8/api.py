# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import ast
import base64
from collections import defaultdict
import contextlib
import datetime
import difflib
import functools
import random
import re
import urllib

# pylint: disable=relative-import
from builders import TestSpec
from recipe_engine.types import freeze
from recipe_engine import recipe_api
from . import bisection
from . import builders as v8_builders
from . import testing


MILO_HOST = 'luci-milo.appspot.com'
V8_URL = 'https://chromium.googlesource.com/v8/v8'

COMMIT_TEMPLATE = '%s/+/%%s' % V8_URL

# Regular expressions for v8 branch names.
RELEASE_BRANCH_RE = re.compile(r'^refs/branch-heads/\d+\.\d+$')

# Regular expressions for getting target bits from gn args.
TARGET_CPU_RE = re.compile(r'.*target_cpu\s+=\s+"([^"]*)".*')

# With too many letters, labels are to big and stretch the UI.
MAX_LABEL_SIZE = 35

# Make sure that a step is not flooded with log lines.
MAX_FAILURE_LOGS = 10

# Factor by which the considered failure for bisection must be faster than the
# ongoing build's total.
BISECT_DURATION_FACTOR = 5

TEST_RUNNER_PARSER = argparse.ArgumentParser()
TEST_RUNNER_PARSER.add_argument('--extra-flags')

VERSION_LINE_RE = r'^#define %s\s+(\d*)$'
VERSION_LINE_REPLACEMENT = '#define %s %s'
V8_MAJOR = 'V8_MAJOR_VERSION'
V8_MINOR = 'V8_MINOR_VERSION'
V8_BUILD = 'V8_BUILD_NUMBER'
V8_PATCH = 'V8_PATCH_LEVEL'

LCOV_IMAGE = 'lcov:2018-01-18_17-03'


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


class V8Api(recipe_api.RecipeApi):
  VERSION_FILE = 'include/v8-version.h'
  EMPTY_TEST_SPEC = v8_builders.EmptyTestSpec
  TEST_SPEC = v8_builders.TestSpec

  def __init__(self, *args, **kwargs):
    super(V8Api, self).__init__(*args, **kwargs)
    self.test_configs = {}
    self.bot_config = None
    self.rerun_failures_count = None
    self.test_duration_sec = None
    self.isolated_tests = None
    self.build_environment = None
    self.checkout_root = None
    self.revision = None
    self.revision_cp = None
    self.revision_number = None

  def bot_config_by_buildername(
      self, builders=None, use_goma=True):
    default = {}
    if not self.m.properties.get('parent_buildername'):
      # Builders and builder_testers both build and need the following set of
      # default chromium configs:
      if use_goma:
        default['chromium_apply_config'] = ['default_compiler', 'goma', 'mb']
      else:
        default['chromium_apply_config'] = ['default_compiler', 'mb']
    return (builders or {}).get(self.m.buildbucket.builder_name, default)

  def update_bot_config(self, bot_config, binary_size_tracking, build_config,
                        clusterfuzz_archive, coverage, enable_swarming,
                        target_arch, target_platform, track_build_dependencies,
                        triggers, triggers_proxy):
    """Update bot_config dict with src-side properties.

    Args:
      bot_config: The bot_config dict to update.
      binary_size_tracking: Additional configurations to enable binary size
          tracking.
      build_config: Config value for BUILD_CONFIG in chromium recipe module.
      clusterfuzz_archive: Additional configurations set for archiving builds to
          GS buckets for clusterfuzz.
      coverage: Optional coverage setting.
      enable_swarming: Switch to enable/disable swarming.
      target_arch: Config value for TARGET_ARCH in chromium recipe module.
      target_platform: Config value for TARGET_PLATFORM in chromium recipe
          module.
      track_build_dependencies: Weather to track and upload build-dependencies.
      triggers: List of tester names to trigger on success.
      triggers_proxy: Weather to trigger the internal trigger proxy.

    Returns:
      An updated copy of the bot_config dict.
    """
    # TODO(machenbach): Turn the bot_config dict into a proper class.
    # Make mutable copy.
    bot_config = dict(bot_config)
    bot_config['v8_config_kwargs'] = dict(
        bot_config.get('v8_config_kwargs', {}))
    # Update only specified properties.
    for k, v in (
        ('BUILD_CONFIG', build_config),
        ('TARGET_ARCH', target_arch),
        ('TARGET_PLATFORM', target_platform)):
      if v is not None:
        bot_config['v8_config_kwargs'][k] = v
    if coverage is not None:
      bot_config['coverage'] = coverage
    if enable_swarming is not None:
      bot_config['enable_swarming'] = enable_swarming
    if binary_size_tracking is not None:
      bot_config['binary_size_tracking'] = binary_size_tracking
    if clusterfuzz_archive is not None:
      bot_config['clusterfuzz_archive'] = clusterfuzz_archive
    if track_build_dependencies is not None:
      bot_config['track_build_dependencies'] = track_build_dependencies
    # Make mutable copy.
    bot_config['triggers'] = list(bot_config.get('triggers', []))
    bot_config['triggers'].extend(triggers or [])
    # TODO(machenbach): Temporarily also dedupe, during migrating triggers src
    # side. Should be removed when everything has migrated.
    bot_config['triggers'] = sorted(list(set(bot_config['triggers'])))
    bot_config['triggers_proxy'] = triggers_proxy
    return bot_config

  def get_test_roots(self):
    """Returns the list of default and extensible test root directories.

    A test root is a directory with the following layout:
    <root>/infra/testing/config.pyl (optional)
    <root>/infra/testing/builders.pyl
    <root>/test/<test suites> (optional)

    By default, the V8 checkout is a test root, and all matching directories
    under v8/custom_deps.

    Returns: List of paths to test roots.
    """
    result = [self.m.path['checkout']]
    custom_deps_dir = self.m.path['checkout'].join('custom_deps')
    self.m.file.ensure_directory('ensure custom_deps dir', custom_deps_dir)
    for path in self.m.file.listdir('list test roots', custom_deps_dir):
      if self.m.path.exists(path.join('infra', 'testing', 'builders.pyl')):
        assert self.bot_type == 'builder_tester', (
            'Separate test checkouts are only supported on builder_testers. '
            'For separate builders and testers, the test configs need to be '
            'transferred as properties')
        result.append(path)
    return result

  def update_test_configs(self, test_configs):
    """Update test configs without mutating previous copy."""
    self.test_configs = dict(self.test_configs)
    self.test_configs.update(test_configs)

  def load_static_test_configs(self):
    """Set predifined test configs from build repository."""
    self.update_test_configs(testing.TEST_CONFIGS)

  def load_dynamic_test_configs(self, root):
    """Add test configs from configured location.

    The test configs in <root>/infra/testing/config.pyl are expected to follow
    the same structure as the TEST_CONFIGS dict in testing.py.

    Args:
      test_checkout: Path to test root, can either be the V8 checkout or an
          additional test checkout.
    Returns: Test config dict.
    """
    test_config_path = root.join('infra', 'testing', 'config.pyl')

    # Fallback for branch builders.
    if not self.m.path.exists(test_config_path):
      return {}

    try:
      # Eval python literal file.
      test_configs = ast.literal_eval(self.m.file.read_text(
          'read test config (%s)' % self.m.path.basename(root),
          test_config_path,
          test_data='{}',
      ))
    except SyntaxError as e:  # pragma: no cover
      raise self.m.step.InfraFailure(
          'Failed to parse test config "%s": %s' % (test_config_path, e))

    for test_config in test_configs.itervalues():
      # This configures the test runner to set the test root to the
      # test_checkout location for all tests from this checkout.
      # TODO(machenbach): This is starting to get hacky. The test config
      # dicts should be refactored into classes similar to test specs. Maybe
      # the extra configurations from test configs could be added to test
      # specs.
      test_config['test_root'] = str(root.join('test'))

    return test_configs

  def apply_bot_config(self, bot_config):
    """Entry method for using the v8 api."""
    self.bot_config = bot_config

    kwargs = {}
    if self.m.properties.get('parent_build_config'):
      kwargs['BUILD_CONFIG'] = self.m.properties['parent_build_config']
    kwargs.update(self.bot_config.get('v8_config_kwargs', {}))

    self.set_config('v8', optional=True, **kwargs)
    self.m.chromium.set_config('v8', **kwargs)
    self.m.gclient.set_config('v8', **kwargs)

    if self.m.chromium.c.TARGET_PLATFORM in ['android', 'fuchsia']:
      self.m.gclient.apply_config(self.m.chromium.c.TARGET_PLATFORM)

    for c in self.bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)

    # On clusterfuzz builders use the default clusterfuzz gn target.
    if self.bot_config.get('clusterfuzz_archive'):
      self.m.chromium.apply_config('default_target_v8_clusterfuzz')

    # Infer gclient variable that instructs sysroot download.
    if (self.m.chromium.c.TARGET_PLATFORM != 'android' and
        self.m.chromium.c.TARGET_ARCH == 'arm'):
      # This grabs both sysroots to not be dependent on additional bitness
      # setting.
      self.m.gclient.c.target_cpu.add('arm')
      self.m.gclient.c.target_cpu.add('arm64')

    # Apply additional configs for coverage builders.
    if self.bot_config.get('coverage') == 'gcov':
      self.bot_config['disable_auto_bisect'] = True
    elif self.bot_config.get('coverage') == 'sanitizer':
      self.m.gclient.apply_config('llvm_compiler_rt')

    if self.bot_config.get('enable_swarming', True):
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

    # Contains list of isolated tests, which can be either a list of tests from
    # one or more steps uploading to isolate server, isolate hashes from the
    # build part of the bisect step or a list of values from the swarm_hashes
    # property (parsed by self.m.isolate.isolated_tests property getter invoked
    # here, which returns a new dict each time, thus no need to copy it here).
    self.isolated_tests = self.m.isolate.isolated_tests

    # This is inferred from the run_mb step or from the parent bot. If mb is
    # run multiple times, it is overwritten. It contains gn arguments.
    self.build_environment = self.m.properties.get(
        'parent_build_environment', {})

  def set_gclient_custom_var(self, var_name):
    """Sets the gclient custom var `var_name` if given.

    This customizes gclient sync, based on conditions on the variable in the
    V8 DEPS file.
    """
    if var_name:
      self.m.gclient.c.solutions[0].custom_vars[var_name] = 'True'

  def set_gclient_custom_deps(self, custom_deps):
    """Configures additional gclient custom_deps to be synced."""
    for name, path in (custom_deps or {}).iteritems():
      self.m.gclient.c.solutions[0].custom_deps[name] = path

  def set_chromium_configs(self, clobber, default_targets):
    if clobber:
      self.m.chromium.c.clobber_before_runhooks = clobber
    if default_targets:
      self.m.chromium.c.compile_py.default_targets = default_targets

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

  def checkout(self, revision=None, **kwargs):
    # Set revision for bot_update.
    revision = revision or self.m.buildbucket.gitiles_commit.id or 'HEAD'
    solution = self.m.gclient.c.solutions[0]
    branch = self.m.buildbucket.gitiles_commit.ref
    if RELEASE_BRANCH_RE.match(branch):
      revision = '%s:%s' % (branch, revision)
    solution.revision = revision

    self.checkout_root = self.m.path['builder_cache']
    self.m.file.ensure_directory(
        'ensure builder cache dir', self.checkout_root)
    with self.m.context(cwd=self.checkout_root):
      update_step = self.m.bot_update.ensure_checkout(**kwargs)

    assert update_step.json.output['did_run']

    self.parse_revision_props(
        self.m.bot_update.last_returned_properties['got_revision'],
        self.m.bot_update.last_returned_properties.get('got_revision_cp'))
    return update_step

  def parse_revision_props(self, got_revision, got_revision_cp=None):
    """Parses got_revision and got_revision_cp properties.

    Sets self.revision, self.revision_cp and self.revision_number.

    Normally this is called from self.checkout above, but it may also be useful
    on bots where we do not have a checkout but have these properties (e.g. set
    by the parent builder when triggering child) and need to parse them.

    Args:
      got_revision: Full git hash of the commit.
      got_revision_cp: Value of the Cr-Commit-Position commit footer, e.g.
          "refs/heads/master@{#12345}".
    """
    self.revision = got_revision
    self.revision_cp = got_revision_cp

    # Note, a commit position might not be available on feature branches.
    self.revision_number = None
    if self.revision_cp:
      _, self.revision_number = self.m.commit_position.parse(self.revision_cp)
      self.revision_number = str(self.revision_number)

  def calculate_patch_base_gerrit(self):
    """Calculates the commit hash a gerrit patch was branched off."""
    commits, _ = self.m.gitiles.log(
        url=V8_URL,
        ref='master..%s' % self.m.tryserver.gerrit_change_fetch_ref,
        limit=100,
        step_name='Get patches',
        step_test_data=self.test_api.example_patch_range,
    )
    # There'll be at least one commit with the patch. Maybe more for dependent
    # CLs.
    assert len(commits) >= 1
    # We don't support merges.
    assert len(commits[-1]['parents']) == 1
    return commits[-1]['parents'][0]

  def set_up_swarming(self):
    if self.bot_config.get('enable_swarming', True):
      self.m.chromium_swarming.check_client_version()

    self.m.chromium_swarming.set_default_dimension('pool', 'Chrome')
    self.m.chromium_swarming.set_default_dimension('os', 'Ubuntu-14.04')
    # TODO(machenbach): Investigate if this is causing a priority inversion
    # with tasks not specifying cores=8. See http://crbug.com/735388
    # self.m.chromium_swarming.set_default_dimension('cores', '8')
    self.m.chromium_swarming.add_default_tag('project:v8')
    self.m.chromium_swarming.default_hard_timeout = 45 * 60

    self.m.chromium_swarming.default_idempotent = True
    self.m.chromium_swarming.task_output_stdout = 'all'

    if self.m.properties['mastername'] == 'tryserver.v8':
      self.m.chromium_swarming.add_default_tag('purpose:pre-commit')
      self.m.chromium_swarming.default_priority = 30

      changes = self.m.buildbucket.build.input.gerrit_changes
      assert len(changes) <= 1
      if changes and changes[0].project:
        self.m.chromium_swarming.add_default_tag(
            'patch_project:%s' % changes[0].project)
    else:
      if self.m.properties['mastername'] in [
          'client.v8', 'client.v8.branches', 'client.v8.ports']:
        self.m.chromium_swarming.default_priority = 25
      else:
        # This should be lower than the CQ.
        self.m.chromium_swarming.default_priority = 35
      self.m.chromium_swarming.add_default_tag('purpose:post-commit')
      self.m.chromium_swarming.add_default_tag('purpose:CI')

  def runhooks(self, **kwargs):
    if (self.m.chromium.c.compile_py.compiler and
        self.m.chromium.c.compile_py.compiler.startswith('goma')):
      # Only ensure goma if we want to use it. Otherwise it might break bots
      # that don't support the goma executables.
      self.m.chromium.ensure_goma()
    env = {}
    self.m.chromium.runhooks(env=env, **kwargs)

  @property
  def bot_type(self):
    if self.bot_config.get('triggers') or self.bot_config.get('triggers_proxy'):
      return 'builder'
    if self.m.properties.get('parent_buildername'):
      return 'tester'
    return 'builder_tester'

  @property
  def builderset(self):
    """Returns a list of names of this builder and all its triggered testers."""
    return (
        [self.m.buildbucket.builder_name] +
        list(self.bot_config.get('triggers', []))
    )

  @property
  def should_build(self):
    return self.bot_type in ['builder', 'builder_tester']

  @property
  def should_test(self):
    return self.bot_type in ['tester', 'builder_tester']

  @property
  def should_upload_build(self):
    return self.bot_config.get('triggers_proxy')

  @property
  def relative_path_to_d8(self):
    return self.m.path.join('out', self.m.chromium.c.build_config_fs, 'd8')

  def extra_tests_from_properties(self):
    """Returns runnable testing.BaseTest objects for each extra test specified
    by parent_test_spec property.
    """
    return [
      testing.create_test(test, self.m)
      for test in v8_builders.TestSpec.from_properties_dict(self.m.properties)
    ]

  def extra_tests_from_test_spec(self, test_spec):
    """Returns runnable testing.BaseTest objects for each extra test specified
    in the test spec of the current builder.
    """
    return [
      testing.create_test(test, self.m)
      for test in test_spec.get_tests(self.m.buildbucket.builder_name)
    ]

  def dedupe_tests(self, high_prec_tests, low_prec_tests):
    """Dedupe tests with lower precedence."""
    high_prec_ids = set([test.id for test in high_prec_tests])
    return high_prec_tests + [
      test for test in low_prec_tests if test.id not in high_prec_ids]

  def read_test_spec(self, root):
    """Reads a test specification file under <root>/infra/testing/builders.pyl.

    Args:
      root: Path to checkout root with configurations.
    Returns: v8_builders.TestSpec object, filtered by interesting builders
      (current builder and all its triggered testers).
    """
    test_spec_file = root.join('infra', 'testing', 'builders.pyl')

    # Fallback for branch builders.
    if not self.m.path.exists(test_spec_file):
      return v8_builders.EmptyTestSpec

    try:
      # Eval python literal file.
      full_test_spec = ast.literal_eval(self.m.file.read_text(
          'read test spec (%s)' % self.m.path.basename(root),
          test_spec_file,
          test_data='{}',
      ))
    except SyntaxError as e:  # pragma: no cover
      raise self.m.step.InfraFailure(
          'Failed to parse test specification "%s": %s' % (test_spec_file, e))

    # Transform into object.
    test_spec = TestSpec.from_python_literal(full_test_spec, self.builderset)

    # Log test spec for debuggability.
    self.m.step.active_result.presentation.logs['test_spec'] = (
        test_spec.log_lines())

    return test_spec

  def isolate_targets_from_tests(self, tests):
    """Returns the isolated targets associated with a list of tests.

    Args:
      tests: A list of test names used as keys in the V8 API's test config.
    """
    if not self.bot_config.get('enable_swarming', True):
      return []
    targets = []
    for test in tests:
      config = self.test_configs.get(test) or {}

      # Tests either define an explicit isolate target or use the test
      # names for convenience.
      if config.get('isolated_target'):
        targets.append(config['isolated_target'])
      elif config.get('tests'):
        targets.extend(config['tests'])
    return targets

  def isolate_tests(self, isolate_targets, out_dir=None):
    """Upload isolated tests to isolate server.

    Args:
      isolate_targets: Targets to isolate.
      out_dir: Name of the build output directory, e.g. 'out-ref'. Defaults to
        'out'. Note that it is not a path, but just the name of the directory.
    """
    output_dir = self.m.chromium.output_dir
    if out_dir:
      output_dir = self.m.path['checkout'].join(
          out_dir, self.m.chromium.c.build_config_fs)

    # Special handling for 'perf' target, since perf tests are going to be
    # executed on an internal swarming server and thus need to be uploaded to
    # internal isolate server.
    if 'perf' in isolate_targets:
      isolate_targets.remove('perf')
      self.m.isolate.isolate_server = 'https://chrome-isolated.appspot.com'
      self.m.isolate.isolate_tests(
          output_dir,
          targets=['perf'],
          verbose=True,
          swarm_hashes_property_name=None,
          step_name='isolate tests (perf)',
      )
      self.isolated_tests.update(self.m.isolate.isolated_tests)
      # https://crbug.com/944904
      self.m.isolate.isolate_server = 'https://isolateserver.appspot.com'

    if isolate_targets:
      self.m.isolate.isolate_tests(
          output_dir,
          targets=isolate_targets,
          verbose=True,
          swarm_hashes_property_name=None,
      )
      self.isolated_tests.update(self.m.isolate.isolated_tests)

    if self.isolated_tests:
      self.upload_isolated_json()

  def _update_build_environment(self, gn_args):
    """Sets the build_environment property based on gn arguments."""
    self.build_environment = {}
    # Space-join all gn args, except goma_dir.
    self.build_environment['gn_args'] = ' '.join(
        l for l in gn_args.splitlines()
        if not l.startswith('goma_dir'))

  @property
  def target_bits(self):
    """Returns target bits (as int) inferred from gn arguments from MB."""
    match = TARGET_CPU_RE.match(self.build_environment.get('gn_args', ''))
    if match:
      return 64 if '64' in match.group(1) else 32
    # If target_cpu is not set, gn defaults to 64 bits.
    return 64  # pragma: no cover

  def _upload_build_dependencies(self, deps):
    values = {
      'ext_h_avg_deps': deps['by_extension']['h']['avg_deps'],
      'ext_h_top100_avg_deps': deps['by_extension']['h']['top100_avg_deps'],
      'ext_h_top200_avg_deps': deps['by_extension']['h']['top200_avg_deps'],
      'ext_h_top500_avg_deps': deps['by_extension']['h']['top500_avg_deps'],
    }
    points = []
    root = '/'.join(['v8.infra', 'build_dependencies', ''])
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

  def _track_binary_size(self, binary, category):
    """Track and upload binary size of configured binaries.

    Args:
      binary: Binary name joined to the build output folder.
      category: ChromePerf category for qualifying the graph names, e.g.
          linux32 or linux64.
    """
    size = self.m.file.filesizes(
        'Check binary size', [self.build_output_dir.join(binary)])[0]

    point_defaults = {
      'units': 'bytes',
      'supplemental_columns': {
        'a_default_rev': 'r_v8_git',
        'r_v8_git': self.revision,
      },
    }

    point = self.m.perf_dashboard.get_skeleton_point(
        '/'.join(['v8.infra', 'binary_size', binary]),
        self.revision_number,
        str(size),
        bot=category,
    )
    point.update(point_defaults)
    self.m.perf_dashboard.add_point([point])

  def compile(
      self, test_spec=v8_builders.EmptyTestSpec, mb_config_path=None,
      out_dir=None, **kwargs):
    """Compile all desired targets and isolate tests.

    Args:
      test_spec: Optional TestSpec object as returned by read_test_spec().
          Expected to contain only specifications for the current builder and
          all triggered builders. All corrensponding extra targets will also be
          isolated.
      mb_config_path: Path to the MB config file. Defaults to
          infra/mb/mb_config.py in the checkout.
      out_dir: Name of the build output directory, e.g. 'out-ref'. Defaults to
        'out'. Note that it is not a path, but just the name of the directory.
    """
    with self.m.osx_sdk('mac'):  # this is no-op on non-Mac hosts
      use_goma = (self.m.chromium.c.compile_py.compiler and
                  'goma' in self.m.chromium.c.compile_py.compiler)

      # Calculate targets to isolate from V8-side test specification. The
      # test_spec contains extra TestStepConfig objects for the current builder
      # and all its triggered builders.
      isolate_targets = self.isolate_targets_from_tests(
          test_spec.get_all_test_names())

      # Add the performance-tests isolate everywhere, where the perf-bot proxy
      # is triggered.
      if self.bot_config.get('triggers_proxy', False):
        isolate_targets = isolate_targets + ['perf']

      # Sort and dedupe.
      isolate_targets = sorted(list(set(isolate_targets)))

      build_dir = None
      if out_dir:  # pragma: no cover
        build_dir = '//%s/%s' % (out_dir, self.m.chromium.c.build_config_fs)
      if self.m.chromium.c.project_generator.tool == 'mb':
        mb_config_rel_path = self.m.properties.get(
            'mb_config_path', 'infra/mb/mb_config.pyl')
        gn_args = self.m.chromium.mb_gen(
            self.m.properties['mastername'],
            self.m.buildbucket.builder_name,
            use_goma=use_goma,
            mb_config_path=(
                mb_config_path or
                self.m.path['checkout'].join(*mb_config_rel_path.split('/'))),
            isolated_targets=isolate_targets,
            build_dir=build_dir,
            gn_args_location=self.m.gn.LOGS)

        # Update the build environment dictionary, which is printed to the
        # user on test failures for easier build reproduction.
        self._update_build_environment(gn_args)

        # Create logs surfacing GN arguments. This information is critical to
        # developers for reproducing failures locally.
        if 'gn_args' in self.build_environment:
          self.m.step.active_result.presentation.logs['gn_args'] = (
              self.build_environment['gn_args'].splitlines())
      elif self.m.chromium.c.project_generator.tool == 'gn':
        self.m.chromium.run_gn(use_goma=use_goma, build_dir=build_dir)

      if use_goma:
        kwargs['use_goma_module'] = True
      self.m.chromium.compile(out_dir=out_dir, **kwargs)

      self.isolate_tests(isolate_targets, out_dir=out_dir)

  @property
  def should_collect_post_compile_metrics(self):
    return (
        self.m.v8.bot_config.get('track_build_dependencies') or
        self.m.v8.bot_config.get('binary_size_tracking'))

  def collect_post_compile_metrics(self):
    with self.m.osx_sdk('mac'):  # this is no-op on non-Mac hosts
      if self.bot_config.get('track_build_dependencies', False):
        with self.m.context(env_prefixes={'PATH': [self.depot_tools_path]}):
          deps = self.m.python(
              name='track build dependencies (fyi)',
              script=self.resource('build-dep-stats.py'),
              args=[
                '-C', self.build_output_dir,
                '-x', '/third_party/',
                '-o', self.m.json.output(),
              ],
              step_test_data=self.test_api.example_build_dependencies,
              ok_ret='any',
              venv=True,
          ).json.output
        if deps:
          self._upload_build_dependencies(deps)

      # Track binary size if specified.
      tracking_config = self.bot_config.get('binary_size_tracking', {})
      if tracking_config:
        self._track_binary_size(
          tracking_config['binary'],
          tracking_config['category'],
        )

  @property
  def depot_tools_path(self):
    """Returns path to depot_tools pinned in the V8 checkout."""
    assert 'checkout' in self.m.path, (
        "Pinned depot_tools is not available before checkout has been created")
    return self.m.path['checkout'].join('third_party', 'depot_tools')

  def _get_default_archive(self):
    return 'gs://chromium-v8/archives/%s/%s' % (
        self.m.properties['mastername'],
        self.m.buildbucket.builder_name,
    )

  def upload_build(self, name_suffix='', archive=None):
    self.m.archive.zip_and_upload_build(
          'package build' + name_suffix,
          self.m.chromium.c.build_config_fs,
          archive or self._get_default_archive(),
          src_dir=self.checkout_root.join('v8'))

  @property
  def isolated_archive_path(self):
    buildername = (self.m.properties.get('parent_buildername') or
                   self.m.buildbucket.builder_name)
    return 'chromium-v8/isolated/%s/%s' % (
        self.m.properties['mastername'], buildername)

  def upload_isolated_json(self):
    self.m.gsutil.upload(
        self.m.json.input(self.isolated_tests),
        self.isolated_archive_path,
        '%s.json' % self.revision,
        args=['-a', 'public-read'],
    )

  def maybe_create_clusterfuzz_archive(self, update_step):
    clusterfuzz_archive = self.bot_config.get('clusterfuzz_archive')
    if clusterfuzz_archive:
      kwargs = {}
      if clusterfuzz_archive.get('bitness'):
        kwargs['use_legacy'] = False
        kwargs['bitness'] = clusterfuzz_archive['bitness']
      self.m.archive.clusterfuzz_archive(
          revision_dir='v8',
          build_dir=self.build_output_dir,
          update_properties=update_step.presentation.properties,
          gs_bucket=clusterfuzz_archive.get('bucket'),
          gs_acl='public-read',
          archive_prefix=clusterfuzz_archive.get('name'),
          **kwargs
      )

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
    self.isolated_tests = step_result.json.output

  @property
  def build_output_dir(self):
    """Absolute path to the build product based on the 'checkout' path."""
    return self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs)

  @property
  def generate_gcov_coverage(self):
    return self.bot_config.get('coverage') == 'gcov'

  def init_gcov_coverage(self):
    """Delete all gcov counter files."""
    self.m.docker.login()
    self.m.docker.run(
        LCOV_IMAGE,
        'lcov zero counters',
        ['lcov', '--directory', self.build_output_dir, '--zerocounters'],
        dir_mapping=[(self.build_output_dir, self.build_output_dir)],
    )

  def upload_gcov_coverage_report(self):
    """Capture coverage data and upload a report."""
    coverage_dir = self.m.path.mkdtemp('gcov_coverage')
    report_dir = self.m.path.mkdtemp('gcov_coverage_html')
    output_file = self.m.path.join(coverage_dir, 'app.info')

    dir_mapping = [
        # We need to map entire checkout, since some of the files generated by
        # lcov inside the build output dir contain relative paths to files in
        # the checkout and without this map, genhtml step below will fail to
        # find them.
        (self.m.path['checkout'], self.m.path['checkout']),
        (coverage_dir, coverage_dir),
        (report_dir, report_dir),
    ]

    # Capture data from gcda and gcno files.
    self.m.docker.run(
        LCOV_IMAGE,
        'lcov capture',
        [
          'lcov',
          '--directory', self.build_output_dir,
          '--capture',
          '--output-file', output_file,
        ],
        dir_mapping,
    )

    # Remove unwanted data.
    self.m.docker.run(
        LCOV_IMAGE,
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
        dir_mapping,
    )

    # Generate html report into a temp folder.
    self.m.docker.run(
        LCOV_IMAGE,
        'genhtml',
        [
          'genhtml',
          '--output-directory', report_dir,
          output_file,
        ],
        dir_mapping,
    )

    # Upload report to google storage.
    dest = '%s%d_gcov_rel/%s' % (
        self.m.platform.name, self.target_bits, self.revision)
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
    return self.bot_config.get('coverage') == 'sanitizer'

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

  @property
  def is_pure_swarming_tester(self):
    return (self.bot_type == 'tester' and
            self.bot_config.get('enable_swarming', True))

  @contextlib.contextmanager
  def maybe_nest(self, condition, parent_step_name):
    if not condition:
      yield
    else:
      with self.m.step.nest(parent_step_name):
        yield

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

    with self.maybe_nest(swarming_tests, 'trigger tests'):
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

    # Only rebuild the target of the test to retry.
    targets = [failure.failure_dict.get('target_name', 'All')]

    test = self.create_test(failure.test_step_config)
    def test_func(_):
      return test.rerun(failure_dict=failure.failure_dict)

    def is_bad(revision):
      with self.m.step.nest('Bisect ' + revision[:8]):
        if not self.is_pure_swarming_tester:
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
        available_bisect_range = self.get_available_range(bisect_range)
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

  def ui_test_label(self, full_test_name):
    # Use test base name as UI label (without suite and directory names).
    label = full_test_name.split('/')[-1]
    # Truncate the label if it is still too long.
    if len(label) > MAX_LABEL_SIZE:
      label = label[:MAX_LABEL_SIZE - 3] + '...'
    return label

  def _get_failure_logs(self, output, failure_factory):
    if not output['results']:
      return {}, [], {}, []

    unique_results = defaultdict(list)
    for result in output['results']:
      label = self.ui_test_label(result['name'])
      # Group tests with the same label (usually the same test that ran under
      # different configurations).
      unique_results[label].append(result)

    failure_log = {}
    flake_log = {}
    failures = []
    flakes = []
    for label in sorted(unique_results.keys())[:MAX_FAILURE_LOGS]:
      failure_lines = []
      flake_lines = []

      # Group results by command. The same command might have run multiple
      # times to detect flakes.
      results_per_command = defaultdict(list)
      for result in unique_results[label]:
        results_per_command[result['command']].append(result)

      for results in results_per_command.values():
        # Determine flakiness.
        failure = failure_factory(results)
        if failure.is_flaky:
          # This is a flake.
          flakes.append(failure)
          flake_lines += failure.log_lines()
        else:
          # This is a failure.
          failures.append(failure)
          failure_lines += failure.log_lines()

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
      presentation.step_text += 'failures: %d<br/>' % len(failures)

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

    # Add optional non-standard root directory for test suites.
    if test.get('test_root'):
      full_args += ['--test-root', test['test_root']]

    # On reruns, there's a fixed random seed set in the test configuration.
    if ('--random-seed' not in test.get('test_args', []) and
        test.get('use_random_seed', True)):
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

    full_args += [
      '--rerun-failures-count=%d' % self.rerun_failures_count,
    ]

    # TODO(machenbach): This is temporary code for rolling out the new test
    # runner. It should be removed after the roll-out. We skip the branches
    # waterfall, as it runs older versions of the V8 side.
    if self.m.properties['mastername'] != 'client.v8.branches':
      full_args += [
        '--mastername', self.m.properties['mastername'],
        '--buildername', self.m.buildbucket.builder_name,
      ]

    return full_args, env

  @staticmethod
  def _copy_property(src, dest, key):
    if key in src:
      dest[key] = src[key]

  def maybe_trigger(self, test_spec=v8_builders.EmptyTestSpec,
                    **additional_properties):
    triggers = self.bot_config.get('triggers', [])
    triggers_proxy = self.bot_config.get('triggers_proxy', False)
    if not triggers and not triggers_proxy:
      return

    properties = {
      'parent_got_revision': self.revision,
      'parent_buildername': self.m.buildbucket.builder_name,
      'parent_build_config': self.m.chromium.c.BUILD_CONFIG,
    }
    if self.revision_cp:
      properties['parent_got_revision_cp'] = self.revision_cp
    if self.m.tryserver.is_tryserver:
      properties.update(
        category=self.m.properties.get('category', 'manual_ts'),
        reason=str(self.m.properties.get('reason', 'ManualTS')),
        # On tryservers, set revision to the same as on the current bot, as it
        # is used to generate buildset tag in buildbucket_trigger below.
        revision=self.m.buildbucket.gitiles_commit.id or 'HEAD',
        patch_gerrit_url='https://%s' % self.m.tryserver.gerrit_change.host,
        patch_issue=self.m.tryserver.gerrit_change.change,
        patch_project=self.m.tryserver.gerrit_change.project,
        patch_set=self.m.tryserver.gerrit_change.patchset,
        patch_storage='gerrit',
      )
    else:
      # On non-tryservers, we can set the revision to whatever the
      # triggering builder checked out.
      properties['revision'] = self.revision

    if self.m.properties.get('testfilter'):
      properties.update(testfilter=list(self.m.properties['testfilter']))
    self._copy_property(self.m.properties, properties, 'extra_flags')

    # Pass build environment to testers if it doesn't exceed buildbot's
    # limits.
    # TODO(machenbach): Remove the check in the after-buildbot age.
    if len(self.m.json.dumps(self.build_environment)) < 1024:
      properties['parent_build_environment'] = self.build_environment

    swarm_hashes = self.isolated_tests
    if swarm_hashes:
      properties['swarm_hashes'] = swarm_hashes
    properties.update(**additional_properties)

    if triggers:
      if self.m.tryserver.is_tryserver:
        trigger_props = {}
        self._copy_property(self.m.properties, trigger_props, 'revision')
        trigger_props.update(properties)
        self.m.cq.record_triggered_builds(*self.buildbucket_trigger(
            [(builder_name, dict(
              trigger_props,
              **test_spec.as_properties_dict(builder_name)
            )) for builder_name in triggers],
            bucket='try.triggered',
        ))
      else:
        ci_properties = dict(properties)
        if self.should_upload_build:
          ci_properties['archive'] = self._get_default_archive()
        self.m.scheduler.emit_triggers(
            [(
              self.m.scheduler.BuildbucketTrigger(
                properties=dict(
                  ci_properties,
                  **test_spec.as_properties_dict(builder_name)
                ),
              ), 'v8', [builder_name],
            ) for builder_name in triggers],
            step_name='trigger'
        )

    if triggers_proxy:
      proxy_properties = {'archive': self._get_default_archive()}
      proxy_properties.update(properties)
      self.buildbucket_trigger(
          [('v8_trigger_proxy', proxy_properties)],
          project='v8-internal',
          bucket='ci',
          step_name='trigger_internal')

  def buildbucket_trigger(
      self, requests, project=None, bucket=None, step_name='trigger'):
    """Triggers builds via buildbucket.

    Args:
      requests: List of 2-tuples (builder_name, properties).
      project: Project to trigger builds in (defaults to same as parent).
      bucket: Bucket to trigger builds in (defaults to same as parent).
      step_name: Name of the triggering step that appear on the build.

    Returns:
      List of api.buildbucket.build_pb2.Build messages.
    """
    # Add user_agent:cq to child builds if the parent is also triggered by CQ.
    extra_tags = {}
    if any(tag.key == 'user_agent' and tag.value == 'cq'
           for tag in self.m.buildbucket.build.tags):
      extra_tags['user_agent'] = 'cq'

    builds = self.m.buildbucket.schedule([
      self.m.buildbucket.schedule_request(
        project=project,
        bucket=bucket,
        builder=builder_name,
        tags=self.m.buildbucket.tags(**extra_tags),
        properties=properties,
      ) for builder_name, properties in requests
    ], step_name=step_name)

    # TODO(sergiyb): Remove this when recipe simulation will start throwing
    # InfraFailure for a non-zero retcode. See https://crbug.com/931473.
    if any(not b.id for b in builds):
      self.m.step.active_result.presentation.status = self.m.step.EXCEPTION
      raise self.m.step.InfraFailure('buildbucket.schedule failed')

    return builds

  def get_change_range(self):
    if self.m.properties.get('override_changes'):
      # This can be used for manual testing or on a staging builder that
      # simulates a change range.
      changes = self.m.properties['override_changes']
      step_result = self.m.step('Override changes', cmd=None)
      step_result.presentation.logs['changes'] = self.m.json.dumps(
        changes, indent=2).splitlines()
    else:
      # TODO(sergiyb): Migrate from Milo API to buildbucket v2.
      data_json = self.m.step(
          'Fetch changes',
          [
            'prpc', 'call', '-format=json', MILO_HOST,
            'milo.Buildbot.GetBuildbotBuildJSON'
          ],
          stdin=self.m.json.input({
            'master': self.m.properties['mastername'],
            'builder': self.m.buildbucket.builder_name,
            'buildNum': self.m.buildbucket.build.number,
          }),
          stdout=self.m.json.output(),
          infra_step=True,
          step_test_data=lambda: self.m.json.test_api.output_stream({
            'data': base64.b64encode(
              self.m.json.dumps(self.test_api.example_buildbot_changes())),
          }),
      ).stdout
      change_json = self.m.json.loads(base64.b64decode(data_json['data']))
      changes = change_json['sourceStamp']['changes']

    assert changes
    changes = sorted(changes, key=lambda c: c['when'])
    oldest_change = changes[0]['revision']
    newest_change = changes[-1]['revision']

    # Commits is a list of gitiles commit dicts in reverse chronological order.
    commits, _ = self.m.gitiles.log(
        url=V8_URL,
        ref='%s~2..%s' % (oldest_change, newest_change),
        limit=100,
        step_name='Get change range',
        step_test_data=self.test_api.example_bisection_range
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

  def get_available_range(self, bisect_range):
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
