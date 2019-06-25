# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import copy
import datetime
import functools
import hashlib
import os.path

from recipe_engine import recipe_api
from recipe_engine import util as recipe_util

# Minimally supported version of swarming.py script (reported by --version).
MINIMAL_SWARMING_VERSION = (0, 8, 6)

# The IMPLIED_*_BINARIES will be installed to the swarming task at this local
# path.
IMPLIED_BINARY_PATH = '.swarming_module'

# This is the name and path for the cache used for the implied binaries
# (specifically vpython). The name of the implied cache will be prepended with
# IMPLIED_CACHE_NAME, and the path will be relative to IMPLIED_CACHE_BASE.
IMPLIED_CACHE_NAME = 'swarming_module_cache'
IMPLIED_CACHE_BASE = '.swarming_module_cache'
IMPLIED_CACHES = {
  'vpython': 'vpython',
}
IMPLIED_ENV_PREFIXES = {
  'VPYTHON_VIRTUALENV_ROOT': '/'.join((IMPLIED_CACHE_BASE, 'vpython')),
}

# These CIPD packages will be automatically put on $PATH for all swarming tasks
# generated from this module. Each key is the name of a package to install and
# its associated value is a dict with the following keys:
#   - "version" (required): the version of the package to install.
#   - "install_path" (optional): path relative to IMPLIED_BINARY_PATH to install
#     the package to. If unspecified, the package is installed to
#     IMPLIED_BINARY_PATH.
#   - "env_path" (optional): path relative to the installed path to put on
#     $PATH. If unspecified, the package's installation root is put on $PATH.
IMPLIED_CIPD_BINARIES = {
  # Both vpython versions MUST be changed together.
  'infra/tools/luci/vpython/${platform}': {
      'version': 'git_revision:cc09450f1c27c0034ec08b1f6d63bbc298294763',
  },
  'infra/tools/luci/vpython-native/${platform}': {
      'version': 'git_revision:cc09450f1c27c0034ec08b1f6d63bbc298294763',
  },

  'infra/tools/luci/logdog/butler/${platform}': {
      'version': 'git_revision:e1abc57be62d198b5c2f487bfb2fa2d2eb0e867c',
  },

  # NOTE(crbug.com/842234): this isn't currently available on mips. See
  # SwarmingApi.trigger_task for hack.
  'infra/python/cpython/${platform}': {
      'install_path': 'cpython',
      'env_path': 'bin',
      'version': 'version:2.7.15.chromium14',
  },
}

PER_TARGET_SWARMING_DIMS = collections.defaultdict(dict)
PER_TARGET_SWARMING_DIMS.update({
    'android': {
      'cpu': None,
      'gpu': None,
      'os': 'Android',
    },
    'chromeos': {
      'cpu': None,
      'gpu': None,
      'os': 'ChromeOS',
    }
})


MASTER_SWARMING_PRIORITIES = collections.defaultdict(lambda: 25)
MASTER_SWARMING_PRIORITIES.update({
    'chromium.android.fyi': 35,
    'chromium.fyi': 35,  # This should be lower than the CQ.
    'client.v8.chromium': 35,
    'client.v8.fyi': 35,
})


def safe(f, *args, **kw):
  try:
    f(*args, **kw)
    return True
  except Exception:
    return False


def filter_outdir(dumps, output_dir, text_files=('.txt', '.json', ''),
                msize=1024):
  """Create a summary of contents of a raw_io.output_dir."""
  outdir_json = {}
  for filename in sorted(output_dir):
    _, ext = os.path.splitext(filename)

    contents = output_dir[filename]

    # If a text file is small enough, just dump it
    if ext in text_files and len(contents) < msize and safe(dumps, contents):
      output = contents

    # Otherwise, just output some details
    else:
      output = {
          'sha1': hashlib.sha1(contents).hexdigest(),
          'size': len(contents),
      }
      if ext in text_files:
        hsize = int(msize/2)
        output['type'] = 'text'
        if safe(dumps, contents[:hsize]):
          # Space in the name so it sorts a[ :x],a[-x:]
          output['contents[ :%s]' % hsize] = contents[:hsize]
        if safe(dumps, contents[-hsize:]):
          output['contents[-%s:]' % hsize] = contents[-hsize:]
      else:
        output['type'] = 'binary'

    outdir_json[filename] = output

  return outdir_json


def text_for_task(task):
  lines = []

  if task.request[0].dimensions.get('id'):
    lines.append('Bot id: %r' % task.request[0].dimensions['id'])
  if task.request[0].dimensions.get('os'):
    lines.append('Run on OS: %r' % task.request[0].dimensions['os'])

  return '<br/>'.join(lines)


def parse_time(value):
  """Converts serialized time from the API to datetime.datetime."""
  # When microseconds are 0, the '.123456' suffix is elided. This means the
  # serialized format is not consistent, which confuses the hell out of python.
  # TODO(maruel): Remove third format once we enforce version >=0.8.2.
  for fmt in ('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'):
    try:
      return datetime.datetime.strptime(value, fmt)
    except ValueError:  # pragma: no cover
      pass
  raise ValueError('Failed to parse %s' % value)  # pragma: no cover


def fmt_time(seconds):
  """Formats some number of seconds into a string. If this is < 60, it will
  render as `NNs`. If it's >= 60 seconds, it will render as 'hh:mm:ss'."""
  return (
    '%ds' % (seconds,) if seconds < 60
    else str(datetime.timedelta(seconds=seconds))
  )


class ReadOnlyDict(dict):
  def __setitem__(self, key, value):
    raise TypeError('ReadOnlyDict is immutable')


