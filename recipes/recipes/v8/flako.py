# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe to bisect flaky tests in V8.

Bisection will start at a known bad to_revision and:
1. Calibrate the number of repetitions until enough confidence is reached.
2. Bisect backwards exponentially, doubling the offset in each step.
3. After finding a good from_revision, bisect into the range
   from_revision..to_revision and report the suspect.

Tests are only run on existing isolated files, looked up on Google Storage.

All revisions during bisections are represented as offsets to the start revision
which has offset 0.

See PROPERTIES for documentation on the recipe's interface.
"""

import re

from recipe_engine.config import Single
from recipe_engine.post_process import (
    DoesNotRun, DropExpectation, Filter, MustRun)
from recipe_engine.post_process import ResultReasonRE
from recipe_engine.recipe_api import Property



DEPS = [
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'depot_tools/gitiles',
    'depot_tools/gsutil',
    'chromium_swarming',
]

PROPERTIES = {
    # Group of the builder that produced the builds for bisection.
    'bisect_builder_group': Property(kind=str),
    # Name of the builder that produced the builds for bisection.
    'bisect_buildername': Property(kind=str),
    # Extra arguments to V8's run-tests.py script.
    'extra_args': Property(default=None, kind=list),
    # Number of commits, backwards bisection will initially leap over.
    'initial_commit_offset': Property(default=1, kind=Single((int, float))),
    # The maximum number of calibration attempts (safeguard to prevent infinite
    # loops). Repetitions are doubled on each attempt until there's enough
    # confidence.
    'max_calibration_attempts': Property(default=5, kind=Single((int, float))),
    # Name of the isolated file (e.g. bot_default, mjsunit).
    'isolated_name': Property(kind=str),
    # Initial number of swarming shards.
    'num_shards': Property(default=2, kind=Single((int, float))),
    # Optional build directory for backwards-compatibility, e.g. 'out/Release'.
    'outdir': Property(default=None, kind=str),
    # Initial number of test repetitions (passed to --random-seed-stress-count
    # option).
    'repetitions': Property(default=5000, kind=Single((int, float))),
    # Switch to only attempt to reproduce with given revision. Skips bisection.
    'repro_only': Property(default=False, kind=bool),
    # Swarming dimensions classifying the type of bot the tests should run on.
    # Passed as list of strings, each in the format name:value.
    'swarming_dimensions': Property(default=None, kind=list),
    # Swarming priority to be used for swarming tasks. The priority is lowered
    # by 10 (actual numberic value increases) when using higher time than the
    # one specified in the total_timeout_sec.
    'swarming_priority': Property(default=25, kind=Single((int, float))),
    # Expiration used for swarming tasks. Counted from the moment task is
    # scheduled.
    'swarming_expiration': Property(default=60 * 60, kind=Single((int, float))),
    # Fully qualified test name passed to run-tests.py. E.g. mjsunit/foobar.
    'test_name': Property(kind=str),
    # Timeout parameter passed to run-tests.py. Keep small when bisecting
    # fast-running tests that occasionally hang.
    'timeout_sec': Property(default=60, kind=Single((int, float))),
    # Initial total timeout for one entire bisect step. During calibration, this
    # time might be increased for more confidence. Set to 0 to disable and
    # specify the 'repetitions' property instead.
    'total_timeout_sec': Property(default=120, kind=Single((int, float))),
    # Revision known to be bad, where backwards bisection will start.
    'to_revision': Property(kind=str),
    # Name of the testing variant passed to run-tests.py.
    'variant': Property(kind=str),
}

# The maximum number of steps for backwards and inwards bisection (safeguard to
# prevent infinite loops).
MAX_BISECT_STEPS = 16

# A build with isolates must be within a distance of maximum 32 revisions for
# any revision that should be tested. We don't look further as a safeguard.
MAX_ISOLATE_OFFSET = 32

# Maximum number of test name characters printed in UI in step names.
MAX_LABEL_SIZE = 32

# Maximum number of swarming shards to be used for a single attempt.
MAX_SWARMING_SHARDS = 8

# Minimim number of flakes needed to have confidence in a run.
MIN_FLAKE_THRESHOLD = 4

# Response of gsutil when non-existing objects are looked up.
GSUTIL_NO_MATCH_TXT = 'One or more URLs matched no objects'

# URL of V8 repository.
REPO = 'https://chromium.googlesource.com/v8/v8'

# Exit code of V8's run-tests.py when no tests were run.
EXIT_CODE_NO_TESTS = 2

# Output of V8's test runner when all tests passed.
TEST_PASSED_TEXT = """
=== All tests succeeded
""".strip()

# Output of V8's test runner when some tests failed.
TEST_FAILED_TEMPLATE = """
=== %d tests failed
""".strip()


class Command(object):
  """Helper class representing a command line to V8's run-tests.py."""
  def __init__(self, test_name, variant, repetitions, repro_only,
               total_timeout_sec, timeout=60, extra_args=None, outdir=None):
    self.repetitions = repetitions
    self.test_name = test_name
    self.total_timeout_sec = total_timeout_sec
    self.min_failures = 1 if repro_only else MIN_FLAKE_THRESHOLD
    self.base_cmd = [
      'tools/run-tests.py',
      '--progress=verbose',
      '--outdir=%s' % (outdir or 'out/build'),
      '--timeout=%d' % timeout,
      '--swarming',
      '--variants=%s' % variant,
    ]
    if repro_only:
      # In repro-only mode we keep running skipped tests.
      self.base_cmd.append('--run-skipped')
    self.base_cmd += (extra_args or [])
    self.base_cmd.append(test_name)

  @property
  def label(self):
    """Test name for UI output limited to MAX_LABEL_SIZE chars."""
    if len(self.test_name) > MAX_LABEL_SIZE:
      return self.test_name[:MAX_LABEL_SIZE - 3] + '...'
    return self.test_name

  def raw_cmd(self, multiplier, offset):
    cmd = list(self.base_cmd)
    if self.total_timeout_sec:
      cmd.append('--random-seed-stress-count=1000000')
      cmd.append(
          '--total-timeout-sec=%d' % (self.total_timeout_sec * multiplier))
    else:
      cmd.append(
          '--random-seed-stress-count=%d' % (self.repetitions * multiplier))
    if offset <= 1024:
      # TODO(machenbach): Make this unconditional in 2019, when the feature has
      # become old enough to be compatible with long backwards bisection.
      # 1024 is a rough approximation of commits since the flag below was
      # introduced.
      cmd.append('--exit-after-n-failures=%d' % self.min_failures)
    return cmd


