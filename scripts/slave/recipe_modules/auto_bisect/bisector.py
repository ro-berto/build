# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import re
import time
import urllib

from . import bisect_exceptions
from . import config_validation
from . import depot_config
from . import revision_state

_DEPS_SHA_PATCH = """
diff --git DEPS.sha DEPS.sha
new file mode 100644
--- /dev/null
+++ DEPS.sha
@@ -0,0 +1 @@
+%(deps_sha)s
"""


ZERO_TO_NON_ZERO = 'Zero to non-zero'
VALID_RESULT_CODES = (
    'TEST_TIMEOUT',  # Timed out waiting for the test job.
    'BUILD_TIMEOUT',  # Timed out waiting for the build.
    'TEST_FAILURE',  # The test failed to produce parseable results|chartjson.
    'BUILD_FAILURE',  # The build could not be requested, or the job failed.
    'BAD_REV',  # The revision range could not be expanded, or the commit
                # positions could not be resolved into commit hashes.
    'REF_RANGE_FAIL',  # Either of the initial 'good' or 'bad' revisions failed
                       # to be tested or built. Used with *_FAILURE|*_TIMEOUT.
    'BAD_CONFIG',  # There was a problem with the bisect_config dictionary
                   # passed to the recipe. See output of the config step
    'CULPRIT_FOUND',  # A Culprit CL was found with 'high' confidence.
    'LO_INIT_CONF',  # Bisect aborted early for lack of confidence.
    'MISSING_METRIC',  # The metric was not found in the test text/json output.
    'LO_FINAL_CONF',  # The bisect completed without a culprit.
)

# When we look for the next revision to build, we search nearby revisions
# looking for a revision that's already been archived. Since we don't want
# to move *too* far from the original revision, we'll cap the search at 25%.
DEFAULT_SEARCH_RANGE_PERCENTAGE = 0.25

_FAILED_INITIAL_CONFIDENCE_ABORT_REASON = (
    'The metric values for the initial "good" and "bad" revisions '
    'do not represent a clear regression.')

_DIRECTION_OF_IMPROVEMENT_ABORT_REASON = (
    'The metric values for the initial "good" and "bad" revisions match the '
    'expected direction of improvement. Thus, likely represent an improvement '
    'and not a regression.')


