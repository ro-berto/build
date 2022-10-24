# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import ast
import contextlib
import re

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

from recipe_engine import recipe_api
from . import bisection

from RECIPE_MODULES.build import chromium

MILO_HOST = 'luci-milo.appspot.com'
V8_URL = 'https://chromium.googlesource.com/v8/v8'

COMMIT_TEMPLATE = '%s/+/%%s' % V8_URL

# Regular expressions for v8 branch names.
RELEASE_BRANCH_RE = re.compile(r'^refs/branch-heads/\d+\.\d+$')

# Regular expressions for getting target bits from gn args.
TARGET_CPU_RE = re.compile(r'.*target_cpu\s+=\s+"([^"]*)".*')

# Factor by which the considered failure for bisection must be faster than the
# ongoing build's total.
BISECT_DURATION_FACTOR = 5

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

  def __str__(self):
    patch_str = '.%s' % self.patch if self.patch and self.patch != '0' else ''
    return f'{self.major}.{self.minor}.{self.build}{patch_str}'

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

  def with_incremented_minor(self):
    new_minor = int(self.minor) + 1
    new_major = int(self.major)
    if new_minor == 10:
      new_minor = 0
      new_major += 1
    return V8Version(str(new_major), str(new_minor), 0, 0)

class Trigger(object):
  def __init__(self, api):
    self.api = api


  def buildbucket(self, requests, project, bucket, step_name):
    """Triggers builds via buildbucket.

    Args:
      requests: List of 2-tuples (builder_name, properties).
      project: Project to trigger builds in (defaults to same as parent).
      bucket: Bucket to trigger builds in (defaults to same as parent).
      step_name: Name of the triggering step that appear on the build.

    Returns:
      List of api.buildbucket.build_pb2.Build messages.
    """
    raise NotImplementedError()  # pragma: no cover

  def scheduler(self, builders, properties, test_spec):
    """Triggers builds via scheduler. Typically used by CI builders.

    Args:
      builders: List of builder names to trigger.
      properties: Properties common for every builder.
      test_spec: Test specification object with configurations per builder.
    """
    raise NotImplementedError()  # pragma: no cover

class ProdTrigger(Trigger):
  def buildbucket(self, requests, project=None, bucket=None,
                  step_name='trigger'):
    project = project or self.api.buildbucket.INHERIT
    bucket = bucket or self.api.buildbucket.INHERIT

    # Add user_agent:cq to child builds if the parent is also triggered by CQ.
    extra_tags = {}
    if any(tag.key == 'user_agent' and tag.value == 'cq'
           for tag in self.api.buildbucket.build.tags):
      extra_tags['user_agent'] = 'cq'

    return self.api.buildbucket.schedule([
      self.api.buildbucket.schedule_request(
        project=project,
        bucket=bucket,
        builder=builder_name,
        tags=self.api.buildbucket.tags(**extra_tags),
        properties=properties,
      ) for builder_name, properties in requests
    ], step_name=step_name)

  def scheduler(self, builders, properties, test_spec):
    with self.api.step.nest('trigger'):
      jobs = self._get_v8_jobs()
      pairs = self._builder_job_pairs(builders, jobs)
      scheduler_triggers = [(self._scheduler_trigger(builder_name,
                                                     properties,
                                                     test_spec), 'v8', [job_id])
                            for builder_name, job_id in pairs]
      self.api.scheduler.emit_triggers(scheduler_triggers, step_name='trigger')

  def _scheduler_trigger(self, builder_name, ci_properties, test_spec):
    return self.api.scheduler.BuildbucketTrigger(
        properties=dict(ci_properties,
                        **test_spec.as_properties_dict(builder_name)),
    )

  def _builder_job_pairs(self, builders, jobs):
    result = []
    for builder in builders:
      if builder in jobs:
        job = builder
      else:
        bucket = self.api.buildbucket.build.builder.bucket
        job = f'{bucket}-{builder}'
      result.append((builder, job))
    return result

  def _get_v8_jobs(self):
    args = [
        'prpc', 'call', '-format=json', 'luci-scheduler.appspot.com',
        'scheduler.Scheduler.GetJobs'
    ]
    input_data = {"project": "v8"}
    jobs_file = self.api.path['tmp_base'].join('jobs.json')
    self.api.step(
        "get V8 jobs",
        args,
        stdin=self.api.json.input(input_data),
        stdout=self.api.json.output(leak_to=jobs_file),
    )
    response = self.api.json.read(
        "read jobs json",
        jobs_file,
        step_test_data=lambda: self.api.json.test_api.output({'jobs': []})
    ).json.output
    return set(job['jobRef']['job'] for job in response['jobs'])


