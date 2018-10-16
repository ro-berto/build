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

from recipe_engine.post_process import DoesNotRun, DropExpectation, MustRun
from recipe_engine.recipe_api import Property


DEPS = [
  'depot_tools/gitiles',
  'depot_tools/gsutil',
  'recipe_engine/json',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'recipe_engine/tempfile',
  'swarming',
  'swarming_client',
]


PROPERTIES = {
  # Master name of the builder that produced the builds for bisection.
  'bisect_mastername': Property(kind=str),
  # Name of the builder that produced the builds for bisection.
  'bisect_buildername': Property(kind=str),
  # Build config passed to V8's run-tests.py script (there it's parameter
  # --mode, example: Release or Debug).
  'build_config': Property(kind=str),
  # Extra arguments to V8's run-tests.py script.
  'extra_args': Property(default=None, kind=list),
  # Number of commits, backwards bisection will initially leap over.
  'initial_commit_offset': Property(default=1, kind=int),
  # Name of the isolated file (e.g. bot_default, mjsunit).
  'isolated_name': Property(kind=str),
  # Initial number of test repetitions (passed to --random-seed-stress-count
  # option).
  'repetitions': Property(default=5000, kind=int),
  # Swarming dimensions classifying the type of bot the tests should run on.
  # Passed as list of strings, each in the format name:value.
  'swarming_dimensions': Property(default=None, kind=list),
  # Fully qualified test name passed to run-tests.py. E.g. mjsunit/foobar.
  'test_name': Property(kind=str),
  # Timeout parameter passed to run-tests.py. Keep small when bisecting
  # fast-running tests that occasionally hang.
  'timeout_sec': Property(default=60, kind=int),
  # Initial total timeout for one entire bisect step. During calibration, this
  # time might be increased for more confidence. Set to 0 to disable and specify
  # the 'repetitions' property instead.
  'total_timeout_sec': Property(default=120, kind=int),
  # Revision known to be bad, where backwards bisection will start.
  'to_revision': Property(kind=str),
  # Name of the testing variant passed to run-tests.py.
  'variant': Property(kind=str),
}

# The maximum number of steps for backwards and inwards bisection (safeguard to
# prevent infinite loops).
MAX_BISECT_STEPS = 16

# The maximum number of calibration attempts (safeguard to prevent infinite
# loops). Repetitions are doubled on each attempt until there's enough
# confidence.
MAX_CALIBRATION_ATTEMPTS = 5

# A build with isolates must be within a distance of maximum 32 revisions for
# any revision that should be tested. We don't look further as a safeguard.
MAX_ISOLATE_OFFSET = 32

# Maximum number of test name characters printed in UI in step names.
MAX_LABEL_SIZE = 32

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
  def __init__(self, test_name, build_config, variant, repetitions,
               total_timeout_sec, timeout=60, extra_args=None):
    self.repetitions = repetitions
    self.test_name = test_name
    self.total_timeout_sec = total_timeout_sec
    self.base_cmd = [
      'tools/run-tests.py',
      '--progress=verbose',
      '--mode=%s' % build_config,
      '--outdir=out',
      '--timeout=%d' % timeout,
      '--swarming',
      '--variants=%s' % variant,
    ] + (extra_args or []) + [test_name]

  @property
  def label(self):
    """Test name for UI output limited to MAX_LABEL_SIZE chars."""
    if len(self.test_name) > MAX_LABEL_SIZE:
      return self.test_name[:MAX_LABEL_SIZE - 3] + '...'
    return self.test_name

  def raw_cmd(self, multiplier):
    if self.total_timeout_sec:
      return (
          self.base_cmd +
          [
            '--random-seed-stress-count=1000000',
            '--total-timeout-sec=%d' % (self.total_timeout_sec * multiplier),
          ]
      )
    else:
      return (
          self.base_cmd +
          ['--random-seed-stress-count=%d' % (self.repetitions * multiplier)]
      )