class Bisector(object):
  """This class abstracts an ongoing bisect (or n-sect) job."""

  def __init__(self, api, bisect_config, revision_class, init_revisions=True,
               **flags):
    """Initializes the state of a new bisect job from a dictionary.

    Note that the initial good_rev and bad_rev MUST resolve to a commit position
    in the chromium repo.
    """
    super(Bisector, self).__init__()
    self.flags = flags
    self._api = api
    self.result_codes = set()
    self.ensure_sync_master_branch()
    self.bisect_config = bisect_config
    self.config_step()
    self._validate_config()
    self.revision_class = revision_class
    self.last_tested_revision = None

    # Test-only properties.
    # TODO: Replace these with proper mod_test_data.
    self.dummy_builds = bisect_config.get('dummy_builds', False)
    self.dummy_tests = bisect_config.get('dummy_tests', False)
    self.bypass_stats_check = bool(bisect_config.get('bypass_stats_check'))

    # Load configuration items.
    self.test_type = bisect_config.get('test_type', 'perf')
    self.improvement_direction = int(bisect_config.get(
        'improvement_direction', 0)) or None

    self.warnings = []
    self.aborted_reason = None

    # Status flags
    self.failed_initial_confidence = False
    self.failed = False
    self.failed_direction = False
    self.lkgr = None  # Last known good revision
    self.fkbr = None  # First known bad revision
    self.culprit = None
    self.bisect_over = False
    self.relative_change = None
    self.internal_bisect = api.internal_bisect
    self.base_depot = 'chromium'
    if self.internal_bisect:
      self.base_depot = 'android-chrome'  # pragma: no cover

    # Initial revision range
    with api.m.step.nest('Expanding reference range'):
      expanding_step = api.m.step.active_result

      bad_hash = self._get_hash(bisect_config['bad_revision'])
      good_hash = self._get_hash(bisect_config['good_revision'])

      self.revisions = []
      self.bad_rev = revision_class(self, bad_hash)
      self.bad_rev.bad = True
      self.bad_rev.read_deps(self.get_perf_tester_name())
      expanding_step.presentation.logs['DEPS - Bad'] = [
          '%s: %s' % (key, value) for key, value in
          sorted(self.bad_rev.deps.items())]
      self.bad_rev.deps = {}
      self.fkbr = self.bad_rev
      self.good_rev = revision_class(self, good_hash)
      self.good_rev.good = True
      self.good_rev.read_deps(self.get_perf_tester_name())
      expanding_step.presentation.logs['DEPS - Good'] = [
          '%s: %s' % (key, value) for key, value in
          sorted(self.good_rev.deps.items())]
      self.good_rev.deps = {}
      self.lkgr = self.good_rev

      if init_revisions:
        self._expand_initial_revision_range(expanding_step.presentation)

  def _get_hash(self, rev):
    """Returns a commit hash given either a commit hash or commit position.

    Args:
      rev (str): A commit hash or commit position number.

    Returns:
      A 40-digit git commit hash string.
    """
    if self._is_sha1(rev):  # pragma: no cover
      return rev
    if rev.isdigit():
      commit_position = self._api.m.commit_position.construct(
          branch='refs/heads/master', value=rev)
      try:
        return self.api.m.crrev.to_commit_hash(
            commit_position,
            step_test_data=lambda: self.api._test_data['hash_cp_map'][rev])
      except self.api.m.step.StepFailure:  # pragma: no cover
        self.surface_result('BAD_REV')
        raise
    self.surface_result('BAD_REV')  # pragma: no cover
    raise self.api.m.step.StepFailure(
        'Invalid input revision: %r' % (rev,))  # pragma: no cover

  @staticmethod
  def _is_sha1(s):
    return bool(re.match('^[0-9A-Fa-f]{40}$', s))

  def compare_revisions(self, revision_a, revision_b):
    """
    Returns:
      SIGNIFICANTLY_DIFFERENT if the samples are significantly different.
      NEED_MORE_DATA if there is not enough data to tell.
      NOT_SIGNIFICANTLY_DIFFERENT if if there's enough data but still can't
          tell the samples apart.
    """
    output_format = 'chartjson'
    values_a = revision_a.chartjson_paths
    values_b = revision_b.chartjson_paths
    if revision_a.valueset_paths and revision_b.valueset_paths:
      output_format = 'valueset'
      values_a = revision_a.valueset_paths
      values_b = revision_b.valueset_paths

    if revision_a.buildbot_paths and revision_b.buildbot_paths:
      output_format = 'buildbot'
      values_a = revision_a.buildbot_paths
      values_b = revision_b.buildbot_paths

    result = self.api.stat_compare(
        values_a,
        values_b,
        self.bisect_config['metric'],
        output_format=output_format,
        step_test_data=lambda: self.api.test_api.compare_samples_data(
            self.api._test_data['parsed_values'], revision_a, revision_b))

    revision_a.debug_values = result['sampleA']
    revision_b.debug_values = result['sampleB']

    res = result['result']['significance']
    if res == revision_state.NEED_MORE_DATA:
      return revision_state.NEED_MORE_DATA
    elif res == revision_state.REJECT:
      return revision_state.SIGNIFICANTLY_DIFFERENT
    elif res == revision_state.FAIL_TO_REJECT:  # pragma: no cover
      return revision_state.NOT_SIGNIFICANTLY_DIFFERENT
    else:   # pragma: no cover
      assert False, 'Unexpected result code from compare_samples: ' + res

  def config_step(self):
    """Yields a step that prints the bisect config."""
    api = self.api

    # bisect_config may come as a FrozenDict (which is not serializable).
    bisect_config = dict(self.bisect_config)

    def fix_windows_backslashes(s):
      backslash_regex = re.compile(r'(?<!\\)\\(?!\\)')
      return backslash_regex.sub(r'\\', s)

    for k, v in bisect_config.iteritems():
      if isinstance(v, basestring):
        bisect_config[k] = fix_windows_backslashes(v)

    # We sort the keys to prevent problems with orders changing when
    # recipe_simulation_test compares against expectation files.
    config_string = json.dumps(bisect_config, indent=2, sort_keys=True)
    step = api.m.step('config', [])
    config_lines = config_string.splitlines()
    step.presentation.logs['Bisect job configuration'] = config_lines

  def _validate_config(self):
    """Raises an error and halts the bisect job if the config is invalid."""
    try:
      config_validation.validate_bisect_config(self.bisect_config)
    except config_validation.ValidationFail as error:
      self.surface_result('BAD_CONFIG')
      self.api.m.halt(error.message)
      raise self.api.m.step.StepFailure(error.message)

  @property
  def api(self):
    return self._api

  def compute_relative_change(self):
    old_value = float(self.good_rev.mean or 0)
    new_value = float(self.bad_rev.mean or 0)

    if new_value and not old_value:  # pragma: no cover
      self.relative_change = ZERO_TO_NON_ZERO
      return

    rel_change = self.api.m.math_utils.relative_change(old_value, new_value)
    self.relative_change = '%.2f%%' % (100 * rel_change)

  def _expand_initial_revision_range(self, presentation):
    """Sets the initial contents of |self.revisions|."""
    good_hash = self.good_rev.commit_hash
    bad_hash = self.bad_rev.commit_hash
    depot = self.good_rev.depot_name
    step_name = 'for revisions %s:%s' % (good_hash, bad_hash)
    revisions = self._revision_range(
        start=good_hash,
        end=bad_hash,
        depot_name=self.base_depot,
        step_name=step_name,
        exclude_end=True,
        step_test_data=lambda: self.api._test_data['revision_list'][depot]
    )
    self.revisions = [self.good_rev] + revisions + [self.bad_rev]
    self._update_revision_list_indexes()

    presentation.step_text += (
        self.api.m.test_utils.format_step_text(
            [['Range: %s:%s (%d commits)' % (
                good_hash, bad_hash, len(revisions))]]))


  def _revision_range(self, start, end, depot_name, base_revision=None,
                      step_name=None, exclude_end=False, **kwargs):
    """Returns a list of RevisionState objects between |start| and |end|.

    When expanding the initial revision range we want to exclude the last
    revision, since both good and bad have already been created and tested.
    When bisecting into a roll on the other hand, we want to include the last
    revision in the roll, because although the code should be equivalent to
    the roll, we want to blame the right culprit and not the roll.

    Args:
      start (str): Start commit hash.
      end (str): End commit hash.
      depot_name (str): Short string name of repo, e.g. chromium or v8.
      base_revision (str): Base revision in the downstream repo (e.g. chromium).
      step_name (str): Optional step name.
      exclude_end (bool): Whether to exclude the last revision in the range,
          i.e. the revision given as end. The use case for this parameter is
          when expanding the initial regression range. The "bad" revision has
          already been instantianted and including it in this response would
          duplicate it.

    Returns:
      A list of RevisionState objects.
    """
    if self.internal_bisect:  # pragma: no cover
      return self._revision_range_with_gitiles(
          start, end, depot_name, base_revision, step_name,
          exclude_end=exclude_end, step_test_data=lambda: self.api._test_data[
              'revision_list_internal'][depot_name])
    try:
      step_result = self.api.m.python(
          step_name,
          self.api.resource('fetch_intervening_revisions.py'),
          [start, end, depot_config.DEPOT_DEPS_NAME[depot_name]['url']],
          stdout=self.api.m.json.output(), **kwargs)
    except self.api.m.step.StepFailure:  # pragma: no cover
      self.surface_result('BAD_REV')
      raise
    revisions = []
    revision_hashes = step_result.stdout
    if exclude_end:
      revision_hashes = revision_hashes[:-1]
    for commit_hash, _ in revision_hashes:
      revisions.append(self.revision_class(
          bisector=self,
          commit_hash=commit_hash,
          depot_name=depot_name,
          base_revision=base_revision))
    return revisions

  def _revision_range_with_gitiles(
      self, start, end, depot_name, base_revision=None, step_name=None,
      exclude_end=False, **kwargs):   # pragma: no cover
    """Returns a list of RevisionState objects between |start| and |end|.

    Args:
      start (str): Start commit hash.
      end (str): End commit hash.
      depot_name (str): Short string name of repo, e.g. chromium or v8.
      base_revision (str): Base revision in the downstream repo (e.g. chromium).
      step_name (str): Optional step name.
      exclude_end (bool): Whether to exclude the last revision in the range,
          i.e. the revision given as end.

    Returns:
      A list of RevisionState objects, not including the given start or end.
    """
    try:
      url = depot_config.DEPOT_DEPS_NAME[depot_name]['url']
      commits = self._commit_log(start, end, url, step_name, **kwargs)

    except self.api.m.step.StepFailure:  # pragma: no cover
      self.surface_result('BAD_REV')
      raise
    revisions = []
    if exclude_end:
      commits = commits[:-1]
    for c in commits:
      revisions.append(self.revision_class(
          bisector=self,
          commit_hash=c['commit'],
          depot_name=depot_name,
          base_revision=base_revision))
    return revisions

  def _commit_log(self, start, end, url, step_name=None,
                  **kwargs):  # pragma: no cover
    """Fetches information about a range of commits.

    Args:
      start (str): The starting commit hash.
      end (str): The ending commit hash.
      url (str): The URL of a repository, e.g.
	  "https://chromium.googlesource.com/chromium/src".
      step_name (str): Optional step name.

    Returns:
     A list of dicts for commits in chronological order, including the
     end commit, but not including the start. Each dict will contain
     a commit hash (key: "commit") and a commit message (key: "message").

    Raises:
     StepFailure: Failed to fetch the commit log.
    """
    try:
     ref = '%s..%s' % (start, end)
     step_name = step_name or 'gitiles log: %s' % ref
     commits, cursor = self.api.m.gitiles.log(
         url, ref, limit=2048, step_name=step_name, **kwargs)
     if cursor:  # pragma: no cover
       raise self.api.m.step.StepFailure('Revision range too large')
     return list(reversed(commits))
    except self.api.m.step.StepFailure:  # pragma: no cover
     self.surface_result('BAD_REV')
     raise

  def _get_chain(self, a):
    chain = [a.depot]

    while True:
      depot = chain[-1]

      if not depot['from']:  # pragma: no cover
        break

      parent_name = depot['from'][0]
      parent_depot = depot_config.DEPOT_DEPS_NAME.get(parent_name)
      if not parent_depot:
        break

      chain.append(parent_depot)
    return chain

  def _find_expand_chain(self, a, b):
    chain1 = self._get_chain(a)
    chain2 = self._get_chain(b)

    if chain1[-1] != chain2[-1]:  # pragma: no cover
      return None

    # TODO: Check they're not different chains

    if len(chain1) > len(chain2):  # pragma: no cover
      return chain1
    return chain2

  def _create_rev_from_deps(self, parent_rev, depot, base_revision):
    depot_name = None
    for k, v in depot_config.DEPOT_DEPS_NAME.iteritems():
      if depot == v:
        depot_name = k
        break
    if not depot_name:  # pragma: no cover
      return None

    commit_hash = parent_rev.deps[depot_name]

    return self.revision_class(
        bisector=self,
        commit_hash=commit_hash,
        depot_name=depot_name,
        base_revision=base_revision)

  def _expand_chain(self, a, chain, base_revision):
    chain = [c for c in reversed(chain)]
    start = chain.index(a.depot)

    rev = a
    for c in chain[start:]:
      if c == rev.depot:
        continue
      rev = self._create_rev_from_deps(rev, c, base_revision)
    return rev

  def _expand_deps_revisions(self, revision_to_expand):
    """Populates the revisions attribute with additional deps revisions.

    Inserts the revisions from the external repos in the appropriate place.

    Args:
      revision_to_expand: A revision where there is a deps change.

    Returns:
      A boolean indicating whether any revisions were inserted.
    """
    # TODO(robertocn): Review variable names in this function. They are
    # potentially confusing.
    assert revision_to_expand is not None
    try:
      min_revision = revision_to_expand.previous_revision
      max_revision = revision_to_expand

      # The revisions may not be pointing to the same depots. Ie. the min
      # might be android, while max is chrome, we need to expand deps in
      # both first so that we can do a revision range between them.
      expand_chain = self._find_expand_chain(min_revision, max_revision)

      min_revision = self._expand_chain(min_revision, expand_chain,
          base_revision=min_revision)
      max_revision = self._expand_chain(max_revision, expand_chain,
          base_revision=min_revision)

      assert min_revision
      assert max_revision

      # Parses DEPS file and sets the .deps property.
      min_revision.read_deps(self.get_perf_tester_name())
      max_revision.read_deps(self.get_perf_tester_name())
      for depot_name in depot_config.DEPOT_DEPS_NAME.keys():
        if depot_name in min_revision.deps and depot_name in max_revision.deps:
          dep_revision_min = min_revision.deps[depot_name]
          dep_revision_max = max_revision.deps[depot_name]
          if (dep_revision_min and dep_revision_max and
              dep_revision_min != dep_revision_max):
            step_name = ('Expanding revision range for revision %s'
                         ' on depot %s' % (dep_revision_max, depot_name))
            rev_list = self._revision_range(
                start=dep_revision_min,
                end=dep_revision_max,
                depot_name=depot_name,
                base_revision=min_revision,
                step_name=step_name,
                step_test_data=lambda:
                    self.api._test_data['revision_list'][depot_name])
            new_revisions = self.revisions[:max_revision.list_index]
            new_revisions += rev_list
            new_revisions += self.revisions[max_revision.list_index:]
            self.revisions = new_revisions
            self._update_revision_list_indexes()
            return True
    except RuntimeError:  # pragma: no cover
      warning_text = ('Could not expand dependency revisions for ' +
                      revision_to_expand.commit_hash)
      self.surface_result('BAD_REV')
      if warning_text not in self.warnings:
        self.warnings.append(warning_text)
      return False

  def _update_revision_list_indexes(self):
    """Sets list_index, next and previous properties for each revision."""
    for i, rev in enumerate(self.revisions):
      rev.list_index = i
    for i in xrange(len(self.revisions)):
      if i:
        self.revisions[i].previous_revision = self.revisions[i - 1]
      if i < len(self.revisions) - 1:
        self.revisions[i].next_revision = self.revisions[i + 1]

  def check_improvement_direction(self):  # pragma: no cover
    """Verifies that the change from 'good' to 'bad' is in the right direction.

    The change between the test results obtained for the given 'good' and
    'bad' revisions is expected to be considered a regression. The
    `improvement_direction` attribute is positive if a larger number is
    considered better, and negative if a smaller number is considered better.

    Returns:
      True if the check passes (i.e. no problem), False if the change is not
      a regression according to the improvement direction.
    """
    good = self.good_rev.mean
    bad = self.bad_rev.mean

    if self.is_return_code_mode():
      return True

    direction = self.improvement_direction
    if direction is None:
      return True
    if (bad > good and direction > 0) or (bad < good and direction < 0):
      self._set_failed_direction_results()
      return False
    return True

  def _set_failed_return_code_direction_results(self):  # pragma: no cover
    self.failed_direction = True
    self.warnings.append('The initial regression range for return code '
                         'appears to show NO sign of a regression.')

  def _set_failed_direction_results(self):  # pragma: no cover
    self.failed_direction = True
    self.warnings.append('The initial regression range appears to represent '
                         'an improvement rather than a regression, given the '
                         'expected direction of improvement.')

  def check_initial_confidence(self):  # pragma: no cover
    """Checks that the initial range presents a clear enough regression.

    We ensure that the good and bad revisions produce significantly different
    results, increasing the sample size until the compare_revisions function
    concludes that a difference exists or not, OR the maximum allowed number of
    repeated tests has been reached.

    Returns: True if the revisions produced results that differ from each
    other in a statistically significant manner. Raises an exception otherwise.
    """
    if self.is_return_code_mode():
      self.compute_relative_change()
      return (self.good_rev.overall_return_code !=
              self.bad_rev.overall_return_code)

    if self.bypass_stats_check:
      self.compare_revisions(self.good_rev, self.bad_rev)
      self.compute_relative_change()
      dummy_result = self.good_rev.mean != self.bad_rev.mean
      if not dummy_result:
        self._raise_low_confidence_error()
      return dummy_result

    compare_result = self.compare_revisions(self.good_rev, self.bad_rev)

    # Only create a superstep if retesting will be needed.
    if compare_result == revision_state.NEED_MORE_DATA:
      with self.api.m.step.nest('Re-testing reference range'):
        while (compare_result == revision_state.NEED_MORE_DATA):
          revision_to_retest = min(self.good_rev, self.bad_rev,
                                   key=lambda x: x.test_run_count)
          if (revision_to_retest.test_run_count
              >= revision_state.MAX_TESTS_PER_REVISION):
            break
          with self.api.m.step.nest('Retesting %s revision' % (
              'GOOD' if revision_to_retest.good else 'BAD')):
            revision_to_retest._do_test()
          compare_result = self.compare_revisions(self.good_rev, self.bad_rev)
    self.compute_relative_change()
    if compare_result == revision_state.SIGNIFICANTLY_DIFFERENT:
      return True
    self._raise_low_confidence_error()

  def _raise_low_confidence_error(self):
    if (not self.good_rev.debug_values or
        not self.bad_rev.debug_values):  # pragma: no cover
      msg = 'No values were found while testing the reference range.'
      self.surface_result('MISSING_METRIC')
    else:
      msg = 'Bisect failed to reproduce the regression with enough confidence.'
      self.surface_result('LO_INIT_CONF')
    self.surface_result('REF_RANGE_FAIL')
    self.failed = True
    self.failed_initial_confidence = True
    raise bisect_exceptions.InconclusiveBisectException(msg)

  def get_exception(self):
    raise NotImplementedError()  # pragma: no cover
    # TODO: should return an exception with the details of the failure.

  def _results_debug_message(self):
    """Returns a string with values used to debug a bisect result."""
    result = 'bisector.lkgr: %r\n' % self.lkgr
    result += 'bisector.fkbr: %r\n\n' % self.fkbr
    result += self._revision_value_table()
    if (self.lkgr and self.lkgr.test_run_count and self.fkbr and
        self.fkbr.test_run_count):
      result += '\n' + '\n'.join([
          'LKGR values: %r' % list(self.lkgr.display_values),
          'FKBR values: %r' % list(self.fkbr.display_values),
      ])
    return result

  def _revision_value_table(self):
    """Returns a string table showing revisions and their values."""
    header = [['Revision', 'Values']]
    with self._api.m.step.nest('Resolving hashes'):
      rows = [[r.revision_string(), str(r.display_values)]
              for r in self.revisions]
    return self._pretty_table(header + rows)

  def _pretty_table(self, data):
    results = []
    for row in data:
      results.append('%-15s' * len(row) % tuple(row))
    return '\n'.join(results)

  def print_result_debug_info(self):
    """Prints extra debug info at the end of the bisect process."""
    # If we emit a null step then add a log to it, the log should be kept
    # longer than 7 days (which is often needed to debug some issues).
    self.api.m.step('Debug Info', [])
    current_step = self.api.m.step.active_result
    lines = self._results_debug_message().splitlines()
    current_step.presentation.logs['Debug Info'] = lines

  def post_result(self, halt_on_failure=False):
    """Posts bisect results to Perf Dashboard."""
    self.api.m.perf_dashboard.set_default_config()
    step_result = self.api.m.perf_dashboard.post_bisect_results(
        self.get_result(), halt_on_failure)
    lines = json.dumps(self.get_result(), indent=2).splitlines()
    step_result.presentation.logs['Debug Info'] = lines

  def get_revision_to_eval(self):
    """Gets the next RevisionState object in the candidate range.

    Returns:
       The next Revision object in a list.
    """
    self._update_candidate_range()
    candidate_range = [revision for revision in
                       self.revisions[self.lkgr.list_index + 1:
                                      self.fkbr.list_index]
                       if not revision.failed]
    if len(candidate_range) == 1:
      return candidate_range[0]
    if len(candidate_range) == 0:
      return None

    default_revision = candidate_range[len(candidate_range) / 2]

    with self.api.m.step.nest(
        'Wiggling revision ' + default_revision.revision_string()):
      # We'll search up to 25% of the range (in either direction) to try and
      # find a nearby commit that's already been built.
      max_wiggle = int(len(candidate_range) * DEFAULT_SEARCH_RANGE_PERCENTAGE)
      for _ in xrange(max_wiggle):  # pragma: no cover
        index = len(candidate_range) / 2
        if candidate_range[index]._is_build_archived():
          return candidate_range[index]
        del candidate_range[index]

      return default_revision

  def check_reach_adjacent_revision(self, revision):
    """Checks if this revision reaches its adjacent revision.

    Reaching the adjacent revision means one revision considered 'good'
    immediately preceding a revision considered 'bad'.
    """
    if (revision.bad and revision.previous_revision and
        revision.previous_revision.good):
      return True
    if (revision.good and revision.next_revision and
        revision.next_revision.bad):
      return True
    return False

  def check_bisect_finished(self, revision):
    """Checks if this revision completes the bisection process.

    In this case 'finished' refers to finding one revision considered 'good'
    immediately preceding a revision considered 'bad' where the 'bad' revision
    does not contain a DEPS change.
    """
    if (revision.bad and revision.previous_revision and
        revision.previous_revision.good):
      if revision.deps_change() and self._expand_deps_revisions(revision):
        return False
      self.culprit = revision
      return True
    if (revision.good and revision.next_revision and
        revision.next_revision.bad):
      if (revision.next_revision.deps_change()
          and self._expand_deps_revisions(revision.next_revision)):
        return False
      self.culprit = revision.next_revision
      return True
    # We'll never get here because revision adjacency is checked before this
    # function is called.
    assert False  # pragma: no cover

  def _update_candidate_range(self):
    """Updates lkgr and fkbr (last known good/first known bad) revisions.

    lkgr and fkbr are 'pointers' to the appropriate RevisionState objects in
    bisectors.revisions."""
    for r in self.revisions:
      if r.test_run_count:
        if r.good:
          self.lkgr = r
        elif r.bad:
          self.fkbr = r
          break
    assert self.lkgr and self.fkbr

  def get_perf_tester_name(self):
    """Gets the name of the tester bot (on tryserver.chromium.perf) to use.

    If the tester bot is explicitly specified using "recipe_tester_name"
    in the bisect config, use that; otherwise make a best guess.
    """
    original_bot_name = self.bisect_config.get('original_bot_name', '')
    recipe_tester_name = self.bisect_config.get('recipe_tester_name')
    if recipe_tester_name:
      return recipe_tester_name
    elif 'win' in original_bot_name:  # pragma: no cover
      return 'win64_nv_tester'
    else:  # pragma: no cover
      # Reasonable fallback.
      return 'linux_perf_tester'

  def get_builder_bot_for_this_platform(self):
    """Returns the name of the builder bot to use."""
    if self.api.builder_bot:  # pragma: no cover
      return self.api.builder_bot

    # TODO(prasadv): Refactor this code to remove hard coded values.
    bot_name = self.get_perf_tester_name()

    # TODO(prasadv): Refactor this code to remove hard coded values and use
    # target_bit from the bot config. crbug.com/640287
    if 'android' in bot_name:  # pragma: no cover
      if any(b in bot_name for b in ['arm64', 'nexus9']):
        return 'android_arm64_perf_bisect_builder'
      return 'android_perf_bisect_builder'

    return 'linux_perf_bisect_builder'

  def get_platform_gs_prefix(self):
    """Returns the prefix of a GS URL where a build can be found.

    This prefix includes the schema, bucket, directory and beginning
    of filename. It is joined together with the part of the filename
    that includes the revision and the file extension to form the
    full GS URL.
    """
    if self.api.buildurl_gs_prefix:  # pragma: no cover
      return self.api.buildurl_gs_prefix

    # TODO(prasadv): Refactor this code to remove hard coded values.
    bot_name = self.get_perf_tester_name()

    # TODO(prasadv): Refactor this code to remove hard coded values and use
    # target_bit from the bot config. crbug.com/640287
    if 'android' in bot_name: #pragma: no cover
      if any(b in bot_name for b in ['arm64', 'nexus9']):
        return 'gs://chrome-perf/Android arm64 Builder/full-build-linux_'
      return 'gs://chrome-perf/Android Builder/full-build-linux_'

    return 'gs://chrome-perf/Linux Builder/full-build-linux_'

  def ensure_sync_master_branch(self):
    """Make sure the local master is in sync with the fetched origin/master.

    We have seen on several occasions that the local master branch gets reset
    to previous revisions and also detached head states. Running this should
    take care of either situation.
    """
    # TODO(robertocn): Investigate what causes the states mentioned in the
    # docstring in the first place.
    with self.api.m.context(cwd=self.api.m.path['checkout']):
      self.api.m.git('update-ref', 'refs/heads/master',
                     'refs/remotes/origin/master')
      self.api.m.git('checkout', 'master')

  def is_return_code_mode(self):
    """Checks whether this is a bisect on the test's exit code."""
    return self.test_type == 'return_code'

  def surface_result(self, result_string):
    assert result_string in VALID_RESULT_CODES
    prefix = 'B4T_'  # To avoid collision. Stands for bisect (abbr. `a la i18n).
    result_code = prefix + result_string
    assert len(result_code) <= 20
    if result_code not in self.result_codes:
      self.result_codes.add(result_code)
      properties = self.api.m.step.active_result.presentation.properties
      properties['extra_result_code'] = sorted(self.result_codes)

  def get_result(self):
    """Returns the results as a jsonable object."""
    config = self.bisect_config

    if self.failed:
      status = 'failed'
    elif self.bisect_over:
      status = 'completed'
    else:
      status = 'started'

    aborted_reason = None
    if self.failed_initial_confidence:
      aborted_reason = _FAILED_INITIAL_CONFIDENCE_ABORT_REASON
    elif self.failed_direction:  # pragma: no cover
      aborted_reason = _DIRECTION_OF_IMPROVEMENT_ABORT_REASON

    return {
        'try_job_id': config.get('try_job_id'),
        'bug_id': config.get('bug_id'),
        'status': status,
        'buildbot_log_url': self._get_build_url(),
        'bisect_bot': self.get_perf_tester_name(),
        'command': config['command'],
        'test_type': config['test_type'],
        'metric': config.get('metric'),
        'change': self.relative_change,
        'good_revision': self.good_rev.commit_hash,
        'bad_revision': self.bad_rev.commit_hash,
        'warnings': self.warnings,
        'aborted_reason': self.aborted_reason or aborted_reason,
        'culprit_data': self._culprit_data(),
        'revision_data': self._revision_data(),
    }

  def _culprit_data(self):
    culprit = self.culprit
    api = self.api
    if not culprit:
      return None
    culprit_info = api.query_revision_info(self.culprit)

    if not culprit_info:  # pragma: no cover
      return None

    return {
        'subject': culprit_info['subject'],
        'author': culprit_info['author'],
        'email': culprit_info['email'],
        'cl_date': culprit_info['date'],
        'commit_info': culprit_info['body'],
        'revisions_links': [],
        'cl': culprit.commit_hash
    }

  def _revision_data(self):
    revision_rows = []
    for r in self.revisions:
      row = {
          'depot_name': r.depot_name,
          'commit_hash': r.commit_hash,
          'revision_string': r.revision_string(),
          'n_observations': len(r.display_values),
          'result': 'good' if r.good else 'bad' if r.bad else 'unknown',
          'failed': r.failed,
          'failure_reason': r.failure_reason,
          'build_id': r.build_id,
      }
      if r.test_run_count:
        row['mean_value'] = (r.overall_return_code
            if r.bisector.is_return_code_mode() else r.mean)
        row['std_dev'] = r.std_dev
      revision_rows.append(row)
    return revision_rows

  def _get_build_url(self):
    properties = self.api.m.properties
    bot_url = properties.get('buildbotURL',
                             'http://build.chromium.org/p/chromium/')
    builder_name = urllib.quote(properties.get('buildername', ''))
    builder_number = str(properties.get('buildnumber', ''))
    return '%sbuilders/%s/builds/%s' % (bot_url, builder_name, builder_number)