class SwarmingApi(recipe_api.RecipeApi):
  """Recipe module to use swarming.py tool to run tasks on Swarming.

  General usage:
    1. Tweak default task parameters applied to all swarming tasks (such as
       default_dimensions and default_priority).
    2. Isolate some test using 'isolate' recipe module. Get isolated hash as
       a result of that process.
    3. Create a task configuration using 'task(...)' method, providing
       isolated hash obtained previously.
    4. Tweak the task parameters. This step is optional.
    5. Launch the task on swarming by calling 'trigger_task(...)'.
    6. Continue doing useful work locally while the task is running concurrently
       on swarming.
    7. Wait for task to finish and collect its result (exit code, logs)
       by calling 'collect_task(...)'.

  See also example.py for concrete code.
  """

  def _get_exit_code(self, shard):
    if 'exit_code' in shard:
      return int(shard['exit_code'])

    if shard.get('state') == 'COMPLETED':
      # This case, task finished successfully.
      return 0
    return None

  def __init__(self, **kwargs):
    super(SwarmingApi, self).__init__(**kwargs)
    # All tests default to a x86-64 bot running with no GPU. This simplifies
    # management so that new tests are not executed on exotic bots by accidents
    # even if misconfigured.
    self._default_dimensions = {
      'cpu': 'x86-64',
      'gpu': None,
    }
    # Expirations are set to mildly good values and will be tightened soon.
    self._default_expiration = 60*60
    self._default_env = {}
    self._default_hard_timeout = 60*60
    self._default_idempotent = False
    self._default_io_timeout = 20*60
    # The default priority is extremely low and should be increased dependending
    # on the type of task.
    self._default_priority = 200
    self._default_tags = set()
    self._default_user = None
    self._pending_tasks = set()
    self._service_account_json = None
    self._show_outputs_ref_in_collect_step = True
    self._show_shards_in_collect_step = False
    self._swarming_server = 'https://chromium-swarm.appspot.com'
    self._verbose = False

    # Record all durations of shards for aggregation.
    self._shards_durations = []

    # Counter used to ensure test data task ids are unique across different
    # triggers.
    self._task_test_data_id_offset = 0

    self._task_output_stdout = 'all'

    # Path to chromium source testing directory.
    self._path_to_testing_dir = None

  def initialize(self):
    self.add_default_tag(
        'build_is_experimental:' + str(self.m.runtime.is_experimental).lower())

  @recipe_util.returns_placeholder
  def summary(self):
    return self.m.json.output()

  @property
  def service_account_json(self):
    """Service account json to use for swarming."""
    return self._service_account_json

  @service_account_json.setter
  def service_account_json(self, value):
    """Service account json to use for swarming."""
    self._service_account_json = value

  @property
  def swarming_server(self):
    """URL of Swarming server to use, default is a production one."""
    return self._swarming_server

  @swarming_server.setter
  def swarming_server(self, value):
    """Changes URL of Swarming server to use."""
    self._swarming_server = value

  @property
  def verbose(self):
    """True to run swarming scripts with verbose output."""
    return self._verbose

  @verbose.setter
  def verbose(self, value):
    """Enables or disables verbose output in swarming scripts."""
    assert isinstance(value, bool), value
    self._verbose = value

  @property
  def default_expiration(self):
    """Number of seconds that the server will wait to find a bot able to run the
    task.

    If not bot runs the task by this number of seconds, the task is canceled as
    EXPIRED.

    This value can be changed per individual task.
    """
    return self._default_expiration

  @default_expiration.setter
  def default_expiration(self, value):
    assert 30 <= value <= 24*60*60, value
    self._default_expiration = value

  @property
  def default_hard_timeout(self):
    """Number of seconds in which the task must complete.

    If the task takes more than this amount of time, the process is assumed to
    be hung. It forcibly killed via SIGTERM then SIGKILL after a grace period
    (default: 30s). Then the task is marked as TIMED_OUT.

    This value can be changed per individual task.
    """
    return self._default_hard_timeout

  @default_hard_timeout.setter
  def default_hard_timeout(self, value):
    assert 30 <= value <= 6*60*60, value
    self._default_hard_timeout = value

  @property
  def default_io_timeout(self):
    """Number of seconds at which interval the task must write to stdout or
    stderr.

    If the task takes more than this amount of time between writes to stdout or
    stderr, the process is assumed to be hung. It forcibly killed via SIGTERM
    then SIGKILL after a grace period (default: 30s). Then the task is marked as
    TIMED_OUT.

    This value can be changed per individual task.
    """
    return self._default_io_timeout

  @default_io_timeout.setter
  def default_io_timeout(self, value):
    assert 30 <= value <= 6*60*60, value
    self._default_io_timeout = value

  @property
  def default_idempotent(self):
    """Bool to specify if task deduplication can be done.

    When set, the server will search for another task that ran in the last days
    that had the exact same properties. If it finds one, the task will not be
    run at all, the previous results will be returned as-is.

    For more infos, see:
    https://github.com/luci/luci-py/blob/master/appengine/swarming/doc/User-Guide.md#task-idempotency

    This value can be changed per individual task.
    """
    return self._default_idempotent

  @default_idempotent.setter
  def default_idempotent(self, value):
    assert isinstance(value, bool), value
    self._default_idempotent = value

  @property
  def default_user(self):
    """String to represent who triggered the task.

    The user should be an email address when someone requested testing via
    pre-commit or manual testing.

    This value can be changed per individual task.
    """
    return self._default_user

  @default_user.setter
  def default_user(self, value):
    assert value is None or isinstance(value, basestring), value
    self._default_user = value

  @property
  def default_dimensions(self):
    """Returns a copy of the default Swarming dimensions to run task on.

    The dimensions are what is used to filter which bots are able to run the
    task successfully. This is particularly useful to discern between OS
    versions, type of CPU, GPU card or VM, or preallocated pool.

    Example:
      {'cpu': 'x86-64', 'os': 'Windows-XP-SP3'}

    This value can be changed per individual task.
    """
    return ReadOnlyDict(self._default_dimensions)

  def set_default_dimension(self, key, value):
    assert isinstance(key, basestring), key
    assert isinstance(value, basestring) or value is None, value
    if value is None:
      self._default_dimensions.pop(key, None)
    else:
      self._default_dimensions[key] = value

  @property
  def default_env(self):
    """Returns a copy of the default environment variable to run tasks with.

    By default the environment variable is not modified. Additional environment
    variables can be specified for each task.

    This value can be changed per individual task.
    """
    return ReadOnlyDict(self._default_env)

  def set_default_env(self, key, value):
    assert isinstance(key, basestring), key
    assert isinstance(value, basestring), value
    self._default_env[key] = value

  @property
  def default_priority(self):
    """Swarming task priority for tasks triggered from the recipe.

    Priority ranges from 1 to 255. The lower the value, the most important the
    task is and will preempty any task with a lower priority.

    This value can be changed per individual task.
    """
    return self._default_priority

  @default_priority.setter
  def default_priority(self, value):
    assert 1 <= value <= 255
    self._default_priority = value

  @property
  def task_output_stdout(self):
    """Flag passed to swarming client with -task-output-stdout."""
    return self._task_output_stdout

  @task_output_stdout.setter
  def task_output_stdout(self, value):
    assert value in ('none', 'json', 'console', 'all')
    self._task_output_stdout = value

  def add_default_tag(self, tag):
    """Adds a tag to the Swarming tasks triggered.

    Tags are used for maintenance, they can be used to calculate the number of
    tasks run for a day to calculate the cost of a type of type (CQ, ASAN, etc).

    Tags can be added per individual task.
    """
    assert ':' in tag, tag
    self._default_tags.add(tag)

  @property
  def show_outputs_ref_in_collect_step(self):
    """Show the shard's isolated out link in each collect step."""
    return self._show_outputs_ref_in_collect_step

  @show_outputs_ref_in_collect_step.setter
  def show_outputs_ref_in_collect_step(self, value):
    self._show_outputs_ref_in_collect_step = value

  @property
  def show_shards_in_collect_step(self):
    """Show the shard link in each collect step."""
    return self._show_shards_in_collect_step

  @show_shards_in_collect_step.setter
  def show_shards_in_collect_step(self, value):
    self._show_shards_in_collect_step = value

  @staticmethod
  def prefered_os_dimension(platform):
    """Given a platform name returns the prefered Swarming OS dimension.

    Platform name is usually provided by 'platform' recipe module, it's one
    of 'win', 'linux', 'mac'. This function returns more concrete Swarming OS
    dimension that represent this platform on Swarming by default.

    Recipes are free to use other OS dimension if there's a need for it. For
    example WinXP try bot recipe may explicitly specify 'Windows-XP-SP3'
    dimension.
    """
    return {
      'linux': 'Ubuntu-14.04',
      'mac': 'Mac-10.13',
      'win': 'Windows-7-SP1',
    }[platform]

  def merge_script_path(self, name):
    """Returns the path to a merge script.

    This assumes that a chromium checkout exists, and the chromium module is
    configured correctly.
    """
    return self.m.path.join(self._path_to_testing_dir, 'merge_scripts', name)

  def task(self, name=None, build_properties=None, cipd_packages=None,
           collect_step=None, env=None, env_prefixes=None, extra_args=None,
           failure_as_exception=True, idempotent=None,
           ignore_task_failure=False, isolated=None, merge=None,
           named_caches=None, optional_dimensions=None, raw_cmd=None,
           service_account=None, shards=1, shard_indices=None,
           task_output_dir=None, task_to_retry=None, trigger_script=None):
    """Returns a new SwarmingTask instance to run an isolated executable on
    Swarming.

    For google test executables, use gtest_task() instead.

    At the time of this writting, this code is used by V8, Skia and iOS.

    The return value can be customized if necessary (see SwarmingTask class
    below). Pass it to 'trigger_task' to launch it on swarming. Later pass the
    same instance to 'collect_task' to wait for the task to finish and fetch its
    results.

    The default collect step will raise a StepFailure exception if there is a
    test failure. To change this behavior, overwrite the default collect step.

    Args:
      * name: name of the test, used as part of a task ID.
      * isolated: hash of isolated test on isolate server, the test should
          be already isolated there, see 'isolate' recipe module.
      * ignore_task_failure: whether to ignore the test failure of swarming
        tasks. By default, this is set to False.
      * shards: if defined, the number of shards to use for the task. By default
          this value is either 1 or based on the name.
      * shard_indices: Which shards to run. If None, all shards are run.
      * task_output_dir: if defined, the directory where task results are
          placed. The caller is responsible for removing this folder when
          finished.
      * extra_args: list of command line arguments to pass to isolated tasks.
      * idempotent: whether this task is considered idempotent. Defaults
          to self.default_idempotent if not specified.
      * cipd_packages: list of 3-tuples corresponding to CIPD packages needed
          for the task: ('path', 'package_name', 'version'), defined as
          follows:
        * path: Path relative to the Swarming root dir in which to install
                  the package.
        * package_name: Name of the package to install,
                  eg. "infra/tools/luci-auth/${platform}"
        * version: Version of the package, either a package instance ID,
                  ref, or tag key/value pair.
      * build_properties: An optional dict containing various build properties.
          These are typically but not necessarily the properties emitted by
          bot_update.
      * merge: An optional dict containing:
        * "script": path to a script to call to post process and merge the
              collected outputs from the tasks. The script should take one
              named (but required) parameter, '-o' (for output), that represents
              the path that the merged results should be written to, and accept
              N additional paths to result files to merge. The merged results
              should be in the JSON Results File Format
              (https://www.chromium.org/developers/the-json-test-results-format)
              and may optionally contain a top level "links" field that
              may contain a dict mapping link text to URLs, for a set of
              links that will be included in the buildbot output.
        * "args": an optional list of additional arguments to pass to the
              above script.
      * trigger_script: An optional dict containing:
        * "script": path to a script to call which will use custom logic to
              trigger appropriate swarming jobs, using swarming.py.
        * "args": an optional list of additional arguments to pass to the
              script.
          See SwarmingTask.__init__ docstring for more details.
      * named_caches: a dict {name: relpath} requesting a cache named `name`
          to be installed in `relpath` relative to the task root directory.
      * service_account: (string) a service account email to run the task under.
      * raw_cmd: Optional list of arguments to be used as raw command. Can be
          used instead of extra args.
      * env_prefixes: a dict {ENVVAR: [relative, paths]} which instructs
          swarming to prepend the given relative paths to the PATH-style ENVVAR
          specified.
      * env: a dict {ENVVAR: ENVVALUE} which instructs swarming to set the
          environment variables before invoking the command. These are applied
          on top of the default environment variables.
      * optional_dimensions: {expiration: [{key: value]} mapping with swarming
          dimensions that specify on what Swarming slaves tasks can run.  These
          are similar to what is specified in dimensions but will create
          additional 'fallback' task slice(s) with the optional dimensions.
      * task_to_retry: Task object. If set, indicates that this task is a
          (potentially partial) retry of another task. When collecting, the
          successful shards from 'task_to_retry' will be merged with the new
          shards in this task.
      * failure_as_exception: Boolean. Whether test failures should throw a
        recipe exception during the collect step.
    """

    if not collect_step:
      collect_step = functools.partial(
        self._default_collect_step, failure_as_exception=failure_as_exception)

    ensure_file = self.m.cipd.EnsureFile()
    if cipd_packages:
      for package in cipd_packages:
        ensure_file.add_package(package[1], package[2], package[0])

    env_prefixes = {
      var: list(paths) for var, paths in (env_prefixes or {}).items()}

    if idempotent is None:
      idempotent = self.default_idempotent

    init_env = self.default_env.copy()
    init_env.update(env or {})

    optional_dimensions_var = None
    if optional_dimensions:
      optional_dimensions_var = optional_dimensions.copy()

    shard_indices = shard_indices or range(shards)

    spec_name = ''
    builder_id = self.m.buildbucket.build.builder
    if builder_id.bucket and builder_id.project:
      spec_name = '%s.%s:%s' % (
          builder_id.project, builder_id.bucket, builder_id.builder)

    builder_info = None
    buildername = self.m.buildbucket.builder_name
    if buildername:
      builder_info = (buildername, (self.m.buildbucket.build.number or -1))

    request = (self.m.swarming.task_request().
      with_name(name or '').
      with_priority(self.default_priority).
      with_service_account(service_account or '').
      with_user(self.default_user or ''))

    request = (request.with_slice(0, request[0].
      with_cipd_ensure_file(ensure_file).
      with_command(raw_cmd or []).
      with_dimensions(**self._default_dimensions).
      with_env_vars(**init_env.copy()).
      with_env_prefixes(**env_prefixes).
      with_execution_timeout_secs(self.default_hard_timeout).
      with_expiration_secs(self.default_expiration).
      with_io_timeout_secs(self.default_io_timeout).
      with_isolated(isolated or ('0' * 40)).
      with_idempotent(idempotent)))

    return SwarmingTask(
      request=request,
      builder_info=builder_info,
      collect_step=collect_step,
      extra_args=extra_args,
      ignore_task_failure=ignore_task_failure,
      named_caches=named_caches,
      optional_dimensions=optional_dimensions_var,
      shard_indices=shard_indices,
      shards=shards,
      spec_name=spec_name,
      task_output_dir=task_output_dir,
      task_to_retry=task_to_retry,
      build_properties=build_properties,
      merge=merge,
      trigger_script=trigger_script
    )

  def gtest_task(self, name=None, isolated=None, extra_args=None,
                 cipd_packages=None, merge=None, **kwargs):
    """Returns a new SwarmingTask instance to run an isolated gtest on Swarming.

    The implementation uses a test_utils.gtest_results() placeholder to parse
    the JSON output.

    For meaning of the rest of the arguments see 'task' method.
    """
    extra_args = list(extra_args or [])

    # Ensure --test-launcher-summary-output is not already passed. We are going
    # to overwrite it.
    bad_args = any(
        x.startswith('--test-launcher-summary-output=') for x in extra_args)
    if bad_args:  # pragma: no cover
      raise ValueError('--test-launcher-summary-output should not be used.')

    # Append it. output.json name is expected by collect_task.py.
    extra_args.append(
        '--test-launcher-summary-output=${ISOLATED_OUTDIR}/output.json')

    merge = merge or {'script': self.merge_script_path(
        'standard_gtest_merge.py')}

    # Make a task, configure it to be collected through shim script.
    task = self.task(name=name, cipd_packages=cipd_packages,
                     collect_step=self._gtest_collect_step,
                     extra_args=extra_args, isolated=isolated, merge=merge,
                     **kwargs)
    return task

  def isolated_script_task(self):
    """Returns a new SwarmingTask to run an isolated script test on Swarming.

    At the time of this writting, this code is used by WebRTC and
    "isolated_scripts" entries in Chromium's src/testing/buildbot/*.json.

    Swarming recipe module knows how collect JSON file with test execution
    summary produced by isolated script tests launcher. A custom script
    can be passed to merge the collected results and post-process them.
    """

    def _create_output_flag(flag, output_file_name):
      return '--%s=${ISOLATED_OUTDIR}/%s' % (flag, output_file_name)

    extra_args = []
    # output.json name is expected by collect_task.py.
    extra_args.append(_create_output_flag(
        'isolated-script-test-output', 'output.json'))
    # perftest-output.json name is expected by benchmarks generating chartjson
    # or histogram output
    extra_args.append(_create_output_flag(
        'isolated-script-test-perf-output',
        'perftest-output.json'))

    merge = {
      'script': self.merge_script_path('standard_isolated_script_merge.py')
    }

    task = self.task()
    task.extra_args = extra_args
    task.merge = merge
    task.collect_step = self._isolated_script_collect_step
    return task

  def check_client_version(self, step_test_data=None):
    """Yields steps to verify compatibility with swarming_client version."""
    return self.m.swarming_client.ensure_script_version(
        'swarming.py', MINIMAL_SWARMING_VERSION, step_test_data)

  def trigger_task(self, task, **kwargs):
    """Triggers one task.

    It the task is sharded, will trigger all shards. This steps justs posts
    the task and immediately returns. Use 'collect_task' to wait for a task to
    finish and grab its result.

    Returns a list of StepResults, one for each shard triggered. Raises
    StepFailure if any shard fails to trigger. Subsequent shards are not
    triggered.

    Args:
      task: SwarmingTask instance.
      kwargs: passed to recipe step constructor as-is.
    Returns:
      A list of StepResults, one for each shard triggered.
    """
    assert isinstance(task, SwarmingTask)
    assert task.task_name not in self._pending_tasks, (
        'Triggered same task twice: %s' % task.request.name)
    assert 'os' in task.request[0].dimensions, task.request[0].dimensions

    # There is a single pending task, regardless of how many shards get
    # triggered.
    self._pending_tasks.add(task.task_name)

    step_results = []

    base_task_name = None
    tasks = {}

    # The public interface for perf_device_trigger.py and the default trigger
    # script are starting to diverge. The former requires that all shard indices
    # are simultaneously passed. The go implementation of the latter requires
    # that shard indices are passed one at a time. See https://crbug.com/937927.
    if task.trigger_script and task.trigger_script.get(
        'requires_simultaneous_shard_dispatch', False):
      return [self.trigger_all_task_shards(task, task.shard_indices, **kwargs)]

    for shard_index in task.shard_indices:
      step_result, json_output = (
          self.trigger_task_shard(task, shard_index, **kwargs))
      step_results.append(step_result)

      # Merge the JSON outputs. There should be two fields: base_task_name,
      # which should be identical from all outputs. And tasks, a dictionary of
      # dictionaries. Each of the keys in tasks should be unique.
      new_base_task_name = json_output['base_task_name']
      if (base_task_name and base_task_name
          != new_base_task_name): # pragma: no cover
        raise recipe_api.StepFailure(
            'Triggered shards for a single swarming task had different base '
            'names: {} and {}'.format(base_task_name, new_base_task_name),
            result=step_result)

      base_task_name = new_base_task_name
      for key,value in json_output['tasks'].iteritems():
        tasks[key] = value

    if len(tasks) != len(task.shard_indices): # pragma: no cover
      raise recipe_api.StepFailure(
          'Wrong number of triggered tasks. Expected: {}. Actual: {}.'.format(
              len(task.shard_indices), len(tasks)), result=step_result)

    trigger_output = {
        'base_task_name' : base_task_name,
        'tasks' : tasks
    }
    task._trigger_output = trigger_output

    return step_results

  def generate_trigger_task_shard_args(self, task, **kwargs):
    """Generates the arguments for triggered shards.

    This generates all arguments other than sharding parameters.

    Returns: (script, pre_trigger_args, post_trigger_args)
      script: The script to invoke
      pre_trigger_args: All arguments up to and including 'trigger'
      post_triggers_args: All arguments following 'trigger'
    """
    task_request = task.request
    task_slice = task.request[0]

    # Mix in standard infra packages 'vpython' and 'logdog' so that the task can
    # always access them on $PATH.
    task_cipd_packages = task_slice.cipd_ensure_file.packages
    cipd_packages = []
    if task_cipd_packages:
      for path in sorted(task_cipd_packages):
        for pkg in task_cipd_packages[path]:
          cipd_packages.append(((path or '.'), pkg.name, pkg.version))

    for pkg in cipd_packages:
      assert not pkg[0].startswith(IMPLIED_BINARY_PATH), \
        'cipd_packages may not be installed to %r' % (IMPLIED_BINARY_PATH,)

    to_add = dict(IMPLIED_CIPD_BINARIES)

    # HACK(crbug.com/842234) - we don't support cpython on mips yet, so remove
    # it from packages to inject.
    cpu_dimension = task_slice.dimensions.get('cpu', '')
    if 'mips' in cpu_dimension:
      to_add.pop('cpython', None)

    path_env_prefix = set()
    for pkg, details in sorted(to_add.items()):
      path = IMPLIED_BINARY_PATH
      if details.get('install_path'):
        path = '/'.join((path, details['install_path']))
      if details.get('env_path'):
        path_env_prefix.add('/'.join((path, details['env_path'])))
      else:
        path_env_prefix.add(path)
      vers = 'TEST_VERSION' if self._test_data.enabled else details['version']
      cipd_packages.append((path, pkg, vers))

    # update implied caches
    named_caches = dict(task.named_caches or {})
    named_caches.update({
      '_'.join((IMPLIED_CACHE_NAME, k)): '/'.join((IMPLIED_CACHE_BASE,v))
      for k, v in IMPLIED_CACHES.iteritems()
    })

    # update $PATH
    env_prefixes = dict(task_slice.env_prefixes or {})            # copy it
    env_prefixes.setdefault('PATH', [])[:0] = sorted(  # prepend stuff
      path_env_prefix, key=lambda x: (len(x), x))
    for k, path in IMPLIED_ENV_PREFIXES.iteritems():
      env_prefixes.setdefault(k, [path])

    # Trigger parameters.
    pre_trigger_args = ['trigger']
    # TODO(maruel): https://crbug.com/944904
    args = [
      '--swarming', self.swarming_server,
      '--isolate-server', self.m.isolate.isolate_server,
      '--namespace', self.m.isolate.namespace,
      '--priority', str(task_request.priority),
      '--task-name', task.task_name,
      '--dump-json', self.m.json.output(),
      '--expiration', str(task_slice.expiration_secs),
      '--io-timeout', str(task_slice.io_timeout_secs),
      '--hard-timeout', str(task_slice.execution_timeout_secs),
    ]

    for name, value in sorted(task_slice.dimensions.iteritems()):
      assert isinstance(value, basestring), \
        'dimension %s is not a string: %s' % (name, value)
      args.extend(['--dimension', name, value])

    if task.optional_dimensions:
      for exp, dimensions in task.optional_dimensions.iteritems():
        for d in dimensions:
          for name, value in d.iteritems():
            assert isinstance(value, basestring), \
                'optional-dimension %s is not a string: %s' % (name, value)
            args.extend(['--optional-dimension', name, value, exp])

    for name, value in sorted(task_slice.env_vars.iteritems()):
      assert isinstance(value, basestring), \
        'env var %s is not a string: %s' % (name, value)
      args.extend(['--env', name, value])

    for name, relpath in sorted(named_caches.iteritems()):
      args.extend(['--named-cache', name, relpath])

    if task_request.service_account:
      args.extend(['--service-account', task_request.service_account])

    if self.service_account_json:
      args.extend(['--auth-service-account-json', self.service_account_json])

    if task.wait_for_capacity:
      args.append('--wait-for-capacity')

    if task.containment_type:
      args.extend(['--containment-type', task.containment_type])

    # Default tags.
    tags = set(task.tags)
    tags.update(self._default_tags)

    tags.add('data:' + task_slice.isolated)
    tags.add('name:' + task_request.name.split(' ')[0])
    mastername = self.m.properties.get('mastername')
    if mastername:
      tags.add('master:' + mastername)

    if task.spec_name:
      tags.add('spec_name:' + task.spec_name)

    if task.builder_info:
      tags.add('buildername:' + task.builder_info[0])
      if not task.builder_info[1] == -1:
        tags.add('buildnumber:%s' % task.builder_info[1])

    if self.m.properties.get('bot_id'):
      tags.add('slavename:%s' % self.m.properties['bot_id'])

    tags.add('stepname:%s' % self.get_step_name('', task))
    for cl in self.m.buildbucket.build.input.gerrit_changes:
      tags.add('gerrit:https://%s/c/%s/%s' % (cl.host, cl.change, cl.patchset))
    for tag in sorted(tags):
      assert ':' in tag, tag
      args.extend(['--tag', tag])

    if self.verbose:
      args.append('--verbose')
    if task_slice.idempotent:
      args.append('--idempotent')
    if task_request.user:
      args.extend(['--user', task_request.user])

    if cipd_packages:
      for path, pkg, version in cipd_packages:
        args.extend(['--cipd-package', '%s:%s:%s' % (path, pkg, version)])

    if env_prefixes:
      for key, paths in sorted(env_prefixes.items()):
        for path in paths:
          args.extend(('--env-prefix', key, path))

    # What isolated command to trigger.
    if not task_slice.isolated == '0' * 40:
      args.extend(('--isolated', task_slice.isolated))

    # Use a raw command as extra-args on tasks without command.
    if task_slice.command:
      # Allow using only one of raw_cmd or extra_args.
      assert not task.extra_args
      args.append('--raw-cmd')

    # Additional command line args for isolated command.
    if task.extra_args or task_slice.command:
      args.append('--')
      args.extend(task.extra_args or task_slice.command)

    script = self.m.swarming_client.path.join('swarming.py')
    if task.trigger_script:
      script = task.trigger_script['script']
      if task.trigger_script.get('args'):
        pre_trigger_args = task.trigger_script['args'] + pre_trigger_args

    return script, pre_trigger_args, args

  def trigger_all_task_shards(self, task, shard_indices, **kwargs):
    """Triggers all shards as a single step.

    This method adds links to the presentation, and updates
    task._trigger_output.

    Returns:
      StepResult from the step.
    """
    script, pre_trigger_args, post_trigger_args = (
        self.generate_trigger_task_shard_args(task, **kwargs))
    assert len(shard_indices) == task.shards, (
        'The only trigger script that requires all shards to be simultaneously '
        'triggered is perf_device_trigger.py, and it doesn\'t support multi '
        'index dispatch')
    assert range(task.shards) == shard_indices, (
        'The list of shards being dispatched should be the enumeration of '
        'task.shards.'
    )
    pre_trigger_args += ['--shards', str(task.shards)]
    args = pre_trigger_args + post_trigger_args

    # The step can fail only on infra failures, so mark it as 'infra_step'.
    step_result = self.m.python(
        name=self.get_step_name('trigger', task),
        script=script, args=args,
        step_test_data=functools.partial(
            self._gen_trigger_step_test_data, task, shard_indices),
        infra_step=True,
        **kwargs)
    step_result.presentation.step_text += text_for_task(task)

    task._trigger_output = step_result.json.output
    links = step_result.presentation.links
    for shard_index in shard_indices:
      url = task.get_shard_view_url(shard_index, step_result.json.output)
      if url:
        links['shard #%d' % shard_index] = url

    return step_result

  def trigger_task_shard(self, task, shard_index, **kwargs):
    """Triggers a single shard for a task.

    Returns: (step_result, json_output)
      step_result: The step representing the triggered shard.
      json_output: The JSON output of the triggered shard.

    Raises:
      InfraFailure if shard cannot be triggered.
    """
    script, pre_trigger_args, post_trigger_args = (
        self.generate_trigger_task_shard_args(task, **kwargs))

    if task.shards == 1:
      # TODO(erikchen): Remove this placeholder logic. It should have no
      # functional effect, it's just there to make expectation diffs easier to
      # review.
      pre_trigger_args += ['--shards', str(task.shards)]
    else:
      # We must use different logic for swarming.py vs. custom trigger script.
      if task.trigger_script:
        pre_trigger_args += ['--shard-index', str(shard_index)]
        pre_trigger_args += ['--shards', str(task.shards)]
      else:
        pre_trigger_args += ['--env', 'GTEST_SHARD_INDEX', str(shard_index)]
        pre_trigger_args += ['--env', 'GTEST_TOTAL_SHARDS', str(task.shards)]

    args = pre_trigger_args + post_trigger_args

    # The step can fail only on infra failures, so mark it as 'infra_step'.
    step_result = self.m.python(
        name=self.get_step_name('trigger', task),
        script=script, args=args,
        step_test_data=functools.partial(
            self._gen_trigger_step_test_data, task, [shard_index]),
        infra_step=True,
        **kwargs)
    step_result.presentation.step_text += text_for_task(task)

    # While it might make more sense to update all presentation links in
    # trigger_task(), this is currently not possible. Steps are run in series,
    # and once a step is finalized, it becomes immutable.
    # Update the presentation links now that _trigger_output has been generated.
    if step_result.presentation != self.m.step.FAILURE:
      links = step_result.presentation.links
      url = task.get_shard_view_url(shard_index, step_result.json.output)
      if url:
        links['shard #%d' % shard_index] = url

    return step_result, step_result.json.output

  def collect_task(self, task, **kwargs):
    """Waits for a single triggered task to finish.

    If the task is sharded, will wait for all shards to finish. Behaves as
    a regular recipe step: returns StepData with step results on success or
    raises StepFailure if task fails.

    Args:
      task: SwarmingTask instance, previously triggered with 'trigger' method.
      kwargs: passed to recipe step constructor as-is.
    """
    # TODO(vadimsh): Raise InfraFailure on Swarming failures.
    assert isinstance(task, SwarmingTask)
    assert task.task_name in self._pending_tasks, (
        'Trying to collect a task that was not triggered: %s' %
        task.task_name)
    self._pending_tasks.remove(task.task_name)
    try:
      return task.collect_step(task, **kwargs)
    finally:
      pass

  def report_stats(self):
    """Report statistics on all tasks ran so far."""
    if not self._shards_durations:
      return
    stats = ['Total shards: %d' % len(self._shards_durations)]
    total = sum(self._shards_durations)
    mean = total / len(self._shards_durations)
    stats.extend([
      'Total runtime: %s ' % fmt_time(total),
    ])
    detailed_stats = stats + [
      'Min/mean/max: %s / %s / %s' % (
          fmt_time(min(self._shards_durations)),
          fmt_time(mean),
          fmt_time(max(self._shards_durations)),
      ),
    ]
    step_text = self.m.test_utils.format_step_text([
        ('Stats', stats)])
    result = self.m.python.succeeding_step('Tests statistics', step_text)
    result.presentation.logs['detailed stats'] = detailed_stats

  @staticmethod
  def _display_pending(shards, step_presentation):
    """Shows max pending time in seconds across all shards if it exceeds 10s,
    and also displays the min and max shard duration accross all shards."""
    max_pending = (-1, None)
    max_duration = (-1, None)
    min_duration = (None, None)
    for i, shard in enumerate(shards):
      if not shard or not shard.get('started_ts'):
        continue

      created = parse_time(shard['created_ts'])
      started = parse_time(shard['started_ts'])

      pending = (started - created).total_seconds()
      if pending > max_pending[0]:
        max_pending = (pending, i)

      if shard.get('completed_ts'):
        duration = (parse_time(shard['completed_ts']) - started).total_seconds()
        if duration > max_duration[0]:
          max_duration = (duration, i)
        if min_duration[0] is None or duration < min_duration[0]:
          min_duration = (duration, i)

    # Only display annotation when pending more than 10 seconds to reduce noise.
    if max_pending[0] > 10:
      prefix = 'P' if len(shards) <= 1 else 'Max p'
      suffix = '' if len(shards) <= 1 else ' (shard #%d)' % max_pending[1]
      step_presentation.step_text += (
        '<br>%sending time: %s%s' % (prefix, fmt_time(max_pending[0]), suffix))

    if max_duration[0] > 0:
      prefix = 'S' if len(shards) <= 1 else 'Max s'
      suffix = '' if len(shards) <= 1 else ' (shard #%d)' % max_duration[1]
      step_presentation.step_text += (
        '<br>%shard duration: %s%s' % (
          prefix, fmt_time(max_duration[0]), suffix))

    if min_duration[0] is not None and len(shards) > 1:
      step_presentation.step_text += (
        '<br>Min shard duration: %s (shard #%d)' % (
          fmt_time(min_duration[0]), min_duration[1]))

  def _default_collect_step(
      self, task, failure_as_exception, output_placeholder=None, name=None,
      gen_step_test_data=None, **kwargs):
    """Produces a step that collects the results of a Task object.

    A Task object may have triggered multiple swarming tasks.

    The go and python implementation of swarming collect have diverged. The go
    implementation has exit code 0 if the tasks were successfully collected. The
    python implementation has non-zero exit code if any of the swarming tasks
    has non-zero exit code, with later exit codes overriding previous ones.

    The behavior of the python implementation is undesirable, as it makes it
    impossible to distinguish between non-zero exit code due to an actual
    collection error, and successful collection but failed swarming tasks. For
    now, we wrap the python implementation with manual logic to mimic the
    behavior of the go implementation. Once we switch over to the go
    implementation, this wrapper logic can be removed.

    This method will always update the presentation status with EXCEPTION if
    there was an infra error, or FAILURE if any of the shards timed out or had
    non-zero exit code.

    If failure_as_exception is True, this method will raise a StepFailure
    exception when the presentation status is EXCEPTION or FAILURE.

    Regardless of whether an exception is raised, subsequent recipe logic will
    need to know if there are missing shards. This information is transported
    through a side channel. The merge script will set the global tag
    'UNRELIABLE_RESULTS', which the results parser recognizes.

    Args:
      task: A Task object that must have dispatched tasks
      failure_as_exception: Whether a non-zero retcode of a dispatched task
                            should raise a StepFailure exception.
      output_placeholder: A custom placeholder that will transform test
                          results. Defaults to json.output().
      name: Name to use for the collect step.
      gen_step_test_data: A generator that produces default step_test_data.
    Returns: A StepData result for the recipe step, and a boolean indicating if
             the task results should be considered valid.
             They can be invalid if the task didn't successfully execute as
             expected; for example, if the task timed out or an internal
             swarming failure occured.
    """
    task_output_dir = task.task_output_dir or self.m.raw_io.output_dir()

    # If we don't already have a Placeholder, wrap the task_output_dir in one
    # so we can read out of it later w/ step_result.raw_io.output_dir.
    if not isinstance(task_output_dir, recipe_util.Placeholder):
      task_output_dir = self.m.raw_io.output_dir(leak_to=task_output_dir)

    task_args = [
      '--verbose',
      '-o', output_placeholder or self.m.json.output(),
      '--task-output-dir', task_output_dir,
    ]

    merge_script = (task.merge.get('script')
                    # This script still exists here, since there are many
                    # clients which depend on this module which don't
                    # necessarily have a chromium checkout (it's hard to verify
                    # they do via expectations). Leave this here for now, since
                    # this is a sane default to ship with the module.
                    or self.resource('noop_merge.py'))

    merge_args = (task.merge.get('args') or [])
    task_args.extend([
      '--merge-script', merge_script,
      '--merge-script-stdout-file',
      self.m.raw_io.output('merge_script_log'),
      '--merge-additional-args', self.m.json.dumps(merge_args),
    ])
    if task.build_properties:
      properties = dict(task.build_properties)
      # exclude any recipe-engine-controlling properties (starting with $)
      properties.update((k, v) for k, v in self.m.properties.thaw().iteritems()
                        if not k.startswith('$'))
      task_args.extend([
          '--build-properties', self.m.json.dumps(properties),
      ])

    # Arguments for the actual 'collect' command.
    collect_cmd = [
      'swarming',
    ]
    # go's client does not generate summary file under output dir.
    # Need to tell the location of summary file to collect_task.py.
    task_args.extend(['--summary-json-file', self.summary()])

    collect_cmd.extend(self.get_collect_cmd_args(task))

    task_args.append('--')

    task_args.extend(collect_cmd)

    # The call to collect_task emits two JSON files and one text file:
    #  1) a task summary JSON emitted by swarming
    #  2) a gtest results JSON emitted by the task
    #  3) a merge script stdout/stderr log emitted by the task
    # This builds an instance of StepTestData that covers all of them.
    if not gen_step_test_data:
      def gen_default_step_test_data():
        dispatched_task_placeholder = (self.m.json.test_api.output({}) +
            self.m.raw_io.test_api.output('Successfully merged all data'))
        return self.test_api.canned_summary_output(
            dispatched_task_placeholder, task.shards, task.shard_indices)
      gen_step_test_data = gen_default_step_test_data
    with self.m.swarming.on_path():
      with self.m.context(cwd=self.m.path['start_dir']):
        # TODO(erikchen): Once we switch over to the go implementation of
        # swarming, we should stop accepting all return codes.
        # https://crbug.com/944179.
        step_result = self.m.build.python(
            name=name or self.get_step_name('', task),
            script=self.resource('collect_task.py'),
            args=task_args,
            ok_ret='any',
            step_test_data=gen_step_test_data,
            **kwargs)
    step_result.presentation.step_text = text_for_task(task)

    step_result.presentation.logs['Merge script log'] = [
        step_result.raw_io.output]

    links = {}
    if hasattr(step_result, 'json') and hasattr(
        step_result.json, 'output') and step_result.json.output:
      links = step_result.json.output.get('links', {})
    elif (hasattr(step_result, 'test_utils') and
          hasattr(step_result.test_utils, 'gtest_results')):
      links = step_result.test_utils.gtest_results.raw.get('links', {})
    for k, v in links.iteritems():
      step_result.presentation.links[k] = v

    exception, has_valid_results = self._handle_summary_json(task, step_result)

    if (step_result.retcode != 0 and failure_as_exception and not
        task.ignore_task_failure):
      raise recipe_api.StepFailure(
          'Swarming collect had non-zero exit code.',
          result=step_result)

    if exception and failure_as_exception:
      raise exception
    return step_result, has_valid_results

  def _check_for_missing_shard(self, merged_results_json, active_step, task):
    if merged_results_json:
      missing_shards = merged_results_json.get('missing_shards') or []
      if missing_shards:
        active_step.presentation.status = self.m.step.EXCEPTION
        for index in missing_shards:
          active_step.presentation.links['missing shard #%d' % index] = \
              task.get_shard_view_url(index)

  def _gtest_collect_step(self, task, **kwargs):
    """Produces a step that collects and processes a result of google-test task.
    """
    output_placeholder = self.m.test_utils.gtest_results(add_json_log=False)

    # The call to collect_task emits two JSON files and a test file:
    #  1) a task summary JSON emitted by swarming
    #  2) a gtest results JSON emitted by the task
    #  3) a log file that stores stdout/stderr of task
    # This builds an instance of StepTestData that covers all three.
    def gen_default_step_test_data():
      dispatched_step_test_data = (
          self.m.test_utils.test_api.canned_gtest_output(True))
      dispatched_step_test_data += self.test_api.merge_script_log_file(
          'Gtest merged successfully')
      return self.test_api.canned_summary_output(
        dispatched_step_test_data, task.shards, task.shard_indices)

    step_result, has_valid_results = self._default_collect_step(
        task,
        output_placeholder=output_placeholder,
        gen_step_test_data=gen_default_step_test_data,
        allow_subannotations=True,
        failure_as_exception=False,
        **kwargs)

    gtest_results = self.m.test_utils.present_gtest_failures(step_result)
    if gtest_results and gtest_results.valid:
      self._check_for_missing_shard(gtest_results.raw, step_result, task)

    return step_result, has_valid_results

  def _merge_isolated_script_perftest_output_shards(self, task, step_result):
    # Taken from third_party/catapult/telemetry/telemetry/internal/results/
    # chart_json_output_formatter.py, the json entries are as follows:
    # result_dict = {
    #   'format_version': '0.1',
    #   'next_version': '0.2',
    #   'benchmark_name': benchmark_metadata.name,
    #   'benchmark_description': benchmark_metadata.description,
    #   'trace_rerun_options': benchmark_metadata.rerun_options,
    #   'benchmark_metadata': benchmark_metadata.AsDict(),
    #   'charts': charts,
    # }
    #
    # Therefore, all entries should be the same and we should only need to merge
    # the chart from each shard.
    collected_results = []
    for i in task.shard_indices:
      path = self.m.path.join(str(i), 'perftest-output.json')
      if path not in step_result.raw_io.output_dir:
        # perf test results were not written for this shard, not an error,
        # just continue to the next shard
        continue

      results_raw = step_result.raw_io.output_dir[path]
      if not results_raw:
        continue
      perf_results_json = self.m.json.loads(results_raw)
      collected_results.append(perf_results_json)

    if collected_results:
      # If the first result is a dict, we assume that we're dealing with
      # chart JSON. By contrast, HistogramSets are serialized as lists.
      if isinstance(collected_results[0], dict):
        return self._merge_chartjson_results(collected_results), False
      elif isinstance(collected_results[0], list):
        return self._merge_histogram_results(collected_results), True

    return {}, False

  def _merge_chartjson_results(self, chartjson_dicts):
    merged_results = chartjson_dicts[0]
    for chartjson_dict in chartjson_dicts[1:]:
      for key in chartjson_dict:
        if key == 'charts':
          for add_key in chartjson_dict[key]:
            merged_results[key][add_key] = chartjson_dict[key][add_key]

    return merged_results

  def _merge_histogram_results(self, histogram_lists):
    merged_results = []
    for histogram_list in histogram_lists:
      merged_results += histogram_list

    return merged_results

  def wait_for_finished_task_set(self, task_sets, suffix=None, attempts=0):
    """Waits for a finished set of tasks.

    Args:
      task_sets: A list of lists. Each item in task_sets is a set of tasks,
                 which should be collected together.
      suffix: An optional name suffix.
      attempts: How many times have we polled swarming for this data. Used
                to retry at a slower rate, so we don't overload the server
                with requests.

    Returns:
      A tuple of two items:
        1. A list of task sets which have finished.
        2. How many attempts we've now made to get task data.

    Uses the 'get_states' endpoint on the swarming server."""
    args = [
        '--swarming-server', self.swarming_server,
        '--swarming-py-path', self.m.swarming_client.path.join('swarming.py'),
        '--output-json', self.m.json.output(),
        '--input-json', self.m.json.input(data=task_sets),
        '--attempts', attempts,
        '--verbose',
    ]

    if self.service_account_json:
      args.extend(['--auth-service-account-json', self.service_account_json])

    result = self.m.python(
        'wait for tasks%s' % (suffix or ''),
        self.resource('wait_for_finished_task_set.py'),
        step_test_data=lambda: self.m.json.test_api.output(data={
            'attempts': 0,
            'sets': task_sets,
        }),
        args=args)
    return [
        tuple(task_set) for task_set in result.json.output['sets']
    ], result.json.output['attempts']

  def _isolated_script_collect_step(self, task, **kwargs):
    """Collects results for a step that is *not* a googletest, like telemetry.
    """
    def gen_default_step_test_data():
      isolated_script_results_test_data = (
          self.m.test_utils.test_api.canned_isolated_script_output(
              passing=True, is_win=self.m.platform.is_win, swarming=True,
              use_json_test_format=True, shards=task.shards,
              shard_indices=task.shard_indices))

      # The call to collect_isolated_script_task emits two JSON files:
      #  1) a task summary JSON emitted by swarming
      #  2) a test results JSON emitted by the task
      # This builds an instance of StepTestData that covers both.
      dispatched_task_placeholder = (isolated_script_results_test_data +
          self.test_api.merge_script_log_file('Merged succesfully'))
      return self.test_api.canned_summary_output(
          dispatched_task_placeholder, task.shards, task.shard_indices)

    step_result, has_valid_results = self._default_collect_step(
        task, gen_step_test_data=gen_default_step_test_data,
        failure_as_exception=False, **kwargs)

    # Regardless of the outcome of the test (pass or fail), we try to parse
    # the results. If any error occurs while parsing results, then we set them
    # to None, which caller should treat as invalid results.
    # Note that try-except block below will not mask the
    # recipe_api.StepFailure exception from the collect step above. Instead
    # it is being allowed to propagate after the results have been parsed.
    outdir = filter_outdir(
        self.m.json.dumps, step_result.raw_io.output_dir)
    outdir_json = self.m.json.dumps(outdir, indent=2)
    step_result.presentation.logs['outdir_json'] = (
        outdir_json.splitlines())

    step_result.isolated_script_results = step_result.json.output
    self._check_for_missing_shard(
        step_result.isolated_script_results, step_result, task)

    # Obtain perftest results if present
    perftest_results, is_histogramset = \
      self._merge_isolated_script_perftest_output_shards(
          task, step_result)
    step_result.isolated_script_perf_results = {
      'is_histogramset': is_histogramset,
      'data': perftest_results
    }

    return step_result, has_valid_results

  def get_step_name(self, prefix, task):
    """SwarmingTask -> name of a step of a waterfall.

    Will take a task name (+ step name prefix) and append OS dimension to it.

    Args:
      prefix: prefix to append to task name, like 'trigger'.
      task: SwarmingTask instance.

    Returns:
      '[<prefix>] <task name> on <OS>'
    """
    prefix = '[%s] ' % prefix if prefix else ''
    task_os = task.request[0].dimensions['os']

    bot_os = self.prefered_os_dimension(self.m.platform.name)
    suffix = ('' if (
        task_os == bot_os or task_os.lower() == self.m.platform.name.lower() or
        task_os in task.request.name)
              else ' on %s' % task_os)
    # Note: properly detecting dimensions of the bot the recipe is running
    # on is somewhat non-trivial. It is not safe to assume it uses default
    # or preferred dimensions for its OS. For example, the version of the OS
    # can differ.
    return ''.join((prefix, task.request.name, suffix))


  def _handle_summary_json(self, task, step_result):
    """Updates presentation with results from swarming collect.

    The presentation is updated with links and details for each of the shards.
    The presentation's status is set to:
      * EXCEPTION if there is any type of infra error.
      * FAILURE if shards timed out or had non-zero exit code.

    task.failed_shards is updated with the indices of the failed shards.

    Args:
      * task: The Task object with dispatched shards.
      * step_result: The StepData from the collect step.
    Returns: A StepFailure() exception describing an expected error, and a
             boolean representing if the results from this swarming task should
             be considered valid.
             Examples of expected errors include: An expired shard, a timed
             out shard, or test failures. If there are no issues, returns None.
             The task will be considered valid as long as it was able to
             successfully complete execution as expected. A failed task still
             can have valid results. A task which times out or has an internal
             failure does not, since the task didn't execute as intended.
    Raises: An InfraFailure() if there is an unexpected error. Examples include
            if the swarming summary is formatted incorrectly.
    """
    summary = step_result.chromium_swarming.summary
    # We store this now, and add links to all shards first, before failing the
    # build. Format is tuple of (error message, shard that failed)
    unexpected_errors = []
    expected_errors = []
    # Test failures should present as FAILURE [red].
    # Some expected errors [e.g. expiration] should present as EXCEPTION
    # [purple].
    expected_error_present_as_exception = False
    # Do we have valid results? We count shards as not having valid resuls if
    # they weren't able to complete execution normally, due to timing out or
    # the bot dying. Completing execution, but failing, gives valid results.
    has_valid_results = True
    failed_shards = []

    summary_shards = summary['shards']
    links = step_result.presentation.links
    for index, shard in enumerate(summary_shards):
      url = task.get_shard_view_url(index)
      duration = shard and shard.get('duration')
      if duration is not None:
        display_text = 'shard #%d (%.1f sec)' % (index, duration)
        self._shards_durations.append(duration)
      else:
        display_text = 'shard #%d' % index

      if shard and shard.get('deduped_from'):
        display_text += ' (deduped)'

      if not shard:
        display_text = 'shard #%d failed without producing output.json' % index
        unexpected_errors.append(
            (index, 'Details unknown (missing shard results)'))
        failed_shards.append(index)
        has_valid_results = False
      elif shard.get('internal_failure'):
        display_text = (
          'shard #%d had an internal swarming failure' % index)
        # Unfortunately, src/ tests can trigger swarming internal failures.
        # Examples include: macOS tests killing the window server.
        # Since we cannot distinguish between infra failures and test failures,
        # we mark this as an unexpected error.
        expected_errors.append((index, 'Internal swarming failure'))
        expected_error_present_as_exception = True
        failed_shards.append(index)
        has_valid_results = False
      elif shard.get('state') == 'EXPIRED':
        display_text = (
          'shard #%d expired, not enough capacity' % index)
        expected_errors.append(display_text)
        expected_error_present_as_exception = True
        failed_shards.append(index)
        has_valid_results = False
      elif shard.get('state') == 'TIMED_OUT':
        if duration is not None:
          display_text = (
              'shard #%d timed out after %.1f sec' % (index, duration))
        else: # pragma: no cover
          # TODO(tikuta): Add coverage for this code.
          display_text = (
              'shard #%d timed out, took too much time to complete' % index)
        expected_errors.append(display_text)
        failed_shards.append(index)
        has_valid_results = False
      elif self._get_exit_code(shard) != 0:
        # TODO(bpastene): Add coverage for this code.
        if duration is not None:  # pragma: no cover
          display_text = 'shard #%d (failed) (%.1f sec)' % (index, duration)
        else:
          display_text = 'shard #%d (failed)' % index
        expected_errors.append(display_text)
        failed_shards.append(index)

      # We only want to show shards if they were dispatched in this retry
      # step, not if they were duplicated from a previous step.
      should_show_shard = True
      if shard and task.task_to_retry:
        task_id = shard.get('task_id')
        dispatched_task_ids = set()
        for task_dict in task._trigger_output['tasks'].itervalues():
          dispatched_task_ids.add(task_dict['task_id'])
        should_show_shard = task_id in dispatched_task_ids

      if shard and self.show_outputs_ref_in_collect_step and should_show_shard:
        outputs_ref = shard.get('outputs_ref')
        if outputs_ref:
          link_name = 'shard #%d isolated out' % index
          links[link_name] = '%s/browse?namespace=%s&hash=%s' % (
            outputs_ref['isolatedserver'], outputs_ref['namespace'],
            outputs_ref['isolated'])

      if url and self.show_shards_in_collect_step and should_show_shard:
        links[display_text] = url

    # Keep track of this in case we want to retry failed shards later. Clients
    # will decide if they want to retry, we just keep track of failed shards
    # here.
    task.failed_shards = failed_shards

    self._display_pending(summary_shards, step_result.presentation)

    if unexpected_errors:
      template = 'Shard #%s failed: %s'

      step_result.presentation.status = self.m.step.EXCEPTION
      raise recipe_api.InfraFailure(
          '\n'.join(template % f for f in unexpected_errors),
          result=step_result)

    if expected_errors:
      step_result.presentation.status = (self.m.step.EXCEPTION if
          expected_error_present_as_exception else self.m.step.FAILURE)
      return recipe_api.StepFailure(str(expected_errors),
                                    result=step_result), has_valid_results

    return None, has_valid_results

  def get_collect_cmd_args(self, task):
    """
    SwarmingTask -> argument list for go swarming command.
    """
    args = [
      'collect',
      '-server', self.swarming_server,

      # TODO(tikuta): Tuning this if necessary.
      '-worker', 50,

      '-task-summary-python',
      '-task-output-stdout', self.task_output_stdout,

      # This is necessary not to cause io timeout.
      '-verbose',
    ]

    args.extend(('-requests-json', self.m.json.input(task.collect_cmd_input())))
    if self.service_account_json:
      args.extend(['-service-account-json', self.service_account_json])
    return args

  def _gen_trigger_step_test_data(self, task, shard_indices):
    """Generates an expected value of --dump-json in 'trigger' step.

    Used when running recipes to generate test expectations.
    """
    # Suffixes of shard subtask names.
    subtasks = []
    if task.shards == 1:
      subtasks = [('', 0)]
    else:
      subtasks = [(':%d:%d' % (task.shards, i), i)
                  for i in shard_indices]
    self._task_test_data_id_offset += len(subtasks)
    tid = lambda i: '1%02d00' % (
        i + 100*(self._task_test_data_id_offset - len(subtasks)))
    return self.m.json.test_api.output({
      'base_task_name': task.task_name,
      'tasks': {
        '%s%s' % (task.task_name, suffix): {
          'task_id': tid(i),
          'shard_index': i,
          'view_url': '%s/user/task/%s' % (self.swarming_server, tid(i)),
        } for (suffix, i) in subtasks
      },
    })

  def configure_swarming(self, project_name, precommit, mastername=None,
                         default_priority=None, path_to_testing_dir=None):
    """Configures default swarming dimensions and tags.

    Uses the 'chromium' global config to determine target platform defaults,
    make sure something like chromium_tests.configure_build() has been called
    beforehand.

    Args:
      project_name: Lowercase name of the project, e.g. "blink", "chromium".
      precommit: Boolean flag to indicate whether the tests are running before
          the changes are commited.
      mastername: optional name of the mastername to use to configure the
          default priority of swarming tasks.
      default_priority: optional default_priority to use. Will override the
          priority name inherited from the mastername (or the global default).
      path_to_testing_dir: The path to a local directory mirroring
          https://chromium.googlesource.com/chromium/src/+/master/testing. This
          is needed to access merge and trigger scripts. If unset, this module
          will look at self.m.chromium_checkout.working_dir.
    """

    # Set platform-specific default dims.
    target_platform = self.m.chromium.c.TARGET_PLATFORM
    swarming_dims = PER_TARGET_SWARMING_DIMS[target_platform]

    for k, v in swarming_dims.iteritems():
      self.set_default_dimension(k, v)

    self.set_default_dimension('pool', 'Chrome')
    self.add_default_tag('project:%s' % project_name)
    self.default_idempotent = True
    self.show_shards_in_collect_step = True

    if precommit:
      self.default_priority = 30
      self.add_default_tag('purpose:pre-commit')
      requester = self.m.properties.get('requester')
      if requester == 'commit-bot@chromium.org':
        self.add_default_tag('purpose:CQ')
        blamelist = self.m.properties.get('blamelist')
        if len(blamelist) == 1:
          requester = blamelist[0]
      else:
        self.add_default_tag('purpose:ManualTS')
      self.default_user = requester

      if self.m.tryserver.gerrit_change:
        self.add_default_tag(
            'patch_project:%s' % self.m.tryserver.gerrit_change.project)
    else:
      self.default_priority = MASTER_SWARMING_PRIORITIES[mastername]
      self.add_default_tag('purpose:post-commit')
      self.add_default_tag('purpose:CI')

    if default_priority is not None:
      # TODO(crbug.com/876570): We should move the Mojo builders to a
      # different "master" and get rid of this code path; we don't really want
      # different builders on the same master to have different priorities,
      # it makes reasoning about builders harder for sheriffs and troopers.
      self.default_priority = default_priority

    if self.m.runtime.is_experimental:
      # The experimental half of LUCI conversions should be lower than
      # everything else.
      self.default_priority = 40
    if self.m.runtime.is_luci:
      self.add_default_tag('purpose:luci')

    # TODO(tikuta): Remove this (crbug.com/894045).
    self.use_go_client = True # pylint: disable=attribute-defined-outside-init

    if path_to_testing_dir:
      self._path_to_testing_dir = path_to_testing_dir
    else:
      # TODO(martiniss): Assert that working_dir is not None once the
      # auto_bisect module is deleted.
      self._path_to_testing_dir = self.m.chromium_checkout.working_dir.join(
          'src', 'testing')