class Depot(object):
  """Helper class for interacting with remote storage (GS bucket and git)."""

  def __init__(self, api, builder_group, buildername, isolated_name, revision):
    """
    Args:
      builder_group: Group name of the builder that produced the builds for
          bisection.
      buildername: Name of the builder that produced the builds for bisection.
      isolated_name: Name of the isolated file (e.g. bot_default, mjsunit).
      revision: Start revision of bisection (known bad revision). All other
          revisions during bisection will be represented as offsets to this
          revision.
    """
    self.api = api
    self.gs_url_template = ('gs://chromium-v8/isolated/%s/%s/%%s.json' %
                            (builder_group, buildername))
    self.isolated_name = isolated_name
    self.revision = revision
    # Cache for mapping offsets to real revisions.
    self.revisions = {0: revision}
    # Cache for isolated hashes.
    self.isolates = {}
    # Offset cache for closets builds with isolates.
    self.closest_builds = {}

  def get_revision(self, offset):
    """Returns the git revision at the given offset (cached)."""
    revision = self.revisions.get(offset)
    if not revision:
      commits, _ = self.api.gitiles.log(
          REPO, '%s~%d' % (self.revision, offset), limit=1,
          step_name='get revision #%d' % offset)
      assert commits
      for i, commit in enumerate(commits):
        # Gitiles returns several commits. Fill our cache to avoid subsequent
        # calls.
        self.revisions[offset + i] = commit['commit']
    return self.revisions[offset]

  def has_build(self, offset):
    """Checks if an isolate exists for the given offset."""
    rev = self.get_revision(offset)
    link = '%s/+/%s' % (REPO, rev)
    try:
      self.api.gsutil.list(
          self.gs_url_template % rev,
          name='lookup isolates for #%d' % offset,
          stderr=self.api.raw_io.output_text(),
      )
      return True
    except self.api.step.StepFailure as e:
      # Gsutil's api has no good result format for missing objects, hence, we
      # look for the output text for missing objects. Treat missing object as
      # success as we expect some builds not to exist.
      if GSUTIL_NO_MATCH_TXT in e.result.stderr:
        e.result.presentation.status = self.api.step.SUCCESS
        return False
      raise  # pragma: no cover
    finally:
      self.api.step.active_result.presentation.links[rev[:8]] = link

  def find_closest_build(self, offset, max_offset=None):
    """Looks backwards for the closest offset with an existing isolate (cached).

    Args:
      offset: The offset to the base revision where the lookup is started.
      max_offset: Lookup stops at this offset if reached.
    Returns:
      The closest offset for which an isolate exists.
    """
    closest = self.closest_builds.get(offset)
    if closest is not None:
      return closest
    for i in range(MAX_ISOLATE_OFFSET):
      closest = offset + i
      if closest == max_offset or self.has_build(closest):
        for j in range(offset, closest + 1):
          # Cache the closest build for all offsets we tried.
          self.closest_builds[j] = closest
        return closest
    raise self.api.step.StepFailure('Couldn\'t find isolates.')

  def get_isolated_hash(self, offset):
    """Returns the isolated hash for a given offset (cached)."""
    if offset in self.isolates:
      return self.isolates[offset]

    self.api.gsutil.download_url(
        self.gs_url_template % self.get_revision(offset),
        self.api.json.output(),
        name='get isolates for #%s' % offset,
        step_test_data=lambda: self.api.json.test_api.output(
            {'foo_isolated': '[dummy hash for foo_isolated]'}),
    )
    step_result = self.api.step.active_result
    self.isolates[offset] = step_result.json.output[self.isolated_name]
    return self.isolates[offset]