class Depot(object):
  """Helper class for interacting with remote storage (GS bucket and git)."""
  def __init__(self, api, mastername, buildername, isolated_name, revision):
    """
    Args:
      mastername: Master name of the builder that produced the builds for
          bisection.
      buildername: Name of the builder that produced the builds for bisection.
      isolated_name: Name of the isolated file (e.g. bot_default, mjsunit).
      revision: Start revision of bisection (known bad revision). All other
          revisions during bisection will be represented as offsets to this
          revision.
    """
    self.api = api
    self.gs_url_template = (
        'gs://chromium-v8/isolated/%s/%s/%%s.json' % (mastername, buildername))
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
  def __init__(self, api, depot, command):
    self.api = api
    self.depot = depot
    self.command = command
    self.multiplier = 1

  def calibrate(self, offset):
    """Calibrates the multiplier for test time or repetitions of the runner for
    the given offset.

    Testing is repeated until MIN_FLAKE_THRESHOLD test failures are counted in
    an attempt. The multiplier is doubled on each fresh attempt.
    """
    for _ in range(MAX_CALIBRATION_ATTEMPTS):
      if self.check_num_flakes(offset) >= MIN_FLAKE_THRESHOLD:
        return True
      self.multiplier *= 2
    return False

  def check_num_flakes(self, offset):
    """Stress tests the given revision and returns the number of failures."""
    isolated_hash = self.depot.get_isolated_hash(offset)
    with self.api.tempfile.temp_dir('v8-flake-bisect-') as path:
      task = self.api.swarming.task(
          'check %s at #%d - %d' %
            (self.command.label, offset, self.multiplier),
          isolated_hash,
          task_output_dir=path.join('task_output_dir'),
          raw_cmd=self.command.raw_cmd(self.multiplier),
      )
      self.api.swarming.trigger_task(task)
      try:
        step_result = self.api.swarming.collect_task(task)
        data = step_result.swarming.summary['shards'][0]
        # Sanity checks.
        # TODO(machenbach): Add this information to the V8 test runner's json
        # output as parsing stdout is brittle.
        assert TEST_PASSED_TEXT in data['outputs'][-1]
        return 0
      except self.api.step.StepFailure as e:
        data = e.result.swarming.summary['shards'][0]
        assert data['exit_codes'], (
            'The bot might have died. Please restart the analysis')
        if data['exit_codes'][-1] == EXIT_CODE_NO_TESTS:
          # The desired tests seem to not exist in this revision.
          # TODO(machenbach): Add special logic for dealing with tests not
          # existing. They might have been added in a revision and are flaky
          # since then. Treat them as good revisions for now.
          # Maybe we should not do this during initialization to make sure it's
          # not a setup error?
          return 0  # pragma: no cover
        stdout = data['outputs'][-1]
        if TEST_PASSED_TEXT in stdout:  # pragma: no cover
          # It's possible that the return code is non-zero due to a test runner
          # leak.
          # TODO(machenbach): Remove this when https://crbug.com/v8/8001 is
          # resolved.
          return 0
        match = re.search(r'=== (\d+) tests failed', stdout)
        assert match
        return int(match.group(1))


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

def setup_swarming(api, swarming_dimensions):
  api.swarming_client.checkout('master')
  api.swarming.default_expiration = 60 * 60
  api.swarming.default_hard_timeout = 60 * 60
  api.swarming.default_io_timeout = 20 * 60
  api.swarming.default_idempotent = False
  api.swarming.default_priority = 25
  api.swarming.default_user = 'v8-flake-bisect'
  api.swarming.add_default_tag('purpose:v8-flake-bisect')
  api.swarming.set_default_dimension('pool', 'Chrome')
  api.swarming.set_default_dimension('gpu', 'none')
  for item in swarming_dimensions:
    k, v = item.split(':')
    api.swarming.set_default_dimension(k, v)


def RunSteps(api, bisect_mastername, bisect_buildername, build_config,
             extra_args, initial_commit_offset, isolated_name, repetitions,
             swarming_dimensions, test_name, timeout_sec, total_timeout_sec,
             to_revision, variant):
  # Set up swarming client.
  setup_swarming(api, swarming_dimensions)

  # Set up bisection helpers.
  depot = Depot(
      api, bisect_mastername, bisect_buildername, isolated_name, to_revision)
  command = Command(
      test_name, build_config, variant, repetitions, total_timeout_sec,
      timeout_sec, extra_args)
  runner = Runner(api, depot, command)

  # Get confidence that the initial revision is flaky and calibrate the
  # repetitions.
  to_offset = depot.find_closest_build(0)
  if not runner.calibrate(to_offset):
    raise api.step.StepFailure('Could not reach enough confidence.')

  # Run bisection.
  bisect(api, depot, initial_commit_offset, runner.check_num_flakes, to_offset)