class SwarmingTask(object):
  """Definition of a task to run on swarming."""

  def __init__(self, request, collect_step, extra_args, ignore_task_failure,
               shards, shard_indices, spec_name, task_output_dir,
               build_properties=None, builder_info=None, containment_type=None,
               merge=None, named_caches=None, optional_dimensions=None,
               task_to_retry=None, trigger_script=None):

    """Configuration of a swarming task.

    Args:
      * request: swarming.TaskRequest instance as created by
          swarming.task_request().
      * build_properties: An optional dict containing various build properties.
          These are typically but not necessarily the properties emitted by
          bot_update.
      * builder_info: Information about the builder collected from buildbucket.
        Usually composed of buildername and buildnumber.
      * collect_step: callback that will be called to collect and processes
          results of task execution. Expected signature is
          collect_step(task, **kwargs).
      * containment_type: string. Type of containment to use for the task. This
          is being added to fix https://crbug.com/965222, please talk to
          martiniss@ if you are using this feature; it should be deleted in the
          next few months.
      * extra_args: list of command line arguments to pass to isolated tasks.
      * ignore_task_failure: whether to ignore the test failure of swarming
          tasks.
      * merge: An optional dict containing:
        * "script": path to a script to call to post process and merge the
              collected outputs from the tasks.
        * "args": an optional list of additional arguments to pass to the
              above script.
      * named_caches: a dict {name: relpath} requesting a cache named `name`
          to be installed in `relpath` relative to the task root directory..
      * spec_name: task spec name. Used in monitoring.
      * task_output_dir: if defined, the directory where task results are placed
          during the collect step.
      * task_to_retry: Task object. If set, indicates that this task is a
          (potentially partial) retry of another task. When collecting, should
          re-use some shards from the retried task.
      * trigger_script: An optional dict containing:
        * "script": path to a script to call which will use custom logic to
              trigger appropriate swarming jobs, using swarming.py. Required.
        * "args": an optional list of additional arguments to pass to the
              script.
          The script will receive the exact same arguments that are normally
          passed to calls to `swarming.py trigger`, along with any arguments
          provided in the "args" entry.

          The script is required to output a json file to the location provided
          by the --dump-json argument. This json file should describe the
          swarming tasks it launched, as well as some information about the
          request, which is used when swarming collects the tasks.

          If the script launches multiple swarming shards, it needs to pass the
          appropriate environment variables to each shard (this is normally done
          by swarming.py trigger). Specifically, each shard should receive
          GTEST_SHARD_INDEX, which is its shard index, and
          GTEST_TOTAL_SHARDS, which is the total number of shards.
          This can be done by passing `--env GTEST_SHARD_INDEX [NUM]` and
          `--env GTEST_SHARD_SHARDS [NUM]` when calling swarming.py trigger.
    """
    self._trigger_output = None
    self.build_properties = build_properties
    self.builder_info = builder_info
    self.collect_step = collect_step
    self.containment_type = containment_type
    self.extra_args = extra_args or []
    self.failed_shards = []
    self.ignore_task_failure = ignore_task_failure
    self.merge = merge or {}
    self.named_caches = named_caches or {}
    self.optional_dimensions = optional_dimensions
    self.request = request
    self.shards = shards
    self.shard_indices = shard_indices
    self.spec_name = spec_name
    self.tags = set()
    self.task_output_dir = task_output_dir
    self.task_to_retry = task_to_retry
    self.trigger_script = trigger_script or {}
    self.wait_for_capacity = False

  @property
  def task_name(self):
    """Name of this task, derived from its other properties.

    The task name is purely to make sense of the task and is not used in any
    other way.
    """
    task_name_suffix = ''
    if self.builder_info:
      task_name_suffix += '/%s/%s' % (
        self.builder_info[0], self.builder_info[1])

    return '%s/%s/%s%s' % (
        self.request.name,
        self.request[0].dimensions['os'],
        self.request[0].isolated[:10],
        task_name_suffix
    )
  @property
  def trigger_output(self):
    """JSON results of 'trigger' step or None if not triggered.

    This includes shards whose results are being reused from a previous retry
    attempt. The actual triggered shards from this attempt can be obtained by
    directly accessing the member.
    """
    # JSON results of 'trigger' step converted for luci-go client.
    # This is used for isolated script tasks.
    tasks = sorted(self._trigger_output['tasks'].values(),
                   key=lambda x: x['shard_index'])
    if self.task_to_retry:
      old_tasks = copy.deepcopy(self.task_to_retry.trigger_output['tasks'])

      # Overwrite old task outputs with new ones.
      for task in tasks:
        old_tasks[task['shard_index']] = task

      tasks = old_tasks.values()

    return {
        'tasks': {task['shard_index']: task for task in tasks},
    }

  def collect_cmd_input(self):
    """Returns a list of tasks.

    Intended to be passed as an argument to `swarming collect`.
    """
    return {
        'tasks': [{
            'task_id': task['task_id']
        } for task in self.trigger_output['tasks'].values()]
    }

  def get_task_shard_output_dirs(self):
    """Return the directory of each task shard outputs."""
    return self.get_task_ids()

  def get_shard_view_url(self, index, trigger_output=None):
    """Returns URL of HTML page with shard details or None if not available.

    Works only after the task has been successfully triggered.

    Args:
      index: The index of the triggered shard.
      trigger_output: The JSON output of the triggered swarming task.
    """
    if trigger_output is None:
      trigger_output = self.trigger_output
    if trigger_output and trigger_output.get('tasks'):
      for shard_dict in trigger_output['tasks'].itervalues():
        if shard_dict['shard_index'] == index:
          return shard_dict['view_url']

  def get_task_ids(self):
    """Returns task id of all shards.

    Works only after the task has been successfully triggered.
    """
    task_ids = []
    if self.trigger_output and self.trigger_output.get('tasks'):
      for shard_dict in self.trigger_output['tasks'].itervalues():
        task_ids.append(shard_dict['task_id'])
    return task_ids