class Runner(object):
  """Helper class for executing the V8 test runner to check for flakes."""
  def __init__(self, api, depot, command, num_shards, repro_only,
               max_calibration_attempts):
    self.api = api
    self.depot = depot
    self.command = command
    self.num_shards = min(num_shards, MAX_SWARMING_SHARDS)
    self.repro_only = repro_only
    self.multiplier = 1
    self.max_calibration_attempts = max_calibration_attempts

  def calibrate(self, offset):
    """Calibrates the multiplier for test time or repetitions of the runner for
    the given offset.

    Testing is repeated until MIN_FLAKE_THRESHOLD test failures are counted in
    an attempt. First the number of swarming shards, then the multiplier is
    doubled on each fresh attempt.

    Args:
      offset (int): Distance to the start commit.
    """
    for i in range(self.max_calibration_attempts):
      # Nest to disambiguate step names during calibration.
      with self.api.step.nest('calibration attempt %d' % (i + 1)) as parent:
        num_failures = self.check_num_flakes(offset)
        if (self.repro_only and num_failures or
            num_failures >= MIN_FLAKE_THRESHOLD):
          parent.presentation.step_text = 'successfully reproduced flaky test'
          return True
        if self.num_shards < MAX_SWARMING_SHARDS:
          # First double the swarming shards until reaching the maximum.
          self.num_shards = min(self.num_shards * 2, MAX_SWARMING_SHARDS)
        else:
          self.multiplier *= 2
        if i == self.max_calibration_attempts - 1:
          parent.presentation.step_text = 'failed to reproduce the flaky test'
    return False

  def _default_task_pass_test_data(self):
    test_data = self.api.chromium_swarming.test_api.canned_summary_output_raw()
    test_data['shards'][0]['output'] = TEST_PASSED_TEXT
    return (
        self.api.chromium_swarming.test_api.summary(
            self.api.json.test_api.output({}) +
            self.api.raw_io.test_api.output(''),
            test_data)
    )

  def check_num_flakes(self, offset):
    """Stress tests the given revision and returns the number of failures.

    Returns: Boolean indicating if enough failures have been found.
    """
    # TODO(machenbach): Use the sharding logic from the swarming module. We
    # don't use it yet, since swarming sets the GTEST_SHARD_INDEX environment
    # variable, which is used by the V8 test runner. This makes the test
    # disappear on all but one shards, because the test runner distributes tests
    # in a way such that each test only runs on one shard.
    # We first need a change of that logic on V8-side to suppress using
    # GTEST_SHARD_INDEX for flake bisection (e.g. by introducing another flag).
    # This V8-side commit needs to age enough before using it on infra-side,
    # so that it is availabe in each revision when bisecting backwards.

    isolated_hash = self.depot.get_isolated_hash(offset)
    step_prefix = 'check %s at #%d' % (self.command.label, offset)

    def trigger_task(path, shard):
      # TODO(machenbach): Allow legacy isolate hashes for a grace period to not
      # break flake bisection. Flip this permanently to true mid Q2 2021.
      kwargs = {}
      if '/' in isolated_hash:
        kwargs['cas_input_root'] = isolated_hash
      else:
        kwargs['isolated'] = isolated_hash
      # TODO(machenbach): Would be nice to just use 'shard X' as step names for
      # trigger/collect. But swarming enforces unique task titles and we can't
      # use our optimization to not collect some tasks. Either properly
      # cancel the task, such that they are not in the list of pending tasks or
      # override the step names.
      task = self.api.chromium_swarming.task(
          name='%s - shard %d' % (step_prefix, shard),
          task_output_dir=path.join('task_output_dir_%d' % shard),
          raw_cmd=self.command.raw_cmd(self.multiplier, offset),
          **kwargs
      )

      # Use lower swarming priority given the increased time of the task.
      if self.multiplier > 1:
        task.request = (task.request.with_priority(
                          max(task.request.priority + 10, 255)))

      # Override cpu defaults for Android as such devices don't have this
      # dimension.
      task_slice = task.request[0]
      task_dimensions = task_slice.dimensions
      if task_dimensions['os'] == 'Android':
        task_dimensions['cpu'] = None

      task_slice = task_slice.with_dimensions(**task_dimensions)
      task.request = task.request.with_slice(0, task_slice)

      self.api.chromium_swarming.trigger_task(task)
      return task

    def collect_task(task):
      try:
        step_result, _ = self.api.chromium_swarming.collect_task(
          task, allow_missing_json=True,
          gen_step_test_data=self._default_task_pass_test_data)
        # TODO(machenbach): Handle valid results data.
        data = step_result.chromium_swarming.summary['shards'][0]
        # Sanity checks.
        # TODO(machenbach): Add this information to the V8 test runner's json
        # output as parsing stdout is brittle.

        output = data.get('output')
        assert TEST_PASSED_TEXT in output
        return 0
      except self.api.step.StepFailure as e:
        data = e.result.chromium_swarming.summary['shards'][0]
        assert data['exit_code'], (
            'The bot might have died. Please restart the analysis')
        if data['exit_code'] == EXIT_CODE_NO_TESTS:
          # The desired tests seem to not exist in this revision.
          # TODO(machenbach): Add special logic for dealing with tests not
          # existing. They might have been added in a revision and are flaky
          # since then. Treat them as good revisions for now.
          # Maybe we should not do this during initialization to make sure it's
          # not a setup error?
          return 0  # pragma: no cover

        output = data.get('output')
        if TEST_PASSED_TEXT in output:  # pragma: no cover
          # It's possible that the return code is non-zero due to a test runner
          # leak.
          # TODO(machenbach): Remove this when https://crbug.com/v8/8001 is
          # resolved.
          return 0
        match = re.search(r'=== (\d+) tests failed', output)
        assert match
        return int(match.group(1))

    # TODO(sergiyb): Make bisect more robust to infra failures, e.g. we trigger
    # several dozen of tasks during bisect and currently if one expires, the
    # whole thing goes purple.
    path = self.api.path.mkdtemp('v8-flake-bisect-')
    with self.api.step.nest(step_prefix) as parent:
      tasks = [
        trigger_task(path, shard)
        for shard in range(self.num_shards)
      ]
      num_failures = 0
      for task in tasks:
        num_failures += collect_task(task)
        if (self.repro_only and num_failures or
            num_failures >= MIN_FLAKE_THRESHOLD):
          # Stop waiting for more tasks early if already enough failures are
          # found.
          # TODO(machenbach): Cancel the tasks we don't collect. During
          # calibration we might even want to figure out a better number of
          # shards? E.g. when doubling from 4 to 8, maybe 5 was enough and
          # should be used throughout.
          break
      parent.presentation.step_text = '%d failures' % num_failures
      return num_failures