def GenTests(api):
  def test(name):
    return (
        api.test(name) +
        api.properties(
            bisect_mastername='foo.v8',
            bisect_buildername='V8 Foobar',
            extra_args=['--foo-flag', '--bar-flag'],
            isolated_name='foo_isolated',
            build_config='Debug',
            repetitions=64,
            swarming_dimensions=['os:Ubuntu-14.04', 'cpu:x86-64'],
            test_name='mjsunit/foobar',
            timeout_sec=20,
            to_revision='a0',
            variant='stress_foo',
        )
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

  def is_flaky(offset, multiplier, flakes, test_name='mjsunit/foobar'):
    test_data = api.swarming.canned_summary_output_raw()
    if flakes:
      output = TEST_FAILED_TEMPLATE % flakes
      exit_code = 1
    else:
      output = TEST_PASSED_TEXT
      exit_code = 0
    test_data['shards'][0]['outputs'][-1] = output
    test_data['shards'][0]['exit_codes'][-1] = exit_code
    return api.step_data(
        'check %s at #%d - %d' % (test_name, offset, multiplier),
        api.swarming.summary(test_data),
        retcode=exit_code,
    )

  def verify_suspects(from_offset, to_offset):
    """Verify that the correct reporting step for from_offset..to_offset is
    emitted.
    """
    git_range = 'a%d..a%d' % (from_offset, to_offset)
    step_name = 'Result: Suspecting #%d..#%d' % (from_offset, to_offset)
    def suspects_internal(check, steps):
      check(step_name in steps)
      check(steps[step_name]['~followup_annotations'][0] ==
            '@@@STEP_LINK@%s@%s/+log/%s@@@' % (git_range, REPO, git_range))
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
      # Calibration. We check for flakes until enough are found.
      is_flaky(1, 1, 2) +
      is_flaky(1, 2, 5) +
      # Bisect backwards from a1 until good revision a5 is found.
      is_flaky(2, 2, 3) +
      is_flaky(5, 2, 0) +
      # Bisect into a5..a2.
      is_flaky(3, 2, 3) +
      verify_suspects(5, 3)
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
      is_flaky(0, 1, 5) +
      # Bisect backwards from a0 until good revision a7 is found.
      is_flaky(1, 1, 3) +
      is_flaky(3, 1, 3) +
      is_flaky(7, 1, 0) +
      # Bisect into a7..a3.
      is_flaky(5, 1, 0) +
      is_flaky(4, 1, 2) +
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
      # Bad build #0.
      is_flaky(0, 1, 5) +
      # Good build #4.
      is_flaky(4, 1, 0) +
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

  def verify_failure_reason(reason):
    """Helper for verifing the failure reason text of the recipe."""
    def _verify_failure_reason(check, steps):
      check(steps['$result']['reason'] == reason)
    return api.post_process(_verify_failure_reason)

  # Simulate not finding any isolates.
  yield (
      test('no_isolates') +
      sum((isolated_lookup(i, False) + get_revisions(i, 'a%d' % i)
           for i in range(1, MAX_ISOLATE_OFFSET)),
          isolated_lookup(0, False)) +
      verify_failure_reason('Couldn\'t find isolates.') +
      api.post_process(DropExpectation)
  )

  # Simulate not finding enough flakes during calibration.
  # Also test cutting off overly long test names in step names.
  long_test_name = (29 * '*') + 'too_long'
  shortened_test_name = (29 * '*') + '...'
  yield (
      test('no_confidence') +
      api.properties(test_name=long_test_name) +
      isolated_lookup(0, True) +
      is_flaky(0, 1, 0, test_name=shortened_test_name) +
      is_flaky(0, 2, 2, test_name=shortened_test_name) +
      is_flaky(0, 4, 1, test_name=shortened_test_name) +
      is_flaky(0, 8, 3, test_name=shortened_test_name) +
      is_flaky(0, 16, 3, test_name=shortened_test_name) +
      verify_failure_reason('Could not reach enough confidence.') +
      api.post_process(DropExpectation)
  )