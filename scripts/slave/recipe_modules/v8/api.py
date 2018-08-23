# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import ast
import base64
import contextlib
import datetime
import difflib
import functools
import random
import re
import urllib

from builders import EmptyTestSpec, TestStepConfig, TestSpec
from recipe_engine.types import freeze
from recipe_engine import recipe_api
from . import bisection
from . import builders
from . import testing


MILO_HOST = 'luci-milo.appspot.com'
V8_URL = 'https://chromium.googlesource.com/v8/v8'

COMMIT_TEMPLATE = '%s/+/%%s' % V8_URL

# Regular expressions for v8 branch names.
RELEASE_BRANCH_RE = re.compile(r'^(?:refs/branch-heads/)?\d+\.\d+$')

# With more than 23 letters, labels are to big for buildbot's popup boxes.
MAX_LABEL_SIZE = 23

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
  BUILDERS = builders.BUILDERS
  FLATTENED_BUILDERS = builders.FLATTENED_BUILDERS
  VERSION_FILE = 'include/v8-version.h'
  EMPTY_TEST_SPEC = EmptyTestSpec
  TEST_SPEC = TestSpec

  def bot_config_by_buildername(self, builders=FLATTENED_BUILDERS):
    default = {}
    if not self.m.properties.get('parent_buildername'):
      # Builders and builder_testers both build and need the following set of
      # default chromium configs:
      default['chromium_apply_config'] = ['default_compiler', 'goma', 'mb']
    return builders.get(self.m.properties.get('buildername'), default)

  def update_bot_config(self, bot_config, build_config, enable_swarming,
                        target_arch, target_platform, triggers):
    """Update bot_config dict with src-side properties.

    Args:
      bot_config: The bot_config dict to update.
      build_config: Config value for BUILD_CONFIG in chromium recipe module.
      enable_swarming: Switch to enable/disable swarming.
      target_arch: Config value for TARGET_ARCH in chromium recipe module.
      target_platform: Config value for TARGET_PLATFORM in chromium recipe
          module.
      triggers: List of tester names to trigger on success.

    Returns:
      An updated copy of the bot_config dict.
    """
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
    if enable_swarming is not None:
      bot_config['enable_swarming'] = enable_swarming
    # Make mutable copy.
    bot_config['triggers'] = list(bot_config.get('triggers', []))
    bot_config['triggers'].extend(triggers or [])
    # TODO(machenbach): Temporarily also dedupe, during migrating triggers src
    # side. Should be removed when everything has migrated.
    bot_config['triggers'] = sorted(list(set(bot_config['triggers'])))
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
    self.test_configs = dict(getattr(self, 'test_configs', {}))
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

    for c in self.bot_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)
    for c in self.bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)
    for c in self.bot_config.get('v8_apply_config', []):
      self.apply_config(c)

    # Infer gclient variable that instructs sysroot download.
    if (self.m.chromium.c.TARGET_PLATFORM != 'android' and
        self.m.chromium.c.TARGET_ARCH == 'arm'):
      # This grabs both sysroots to not be dependent on additional bitness
      # setting.
      self.m.gclient.c.target_cpu.add('arm')
      self.m.gclient.c.target_cpu.add('arm64')

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

    # Cache to compute isolated targets only once.
    self._isolate_targets_cached = []

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
    revision = revision or self.m.properties.get(
        'parent_got_revision', self.m.properties.get('revision', 'HEAD'))
    solution = self.m.gclient.c.solutions[0]
    branch = self.m.properties.get('branch', 'master')
    if RELEASE_BRANCH_RE.match(branch):
      if branch.startswith('refs/branch-heads/'):
        revision = '%s:%s' % (branch, revision)
      else:
        # TODO(sergiyb): Deprecate this after migrating branch builders to LUCI.
        revision = 'refs/branch-heads/%s:%s' % (branch, revision)
    solution.revision = revision

    self.checkout_root = self.m.path['builder_cache']
    if self.m.runtime.is_luci:
      self.checkout_root = self.m.path['builder_cache']
    else:
      # TODO(sergiyb): Deprecate this after migrating all builders to LUCI.
      safe_buildername = ''.join(
          c if c.isalnum() else '_' for c in self.m.properties['buildername'])
      self.checkout_root = self.m.path['builder_cache'].join(safe_buildername)

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
      self.revision_number = str(self.m.commit_position.parse_revision(
          self.revision_cp))

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
    if self.bot_config.get('enable_swarming', True):
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
      self.m.swarming.default_priority = 30

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

    if self.m.runtime.is_experimental:
      # Use lower priority for tasks scheduled from experimental builds.
      self.m.swarming.default_priority = 60

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
        [self.m.properties['buildername']] +
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
    return (self.bot_config.get('triggers_proxy') or
            self.bot_config.get('should_upload_build'))

  @property
  def should_download_build(self):
    return self.bot_type == 'tester' and not self.is_pure_swarming_tester

  @property
  def relative_path_to_d8(self):
    return self.m.path.join('out', self.m.chromium.c.build_config_fs, 'd8')

  def extra_tests_from_properties(self):
    """Returns runnable testing.BaseTest objects for each extra test specified
    by parent_test_spec property.
    """
    return [
      testing.create_test(test, self.m)
      for test in TestSpec.from_properties_dict(self.m.properties)
    ]

  def extra_tests_from_test_spec(self, test_spec):
    """Returns runnable testing.BaseTest objects for each extra test specified
    in the test spec of the current builder.
    """
    return [
      testing.create_test(test, self.m)
      for test in test_spec.get_tests(self.m.properties['buildername'])
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
    Returns: TestSpec object, filtered by interesting builders (current builder
        and all its triggered testers).
    """
    test_spec_file = root.join('infra', 'testing', 'builders.pyl')

    # Fallback for branch builders.
    if not self.m.path.exists(test_spec_file):
      return EmptyTestSpec

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

  @property
  def isolate_targets(self):
    """Returns the isolate targets statically known from builders.py."""
    if self._isolate_targets_cached:
      return self._isolate_targets_cached

    if self.bot_config.get('enable_swarming', True):
      # Find tests to isolate on builders.
      for buildername in self.builderset:
        bot_config = builders.FLATTENED_BUILDERS.get(buildername, {})
        self._isolate_targets_cached.extend(
            self.isolate_targets_from_tests(
                [test.name for test in bot_config.get('tests', [])]))

      # Add the performance-tests isolate everywhere, where the perf-bot proxy
      # is triggered.
      if self.bot_config.get('triggers_proxy', False):
        self._isolate_targets_cached.append('perf')

    self._isolate_targets_cached = sorted(list(set(
        self._isolate_targets_cached)))
    return self._isolate_targets_cached

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

  def _upload_build_dependencies(self, deps):
    values = {
      'ext_h_avg_deps': deps['by_extension']['h']['avg_deps'],
      'ext_h_top100_avg_deps': deps['by_extension']['h']['top100_avg_deps'],
      'ext_h_top200_avg_deps': deps['by_extension']['h']['top200_avg_deps'],
      'ext_h_top500_avg_deps': deps['by_extension']['h']['top500_avg_deps'],
    }
    points = []
    root = '/'.join([
      'v8.infra.experimental' if self.m.runtime.is_experimental else 'v8.infra',
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
      self.build_output_dir.join(*path_pieces)
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

    if self.m.runtime.is_experimental:
      trace_prefix = ['v8.infra.experimental']
    else:
      trace_prefix = ['v8.infra']

    trace_prefix.append('binary_size')

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

  def compile(
      self, test_spec=EmptyTestSpec, mb_config_path=None, out_dir=None,
      **kwargs):
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
    use_goma = (self.m.chromium.c.compile_py.compiler and
                'goma' in self.m.chromium.c.compile_py.compiler)

    # Calculate extra targets to isolate from V8-side test specification. The
    # test_spec contains extra TestStepConfig objects for the current builder
    # and all its triggered builders.
    extra_targets = self.isolate_targets_from_tests(
        test_spec.get_all_test_names())
    isolate_targets = sorted(list(set(self.isolate_targets + extra_targets)))

    build_dir = None
    if out_dir:  # pragma: no cover
      build_dir = '//%s/%s' % (out_dir, self.m.chromium.c.build_config_fs)
    if self.m.chromium.c.project_generator.tool == 'mb':
      mb_config_rel_path = self.m.properties.get(
          'mb_config_path', 'infra/mb/mb_config.pyl')
      gn_args = self.m.chromium.run_mb(
          self.m.properties['mastername'],
          self.m.properties['buildername'],
          use_goma=use_goma,
          mb_config_path=(
              mb_config_path or
              self.m.path['checkout'].join(*mb_config_rel_path.split('/'))),
          isolated_targets=isolate_targets,
          stdout=self.m.raw_io.output_text(),
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
            step_test_data=lambda: self.test_api.example_build_dependencies(),
            ok_ret='any',
            venv=True,
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

    self.isolate_tests(isolate_targets, out_dir=out_dir)

  @property
  def depot_tools_path(self):
    """Returns path to depot_tools pinned in the V8 checkout."""
    assert 'checkout' in self.m.path, (
        "Pinned depot_tools is not available before checkout has been created")
    return self.m.path['checkout'].join('third_party', 'depot_tools')

  def _get_default_archive(self):
    return 'gs://chromium-v8/%sarchives/%s/%s' % (
        'experimental/' if self.m.runtime.is_experimental else '',
        self.m.properties['mastername'],
        self.m.properties['buildername'],
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
                   self.m.properties['buildername'])
    return 'chromium-v8/%sisolated/%s/%s' % (
        'experimental/' if self.m.runtime.is_experimental else '',
        self.m.properties['mastername'],
        buildername,
    )

  def upload_isolated_json(self):
    self.m.gsutil.upload(
        self.m.json.input(self.isolated_tests),
        self.isolated_archive_path,
        '%s.json' % self.revision,
        args=['-a', 'public-read'],
    )

  def maybe_create_clusterfuzz_archive(self, update_step):
    if self.bot_config.get('cf_archive_build', False):
      kwargs = {}
      if self.bot_config.get('cf_archive_bitness'):
        kwargs['use_legacy'] = False
        kwargs['bitness'] = self.bot_config['cf_archive_bitness']
      self.m.archive.clusterfuzz_archive(
          revision_dir='v8',
          build_dir=self.build_output_dir,
          update_properties=update_step.presentation.properties,
          gs_bucket=self.bot_config.get('cf_gs_bucket'),
          gs_acl=self.bot_config.get('cf_gs_acl'),
          archive_prefix=self.bot_config.get('cf_archive_name'),
          **kwargs
      )

  def download_build(self, name_suffix='', archive=None):
    self.m.file.rmtree('build directory' + name_suffix, self.build_output_dir)
    self.m.archive.download_and_unzip_build(
          'extract build' + name_suffix,
          self.m.chromium.c.build_config_fs,
          archive or self.m.properties.get('archive'),
          src_dir=self.checkout_root.join('v8'))

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
    return bool(self.bot_config.get('gcov_coverage_folder'))

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
    dest = '%s/%s' % (self.bot_config['gcov_coverage_folder'], self.revision)
    if self.m.runtime.is_experimental:
      dest = 'experimental/%s' % dest
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

  @property
  def is_pure_swarming_tester(self):
    return (self.bot_type == 'tester' and
            self.bot_config.get('enable_swarming', True))

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

    # Only rebuild the target of the test to retry.
    targets = [failure.failure_dict.get('target_name', 'All')]

    test = self.create_test(failure.test_step_config)
    def test_func(revision):
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
    lines.append('Variant: %s' % results[0]['variant'])
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
        # Only add the data of the first run to the final test results, as rerun
        # data is not important for bisection.
        data = results_per_command[command][0]
        failure = failure_factory(data)
        if all_same(map(lambda x: x['result'], results_per_command[command])):
          # This is a failure.
          failures.append(failure)
          failure_lines += self._command_results_text(
              results_per_command[command], False)
        else:
          # This is a flake.
          flakes.append(failure)
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
        '--buildername', self.m.properties['buildername'],
      ]

    return full_args, env

  @staticmethod
  def _copy_property(src, dest, key):
    if key in src:
      dest[key] = src[key]

  def maybe_trigger(self, test_spec=EmptyTestSpec, **additional_properties):
    triggers = self.bot_config.get('triggers', [])
    triggers_proxy = self.bot_config.get('triggers_proxy', False)
    triggered_build_ids = []
    if triggers or triggers_proxy:
      # Careful! Before adding new properties, note the following:
      # Triggered bots on CQ will either need new properties to be explicitly
      # whitelisted or their name should be prefixed with 'parent_'.
      properties = {
        'parent_got_revision': self.revision,
        'parent_buildername': self.m.properties['buildername'],
        'parent_build_config': self.m.chromium.c.BUILD_CONFIG,
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

      swarm_hashes = self.isolated_tests
      if swarm_hashes:
        properties['swarm_hashes'] = swarm_hashes
      properties.update(**additional_properties)

      if triggers:
        if self.m.tryserver.is_tryserver:
          trigger_props = {}
          self._copy_property(self.m.properties, trigger_props, 'git_revision')
          self._copy_property(self.m.properties, trigger_props, 'revision')
          trigger_props.update(properties)
          try:
            bucket_name = self.m.buildbucket.properties['build']['bucket']
          except (TypeError, KeyError) as e:
            bucket_name = 'master.%s' % self.m.properties['mastername']
          # Generate a list of fake changes from the blamelist property to have
          # correct blamelist displayed on the child build. Unfortunately, this
          # only copies author names, but additional details about the list of
          # changes associated with the build are currently not accessible from
          # the recipe code.
          step_result = self.buildbucket_trigger(
              bucket_name, self.get_changes(),
              [{
                'builder_name': builder_name,
                'properties': dict(
                    trigger_props,
                    **test_spec.as_properties_dict(builder_name)
                ),
              } for builder_name in triggers],
              # Tryserver uses custom buildset that is set by the buildbucket
              # module itself.
              no_buildset=True,
          )
          triggered_build_ids.extend(
              build['build']['id'] for build in step_result.stdout['results'])
        else:
          ci_properties = dict(properties)
          if self.should_upload_build:
            ci_properties['archive'] = self._get_default_archive()
          if self.m.runtime.is_luci:
            self.m.scheduler.emit_triggers(
                [(
                  self.m.scheduler.BuildbucketTrigger(
                    properties=dict(
                      ci_properties,
                      **test_spec.as_properties_dict(builder_name)
                    ),
                    tags={
                      'buildset': 'commit/gitiles/chromium.googlesource.com/v8/'
                                  'v8/+/%s' % ci_properties['revision']
                    }
                  ), 'v8', [builder_name],
                ) for builder_name in triggers],
                step_name='trigger'
            )
          else:
            self.m.trigger(*[{
              'builder_name': builder_name,
              # Attach additional builder-specific test-spec properties.
              'properties': dict(
                  ci_properties,
                  **test_spec.as_properties_dict(builder_name)
              ),
            } for builder_name in triggers])

      if triggers_proxy and not self.m.runtime.is_experimental:
        proxy_properties = {'archive': self._get_default_archive()}
        proxy_properties.update(properties)
        self.buildbucket_trigger(
            'luci.v8-internal.ci', self.get_changes(),
            [{
              'properties': proxy_properties,
              'builder_name': 'v8_trigger_proxy'
            }],
            step_name='trigger_internal'
        )

    if triggered_build_ids:
      output_properties = self.m.step.active_result.presentation.properties
      output_properties['triggered_build_ids'] = triggered_build_ids

  def get_changes(self):
    # TODO(sergiyb): Remove this after migrating all builders to LUCI as
    # there the revision from the buildset will be used instead.
    blamelist = self.m.properties.get('blamelist', ['fake-author'])
    return [{'author': email} for email in blamelist]

  def buildbucket_trigger(self, bucket, changes, requests, step_name='trigger',
                          service_account='v8-bot', no_buildset=False):
    """Triggers builds via buildbucket.

    Args:
      bucket: Name of the bucket to add builds to.
      changes: List of changes to be associated with the scheduled build. Each
          entry is a dictionary like this: {'author': ..., 'revision': ...}. The
          revision is optional and will be extracted from build propeties if not
          provided. The author is an arbitrary string or an email address.
      requests: List of requests, where each request is a dictionary like this:
          {'builder_name': ..., 'properties': {'revision': ..., ...}}. Note that
          builder_name and revision are mandatory, whereas additional properties
          are optional.
      step_name: Name of the triggering step that appear on the build.
      service_account: Puppet service account to be used for authentication to
          buildbucket.
      no_buildset: Disable setting custom buildset. Useful when one needs to
          rely on the built-in buildset set by the buildbucket module, e.g. on
          tryserver.
    """
    # TODO(sergiyb): Remove this line after migrating all builders to swarming.
    # There an implicit task account (specified in the cr-buildbucket.cfg) will
    # be used instead.
    if not self.m.runtime.is_luci:
      self.m.buildbucket.use_service_account_key(
          self.m.puppet_service_account.get_key_path(service_account))

    step_result = self.m.buildbucket.put(
        [{
          'bucket': bucket,
          'tags': {} if no_buildset else {
            'buildset': 'commit/gitiles/chromium.googlesource.com/v8/v8/+/%s' %
               request['properties']['revision']
          },
          'parameters': {
            'builder_name': request['builder_name'],
            'properties': request['properties'],
            # This is required by Buildbot to correctly set 'revision' and
            # 'repository' properties, which are used by Milo and the recipe.
            # TODO(sergiyb): Remove this after migrating to LUCI/Swarming.
            'changes': [{
              'author': {'email': change['author']},
              'revision': change.get(
                'revision', request['properties']['revision']),
              'repo_url': 'https://chromium.googlesource.com/v8/v8'
            } for change in changes],
          },
        } for request in requests],
        name=step_name,
        step_test_data=lambda: (
          self.m.v8.test_api.buildbucket_test_data(len(requests))),
    )

    if 'error' in step_result.stdout:
      step_result.presentation.status = self.m.step.FAILURE

    return step_result

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
            'builder': self.m.properties['buildername'],
            'buildNum': self.m.properties['buildnumber'],
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