def bisect(api, depot, initial_commit_offset, is_bad_func, offset):
  """Exercises the bisection control flow.

  Args:
    api: Recipe api.
    depot: Helper for accessing storage and git.
    initial_commit_offset: Number of commits, backwards bisection will
        initially leap over.
    is_bad_func: Function (revision->bool) determining if a given revision is
        bad.
    offset: Offset at which to start bisection.
  """
  def report_range(text, from_offset, to_offset):
    from_revision = depot.get_revision(from_offset)
    to_revision = depot.get_revision(to_offset)
    offset_range = '#%d..#%d' % (from_offset, to_offset)
    git_range = '%s..%s' % (from_revision[:8], to_revision[:8])
    step_result = api.step(text % offset_range, cmd=None)
    step_result.presentation.links[git_range] = '%s/+log/%s' % (REPO, git_range)

  def report_revision(text, offset):
    rev = depot.get_revision(offset)
    step_result = api.step(text % ('#%d' % offset), cmd=None)
    step_result.presentation.links[rev[:8]] = '%s/+/%s' % (REPO, rev)

  def bisect_back(to_offset):
    """Bisects backwards from to_offset, doubling the delta in each
    iteration.

    Returns:
        A tuple of (from_offset, to_offset), where from_offset..to_offset
        represents the range of good..bad revision found.
    """
    commit_offset = initial_commit_offset
    for _ in range(MAX_BISECT_STEPS):
      from_offset = to_offset + commit_offset

      # Check if from_offset is bad and iterate backwards if so.
      from_offset = depot.find_closest_build(from_offset)
      report_revision('Checking %s', from_offset)
      if is_bad_func(from_offset):
        to_offset = from_offset
        commit_offset *= 2
        continue

      return from_offset, to_offset
    raise api.step.StepFailure(
        'Could not not find a good revision.')  # pragma: no cover

  def bisect_into(from_offset, to_offset):
    """Bisects into a given range from_offset..to_offset and determins a
    suspect commit range.
    """
    assert from_offset >= to_offset
    known_good = from_offset
    known_bad = to_offset
    report_range('Bisecting %s', from_offset, to_offset)
    for _ in range(MAX_BISECT_STEPS):
      # End of bisection. Note that possibly known_good..known_bad is a larger
      # range than 1 commit due to missing isolates.
      if from_offset - to_offset <= 1:
        return known_good, known_bad
      middle_offset = to_offset + (from_offset - to_offset ) / 2
      build_offset = depot.find_closest_build(middle_offset, from_offset)

      if build_offset >= from_offset:
        report_range('No builds in %s', from_offset, middle_offset)
        # There are no isolates in lower half. Skip it and continue.
        from_offset = middle_offset
        continue

      report_revision('Checking %s', build_offset)
      if is_bad_func(build_offset):
        to_offset = build_offset
        known_bad = build_offset
      else:
        from_offset = build_offset
        known_good = build_offset

  from_offset, to_offset = bisect_back(offset)
  from_offset, to_offset = bisect_into(from_offset, to_offset)
  report_range('Result: Suspecting %s', from_offset, to_offset)

