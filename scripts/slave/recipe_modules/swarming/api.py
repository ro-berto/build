# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime
import functools
import hashlib
import logging
import os.path

from recipe_engine import recipe_api
from recipe_engine import util as recipe_util

# Minimally supported version of swarming.py script (reported by --version).
MINIMAL_SWARMING_VERSION = (0, 8, 6)


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

  if task.dimensions.get('id'):
    lines.append('Bot id: %r' % task.dimensions['id'])
  if task.dimensions.get('os'):
    lines.append('Run on OS: %r' % task.dimensions['os'])

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

  class State(object):
    """Copied from appengine/swarming/server/task_result.py.

    KEEP IN SYNC.

    Used to parse the 'state' value in task result.
    """
    RUNNING = 0x10    # 16
    PENDING = 0x20    # 32
    EXPIRED = 0x30    # 48
    TIMED_OUT = 0x40  # 64
    BOT_DIED = 0x50   # 80
    CANCELED = 0x60   # 96
    COMPLETED = 0x70  # 112

    STATES = (
        RUNNING, PENDING, EXPIRED, TIMED_OUT, BOT_DIED, CANCELED, COMPLETED)
    STATES_RUNNING = (RUNNING, PENDING)
    STATES_NOT_RUNNING = (EXPIRED, TIMED_OUT, BOT_DIED, CANCELED, COMPLETED)
    STATES_DONE = (TIMED_OUT, COMPLETED)
    STATES_ABANDONED = (EXPIRED, BOT_DIED, CANCELED)

    _NAMES = {
      RUNNING: 'Running',
      PENDING: 'Pending',
      EXPIRED: 'Expired',
      TIMED_OUT: 'Execution timed out',
      BOT_DIED: 'Bot died',
      CANCELED: 'User canceled',
      COMPLETED: 'Completed',
    }

    @classmethod
    def to_string(cls, state):
      """Returns a user-readable string representing a State."""
      return cls._NAMES[state]

  #############################################################################
  # The below are helper functions to help transition between the old and new #
  # swarming result formats. TODO(martiniss): remove these                    #
  #############################################################################

  def _is_expired(self, shard):
    # FIXME: We really should only have one format for enums. We want to move to
    # strings, currently have numbers.
    return (
        shard.get('state') == self.State.EXPIRED or
        shard.get('state') == 'EXPIRED')

  def _is_timed_out(self, shard):
    # FIXME: We really should only have one format for enums. We want to move to
    # strings, currently have numbers.
    return (
        shard.get('state') == self.State.TIMED_OUT or
        shard.get('state') == 'TIMED_OUT')

  def _get_exit_code(self, shard):
    if shard.get('exit_code'):
      return shard.get('exit_code')
    lst = shard.get('exit_codes', [])
    return str(lst[0]) if lst else None

  def __init__(self, **kwargs):
    super(SwarmingApi, self).__init__(**kwargs)
    # All tests default to a x86-64 bot running with no GPU. This simplifies
    # management so that new tests are not executed on exotic bots by accidents
    # even if misconfigured.
    self._default_dimensions = {
      'cpu': 'x86-64',
      'gpu': 'none',
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
    self._show_isolated_out_in_collect_step = True
    self._show_shards_in_collect_step = False
    self._swarming_server = 'https://chromium-swarm.appspot.com'
    self._verbose = False

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

  def add_default_tag(self, tag):
    """Adds a tag to the Swarming tasks triggered.

    Tags are used for maintenance, they can be used to calculate the number of
    tasks run for a day to calculate the cost of a type of type (CQ, ASAN, etc).

    Tags can be added per individual task.
    """
    assert ':' in tag, tag
    self._default_tags.add(tag)

  @property
  def show_isolated_out_in_collect_step(self):
    """Show the shard's isolated out link in each collect step."""
    return self._show_isolated_out_in_collect_step

  @show_isolated_out_in_collect_step.setter
  def show_isolated_out_in_collect_step(self, value):
    self._show_isolated_out_in_collect_step = value

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
      'linux': 'Ubuntu-12.04',
      'mac': 'Mac-10.9',
      'win': 'Windows-7-SP1',
    }[platform]

  def task(self, title, isolated_hash, shards=1, task_output_dir=None,
           extra_args=None, idempotent=None, cipd_packages=None,
           build_properties=None, merge=None):
    """Returns a new SwarmingTask instance to run an isolated executable on
    Swarming.

    For google test executables, use gtest_task() instead.

    At the time of this writting, this code is used by V8, Skia and iOS.

    The return value can be customized if necessary (see SwarmingTask class
    below). Pass it to 'trigger_task' to launch it on swarming. Later pass the
    same instance to 'collect_task' to wait for the task to finish and fetch its
    results.

    Args:
      title: name of the test, used as part of a task ID.
      isolated_hash: hash of isolated test on isolate server, the test should
          be already isolated there, see 'isolate' recipe module.
      shards: if defined, the number of shards to use for the task. By default
          this value is either 1 or based on the title.
      task_output_dir: if defined, the directory where task results are placed.
          The caller is responsible for removing this folder when finished.
      extra_args: list of command line arguments to pass to isolated tasks.
      idempotent: whether this task is considered idempotent. Defaults
          to self.default_idempotent if not specified.
      cipd_packages: list of 3-tuples corresponding to CIPD packages needed for
          the task: ('path', 'package_name', 'version'), defined as follows:
              path: Path relative to the Swarming root dir in which to install
                  the package.
              package_name: Name of the package to install,
                  eg. "infra/tools/authutil/${platform}"
              version: Version of the package, either a package instance ID,
                  ref, or tag key/value pair.
      build_properties: An optional dict containing various build properties.
          These are typically but not necessarily the properties emitted by
          bot_update.
      merge: An optional dict containing:
          "merge": path to a script to call to post process and merge the
              collected outputs from the tasks. The script should take one
              named (but required) parameter, '-o' (for output), that represents
              the path that the merged results should be written to, and accept
              N additional paths to result files to merge. The merged results
              should be in the JSON Results File Format
              (https://www.chromium.org/developers/the-json-test-results-format)
              and may optionally contain a top level "links" field that
              may contain a dict mapping link text to URLs, for a set of
              links that will be included in the buildbot output.
          "args": an optional list of additional arguments to pass to the
              above script.
    """
    if idempotent is None:
      idempotent = self.default_idempotent
    return SwarmingTask(
        title=title,
        isolated_hash=isolated_hash,
        dimensions=self._default_dimensions,
        env=self._default_env,
        priority=self.default_priority,
        shards=shards,
        buildername=self.m.properties.get('buildername'),
        buildnumber=self.m.properties.get('buildnumber'),
        user=self.default_user,
        expiration=self.default_expiration,
        io_timeout=self.default_io_timeout,
        hard_timeout=self.default_hard_timeout,
        idempotent=idempotent,
        extra_args=extra_args,
        collect_step=self._default_collect_step,
        task_output_dir=task_output_dir,
        cipd_packages=cipd_packages,
        build_properties=build_properties,
        merge=merge)

  def gtest_task(self, title, isolated_hash, test_launcher_summary_output=None,
                 extra_args=None, cipd_packages=None, **kwargs):
    """Returns a new SwarmingTask instance to run an isolated gtest on Swarming.

    Swarming recipe module knows how collect and interpret JSON files with test
    execution summary produced by chromium test launcher. It will combine JSON
    results from multiple shards and place it in path provided by
    |test_launcher_summary_output| placeholder.

    For meaning of the rest of the arguments see 'task' method.
    """
    extra_args = list(extra_args or [])

    # Ensure --test-launcher-summary-output is not already passed. We are going
    # to overwrite it.
    bad_args = any(
        x.startswith('--test-launcher-summary-output=') for x in extra_args)
    if bad_args:  # pragma: no cover
      raise ValueError('--test-launcher-summary-output should not be used.')

    # Append it. output.json name is expected by collect_gtest_task.py.
    extra_args.append(
        '--test-launcher-summary-output=${ISOLATED_OUTDIR}/output.json')

    # Make a task, configure it to be collected through shim script.
    task = self.task(title, isolated_hash, extra_args=extra_args,
                     cipd_packages=cipd_packages, **kwargs)
    task.collect_step = lambda *args, **kw: (
        self._gtest_collect_step(test_launcher_summary_output, *args, **kw))
    return task

  def _check_and_set_output_flag(self, extra_args, flag, output_file_name):
    extra_args = list(extra_args or [])
    # Ensure flag is not already passed. We are going to overwrite it.
    flag_value = '--%s=' % flag
    bad_args = any(x.startswith(flag_value) for x in extra_args)
    if bad_args: # pragma: no cover
      raise ValueError('--%s should not be used' % flag)

    # Append it.
    output_arg = '--%s=${ISOLATED_OUTDIR}/%s' % (flag, output_file_name)
    extra_args.append(output_arg)
    return extra_args

  def isolated_script_task(self, title, isolated_hash, extra_args=None,
                           idempotent=False, **kwargs):
    """Returns a new SwarmingTask to run an isolated script test on Swarming.

    At the time of this writting, this code is used by WebRTC and
    "isolated_scripts" entries in Chromium's src/testing/buildbot/*.json.

    Swarming recipe module knows how collect JSON file with test execution
    summary produced by isolated script tests launcher. A custom script
    can be passed to merge the collected results and post-process them.

    For meaning of the rest of the arguments see 'task' method.
    """

    # Ensure output flags are not already passed. We are going
    # to overwrite them.
    # output.json name is expected by collect_gtest_task.py.
    extra_args = self._check_and_set_output_flag(
      extra_args, 'isolated-script-test-output', 'output.json')
    # chartjson-output.json name is expected by benchmarks generating chartjson
    # output
    extra_args = self._check_and_set_output_flag(
      extra_args,
      'isolated-script-test-chartjson-output',
      'chartjson-output.json')

    task = self.task(title, isolated_hash, extra_args=extra_args,
                     idempotent=idempotent, **kwargs)
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

    Behaves as a regular recipe step: returns StepData with step results
    on success or raises StepFailure if step fails.

    Args:
      task: SwarmingTask instance.
      kwargs: passed to recipe step constructor as-is.
    """
    assert isinstance(task, SwarmingTask)
    assert task.task_name not in self._pending_tasks, (
        'Triggered same task twice: %s' % task.task_name)
    assert 'os' in task.dimensions, task.dimensions
    self._pending_tasks.add(task.task_name)

    # Trigger parameters.
    args = [
      'trigger',
      '--swarming', self.swarming_server,
      '--isolate-server', self.m.isolate.isolate_server,
      '--priority', str(task.priority),
      '--shards', str(task.shards),
      '--task-name', task.task_name,
      '--dump-json', self.m.json.output(),
      '--expiration', str(task.expiration),
      '--io-timeout', str(task.io_timeout),
      '--hard-timeout', str(task.hard_timeout),
    ]
    for name, value in sorted(task.dimensions.iteritems()):
      assert isinstance(value, basestring), value
      args.extend(['--dimension', name, value])
    for name, value in sorted(task.env.iteritems()):
      assert isinstance(value, basestring), value
      args.extend(['--env', name, value])

    # Default tags.
    tags = set(task.tags)
    tags.update(self._default_tags)
    tags.add('data:' + task.isolated_hash)
    tags.add('name:' + task.title.split(' ')[0])
    mastername = self.m.properties.get('mastername')
    if mastername:
      tags.add('master:' + mastername)
    if task.buildername:
      tags.add('buildername:' + task.buildername)
    if task.buildnumber:
      tags.add('buildnumber:%s' % task.buildnumber)
    if task.dimensions.get('os'):
      tags.add('os:' + task.dimensions['os'])
    if self.m.properties.get('slavename'):
      tags.add('slavename:%s' % self.m.properties['slavename'])
    tags.add('stepname:%s' % self.get_step_name('', task))
    rietveld = self.m.properties.get('rietveld')
    issue = self.m.properties.get('issue')
    patchset = self.m.properties.get('patchset')
    if rietveld and issue and patchset:
      # The expected format is strict to the usage of buildbot properties on the
      # Chromium Try Server. Fix if necessary.
      tags.add('rietveld:%s/%s/#ps%s' % (rietveld, issue, patchset))
    for tag in sorted(tags):
      assert ':' in tag, tag
      args.extend(['--tag', tag])

    if self.verbose:
      args.append('--verbose')
    if task.idempotent:
      args.append('--idempotent')
    if task.user:
      args.extend(['--user', task.user])

    if task.cipd_packages:
      for path, pkg, version in task.cipd_packages:
        args.extend(['--cipd-package', '%s:%s:%s' % (path, pkg, version)])

    # What isolated command to trigger.
    args.append(task.isolated_hash)

    # Additional command line args for isolated command.
    if task.extra_args:
      args.append('--')
      args.extend(task.extra_args)

    # The step can fail only on infra failures, so mark it as 'infra_step'.
    try:
      return self.m.python(
          name=self.get_step_name('trigger', task),
          script=self.m.swarming_client.path.join('swarming.py'),
          args=args,
          step_test_data=functools.partial(
              self._gen_trigger_step_test_data, task),
          infra_step=True,
          **kwargs)
    finally:
      # Store trigger output with the |task|, print links to triggered shards.
      step_result = self.m.step.active_result
      step_result.presentation.step_text += text_for_task(task)

      if step_result.presentation != self.m.step.FAILURE:
        task._trigger_output = step_result.json.output
        links = step_result.presentation.links
        for index in xrange(task.shards):
          url = task.get_shard_view_url(index)
          if url:
            links['shard #%d' % index] = url
      assert not hasattr(step_result, 'swarming_task')
      step_result.swarming_task = task

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
      self.m.step.active_result.swarming_task = task

  def trigger(self, tasks, **kwargs):  # pragma: no cover
    """Batch version of 'trigger_task'.

    Deprecated, to be removed soon. Use 'trigger_task' in a loop instead,
    properly handling exceptions. This method doesn't handle trigger failures
    well (it aborts on a first failure).
    """
    return [self.trigger_task(t, **kwargs) for t in tasks]

  def collect(self, tasks, **kwargs):  # pragma: no cover
    """Batch version of 'collect_task'.

    Deprecated, to be removed soon. Use 'collect_task' in a loop instead,
    properly handling exceptions. This method doesn't handle collect failures
    well (it aborts on a first failure).
    """
    return [self.collect_task(t, **kwargs) for t in tasks]

  # To keep compatibility with some build_internal code. To be removed as well.
  collect_each = collect

  @staticmethod
  def _display_pending(summary_json, step_presentation):
    """Shows max pending time in seconds across all shards if it exceeds 10s."""
    pending_times = [
      (parse_time(shard['started_ts']) -
        parse_time(shard['created_ts'])).total_seconds()
      for shard in summary_json.get('shards', []) if shard.get('started_ts')
    ]
    max_pending = max(pending_times) if pending_times else 0

    # Only display annotation when pending more than 10 seconds to reduce noise.
    if max_pending > 10:
      step_presentation.step_text += '<br>swarming pending %ds' % max_pending

  def _default_collect_step(self, task, **kwargs):
    """Produces a step that collects a result of an arbitrary task."""
    args = self.get_collect_cmd_args(task)
    args.extend(['--task-summary-json', self.m.json.output()])
    if task.task_output_dir:
      args.extend(['--task-output-dir', task.task_output_dir])

    try:
      return self.m.python(
          name=self.get_step_name('', task),
          script=self.m.swarming_client.path.join('swarming.py'),
          args=args,
          step_test_data=functools.partial(
              self._gen_collect_step_test_data, task),
          **kwargs)
    finally:
      step_result = self.m.step.active_result

      step_result.presentation.step_text = text_for_task(task)
      summary_json = step_result.json.output
      if summary_json:
        self._handle_summary_json(task, summary_json, step_result)

  def _gtest_collect_step(self, merged_test_output, task, **kwargs):
    """Produces a step that collects and processes a result of google-test task.
    """
    args = [
      'python',
      self.resource('collect_gtest_task.py'),
      '--swarming-client-dir', self.m.swarming_client.path,
      '--temp-root-dir', self.m.path['tmp_base'],
    ]

    # Where to put combined summary to, consumed by recipes. Also emit
    # test expectation only if |merged_test_output| is really used.
    step_test_data = kwargs.pop('step_test_data', None)
    if merged_test_output:
      args.extend(['--merged-test-output', merged_test_output])
      if not step_test_data:
        sample_swarming_summary = {
          'swarming_summary': {
            'shards': [{
              'outputs_ref': {
                'view_url': 'blah',
              },
            }]
          },
        }

        step_test_data = lambda: self.m.test_utils.test_api.canned_gtest_output(
            True, extra_json=sample_swarming_summary)

    # Arguments for actual 'collect' command.
    args.append('--')
    args.extend(self.get_collect_cmd_args(task))

    # Always wait for all tasks to finish even if some of them failed. Allow
    # collect_gtest_task.py to emit all necessary annotations itself.
    try:
      return self.m.python(
          name=self.get_step_name('', task),
          script=self.package_repo_resource('scripts', 'tools', 'runit.py'),
          args=args,
          allow_subannotations=True,
          step_test_data=step_test_data,
          **kwargs)
    finally:
      # HACK: it is assumed that caller used 'api.test_utils.gtest_results'
      # placeholder for 'test_launcher_summary_output' parameter when calling
      # gtest_task(...). It's not enforced in any way.
      step_result = self.m.step.active_result

      step_result.presentation.step_text = text_for_task(task)
      gtest_results = getattr(step_result.test_utils, 'gtest_results', None)
      if gtest_results and gtest_results.raw:
        p = step_result.presentation
        missing_shards = gtest_results.raw.get('missing_shards') or []
        if missing_shards:
          step_result.presentation.status = self.m.step.EXCEPTION
          for index in missing_shards:
            p.links['missing shard #%d' % index] = \
                task.get_shard_view_url(index)
        if gtest_results.valid:
          p.step_text += self.m.test_utils.format_step_text([
            ['failures:', gtest_results.failures]
          ])
        swarming_summary = gtest_results.raw.get('swarming_summary', {})
        self._display_pending(swarming_summary, step_result.presentation)

        # Show any remaining isolated outputs (such as logcats).
        # Note that collect_gtest_task.py uses the default summary.json, which
        # only has 'outputs_ref' instead of the deprecated 'isolated_out'.
        for index, shard in enumerate(swarming_summary.get('shards', [])):
          outputs_ref = shard.get('outputs_ref')
          if outputs_ref:
            link_name = 'shard #%d isolated out' % index
            p.links[link_name] = outputs_ref['view_url']

  def _merge_isolated_script_chartjson_output_shards(self, task, step_result):
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
    merged_results = {}
    seen_first_shard = False
    for i in xrange(task.shards):
      path = self.m.path.join(str(i), 'chartjson-output.json')
      if path not in step_result.raw_io.output_dir:
        # chartjson results were not written for this shard, not an error,
        # just continue to the next shard
        continue
      results_raw = step_result.raw_io.output_dir[path]
      try:
        chartjson_results_json = self.m.json.loads(results_raw)
      except Exception as e:
        raise Exception('error decoding chart JSON results from shard #%d' % i)
      if not seen_first_shard:
        merged_results = chartjson_results_json
        seen_first_shard = True
        continue
      for key in chartjson_results_json:
        if key == 'charts':
          # Append each additional chart to our merged results
          for add_key in chartjson_results_json[key]:
            merged_results[key][add_key] = chartjson_results_json[key][add_key]
    return merged_results

  def _isolated_script_collect_step(self, task, **kwargs):
    """Collects results for a step that is *not* a googletest, like telemetry.
    """
    step_test_data = kwargs.pop('step_test_data', None)
    if not step_test_data:
      step_test_data = self.m.test_utils.test_api.canned_isolated_script_output(
          passing=True, is_win=self.m.platform.is_win, swarming=True,
          use_json_test_format=True)

    collect_cmd = [
      'python',
      self.m.swarming_client.path.join('swarming.py')
    ]
    collect_cmd.extend(self.get_collect_cmd_args(task))

    task_args = [
      '-o', self.m.json.output(),
      '--task-output-dir', self.m.raw_io.output_dir()
    ]
    if task.build_properties:
      task_args.extend([
          '--build-properties', self.m.json.dumps(task.build_properties),
      ])

    merge_script = (task.merge.get('script')
                    or self.resource('standard_isolated_script_merge.py'))
    merge_args = (task.merge.get('args') or [])

    task_args.extend([
        '--merge-script', merge_script,
        '--merge-additional-args', self.m.json.dumps(merge_args),
    ])

    task_args.append('--')
    task_args.extend(collect_cmd)

    try:
      return self.m.python(
          name=self.get_step_name('', task),
          script=self.resource('collect_isolated_script_task.py'),
          args=task_args,
          step_test_data=lambda: step_test_data,
          **kwargs)
    finally:
      # Regardless of the outcome of the test (pass or fail), we try to parse
      # the results. If any error occurs while parsing results, then we set them
      # to None, which caller should treat as invalid results.
      # Note that try-except block below will not mask the
      # recipe_api.StepFailure exception from the collect step above. Instead
      # it is being allowed to propagate after the results have been parsed.
      try:
        step_result = self.m.step.active_result

        outdir = filter_outdir(
            self.m.json.dumps, step_result.raw_io.output_dir)
        outdir_json = self.m.json.dumps(outdir, indent=2)
        step_result.presentation.logs['outdir_json'] = outdir_json.splitlines()

        step_result.presentation.step_text = text_for_task(task)

        # Check if it's an internal failure. 'summary.json' is saved in the
        # output directory.
        summary_json = self.m.json.loads(
            step_result.raw_io.output_dir['summary.json'])

        self._handle_summary_json(task, summary_json, step_result)

        step_result.isolated_script_results = step_result.json.output
        links = (step_result.isolated_script_results or {}).get('links', {})
        for k, v in links.iteritems():
          step_result.presentation.links[k] = v

        # Obtain chartjson results if present
        step_result.isolated_script_chartjson_results = \
          self._merge_isolated_script_chartjson_output_shards(task, step_result)

      except Exception as e:
        self.m.step.active_result.presentation.logs['no_results_exc'] = [str(e)]
        self.m.step.active_result.isolated_script_results = None

  def get_step_name(self, prefix, task):
    """SwarmingTask -> name of a step of a waterfall.

    Will take a task title (+ step name prefix) and append OS dimension to it.

    Args:
      prefix: prefix to append to task title, like 'trigger'.
      task: SwarmingTask instance.

    Returns:
      '[<prefix>] <task title> on <OS>'
    """
    prefix = '[%s] ' % prefix if prefix else ''
    task_os = task.dimensions['os']

    bot_os = self.prefered_os_dimension(self.m.platform.name)
    suffix = ('' if (
        task_os == bot_os or task_os.lower() == self.m.platform.name.lower())
              else ' on %s' % task_os)
    # Note: properly detecting dimensions of the bot the recipe is running
    # on is somewhat non-trivial. It is not safe to assume it uses default
    # or preferred dimensions for its OS. For example, the version of the OS
    # can differ.
    return ''.join((prefix, task.title, suffix))

  def _handle_summary_json(self, task, summary, step_result):
    # We store this now, and add links to all shards first, before failing the
    # build. Format is tuple of (error message, shard that failed)
    infra_failures = []
    links = step_result.presentation.links
    for index, shard in enumerate(summary['shards']):
      url = task.get_shard_view_url(index)
      display_text = 'shard #%d' % index

      if not shard or shard.get('internal_failure'):
        display_text = (
          'shard #%d had an internal swarming failure' % index)
        infra_failures.append((index, 'Internal swarming failure'))
      elif self._is_expired(shard):
        display_text = (
          'shard #%d expired, not enough capacity' % index)
        infra_failures.append((
            index, 'There isn\'t enough capacity to run your test'))
      elif self._is_timed_out(shard):
        display_text = (
          'shard #%d timed out, took too much time to complete' % index)
      elif self._get_exit_code(shard) != '0':
        display_text = 'shard #%d (failed)' % index

      if self.show_isolated_out_in_collect_step:
        isolated_out = shard.get('isolated_out')
        if isolated_out:
          link_name = 'shard #%d isolated out' % index
          links[link_name] = isolated_out['view_url']

      if url and self.show_shards_in_collect_step:
        links[display_text] = url

    self._display_pending(summary, step_result.presentation)

    if infra_failures:
      template = 'Shard #%s failed: %s'

      # Done so that raising an InfraFailure doesn't cause an error.
      # TODO(martiniss): Remove this hack. Requires recipe engine change
      step_result._retcode = 2
      step_result.presentation.status = self.m.step.EXCEPTION
      raise recipe_api.InfraFailure(
          '\n'.join(template % f for f in infra_failures), result=step_result)

  def get_collect_cmd_args(self, task):
    """SwarmingTask -> argument list for 'swarming.py' command."""
    args = [
      'collect',
      '--swarming', self.swarming_server,
      '--decorate',
      '--print-status-updates',
    ]
    if self.verbose:
      args.append('--verbose')
    args.extend(('--json', self.m.json.input(task.trigger_output)))
    return args

  def _gen_trigger_step_test_data(self, task):
    """Generates an expected value of --dump-json in 'trigger' step.

    Used when running recipes to generate test expectations.
    """
    # Suffixes of shard subtask names.
    subtasks = []
    if task.shards == 1:
      subtasks = ['']
    else:
      subtasks = [':%d:%d' % (task.shards, i) for i in range(task.shards)]
    return self.m.json.test_api.output({
      'base_task_name': task.task_name,
      'tasks': {
        '%s%s' % (task.task_name, suffix): {
          'task_id': '1%02d00' % i,
          'shard_index': i,
          'view_url': '%s/user/task/1%02d00' % (self.swarming_server, i),
        } for i, suffix in enumerate(subtasks)
      },
    })

  def _gen_collect_step_test_data(self, task):
    """Generates an expected value of --task-summary-json in 'collect' step.

    Used when running recipes to generate test expectations.
    """
    return self.m.json.test_api.output({
      'shards': [
        {
          'abandoned_ts': None,
          'bot_id': 'vm30',
          'completed_ts': '2014-09-25T01:42:00.123',
          'created_ts': '2014-09-25T01:41:00.123',
          'durations': [5.7, 31.5],
          'exit_codes': [0, 0],
          'failure': False,
          'id': '148aa78d7aa%02d00' % i,
          'internal_failure': False,
          'isolated_out': {
            'isolated': 'abc123',
            'isolatedserver': 'https://isolateserver.appspot.com',
            'namespace': 'default-gzip',
            'view_url': 'blah',
          },
          'modified_ts': '2014-09-25 01:42:00',
          'name': 'heartbeat-canary-2014-09-25_01:41:55-os=Windows',
          'outputs': [
            'Heart beat succeeded on win32.\n',
            'Foo',
          ],
          'started_ts': '2014-09-25T01:42:11.123',
          'state': self.State.COMPLETED,
          'try_number': 1,
          'user': 'unknown',
        } for i in xrange(task.shards)
      ],
    })


class SwarmingTask(object):
  """Definition of a task to run on swarming."""

  def __init__(self, title, isolated_hash, dimensions, env, priority,
               shards, buildername, buildnumber, expiration, user, io_timeout,
               hard_timeout, idempotent, extra_args, collect_step,
               task_output_dir, cipd_packages=None, build_properties=None,
               merge=None):
    """Configuration of a swarming task.

    Args:
      title: display name of the task, hints to what task is doing. Usually
          corresponds to a name of a test executable. Doesn't have to be unique.
      isolated_hash: hash of isolated file that describes all files needed to
          run the task as well as command line to launch. See 'isolate' recipe
          module.
      cipd_packages: list of 3-tuples corresponding to CIPD packages needed for
          the task: ('path', 'package_name', 'version'), defined as follows:
              path: Path relative to the Swarming root dir in which to install
                  the package.
              package_name: Name of the package to install,
                  eg. "infra/tools/authutil/${platform}"
              version: Version of the package, either a package instance ID,
                  ref, or tag key/value pair.
      collect_step: callback that will be called to collect and processes
          results of task execution, signature is collect_step(task, **kwargs).
      dimensions: key-value mapping with swarming dimensions that specify
          on what Swarming slaves task can run. One important dimension is 'os',
          which defines platform flavor to run the task on. See Swarming doc.
      env: key-value mapping with additional environment variables to add to
          environment before launching the task executable.
      priority: integer [0, 255] that defines how urgent the task is.
          Lower value corresponds to higher priority. Swarming service executes
          tasks with higher priority first.
      shards: how many concurrent shards to run, makes sense only for
          isolated tests based on gtest. Swarming uses GTEST_SHARD_INDEX
          and GTEST_TOTAL_SHARDS environment variables to tell the executable
          what shard to run.
      buildername: buildbot builder this task was triggered from.
      buildnumber: build number of a build this task was triggered from.
      expiration: number of schedule until the task shouldn't even be run if it
          hadn't started yet.
      user: user that requested this task, if applicable.
      io_timeout: number of seconds that the task is allowed to not emit any
          stdout bytes, after which it is forcibly killed.
      hard_timeout: number of seconds for which the task is allowed to run,
          after which it is forcibly killed.
      idempotent: True if the results from a previous task can be reused. E.g.
          this task has no side-effects.
      extra_args: list of command line arguments to pass to isolated tasks.
      task_output_dir: if defined, the directory where task results are placed
          during the collect step.
      build_properties: An optional dict containing various build properties.
          These are typically but not necessarily the properties emitted by
          bot_update.
      merge: An optional dict containing:
          "script": path to a script to call to post process and merge the
              collected outputs from the tasks.
          "args": an optional list of additional arguments to pass to the
              above script.
    """
    self._trigger_output = None
    self.build_properties = build_properties
    self.buildername = buildername
    self.buildnumber = buildnumber
    self.cipd_packages = cipd_packages
    self.collect_step = collect_step
    self.dimensions = dimensions.copy()
    self.env = env.copy()
    self.expiration = expiration
    self.extra_args = tuple(extra_args or [])
    self.hard_timeout = hard_timeout
    self.idempotent = idempotent
    self.io_timeout = io_timeout
    self.isolated_hash = isolated_hash
    self.merge = merge or {}
    self.priority = priority
    self.shards = shards
    self.tags = set()
    self.task_output_dir = task_output_dir
    self.title = title
    self.user = user

  @property
  def task_name(self):
    """Name of this task, derived from its other properties.

    The task name is purely to make sense of the task and is not used in any
    other way.
    """
    out = '%s/%s/%s' % (
        self.title, self.dimensions['os'], self.isolated_hash[:10])
    if self.buildername:
      out += '/%s/%s' % (self.buildername, self.buildnumber or -1)
    return out

  @property
  def trigger_output(self):
    """JSON results of 'trigger' step or None if not triggered."""
    return self._trigger_output

  def get_shard_view_url(self, index):
    """Returns URL of HTML page with shard details or None if not available.

    Works only after the task has been successfully triggered.
    """
    if self._trigger_output and self._trigger_output.get('tasks'):
      for shard_dict in self._trigger_output['tasks'].itervalues():
        if shard_dict['shard_index'] == index:
          return shard_dict['view_url']

  def get_task_ids(self):
    """Returns task id of all shards.

    Works only after the task has been successfully triggered.
    """
    task_ids = []
    if self._trigger_output and self._trigger_output.get('tasks'):
      for shard_dict in self._trigger_output['tasks'].itervalues():
        task_ids.append(shard_dict['task_id'])
    return task_ids