class LedTrigger(Trigger):
  def buildbucket(self, requests, project='v8', bucket=None,
                  step_name=None):
    bucket = bucket or self.api.buildbucket.build.builder.bucket
    for builder_name, properties in requests:
      self.api.led.trigger_builder(project, bucket, builder_name, properties)
    return []  # Empty list of production buildbucket builds.

  def scheduler(self, builders, properties, test_spec):
    bucket = self.api.buildbucket.build.builder.bucket
    for builder_name in builders:
      self.api.led.trigger_builder(
          'v8',
          bucket,
          builder_name,
          dict(properties, **test_spec.as_properties_dict(builder_name)),
      )


class V8Api(recipe_api.RecipeApi):
  VERSION_FILE = 'include/v8-version.h'

  def __init__(self, properties, *args, **kwargs):
    super(V8Api, self).__init__(*args, **kwargs)
    self.bot_config = None
    self.checkout_root = None
    self.revision = None
    self.revision_cp = None
    self.revision_number = None
    self.use_remoteexec = properties.get('use_remoteexec', False)

  # TODO(machenbach): Temporary convenience method to update recipe
  # dependencies.
  def update_test_configs(self, *args, **kwargs):  # pragma: no cover
    return self.m.v8_tests.update_test_configs(*args, **kwargs)

  # TODO(machenbach): Temporary convenience method to update recipe
  # dependencies.
  @property
  def TEST_SPEC(self):  # pragma: no cover
    return self.m.v8_tests.TEST_SPEC

  # TODO(machenbach): Temporary convenience method to update recipe
  # dependencies.
  @property
  def isolated_tests(self):  # pragma: no cover
    return self.m.v8_tests.isolated_tests

  @property
  def trigger(self):
    if self.m.led.launched_by_led:
      return LedTrigger(self.m)
    else:
      return ProdTrigger(self.m)

  @property
  def trigger_prod(self):
    return ProdTrigger(self.m)

  def _python(self, name, exe, script, args, **kwargs):
    cmd = [exe, '-u', script] + list(args or [])
    return self.m.step(name, cmd, **kwargs)

  def python(self, name, script, args=None, **kwargs):
    return self._python(name, 'python3', script, args, **kwargs)

  def vpython(self, name, script, args=None, **kwargs):
    return self._python(name, 'vpython3', script, args, **kwargs)

  def bot_config_by_buildername(self,
                                builders=None,
                                use_goma=True):
    default = {}
    assert not use_goma or not self.use_remoteexec
    if not self.m.properties.get('parent_buildername'):
      # Builders and builder_testers both build and need the following set of
      # default chromium configs:
      if use_goma:
        default['chromium_apply_config'] = [
            'default_compiler', 'goma', 'mb', 'mb_no_luci_auth'
        ]
      else:
        default['chromium_apply_config'] = [
            'default_compiler', 'mb', 'mb_no_luci_auth'
        ]
      if self.use_remoteexec:
        default['gclient_apply_config'] = [
            'enable_reclient',
        ]
    return (builders or {}).get(self.m.buildbucket.builder_name, default)

  def update_bot_config(self, bot_config, binary_size_tracking,
                        clusterfuzz_archive, coverage, enable_swarming,
                        target_arch, target_platform, track_build_dependencies,
                        triggers, triggers_proxy):
    """Update bot_config dict with src-side properties.

    Args:
      bot_config: The bot_config dict to update.
      binary_size_tracking: Additional configurations to enable binary size
          tracking.
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
          f'read test config ({self.m.path.basename(root)})',
          test_config_path,
          test_data='{}',
      ))
    except SyntaxError as e:  # pragma: no cover
      raise self.m.step.InfraFailure(
          f'Failed to parse test config "{test_config_path}": {e}')

    for test_config in test_configs.values():
      # This configures the test runner to set the test root to the
      # test_checkout location for all tests from this checkout.
      # TODO(machenbach): This is starting to get hacky. The test config
      # dicts should be refactored into classes similar to test specs. Maybe
      # the extra configurations from test configs could be added to test
      # specs.
      test_config['test_root'] = str(root.join('test'))

    return test_configs

  def _configure_clusterfuzz_builders(self):
    if self.bot_config.get('clusterfuzz_archive'):
      self.m.chromium.apply_config('default_target_v8_clusterfuzz')

  def _configure_perf_builders(self):
    if self.m.builder_group.for_current == 'client.v8.perf':
      self.m.chromium.apply_config('default_target_d8')

  def apply_bot_config(self, bot_config):
    """Entry method for using the v8 api."""
    self.bot_config = bot_config

    kwargs = {}
    kwargs.update(self.bot_config.get('v8_config_kwargs', {}))

    self.set_config('v8', optional=True, **kwargs)
    self.m.v8_tests.set_config('v8')
    self.m.chromium.set_config('v8', **kwargs)
    self.m.gclient.set_config('v8', **kwargs)

    if self.m.chromium.c.TARGET_PLATFORM in ['android', 'fuchsia']:
      self.m.gclient.apply_config(self.m.chromium.c.TARGET_PLATFORM)

    if self.m.chromium.c.TARGET_PLATFORM == 'ios':
      self.m.gclient.apply_config('v8_ios')

    for c in self.bot_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)

    for c in self.bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)

    self._configure_clusterfuzz_builders()
    self._configure_perf_builders()

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

    self.m.v8_tests.enable_swarming = self.bot_config.get(
        'enable_swarming', True)

  def set_gclient_custom_vars(self, gclient_vars):
    """Sets additional gclient custom variables."""
    for key, value in (gclient_vars or {}).items():
      self.m.gclient.c.solutions[0].custom_vars[key] = value

  def set_gclient_custom_deps(self, custom_deps):
    """Configures additional gclient custom_deps to be synced."""
    for name, path in (custom_deps or {}).items():
      self.m.gclient.c.solutions[0].custom_deps[name] = path

  def set_chromium_configs(self, clobber, default_targets):
    if clobber:
      self.m.chromium.c.clobber_before_runhooks = clobber
    if default_targets:
      self.m.chromium.c.compile_py.default_targets = default_targets

  def checkout(self, revision=None, **kwargs):
    # Set revision for bot_update.
    revision = revision or self.m.buildbucket.gitiles_commit.id or 'HEAD'
    solution = self.m.gclient.c.solutions[0]
    branch = self.m.buildbucket.gitiles_commit.ref
    if RELEASE_BRANCH_RE.match(branch):
      revision = f'{branch}:{revision}'
    solution.revision = revision

    self.checkout_root = self.m.path['cache'].join('builder')
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

  def runhooks(self, **kwargs):
    if (self.m.chromium.c.compile_py.compiler and
        self.m.chromium.c.compile_py.compiler.startswith('goma')):
      # Only ensure goma if we want to use it. Otherwise it might break bots
      # that don't support the goma executables.
      self.m.chromium.ensure_goma()
    self.m.chromium.runhooks(**kwargs)

  # TODO(https://crbug.com/890222): Deprecate this mapping after migration to
  # orchestrator + 4 milestones (2023/Q3).
  def normalized_builder_name(self, triggered):
    """Map given builder names from infra/config to names used for look-ups
    in source configurations.

    This maps a generated experimental trybot to the corresponding parent/child
    names.

    This maps compilator builder names to legacy names to ease the roll-out and
    for backwards-compatibility on release branches.
    """
    builder_name = self.m.buildbucket.builder_name
    triggered_suffix = '_triggered' if triggered else ''
    if builder_name.endswith('_exp'):
      builder_name = builder_name.replace('_exp', '_ng' + triggered_suffix)
    if self.m.properties['recipe'] == 'v8/compilator':
      if builder_name.endswith('_compile_rel'):
        builder_name = builder_name.replace(
            '_compile_rel', '_rel_ng' + triggered_suffix)
      if builder_name.endswith('_compile_dbg'):
        builder_name = builder_name.replace(
            '_compile_dbg', '_dbg_ng' + triggered_suffix)
    return builder_name

  @property
  def bot_type(self):
    if self.bot_config.get('triggers') or self.bot_config.get('triggers_proxy'):
      return 'builder'
    if self.m.properties.get('parent_buildername'):
      return 'tester'
    return 'builder_tester'

  @property
  def builderset(self):
    """
    Returns a list of names of this builder and all its triggered testers.
    It also converts the name of experimental builders to fit the naming
    convention.
    """
    return (
        [self.normalized_builder_name(triggered=True)] +
        list(self.bot_config.get('triggers', []))
    )

  @property
  def should_build(self):
    return self.bot_type in ['builder', 'builder_tester']

  @property
  def should_test(self):
    return self.bot_type in ['tester', 'builder_tester']

  def extra_tests_from_test_spec(self, test_spec):
    """Returns runnable testing.BaseTest objects for each extra test specified
    in the test spec of the current builder. Note that it converts experimental
    builders name in order to fit the naming convention.
    """
    return [
      self.m.v8_tests.create_test(test)
      for test in test_spec.get_tests(
          self.normalized_builder_name(triggered=True))
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
      return self.m.v8_tests.EMPTY_TEST_SPEC

    try:
      # Eval python literal file.
      full_test_spec = ast.literal_eval(self.m.file.read_text(
          f'read test spec ({self.m.path.basename(root)})',
          test_spec_file,
          test_data='{}',
      ))
    except SyntaxError as e:  # pragma: no cover
      raise self.m.step.InfraFailure(
          f'Failed to parse test specification "{test_spec_file}": {e}')

    # Transform into object.
    test_spec = self.m.v8_tests.TEST_SPEC.from_python_literal(
        full_test_spec, self.builderset)

    # Log test spec for debuggability.
    self.m.step.active_result.presentation.logs['test_spec'] = (
        test_spec.log_lines())

    return test_spec

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
      self.m.isolate.isolate_tests(
          output_dir,
          targets=['perf'],
          verbose=True,
          swarm_hashes_property_name=None,
          step_name='isolate tests (perf)',
      )
      self.m.v8_tests.isolated_tests.update(self.m.isolate.isolated_tests)
    elif isolate_targets:
      self.m.isolate.isolate_tests(
          output_dir,
          targets=isolate_targets,
          verbose=True,
          swarm_hashes_property_name=None,
      )
      self.m.v8_tests.isolated_tests.update(self.m.isolate.isolated_tests)

      if self.m.v8_tests.isolated_tests:
        self.upload_isolated_json()

  def _filtered_gn_args(self, gn_args):
    return [
      l for l in gn_args.splitlines()
      if not l.startswith('goma_dir')
    ]

  @property
  def target_bits(self):
    """Returns target bits (as int) inferred from gn arguments from MB."""
    for arg in self.m.v8_tests.gn_args:
      match = TARGET_CPU_RE.match(arg)
      if match:
        return 64 if '64' in match.group(1) else 32
    # If target_cpu is not set, gn defaults to 64 bits.
    return 64  # pragma: no cover

  @contextlib.contextmanager
  def ensure_osx_sdk_if_needed(self):
    """Ensures the sdk is installed for wrapped steps when building for ios.

    When building for mac we use the src-side hermetic toolchain.
    """
    if self.m.chromium.c.TARGET_PLATFORM == 'ios':
      with self.m.osx_sdk('ios'):
        yield
    else:
      yield

  def _upload_build_dependencies(self, deps):
    values = {
      'ext_h_avg_deps': deps['by_extension']['h']['avg_deps'],
      'ext_h_top100_avg_deps': deps['by_extension']['h']['top100_avg_deps'],
      'ext_h_top200_avg_deps': deps['by_extension']['h']['top200_avg_deps'],
      'ext_h_top500_avg_deps': deps['by_extension']['h']['top500_avg_deps'],
    }
    points = []
    root = '/'.join(['v8.infra', 'build_dependencies', ''])
    for k, v in sorted(values.items()):
      p = self.m.perf_dashboard.get_skeleton_point(
          root + k, self.revision_number, str(v))
      p['units'] = 'count'
      p['supplemental_columns'] = {
        'a_default_rev': 'r_v8_git',
        'r_v8_git': self.revision,
      }
      points.append(p)
    if points:
      self.m.perf_dashboard.add_point(points, halt_on_failure=True)

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
    self.m.perf_dashboard.add_point([point], halt_on_failure=True)

  def get_builder_id(self):
    builder_group = self.m.builder_group.for_current
    buildername = self.normalized_builder_name(triggered=False)
    return chromium.BuilderId.create_for_group(builder_group, buildername)

  # TODO(b:238274944): Remove this method after all builders have switched
  # to reclient and the corresponding mb_config.pyl change has reached
  # extended stable. Estimated after M110.
  def reclient_mb_override(self, mb_config_path):
    """Temporary override of mb_config.pyl until reclient migration is
    complete.

    This replaces goma=true gn args in mb_config.pyl for the current run
    and overrides with reclient settings. This allows to switch MB-based
    settings for goma/reclient via a module property in $build/v8 called
    "use_remoteexec".

    This can be removed once the main mb_conig.pyl file was updated and the
    changes made it to all active release branches.
    """
    if not self.use_remoteexec:
      return mb_config_path

    mb_config_data = self.m.file.read_text(
        'read MB config',
        mb_config_path,
        test_data=self.test_api.example_goma_mb_config(),
    )

    mb_config_data = mb_config_data.replace(
        'use_goma=true', 'use_goma=false use_remoteexec=true')

    new_mb_config_path = self.m.path['tmp_base'].join('mb_config.pyl')
    self.m.file.write_text(
        'tweak MB config',
        new_mb_config_path,
        mb_config_data,
    )
    return new_mb_config_path

  def compile(
      self, test_spec=None, mb_config_path=None,
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

    Returns:
      if there is a compile failure:
        RawResult object with compile step status and failure message
      else:
        None
    """
    with self.ensure_osx_sdk_if_needed():
      use_goma = (self.m.chromium.c.compile_py.compiler and
                  'goma' in self.m.chromium.c.compile_py.compiler)

      # Calculate targets to isolate from V8-side test specification. The
      # test_spec contains extra TestStepConfig objects for the current builder
      # and all its triggered builders.
      isolate_targets = self.m.v8_tests.isolate_targets_from_tests(test_spec)

      # Add the performance-tests isolate everywhere, where the perf-bot proxy
      # is triggered.
      if self.bot_config.get('triggers_proxy', False):
        isolate_targets = isolate_targets + ['perf']

      # Sort and dedupe.
      isolate_targets = sorted(list(set(isolate_targets)))

      build_dir = None
      if out_dir:  # pragma: no cover
        build_dir = f'//{out_dir}/{self.m.chromium.c.build_config_fs}'
      if self.m.chromium.c.project_generator.tool == 'mb':
        mb_config_rel_path = self.m.properties.get(
            'mb_config_path', 'infra/mb/mb_config.pyl')

        mb_config_path = (
            mb_config_path or
            self.m.path['checkout'].join(*mb_config_rel_path.split('/')))
        mb_config_path = self.reclient_mb_override(mb_config_path)

        gn_args = self.m.chromium.mb_gen(
            self.get_builder_id(),
            use_goma=use_goma,
            mb_config_path=mb_config_path,
            isolated_targets=isolate_targets,
            build_dir=build_dir,
            gn_args_location=self.m.gn.LOGS)

        # Update the gn args, which are printed to the user on test failures
        # for easier build reproduction.
        self.m.v8_tests.gn_args = self._filtered_gn_args(gn_args)

        # Create logs surfacing GN arguments. This information is critical to
        # developers for reproducing failures locally.
        presentation = self.m.step.active_result.presentation
        presentation.logs['gn_args'] = self.m.v8_tests.gn_args
      elif self.m.chromium.c.project_generator.tool == 'gn':
        self.m.chromium.run_gn(
            use_goma=use_goma, build_dir=build_dir,
            use_reclient=self.use_remoteexec)

      if use_goma and not self.use_remoteexec:
        kwargs['use_goma_module'] = True
      raw_result = self.m.chromium.compile(
          out_dir=out_dir, use_reclient=self.use_remoteexec, **kwargs)
      if raw_result.status != common_pb.SUCCESS:
        return raw_result

      self.isolate_tests(isolate_targets, out_dir=out_dir)

  @property
  def should_collect_post_compile_metrics(self):
    return (
        not self.is_pure_swarming_tester and self.should_build and (
            self.m.v8.bot_config.get('track_build_dependencies') or
            self.m.v8.bot_config.get('binary_size_tracking')))

  def collect_post_compile_metrics(self):
    with self.ensure_osx_sdk_if_needed():
      if self.bot_config.get('track_build_dependencies',
                             False) and not self._is_muted_branch():
        with self.m.context(env_prefixes={'PATH': [self.depot_tools_path]}):
          deps = self.vpython(
              name='track build dependencies (fyi)',
              script=self.resource('build-dep-stats.py'),
              args=[
                '-C', self.build_output_dir,
                '-x', '/third_party/',
                '-o', self.m.json.output(),
              ],
              step_test_data=self.test_api.example_build_dependencies,
              ok_ret='any',
          ).json.output
        if deps:
          self._upload_build_dependencies(deps)

      # Track binary size if specified.
      tracking_config = self.bot_config.get('binary_size_tracking', {})
      if tracking_config and not self._is_muted_branch():
        self._track_binary_size(
          tracking_config['binary'],
          tracking_config['category'],
        )

  def _is_muted_branch(self):
    return self.m.buildbucket.build.builder.bucket not in ['ci', 'try']

  @property
  def depot_tools_path(self):
    """Returns path to depot_tools pinned in the V8 checkout."""
    assert 'checkout' in self.m.path, (
        "Pinned depot_tools is not available before checkout has been created")
    return self.m.path['checkout'].join('third_party', 'depot_tools')

  def _get_default_archive(self):
    return 'gs://chromium-v8/archives/%s/%s' % (
        self.m.builder_group.for_current,
        self.m.buildbucket.builder_name,
    )

  @property
  def isolated_archive_path(self):
    buildername = (self.m.properties.get('parent_buildername') or
                   self.m.buildbucket.builder_name)
    return 'chromium-v8/isolated/%s/%s' % (self.m.builder_group.for_current,
                                           buildername)

  def upload_isolated_json(self):
    self.m.gsutil.upload(
        self.m.json.input(self.m.v8_tests.isolated_tests),
        self.isolated_archive_path,
        f'{self.revision}.json',
        args=['-a', 'public-read'],
    )

  def get_build_type(self):
    """Returns the given build type: 'debug' if gn args is_debug or
    dcheck_always_on are set, 'release' otherwise.
    """
    build_config_path = self.build_output_dir.join('v8_build_config.json')
    build_config = self.m.json.read(
      'read build config', build_config_path,
      step_test_data=self.test_api.example_build_config).json.output
    debug = build_config['is_debug'] or build_config['dcheck_always_on']
    return 'debug' if debug else 'release'

  def maybe_create_clusterfuzz_archive(self, update_step):
    clusterfuzz_archive = self.bot_config.get('clusterfuzz_archive')
    if clusterfuzz_archive:
      kwargs = {}
      if clusterfuzz_archive.get('bitness'):
        kwargs['use_legacy'] = False
        kwargs['bitness'] = clusterfuzz_archive['bitness']
      self.m.archive.clusterfuzz_archive(
          revision_dir='v8',
          build_config=self.get_build_type(),
          build_dir=self.build_output_dir,
          update_properties=update_step.presentation.properties,
          gs_bucket=clusterfuzz_archive.get('bucket'),
          gs_acl='public-read',
          archive_prefix=clusterfuzz_archive.get('name'),
          **kwargs
      )

  def download_isolated_json(self, revision):
    archive = 'gs://' + self.isolated_archive_path + f'/{revision}.json'
    self.m.gsutil.download_url(
        archive,
        self.m.json.output(),
        name='download isolated json',
        step_test_data=lambda: self.m.json.test_api.output(
            {'bot_default': '[dummy hash for bisection]/123'}),
    )
    step_result = self.m.step.active_result
    self.m.v8_tests.isolated_tests = step_result.json.output

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
          '/usr/*',
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
    if self.m.tryserver.is_tryserver:
      dest = 'tryserver/%s%d_gcov_rel/%d/%d' % (
          self.m.platform.name,
          self.target_bits,
          self.m.tryserver.gerrit_change_number,
          self.m.tryserver.gerrit_patchset_number,
      )
    else:
      dest = '%s%d_gcov_rel/%s' % (
          self.m.platform.name,
          self.target_bits,
          self.revision,
      )

    result = self.m.gsutil(
        [
          '-m', 'cp', '-a', 'public-read', '-R', report_dir,
          f'gs://chromium-v8/{dest}',
        ],
        'coverage report',
    )
    result.presentation.links['report'] = (
      f'https://storage.googleapis.com/chromium-v8/{dest}/index.html')

  @property
  def is_pure_swarming_tester(self):
    return (self.bot_type == 'tester' and
            self.bot_config.get('enable_swarming', True))

  def maybe_bisect(self, test_results, test_spec):
    """Build-local bisection for one failure."""
    if (self.bot_config.get('disable_auto_bisect') or
        self.m.properties.get('disable_auto_bisect')):
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
    if (failure.duration * duration_factor >
        self.m.v8_tests.test_duration_sec):
      step_result = self.m.step(
          'Bisection disabled - test too slow', cmd=None)
      return

    # Don't retry failures during bisection.
    self.m.v8_tests.rerun_failures_count = 0

    # Suppress using shards to be able to rerun single tests.
    self.m.v8_tests.c.testing.may_shard = False

    test = self.m.v8_tests.create_test(failure.test_step_config)
    def test_func(_):
      return test.rerun(failure_dict=failure.failure_dict)

    def is_bad(revision):
      with self.m.step.nest('Bisect ' + revision[:8]):
        if not self.is_pure_swarming_tester:
          self.checkout(revision, update_presentation=False)
        if self.bot_type == 'builder_tester':
          # TODO(machenbach): Only compile on demand. We could first check if
          # download_isolated_json already provides isolated targets for this
          # revision. Only compile if not.
          self.runhooks()
          compile_failure = self.compile(test_spec)
          if compile_failure:
            # TODO: Consider changing control flow
            # to handle returning of compile failures
            raise self.m.step.StepFailure(compile_failure.summary_markdown)
        elif self.bot_type == 'tester':
          if test.uses_swarming:
            self.download_isolated_json(revision)
          else:  # pragma: no cover
            raise self.m.step.InfraFailure('Swarming required for bisect.')
        else:  # pragma: no cover
          raise self.m.step.InfraFailure(
              f'Bot type {self.bot_type} not supported.')
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
  def _copy_property(src, dest, key):
    if key in src:
      dest[key] = src[key]

  def maybe_trigger(self, test_spec=None, **additional_properties):
    test_spec = test_spec or self.m.v8_tests.EMPTY_TEST_SPEC
    triggers = self.bot_config.get('triggers', [])
    triggers_proxy = self.bot_config.get('triggers_proxy', False)
    if not triggers and not triggers_proxy:
      return

    properties = {
      'parent_got_revision': self.revision,
      'parent_buildername': self.m.buildbucket.builder_name,
      'parent_build': self.m.buildbucket.build_url(),
      'parent_gn_args': self.m.v8_tests.gn_args,
    }
    if self.m.scheduler.triggers:
      sched_trs = self.m.scheduler.triggers
      if sched_trs[0].HasField('gitiles'):
        properties['oldest_gitiles_revision'] = sched_trs[0].gitiles.revision
      if sched_trs[-1].HasField('gitiles'):
        properties['newest_gitiles_revision'] = sched_trs[-1].gitiles.revision
    if self.revision_cp:
      properties['parent_got_revision_cp'] = self.revision_cp
    if self.m.tryserver.is_tryserver:
      properties.update(
        category=self.m.properties.get('category', 'manual_ts'),
        disable_auto_bisect=True,
        reason=str(self.m.properties.get('reason', 'ManualTS')),
        # On tryservers, set revision to the same as on the current bot, as it
        # is used to generate buildset tag in buildbucket_trigger below.
        revision=self.m.buildbucket.gitiles_commit.id or 'HEAD',
        patch_gerrit_url=f'https://{self.m.tryserver.gerrit_change.host}',
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

    swarm_hashes = self.m.v8_tests.isolated_tests
    if swarm_hashes:
      properties['swarm_hashes'] = swarm_hashes
    properties.update(**additional_properties)

    if triggers:
      if self.m.tryserver.is_tryserver:
        trigger_props = {}
        self._copy_property(self.m.properties, trigger_props, 'revision')
        trigger_props.update(properties)
        self.m.cq.record_triggered_builds(*self.trigger.buildbucket(
            [(builder_name,
              dict(
                  trigger_props,
                  **test_spec.as_properties_dict(builder_name),
              )) for builder_name in triggers],
            bucket='try.triggered',
        ))
      else:
        ci_properties = dict(properties)
        #TODO(liviurau): rename or remove this property
        if self.bot_config.get('triggers_proxy'):
          ci_properties['archive'] = self._get_default_archive()
        self.trigger.scheduler(triggers, ci_properties, test_spec)

    if triggers_proxy:
      proxy_properties = {'archive': self._get_default_archive()}
      proxy_properties.update(properties)
      self.trigger.buildbucket(
          [('v8_trigger_proxy', proxy_properties)],
          project='v8-internal',
          bucket='ci',
          step_name='trigger_internal')

  def get_change_range(self):
    if self.m.properties.get('override_triggers'):
      # This can be used for manual testing or on a staging builder that
      # simulates a change range.
      triggers = self.m.properties['override_triggers']
      step_result = self.m.step('Override triggers', cmd=None)
      step_result.presentation.logs['triggers'] = self.m.json.dumps(
        triggers, indent=2).splitlines()
      oldest_change = triggers[0]
      newest_change = triggers[-1]
    else:
      oldest_trigger = self.m.scheduler.triggers[0]
      if oldest_trigger.HasField('gitiles'):
        # This is a builder and has gitiles triggers with revision ranges.
        oldest_change = oldest_trigger.gitiles.revision
      else:
        # This is a tester and we pass down revision ranges from the parent
        # builder via buildbucket trigger properties.
        assert oldest_trigger.HasField('buildbucket')
        oldest_change = oldest_trigger.buildbucket.properties[
            'oldest_gitiles_revision']

      newest_trigger = self.m.scheduler.triggers[-1]
      if newest_trigger.HasField('gitiles'):
        newest_change = newest_trigger.gitiles.revision
      else:
        assert newest_trigger.HasField('buildbucket')
        newest_change = newest_trigger.buildbucket.properties[
            'newest_gitiles_revision']

    # Commits is a list of gitiles commit dicts in reverse chronological order.
    commits, _ = self.m.gitiles.log(
        url=V8_URL,
        ref=f'{oldest_change}~2..{newest_change}',
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
    archive_url_pattern = f'gs://{self.isolated_archive_path}/%s.json'
    # TODO(machenbach): Maybe parallelize this in a wrapper script.
    args = ['ls']
    available_range = []
    # Check all builds except the last as we already know it is "bad".
    for r in bisect_range[:-1]:
      step_result = self.m.gsutil(
          args + [archive_url_pattern % r],
          name=f'check build {r[:8]}',
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
      text = f'Suspecting {culprit_range[0][:8]}'

    step_result = self.m.step(text, cmd=None)
    for culprit in culprit_range:
      step_result.presentation.links[culprit[:8]] = COMMIT_TEMPLATE % culprit

  def read_version_file(self, ref, step_name_desc):
    """Read and return the version-file content at a paricular ref."""
    with self.m.context(cwd=self.m.path['checkout']):
      return self.m.git(
          'show', f'{ref}:{self.VERSION_FILE}',
          name=f'Check {step_name_desc} version file',
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

  def latest_branches(self):
    branch_step = self.m.git(
        'branch',
        '-r',
        '--list',
        'branch-heads/*',
        stdout=self.m.raw_io.output_text(),
        name='last branches')
    output = branch_step.stdout
    branch_step.presentation.logs['stdout'] = output.splitlines()
    branch_pattern = re.compile(r"branch-heads/(\d+)\.(\d+)")
    versions = []
    for line in output.splitlines():
      m = branch_pattern.match(line.strip())
      if m:
        versions.append(int(m.group(1)) * 10 + int(m.group(2)))
    versions.sort()
    versions.reverse()
    return versions

  def git_output(self, *args, **kwargs):
    """Convenience wrapper."""
    step_result = self.m.git(
        *args, stdout=self.m.raw_io.output_text(), **kwargs)
    result = step_result.stdout
    step_result.presentation.logs['stdout'] = result.splitlines()
    return result.strip()

  def update_version_cl(self, ref, latest_version, push_account,
      bot_commit=False, extra_edits=None):
    """Update the version on branch 'ref'.

      Args:
        api: The recipe api.
        ref: Ref name where to change the version, e.g.
            refs/remotes/branch-heads/1.2.
        latest_version: The currently latest version to be updated in the
        version file.
        push_account: Account to be used for uploading the CL
        bot_commit: Use True to allow a bot commit. This also force lands
            the CL
        extra_edits: Callback used to edit extra files before generating the CL
      """
    self.m.git('branch', '-D', 'work', ok_ret='any')
    self.m.git('clean', '-ffd')

    # Create a fresh work branch.
    self.m.git('new-branch', 'work', '--upstream', ref)
    self.m.git(
        'config',
        'user.name',
        'V8 Autoroll',
        name='git config user.name',
    )
    self.m.git(
        'config',
        'user.email',
        push_account,
        name='git config user.email',
    )

    latest_version_file = self.read_version_file(ref, 'latest')
    latest_version_file = latest_version.update_version_file_blob(
        latest_version_file)

    # Write file to disk.
    self.m.file.write_text(
        'Increment version',
        self.m.path['checkout'].join(self.m.v8.VERSION_FILE),
        latest_version_file,
    )

    if extra_edits:
      extra_edits(self.m)

    # Commit and push changes.
    self.m.git('commit', '-am', f'Version {latest_version}')

    if self.m.properties.get('dry_run') or self.m.runtime.is_experimental:
      self.m.step('Dry-run commit', cmd=None)
    else:
      upload_cmd = ['cl', 'upload', '-f', '--bypass-hooks', '--send-mail',
          '--no-autocc']
      if bot_commit:
        upload_cmd.append('--set-bot-commit')
      self.m.git(*upload_cmd)
      if bot_commit:
        self.m.git('cl', 'land', '-f', '--bypass-hooks')


  def version_num2str(self, version_number):
    """Transforms a version number to a string formated version number
    (i.e. 102  to '10.2')
    """
    return '%s.%s' % divmod(version_number, 10)