def setup_swarming(
    api, swarming_dimensions, swarming_priority, swarming_expiration):
  api.chromium_swarming.default_expiration = swarming_expiration
  api.chromium_swarming.default_hard_timeout = 60 * 60
  api.chromium_swarming.default_io_timeout = 20 * 60
  api.chromium_swarming.default_idempotent = False
  api.chromium_swarming.default_priority = swarming_priority
  api.chromium_swarming.default_user = 'v8-flake-bisect'
  api.chromium_swarming.add_default_tag('purpose:v8-flake-bisect')
  api.chromium_swarming.set_default_dimension('pool', 'chromium.tests')
  api.chromium_swarming.task_output_stdout = 'all'

  for item in swarming_dimensions:
    k, v = item.split(':')
    api.chromium_swarming.set_default_dimension(k, v)


def RunSteps(api, bisect_builder_group, bisect_buildername,
             extra_args, initial_commit_offset, max_calibration_attempts,
             isolated_name, num_shards, outdir, repetitions, repro_only,
             swarming_dimensions, swarming_priority, swarming_expiration,
             test_name, timeout_sec, total_timeout_sec, to_revision, variant):
  # Convert floats to ints.
  initial_commit_offset = int(initial_commit_offset)
  max_calibration_attempts = max(min(int(max_calibration_attempts), 5), 1)
  num_shards = int(num_shards)
  repetitions = int(repetitions)
  timeout_sec = int(timeout_sec)
  swarming_priority = max(min(int(swarming_priority), 255), 10)
  total_timeout_sec = int(total_timeout_sec)

  # Set up swarming client.
  setup_swarming(
      api, swarming_dimensions, swarming_priority, swarming_expiration)

  # Set up bisection helpers.
  depot = Depot(api, bisect_builder_group, bisect_buildername, isolated_name,
                to_revision)
  command = Command(
      test_name, variant, repetitions, repro_only, total_timeout_sec,
      timeout_sec, extra_args, outdir)
  runner = Runner(
      api, depot, command, num_shards, repro_only, max_calibration_attempts)

  to_offset = depot.find_closest_build(0)

  # Get confidence that the given revision is flaky and optionally calibrate the
  # repetitions.
  could_reproduce = runner.calibrate(to_offset)

  if repro_only:
    if could_reproduce:
      api.step('Flake still reproduces.', cmd=None)
      return
    else:
      # We treat it as an error if a flake belived to repro, doesn't repro.
      raise api.step.StepFailure('Could not reproduce flake.')

  if could_reproduce:
    # Generate config for flakes.pyl.
    config = api.json.dumps(
        [{
            'bisect_builder_group': bisect_builder_group,
            'bisect_buildername': bisect_buildername,
            'isolated_name': isolated_name,
            'test_name': test_name,
            'variant': variant,
            'extra_args': extra_args,
            'swarming_dimensions': swarming_dimensions,
            'timeout_sec': timeout_sec,
            'num_shards': runner.num_shards,
            # TODO(sergiyb): Drop total_timeout_sec here and just rely on
            # repetitions, which is more reliable on Windows. Right now,
            # however, we can't use it as it's not correctly calibrated when
            # total_timeout_sec is used. We should only implement this
            # suggestion once we can extract the actual number of repetitions
            # used from the test launcher after the calibration is done.
            'total_timeout_sec': total_timeout_sec * runner.multiplier,
            'repetitions': repetitions * runner.multiplier,
            'bug_url': '<bug-url>',
        }],
        indent=2,
        separators=(',', ': '),
        sort_keys=True)
    log = re.sub(
        r'([^,])(?=\n\s*[\}\]])', r'\1,', config,  # add trailing commas
        flags=re.MULTILINE).splitlines()           # split by line
    api.step('flakes.pyl entry', cmd=None).presentation.logs['config'] = log

  if not could_reproduce:
    raise api.step.StepFailure('Could not reach enough confidence.')

  # Run bisection.
  bisect(api, depot, initial_commit_offset, runner.check_num_flakes, to_offset)


