# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from . import bisect_results
from . import depot_config

_DEPS_SHA_PATCH = """
diff --git DEPS.sha DEPS.sha
new file mode 100644
--- /dev/null
+++ DEPS.sha
@@ -0,0 +1 @@
+%(deps_sha)s
"""


ZERO_TO_NON_ZERO = 'Zero to non-zero'


class Bisector(object):
  """This class abstracts an ongoing bisect (or n-sect) job."""

  def __init__(self, api, bisect_config, revision_class, init_revisions=True):
    """Initializes the state of a new bisect job from a dictionary.

    Note that the initial good_rev and bad_rev MUST resolve to a commit position
    in the chromium repo.
    """
    super(Bisector, self).__init__()
    self._api = api
    self.bisect_config = bisect_config
    self.revision_class = revision_class

    # Test-only properties.
    # TODO: Replace these with proper mod_test_data
    self.dummy_regression_confidence = bisect_config.get(
        'dummy_regression_confidence')
    self.dummy_builds = bisect_config.get('dummy_builds', False)

    # Loading configuration items
    self.test_type = bisect_config.get('test_type', 'perf')
    self.improvement_direction = int(bisect_config.get(
        'improvement_direction', 0)) or None

    self.required_regression_confidence = bisect_config.get(
        'required_regression_confidence', 95)

    self.warnings = []

    # Status flags
    self.initial_regression_confidence = None
    self.results_confidence = None
    self.failed_confidence = False
    self.failed = False
    self.failed_direction = False
    self.lkgr = None  # Last known good revision
    self.fkbr = None  # First known bad revision
    self.culprit = None
    self.bisect_over = False
    self.relative_change = None

    # Initial revision range
    self.revisions = []
    self.bad_rev = revision_class(bisect_config['bad_revision'], self)
    self.bad_rev.bad = True
    self.good_rev = revision_class(bisect_config['good_revision'], self)
    self.good_rev.good = True
    if init_revisions:
      self._expand_revision_range()

  @property
  def api(self):
    return self._api

  @staticmethod
  def _commit_pos_range(a, b):
    """Given 2 commit positions, returns a list with the ones between."""
    a, b = sorted(map(int, [a, b]))
    return xrange(a + 1, b)

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
    except ValueError:
      pass

    raise self.api.m.step.StepFailure('Git did not output a valid hash for the '
                                      'interned file.')

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

    # Modify DEPS
    deps_var = depot['deps_var']
    deps_item_regexp = re.compile(
        r'(?<=["\']%s["\']: ["\'])([a-fA-F0-9]+)(?=["\'])' % deps_var,
        re.MULTILINE)
    if not re.search(deps_item_regexp, original_contents):
      raise self.api.m.step.StepFailure('DEPS file does not contain entry for '
                                        + deps_var)
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

  def _get_rev_range_for_depot(self, depot_name, min_rev, max_rev,
                               base_revision):
    results = []
    depot = depot_config.DEPOT_DEPS_NAME[depot_name]
    depot_path = self.api.m.path['slave_build'].join(depot['src'])
    step_name = ('Expanding revision range for revision %s on depot %s'
                 % (max_rev, depot_name))
    step_result = self.api.m.git('log', '--format=%H', min_rev + '...' +
                                 max_rev, stdout=self.api.m.raw_io.output(),
                                 cwd=depot_path, name=step_name)
    # We skip the first revision in the list as it is max_rev
    new_revisions = step_result.stdout.splitlines()[1:]
    for revision in new_revisions:
      results.append(self.revision_class(None, self,
                                         base_revision=base_revision,
                                         deps_revision=revision,
                                         dependency_depot_name=depot_name,
                                         depot=depot))
    results.reverse()
    return results

  def _expand_revision_range(self):
    """Populates the revisions attribute.

    After running this method, self.revisions should contain all the chromium
    revisions between the good and bad revisions.
    """
    rev_list = self._commit_pos_range(
        self.good_rev.commit_pos, self.bad_rev.commit_pos)
    intermediate_revs = [self.revision_class(str(x), self) for x in rev_list]
    self.revisions = [self.good_rev] + intermediate_revs + [self.bad_rev]
    self._update_revision_list_indexes()

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
      min_revision.read_deps()  # Parses DEPS file and sets the .deps property.
      max_revision.read_deps()  # Ditto.
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
    except RuntimeError:
      warning_text = ('Could not expand dependency revisions for ' +
                      revision_to_expand.revision_string)
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
    """
    direction = self.improvement_direction
    if direction is None:
      return True
    good = self.good_rev.mean_value
    bad = self.bad_rev.mean_value
    if ((bad > good and direction > 0) or
        (bad < good and direction < 0)):
      self._set_failed_direction_results()
      return False
    return True

  def _set_failed_direction_results(self):  # pragma: no cover
    self.failed_direction = True
    self.warnings.append('The initial regression range appears to represent '
                         'an improvement rather than a regression, given the '
                         'expected direction of improvement.')

  def check_regression_confidence(self):
    """Checks that the initial range presents a clear enough regression.

    We calculate the confidence score of the results of 'good' and 'bad'
    revisions and compare it against the required regression confidence set for
    the bisector.

    Note that when a dummy regression confidence value has been set via that
    is used instead.
    """
    if self.test_type != 'perf':
      raise NotImplementedError()  # pragma: no cover

    if self.required_regression_confidence is None:
      return True  # pragma: no cover

    if self.dummy_regression_confidence is not None:
      self.initial_regression_confidence = float(
          self.dummy_regression_confidence)
    else:  # pragma: no cover
      self.initial_regression_confidence = (
          self.api.m.math_utils.confidence_score(
              self.good_rev.values,
              self.bad_rev.values))
    if (self.initial_regression_confidence <
        self.required_regression_confidence):  # pragma: no cover
      self._set_insufficient_confidence_warning(
          self.initial_regression_confidence)
      return False
    return True

  def get_exception(self):
    raise NotImplementedError()  # pragma: no cover
    # TODO: should return an exception with the details of the failure.

  def _set_insufficient_confidence_warning(
      self, actual_confidence):  # pragma: no cover
    """Adds a warning about the lack of initial regression confidence."""
    self.failed_confidence = True
    self.warnings.append(
        ('Bisect failed to reproduce the regression with enough confidence. '
         'Needed {:.2f}%, got {:.2f}%.').format(
             self.required_regression_confidence, actual_confidence))

  def _compute_results_confidence(self):
    self.results_confidence = self.api.m.math_utils.confidence_score(
        self.lkgr.values, self.fkbr.values)

  def print_result(self):
    results = bisect_results.BisectResults(self).as_string()
    self.api.m.step('Results', ['cat'],
                    stdin=self.api.m.raw_io.input(data=results))

  def get_revisions_to_eval(self, max_revisions):
    """Gets N evenly distributed RevisionState objects in the candidate range.

    Args:
      max_revisions: Max number of revisions to return.

    Returns:
       At most `max_revisions` Revision objects in a list.
    """
    self._update_candidate_range()
    candidate_range = self.revisions[self.lkgr.list_index + 1:
                                     self.fkbr.list_index]
    if len(candidate_range) <= max_revisions:
      return candidate_range
    step = len(candidate_range)/(max_revisions + 1)
    return candidate_range[::step][-max_revisions:]

  def check_bisect_finished(self, revision):
    """Checks if this revision completes the bisection process.

    In this case 'finished' refers to finding one revision considered 'good'
    immediately preceding a revision considered 'bad' where the 'bad' revision
    does not contain a deps change.
    """
    if (revision.bad and revision.previous_revision and
        revision.previous_revision.good):  # pragma: no cover
      if revision.deps_change():
        more_revisions = self._expand_deps_revisions(revision)
        return not more_revisions
      self.culprit = revision
      return True
    if (revision.good and revision.next_revision and
        revision.next_revision.bad):
      if revision.next_revision.deps_change():
        more_revisions = self._expand_deps_revisions(revision.next_revision)
        return not more_revisions
      self.culprit = revision.next_revision
      self._compute_results_confidence()
      return True
    return False

  def wait_for_all(self, revision_list):
    """Waits for all revisions in list to finish."""
    while any([r.in_progress for r in revision_list]):
      self.wait_for_any(revision_list)
      for revision in revision_list:
        revision.update_status()

  def sleep_until_next_revision_ready(self, revision_list):
    """Produces a single step that sleeps until any revision makes progress.

    A revision is considered to make progress when a build file is uploaded to
    the appropriate bucket, or when buildbot test job is complete.
    """
    gsutil_path = self.api.m.gsutil.get_gsutil_path()
    name = 'Waiting for revision ' + revision_list[0].revision_string
    if len(revision_list) > 1:
      name += ' and %d other revision(s).' % (len(revision_list) - 1)
    script = self.api.resource('wait_for_any.py')
    args_list = [gsutil_path]
    url_list = [r.get_next_url() for r in revision_list]
    args_list += [url for url in url_list if url and url is not None]
    self.api.m.python(str(name), script, args_list)

  def wait_for_any(self, revision_list):
    """Waits for any of the revisions in the list to finish its job(s)."""
    while True:
      if not revision_list or not any(
          r.in_progress or r.tested for r in revision_list):  # pragma: no cover
        break
      self.sleep_until_next_revision_ready(revision_list)
      for revision in revision_list:
        revision.update_status()
        if revision.tested:
          return revision

  def abort_unnecessary_jobs(self):
    """Checks if any of the pending evaluations is no longer necessary.

    It assumes the candidate range (lkgr, fkbr) has already been set.
    """
    self._update_candidate_range()
    for r in self.revisions:
      if r == self.lkgr:
        break
      if not r.tested:
        r.good = True  # pragma: no cover
      if r.in_progress:
        r.abort()  # pragma: no cover
    for r in self.revisions[self.fkbr.list_index + 1:]:
      if not r.tested:
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
    # TODO: Actually check the current platform
    return 'linux_perf_tester'

  def get_builder_bot_for_this_platform(self):
    # TODO: Actually look at the current platform.
    return 'linux_perf_bisect_builder'

  def get_platform_gs_prefix(self):
    # TODO: Actually check the current platform
    return 'gs://chrome-perf/Linux Builder/full-build-linux_'
