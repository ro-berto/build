# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import re
import time
import urllib

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

# How long to re-test the initial good-bad range for until significant
# difference is established.
REGRESSION_CHECK_TIMEOUT = 2 * 60 * 60
# If we reach this number of samples on the reference range and have not
# achieved statistical significance, bail.
MAX_REQUIRED_SAMPLES = 50

# Significance level to use for determining difference between revisions via
# hypothesis testing.
SIGNIFICANCE_LEVEL = 0.01

_FAILED_INITIAL_CONFIDENCE_ABORT_REASON = (
    'The metric values for the initial "good" and "bad" revisions '
    'do not represent a clear regression.')

_DIRECTION_OF_IMPROVEMENT_ABORT_REASON = (
    'The metric values for the initial "good" and "bad" revisions match the '
    'expected direction of improvement. Thus, likely represent an improvement '
    'and not a regression.')


class Bisector(object):
  """This class abstracts an ongoing bisect (or n-sect) job."""

  def __init__(self, api, bisect_config, revision_class, init_revisions=True):
    """Initializes the state of a new bisect job from a dictionary.

    Note that the initial good_rev and bad_rev MUST resolve to a commit position
    in the chromium repo.
    """
    super(Bisector, self).__init__()
    self._api = api
    self.ensure_sync_master_branch()
    self.bisect_config = bisect_config
    self.config_step()
    self.revision_class = revision_class
    self.result_codes = set()
    self.last_tested_revision = None

    # Test-only properties.
    # TODO: Replace these with proper mod_test_data.
    self.dummy_initial_confidence = bisect_config.get(
        'dummy_initial_confidence')
    self.dummy_builds = bisect_config.get('dummy_builds', False)

    # Load configuration items.
    self.test_type = bisect_config.get('test_type', 'perf')
    self.improvement_direction = int(bisect_config.get(
        'improvement_direction', 0)) or None
    # Required initial confidence might be explicitly set to None,
    # which means that no initial confidence check should be done.
    if ('required_initial_confidence' in bisect_config and
        bisect_config['required_initial_confidence'] is None):
      self.required_initial_confidence = None  # pragma: no cover
    else:
      self.required_initial_confidence = float(bisect_config.get(
          'required_initial_confidence', 80))

    self.warnings = []

    # Status flags
    self.initial_confidence = None
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
    with api.m.step.nest('Resolving reference range'):

      if len(bisect_config['bad_revision']) == 40:  # pragma: no cover
        # Must be hex.
        int (bisect_config['bad_revision'], 16)
        bad_hash = bisect_config['bad_revision']
      else:
        # Must be decimal.
        int(bisect_config['bad_revision'], 10)
        bad_hash = api.m.commit_position.chromium_hash_from_commit_position(
            bisect_config['bad_revision'])

      if len(bisect_config['good_revision']) == 40:  # pragma: no cover
        # Must be hex.
        int (bisect_config['good_revision'], 16)
        good_hash = bisect_config['good_revision']
      else:
        # Must be decimal.
        int(bisect_config['good_revision'], 10)
        good_hash = api.m.commit_position.chromium_hash_from_commit_position(
            bisect_config['good_revision'])

      self.revisions = []
      self.bad_rev = revision_class(self, bad_hash)
      self.bad_rev.bad = True
      self.bad_rev.read_deps(self.get_perf_tester_name())
      api.m.step.active_result.presentation.logs['Debug Bad Revision DEPS'] = [
          '%s: %s' % (key, value) for key, value in
          self.bad_rev.deps.iteritems()]
      self.bad_rev.deps = {}
      self.fkbr = self.bad_rev
      self.good_rev = revision_class(self, good_hash)
      self.good_rev.good = True
      self.good_rev.read_deps(self.get_perf_tester_name())
      api.m.step.active_result.presentation.logs['Debug Good Revision DEPS'] = [
          '%s: %s' % (key, value) for key, value in
          self.good_rev.deps.iteritems()]
      self.good_rev.deps = {}
      self.lkgr = self.good_rev
    if init_revisions:
      self._expand_chromium_revision_range()

  def significantly_different(
      self, list_a, list_b,
      significance_level=SIGNIFICANCE_LEVEL): # pragma: no cover
    """Uses an external script to run hypothesis testing with scipy.

    The reason why we need an external script is that scipy is not available to
    the default python installed in all platforms. We instead rely on an
    anaconda environment to provide those packages.

    Args:
      list_a, list_b: Two lists representing samples to be compared.
      significance_level: Self-describing. As a decimal fraction.

    Returns:
      A boolean indicating whether the null hypothesis ~(that the lists are
      samples from the same population) can be rejected at the specified
      significance level.
    """
    step_result = self.api.m.python(
        'Checking sample difference',
        self.api.resource('significantly_different.py'),
        [json.dumps(list_a), json.dumps(list_b), str(significance_level)],
        stdout=self.api.m.json.output())
    results = step_result.stdout
    if results is None:
      assert self.dummy_builds
      return True
    significantly_different = results['significantly_different']
    step_result.presentation.logs[str(significantly_different)] = [
        'See json.output for details']
    return significantly_different

  def config_step(self):
    """Yields a simple echo step that outputs the bisect config."""
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
    result = api.m.step('config', [])
    config_lines = config_string.splitlines()
    result.presentation.logs['Bisect job configuration'] = config_lines

  @property
  def api(self):
    return self._api

  def compute_relative_change(self):
    old_value = float(self.good_rev.mean_value)
    new_value = float(self.bad_rev.mean_value)

    if new_value and not old_value:  # pragma: no cover
      self.relative_change = ZERO_TO_NON_ZERO
      return

    rel_change = self.api.m.math_utils.relative_change(old_value, new_value)
    self.relative_change = '%.2f%%' % (100 * rel_change)

  def make_deps_sha_file(self, deps_sha):
    """Make a diff patch that creates DEPS.sha.

    Args:
      deps_sha (str): The hex digest of a SHA1 hash of the diff that patches
        DEPS.

    Returns:
      A string containing a git diff.
    """
    return _DEPS_SHA_PATCH % {'deps_sha': deps_sha}

  def _git_intern_file(self, file_contents, cwd, commit_hash):
    """Writes a file to the git database and produces its git hash.

    Args:
      file_contents (str): The contents of the file to be hashed and interned.
      cwd (recipe_config_types.Path): Path to the checkout whose repository the
        file is to be written to.
      commit_hash (str): An identifier for the step.

    Returns:
      A string containing the hash of the interned object.
    """
    cmd = 'hash-object -t blob -w --stdin'.split(' ')
    stdin = self.api.m.raw_io.input(file_contents)
    stdout = self.api.m.raw_io.output()
    step_name = 'Hashing modified DEPS file with revision ' + commit_hash
    step_result = self.api.m.git(*cmd, cwd=cwd, stdin=stdin, stdout=stdout,
                                 name=step_name)
    hash_string = step_result.stdout.splitlines()[0]
    try:
      if hash_string:
        int(hash_string, 16)
        return hash_string
    except ValueError:  # pragma: no cover
      reason = 'Git did not output a valid hash for the interned file.'
      self.api.m.halt(reason)
      raise self.api.m.step.StepFailure(reason)

  def _gen_diff_patch(self, git_object_a, git_object_b, src_alias, dst_alias,
                      cwd, deps_rev):
    """Produces a git diff patch.

    Args:
      git_object_a (str): Tree-ish git object identifier.
      git_object_b (str): Another tree-ish git object identifier.
      src_alias (str): Label to replace the tree-ish identifier on
        the resulting diff patch. (git_object_a)
      dst_alias (str): Same as above for (git_object_b)
      cwd (recipe_config_types.Path): Path to the checkout whose repo contains
        the objects to be compared.
      deps_rev (str): Deps revision to identify the patch generating step.

    Returns:
      A string containing the diff patch as produced by the 'git diff' command.
    """
    # The prefixes used in the command below are used to find and replace the
    # tree-ish git object id's on the diff output more easily.
    cmd = 'diff %s %s --src-prefix=IAMSRC: --dst-prefix=IAMDST:'
    cmd %= (git_object_a, git_object_b)
    cmd = cmd.split(' ')
    stdout = self.api.m.raw_io.output()
    step_name = 'Generating patch for %s to %s' % (git_object_a, deps_rev)
    step_result = self.api.m.git(*cmd, cwd=cwd, stdout=stdout, name=step_name)
    patch_text = step_result.stdout
    src_string = 'IAMSRC:' + git_object_a
    dst_string = 'IAMDST:' + git_object_b
    patch_text = patch_text.replace(src_string, src_alias)
    patch_text = patch_text.replace(dst_string, dst_alias)
    return patch_text

  def make_deps_patch(self, base_revision, base_file_contents,
                      depot, new_commit_hash):
    """Make a diff patch that updates a specific dependency revision.

    Args:
      base_revision (RevisionState): The revision for which the DEPS file is to
        be patched.
      base_file_contents (str): The contents of the original DEPS file.
      depot (str): The dependency to modify.
      new_commit_hash (str): The revision to put in place of the old one.

    Returns:
      A pair containing the git diff patch that updates DEPS, and the
      full text of the modified DEPS file, both as strings.
    """
    original_contents = str(base_file_contents)
    patched_contents = str(original_contents)

    # Modify DEPS.
    deps_var = depot['deps_var']
    deps_item_regexp = re.compile(
        r'(?<=["\']%s["\']: ["\'])([a-fA-F0-9]+)(?=["\'])' % deps_var,
        re.MULTILINE)
    if not re.search(deps_item_regexp, original_contents):  # pragma: no cover
      reason = 'DEPS file does not contain entry for ' + deps_var
      self.api.m.halt(reason)
      raise self.api.m.step.StepFailure(reason)

    patched_contents = re.sub(deps_item_regexp, new_commit_hash,
                              original_contents)

    interned_deps_hash = self._git_intern_file(patched_contents,
                                               self.api.m.path['checkout'],
                                               new_commit_hash)
    patch_text = self._gen_diff_patch(base_revision.commit_hash + ':DEPS',
                                      interned_deps_hash, 'DEPS', 'DEPS',
                                      cwd=self.api.m.path['checkout'],
                                      deps_rev=new_commit_hash)
    return patch_text, patched_contents

  def _expand_chromium_revision_range(self):
    """Populates the revisions attribute.

    After running this method, self.revisions should contain all the chromium
    revisions between the good and bad revisions.
    """
    with self.api.m.step.nest('Expanding revision range'):
      rev_list = self._get_chromium_rev_range(
          self.good_rev.commit_hash, self.bad_rev.commit_hash)
      intervening_revs = [self.revision_class(self, commit_hash)
                          for commit_hash, _ in rev_list]
      self.revisions = [self.good_rev] + intervening_revs + [self.bad_rev]
      self._update_revision_list_indexes()

  def _get_chromium_rev_range(self, min_rev, max_rev):
    """Returns a list of Chromium commit (hash, position) pairs in a range.

    The returned range does not include the given |min_rev| or |max_rev|.
    """
    try:
      step_result = self.api.m.python(
          'for revisions %s:%s' % (min_rev, max_rev),
          self.api.resource('fetch_intervening_revisions.py'),
          [min_rev, max_rev, 'chromium'],
          stdout=self.api.m.json.output())
      return step_result.stdout
    except self.api.m.step.StepFailure:  # pragma: no cover
      self.surface_result('BAD_REV')
      raise

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
      # Parses DEPS file and sets the .deps property.
      min_revision.read_deps(self.get_perf_tester_name())
      max_revision.read_deps(self.get_perf_tester_name())
      for depot_name in depot_config.DEPOT_DEPS_NAME.keys():
        if depot_name in min_revision.deps and depot_name in max_revision.deps:
          dep_revision_min = min_revision.deps[depot_name]
          dep_revision_max = max_revision.deps[depot_name]
          if (dep_revision_min and dep_revision_max and
              dep_revision_min != dep_revision_max):
            rev_list = self._get_rev_range_for_depot(depot_name,
                                                     dep_revision_min,
                                                     dep_revision_max,
                                                     min_revision)
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

  def _get_rev_range_for_depot(self, depot_name, min_rev, max_rev,
                               base_revision):
    """Returns a list of revision objects in a range for a non-Chromium repo.

    Args:
      depot_name: Short string name of repo, e.g. chromium or v8.
      min_rev: Start commit hash (not included).
      max_rev: End commit hash (not included).
      base_revision: Base revision in the downstream repo (e.g. chromium).
    """
    try:
      step_result = self.api.m.python(
          ('Expanding revision range for revision %s on depot %s'
           % (max_rev, depot_name)),
          self.api.resource('fetch_intervening_revisions.py'),
          [min_rev, max_rev, depot_name],
          stdout=self.api.m.json.output())
    except self.api.m.step.StepFailure:  # pragma: no cover
      self.surface_result('BAD_REV')
      raise
    results = []
    for git_hash, _ in step_result.stdout:
      revision_object = self.revision_class(
          self,
          git_hash,
          depot_name,
          base_revision)
      results.append(revision_object)
    return results

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
    """
    good = self.good_rev.mean_value
    bad = self.bad_rev.mean_value

    if self.is_return_code_mode():
      if good == 1 or bad == 0:
        self._set_failed_return_code_direction_results()
        return False
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

    We calculate the confidence of the results of the given 'good'
    and 'bad' revisions and compare it against the required confidence
    set for the bisector.

    Note that when a dummy regression confidence value has been set, that
    is used instead.
    """
    if self.test_type != 'perf':
      return True

    if self.required_initial_confidence is None:
      return True  # pragma: no cover

    # TODO(robertocn): Remove all uses of "confidence".
    if self.dummy_initial_confidence is not None:
      self.initial_confidence = float(
          self.dummy_initial_confidence)
      if (float(self.initial_confidence) <
          float(self.required_initial_confidence)):
        self._set_insufficient_confidence_warning()
        return False
      return True

    if self.dummy_builds:
      dummy_result = self.good_rev.values != self.bad_rev.values
      if not dummy_result:
        self._set_insufficient_confidence_warning()
      return dummy_result

    with self.api.m.step.nest('Re-testing reference range'):
      expiration_time = time.time() + REGRESSION_CHECK_TIMEOUT
      while time.time() < expiration_time:
        if len(self.good_rev.values) >= 5 and len(self.bad_rev.values) >= 5:
          if self.significantly_different(self.good_rev.values,
                                          self.bad_rev.values):
            return True
        if len(self.good_rev.values) == len(self.bad_rev.values):
          revision_to_retest = self.last_tested_revision
        else:
          revision_to_retest = min(self.good_rev, self.bad_rev,
                                   key=lambda x: len(x.values))
        if len(revision_to_retest.values) < MAX_REQUIRED_SAMPLES:
          revision_to_retest.retest()
        else:
          break
      self._set_insufficient_confidence_warning()
      return False


  def get_exception(self):
    raise NotImplementedError()  # pragma: no cover
    # TODO: should return an exception with the details of the failure.

  def _set_insufficient_confidence_warning(
      self):  # pragma: no cover
    """Adds a warning about the lack of initial regression confidence."""
    self.failed_initial_confidence = True
    self.surface_result('LO_INIT_CONF')
    self.warnings.append(
        'Bisect failed to reproduce the regression with enough confidence.')

  def _results_debug_message(self):
    """Returns a string with values used to debug a bisect result."""
    result = 'bisector.lkgr: %r\n' % self.lkgr
    result += 'bisector.fkbr: %r\n\n' % self.fkbr
    result += self._revision_value_table()
    if (self.lkgr and self.lkgr.values and self.fkbr and self.fkbr.values):
      result += '\n' + self._t_test_results()
    return result

  def _revision_value_table(self):
    """Returns a string table showing revisions and their values."""
    header = [['Revision', 'Values']]
    rows = [[r.revision_string(), str(r.values)] for r in self.revisions]
    return self._pretty_table(header + rows)

  def _pretty_table(self, data):
    results = []
    for row in data:
      results.append('%-15s' * len(row) % tuple(row))
    return '\n'.join(results)

  def _t_test_results(self):
    """Returns a string showing t-test results for lkgr and fkbr."""
    t, df, p = self.api.m.math_utils.welchs_t_test(
        self.lkgr.values, self.fkbr.values)
    lines = [
        'LKGR values: %r' % self.lkgr.values,
        'FKBR values: %r' % self.fkbr.values,
        't-statistic: %r' % t,
        'deg. of freedom:  %r' % df,
        'p-value: %r' % p,
        'Confidence score: %r' % (100 * (1 - p))
    ]
    return '\n'.join(lines)

  def print_result_debug_info(self):
    """Prints extra debug info at the end of the bisect process."""
    lines = self._results_debug_message().splitlines()
    # If we emit a null step then add a log to it, the log should be kept
    # longer than 7 days (which is often needed to debug some issues).
    self.api.m.step('Debug Info', [])
    self.api.m.step.active_result.presentation.logs['Debug Info'] = lines

  def post_result(self, halt_on_failure=False):
    """Posts bisect results to Perf Dashboard."""
    self.api.m.perf_dashboard.set_default_config()
    self.api.m.perf_dashboard.post_bisect_results(
        self.get_result(), halt_on_failure)

  def get_revision_to_eval(self):
    """Gets the next RevisionState object in the candidate range.

    Returns:
       The next Revision object in a list.
    """
    self._update_candidate_range()
    candidate_range = [revision for revision in
                       self.revisions[self.lkgr.list_index + 1:
                                      self.fkbr.list_index]
                       if not revision.tested and not revision.failed]
    if len(candidate_range) <= 1:
      return candidate_range

    default_revision = candidate_range[len(candidate_range) / 2]

    with self.api.m.step.nest(
        'Wiggling revision ' + default_revision.revision_string()):
      # We'll search up to 25% of the range (in either direction) to try and
      # find a nearby commit that's already been built.
      max_wiggle = int(len(candidate_range) * DEFAULT_SEARCH_RANGE_PERCENTAGE)
      for _ in xrange(max_wiggle):  # pragma: no cover
        index = len(candidate_range) / 2
        if candidate_range[index]._is_build_archived():
          return [candidate_range[index]]
        del candidate_range[index]

      return [default_revision]

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
        revision.previous_revision.good):  # pragma: no cover
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
    return False

  def wait_for_all(self, revision_list):
    """Waits for all revisions in list to finish."""
    # TODO(simonhatch): Simplify these (and callers) since
    # get_revision_to_eval() no longer returns multiple revisions.
    # See http://crbug.com/546695.
    while any([r.in_progress for r in revision_list]):
      revision_list.remove(self.wait_for_any(revision_list))

  def sleep_until_next_revision_ready(self, revision_list):
    """Produces a single step that sleeps until any revision makes progress.

    A revision is considered to make progress when a build file is uploaded to
    the appropriate bucket, or when buildbot test job is complete.
    """
    api = self.api

    revision_mapping = {}
    gs_jobs = []
    buildbot_jobs = []

    for revision in revision_list:
      url = revision.get_next_url()
      buildbot_job = revision.get_buildbot_locator()
      if url:
        gs_jobs.append({'type': 'gs', 'location': url})
        revision_mapping[url] = revision
      if buildbot_job:
        buildbot_jobs.append(buildbot_job)
        revision_mapping[buildbot_job['job_name']] = revision

    jobs_config = {'jobs': buildbot_jobs + gs_jobs}

    script = api.resource('wait_for_any.py')
    args_list = [api.m.gsutil.get_gsutil_path()] if gs_jobs else []

    try:
      step_name = 'Waiting for revision ' + revision_list[0].commit_hash
      if len(revision_list) > 1:
        step_name += ' and %d other revision(s).' % (len(revision_list) - 1)
      api.m.python(
          str(step_name),
          script,
          args_list,
          stdout=api.m.json.output(),
          stdin=api.m.json.input(jobs_config),
          ok_ret={0, 1})
    except api.m.step.StepFailure as sf:  # pragma: no cover
      if sf.retcode == 2:  # 6 days and no builds finished.
        for revision in revision_list:
          revision.status = revision_state.RevisionState.FAILED
        for revision in revision_list:
          if revision.status == revision.TESTING:
            self.surface_result('TEST_TIMEOUT')
          if revision.status == revision.BUILDING:
            self.surface_result('BUILD_TIMEOUT')
        return None  # All builds are failed, no point in returning one.
      else:  # Something else went wrong.
        raise

    step_results = api.m.step.active_result.stdout
    build_failed = api.m.step.active_result.retcode

    if build_failed:
      # Explicitly make the step red.
      api.m.step.active_result.presentation.status = api.m.step.FAILURE

    if not step_results:
      # For most recipe_simulation_test cases.
      return None

    failed_jobs = step_results.get('failed', [])
    completed_jobs = step_results.get('completed', [])
    last_failed_revision = None
    assert failed_jobs or completed_jobs

    # Marked all failed builds as failed
    for job in failed_jobs:
      last_failed_revision = revision_mapping[str(job.get(
          'location', job.get('job_name')))]
      if 'job_url' in job:
        url = job['job_url']
        api.m.step.active_result.presentation.links['Failed build'] = url
      last_failed_revision.status = revision_state.RevisionState.FAILED

    # Return a completed job if available.
    for job in completed_jobs:
      if 'job_url' in job:  # pragma: no cover
        url = job['job_url']
        api.m.step.active_result.presentation.links['Completed build'] = url
      return revision_mapping[str(job.get(
          'location', job.get('job_name')))]

    # Or return any of the failed revisions.
    return last_failed_revision

  def wait_for_any(self, revision_list):
    """Waits for any of the revisions in the list to finish its job(s)."""
    # TODO(simonhatch): Simplify these (and callers) since
    # get_revision_to_eval() no longer returns multiple revisions.
    # See http://crbug.com/546695.
    while True:
      if not revision_list or any(r.status == revision_state.RevisionState.NEW
                                  for r in revision_list):  # pragma: no cover
        # We want to avoid waiting forever for revisions that are not started,
        # or for an empty list, hence we fail fast.
        assert False

      finished_revision = self.sleep_until_next_revision_ready(revision_list)

      # On recipe simulation, sleep_until_next_revision_ready will by default
      # return nothing.
      revisions = [finished_revision] if finished_revision else revision_list
      for revision in revisions:
        if revision:
          revision.update_status()
          if not revision.in_progress:
            return revision

  def abort_unnecessary_jobs(self):
    """Checks if any of the pending evaluations is no longer necessary.

    It assumes the candidate range (lkgr, fkbr) has already been set.
    """
    self._update_candidate_range()
    for r in self.revisions:
      if r == self.lkgr:
        break
      if not r.tested or r.failed:
        r.good = True  # pragma: no cover
      if r.in_progress:
        r.abort()  # pragma: no cover
    for r in self.revisions[self.fkbr.list_index + 1:]:
      if not r.tested or r.failed:
        r.bad = True  # pragma: no cover
      if r.in_progress:
        r.abort()  # pragma: no cover

  def _update_candidate_range(self):
    """Updates lkgr and fkbr (last known good/first known bad) revisions.

    lkgr and fkbr are 'pointers' to the appropriate RevisionState objects in
    bisectors.revisions."""
    for r in self.revisions:
      if r.tested:
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
    if 'win' in bot_name:
      if any(b in bot_name for b in ['x64', 'gpu']):
        return 'winx64_bisect_builder'
      return 'win_perf_bisect_builder'

    if 'android' in bot_name:
      if 'nexus9' in bot_name:
        return 'android_arm64_perf_bisect_builder'
      return 'android_perf_bisect_builder'

    if 'mac' in bot_name:
      return 'mac_perf_bisect_builder'

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
    if 'win' in bot_name:
      if any(b in bot_name for b in ['x64', 'gpu']):
        return 'gs://chrome-perf/Win x64 Builder/full-build-win32_'
      return 'gs://chrome-perf/Win Builder/full-build-win32_'

    if 'android' in bot_name:
      if 'nexus9' in bot_name:
        return 'gs://chrome-perf/android_perf_rel_arm64/full-build-linux_'
      return 'gs://chrome-perf/android_perf_rel/full-build-linux_'

    if 'mac' in bot_name:
      return 'gs://chrome-perf/Mac Builder/full-build-mac_'

    return 'gs://chrome-perf/Linux Builder/full-build-linux_'

  def ensure_sync_master_branch(self):
    """Make sure the local master is in sync with the fetched origin/master.

    We have seen on several occasions that the local master branch gets reset
    to previous revisions and also detached head states. Running this should
    take care of either situation.
    """
    # TODO(robertocn): Investigate what causes the states mentioned in the
    # docstring in the first place.
    self.api.m.git('update-ref', 'refs/heads/master',
                   'refs/remotes/origin/master')
    self.api.m.git('checkout', 'master', cwd=self.api.m.path['checkout'])

  def is_return_code_mode(self):
    """Checks whether this is a bisect on the test's exit code."""
    return self.bisect_config.get('test_type') == 'return_code'

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
    results_confidence = 0
    if self.culprit:
      results_confidence = self.api.m.math_utils.confidence_score(
          self.lkgr.values, self.fkbr.values)

    if self.failed:
      status = 'failed'
    elif self.bisect_over:
      status = 'completed'
    else:
      status = 'started'

    aborted_reason = None
    if self.failed_initial_confidence:
      aborted_reason = _FAILED_INITIAL_CONFIDENCE_ABORT_REASON
    elif self.failed_direction:
      aborted_reason = _DIRECTION_OF_IMPROVEMENT_ABORT_REASON
    return {
        'try_job_id': config.get('try_job_id'),
        'bug_id': config.get('bug_id'),
        'status': status,
        'buildbot_log_url': self._get_build_url(),
        'bisect_bot': self.get_perf_tester_name(),
        'command': config['command'],
        'test_type': config['test_type'],
        'metric': config['metric'],
        'change': self.relative_change,
        'score': results_confidence,
        'good_revision': self.good_rev.commit_hash,
        'bad_revision': self.bad_rev.commit_hash,
        'warnings': self.warnings,
        'aborted_reason': aborted_reason,
        'culprit_data': self._culprit_data(),
        'revision_data': self._revision_data()
    }

  def _culprit_data(self):
    culprit = self.culprit
    api = self.api
    if not culprit:
      return None
    culprit_info = api.query_revision_info(self.culprit)

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
      if r.tested or r.aborted:
        revision_rows.append({
            'depot_name': r.depot_name,
            'commit_hash': r.commit_hash,
            'revision_string': r.revision_string(),
            'mean_value': r.mean_value,
            'std_dev': r.std_dev,
            'values': r.values,
            'result': 'good' if r.good else 'bad' if r.bad else 'unknown',
        })
    return revision_rows

  def _get_build_url(self):
    properties = self.api.m.properties
    bot_url = properties.get('buildbotURL',
                             'http://build.chromium.org/p/chromium/')
    builder_name = urllib.quote(properties.get('buildername', ''))
    builder_number = str(properties.get('buildnumber', ''))
    return '%sbuilders/%s/builds/%s' % (bot_url, builder_name, builder_number)