def GenTests(api):
  def test(name):
    return api.test(
        name,
        api.properties(
            bisect_builder_group='foo.v8',
            bisect_buildername='V8 Foobar',
            extra_args=['--foo-flag', '--bar-flag'],
            isolated_name='foo_isolated',
            repetitions=64,
            swarming_dimensions=['os:Ubuntu-16.04', 'cpu:x86-64'],
            test_name='mjsunit/foobar',
            timeout_sec=20,
            to_revision='a0',
            variant='stress_foo',
        ),
    )

  def switched_to_cas(offset):
    return api.step_data(
        'calibration attempt 1.gsutil get isolates for #%d' % offset,
        api.json.output(
            {'foo_isolated': '[dummy hash for foo_isolated]/123'}
        ),
    )

  def isolated_lookup(offset, exists):
    return api.step_data(
        'gsutil lookup isolates for #%d' % offset,
        api.raw_io.stream_output(
            '' if exists else GSUTIL_NO_MATCH_TXT,
            stream='stderr',
        ),
        retcode=0 if exists else 1,
    )

  def get_revisions(offset, *revisions):
    return api.step_data(
        'get revision #%d' % offset,
        api.json.output({'log': [
          {'commit': revision} for revision in revisions
        ]}),
    )

  def is_flaky(offset, shard, flakes, calibration_attempt=0,
               test_name='mjsunit/foobar'):
    test_data = api.chromium_swarming.canned_summary_output_raw()
    test_data['shards'][0]['output'] = TEST_FAILED_TEMPLATE % flakes
    test_data['shards'][0]['exit_code'] = 1
    step_prefix = ''
    if calibration_attempt:
      step_prefix = 'calibration attempt %d.' % calibration_attempt
    step_name = 'check %s at #%d' % (test_name, offset)
    return api.step_data(
        '%s%s.%s - shard %d' % (step_prefix, step_name, step_name, shard),
        api.chromium_swarming.summary(dispatched_task_step_test_data=None,
                                            data=test_data, retcode=1)
    )

  def verify_suspects(from_offset, to_offset):
    """Verify that the correct reporting step for from_offset..to_offset is
    emitted.
    """
    git_range = 'a%d..a%d' % (from_offset, to_offset)
    step_name = 'Result: Suspecting #%d..#%d' % (from_offset, to_offset)
    def suspects_internal(check, steps):
      check(steps[step_name].links[git_range] ==
            '%s/+log/%s' % (REPO, git_range))
    return api.post_process(suspects_internal)

  # Full bisect run with some corner cases. Overview of all revisions ordered
  # new -> old.
  # a0: no isolate
  # a1: not flaky enough with 64 but flaky with 128 repetitions
  # a2: flaky
  # a3: flaky
  # a4: no isolate
  # a5: not flaky
  # -> Should result in suspecting range a5..a3.
  yield (
      test('full_bisect') +
      # Test path where total timeout isn't used.
      api.properties(total_timeout_sec=0) +
      # Data for resolving offsets to git hashes. Simulate gitiles page size of
      # 3 commits per call.
      get_revisions(1, 'a1', 'a2', 'a3') +
      get_revisions(4, 'a4', 'a5', 'a6') +
      # Isolate data simulation for all revisions.
      isolated_lookup(0, False) +
      isolated_lookup(1, True) +
      isolated_lookup(2, True) +
      isolated_lookup(3, True) +
      isolated_lookup(4, False) +
      isolated_lookup(5, True) +
      # Calibration. We check for flakes until enough are found. First only one
      # shard reports 2 failures.
      is_flaky(1, 1, 2, calibration_attempt=1) +
      # Then 3 shards report 5 failures total.
      is_flaky(1, 0, 2, calibration_attempt=2) +
      is_flaky(1, 1, 1, calibration_attempt=2) +
      is_flaky(1, 2, 2, calibration_attempt=2) +
      # Bisect backwards from a1 until good revision a5 is found.
      is_flaky(2, 0, 3) +
      # Bisect into a5..a2.
      is_flaky(3, 0, 3) +
      verify_suspects(5, 3) +
      # TODO(machenbach): This simulates a new build that has switched to CAS
      # while older builds have not yet. Remove this as soon as we switch CAS
      # on by default.
      switched_to_cas(1)
  )

  # Similar to above but fewer corner cases. This is for simulating bisection
  # going into the upper half of a git range, which has different code paths
  # above.
  yield (
      test('full_bisect_upper') +
      # Data for resolving offsets to git hashes. Simulate gitiles page size of
      # 8, fetching all data in the first call.
      get_revisions(1, 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'a8') +
      # Isolate data simulation for all revisions.
      isolated_lookup(0, True) +
      isolated_lookup(1, True) +
      isolated_lookup(3, True) +
      isolated_lookup(4, True) +
      isolated_lookup(5, True) +
      isolated_lookup(7, True) +
      # Calibration.
      is_flaky(0, 0, 5, calibration_attempt=1) +
      # Bisect backwards from a0 until good revision a7 is found.
      is_flaky(1, 0, 3) +
      is_flaky(3, 0, 3) +
      # Bisect into a7..a3.
      is_flaky(4, 0, 2) +
      verify_suspects(5, 4) +
      api.post_process(DropExpectation)
  )

  # Test bisecting through a large range of missing builds.
  yield (
      test('large_gap') +
      get_revisions(1, 'a1', 'a2', 'a3', 'a4') +
      # Simulate a large gap between #0 and #4..
      isolated_lookup(0, True) +
      isolated_lookup(1, False) +
      isolated_lookup(2, False) +
      isolated_lookup(3, False) +
      isolated_lookup(4, True) +
      # Bad build #0 wile #4 is a good build using default test data.
      is_flaky(0, 0, 5, calibration_attempt=1) +
      # Check that bisect continues properly after not finding a build in one
      # half.
      api.post_process(MustRun, 'No builds in #4..#2') +
      api.post_process(MustRun, 'No builds in #2..#1') +
      # Check that isolate lookup is cached for the negative case. We look only
      # once for a build that's not found.
      api.post_process(MustRun, 'gsutil lookup isolates for #2') +
      api.post_process(DoesNotRun, 'gsutil lookup isolates for #2 (2)') +
      verify_suspects(4, 0) +
      api.post_process(DropExpectation)
  )

  # Simulate not finding any isolates.
  yield (
      test('no_isolates') +
      sum((isolated_lookup(i, False) + get_revisions(i, 'a%d' % i)
           for i in range(1, MAX_ISOLATE_OFFSET)),
          isolated_lookup(0, False)) +
      api.post_process(ResultReasonRE, 'Couldn\'t find isolates.') +
      api.post_process(DropExpectation)
  )

  # Simulate repro-only mode reproducing a flake.
  yield (
      test('repro_only') +
      api.properties(repro_only=True) +
      isolated_lookup(0, True) +
      is_flaky(0, 0, 1, calibration_attempt=1) +
      api.post_process(MustRun, 'Flake still reproduces.') +
      api.post_process(Filter(
          'calibration attempt 1.check mjsunit/foobar at #0.'
          '[trigger] check mjsunit/foobar at #0 - shard 0'))
  )

  # Simulate repro-only mode not reproducing a flake.
  yield (
      test('repro_only_failed') +
      api.properties(repro_only=True) +
      isolated_lookup(0, True) +
      api.post_process(ResultReasonRE, 'Could not reproduce flake.') +
      api.post_process(DropExpectation)
  )

  # Simulate running tasks on Android and verify correct dimensions.
  def check_dimensions(check, steps):
    step = ('calibration attempt 1.check mjsunit/foobar at #0.'
            '[trigger] check mjsunit/foobar at #0 - shard 0 on Android')
    if check(step in steps):
      check(all(arg != 'cpu' for arg in steps[step].cmd))

  yield (test('android_dimensions') + api.properties(
      repro_only=True,
      swarming_dimensions=[
          'os:Android', 'cpu:x86-64', 'device_os:MMB29Q',
          'device_type:bullhead', 'pool:chromium.tests'
      ]) + isolated_lookup(0, True) + api.post_process(check_dimensions) +
         api.post_process(DropExpectation))

  # Simulate not finding enough flakes during calibration.
  # Also test cutting off overly long test names in step names.
  long_test_name = (29 * '*') + 'too_long'
  shortened_test_name = (29 * '*') + '...'
  yield (
      test('no_confidence') +
      api.properties(test_name=long_test_name, num_shards=8) +
      isolated_lookup(0, True) +
      is_flaky(0, 0, 0, calibration_attempt=1, test_name=shortened_test_name) +
      is_flaky(0, 1, 2, calibration_attempt=2, test_name=shortened_test_name) +
      is_flaky(0, 2, 1, calibration_attempt=3, test_name=shortened_test_name) +
      is_flaky(0, 1, 3, calibration_attempt=4, test_name=shortened_test_name) +
      is_flaky(0, 0, 3, calibration_attempt=5, test_name=shortened_test_name) +
      api.post_process(ResultReasonRE, 'Could not reach enough confidence.') +
      api.post_process(DropExpectation)
  )

  # Simulate triggering of the recipe by the flake verification bot.
  yield (
      test('verify_flake') +
      api.properties(
        repro_only=True, swarming_priority=40, num_shards=2,
        swarming_expiration=7200, total_timeout_sec=240,
        max_calibration_attempts=1) +
      isolated_lookup(0, True) +
      is_flaky(0, 0, 0, calibration_attempt=1) +
      is_flaky(0, 1, 1, calibration_attempt=1) +
      api.post_process(MustRun, 'Flake still reproduces.') +
      api.post_process(Filter(
          'calibration attempt 1.check mjsunit/foobar at #0.'
          '[trigger] check mjsunit/foobar at #0 - shard 1',
          'calibration attempt 1.check mjsunit/foobar at #0.'
          'check mjsunit/foobar at #0 - shard 1'))
  )
