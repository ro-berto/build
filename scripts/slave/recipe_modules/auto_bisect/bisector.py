# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import bisect_results

class Bisector(object):
  """This class abstracts an ongoing bisect (or n-sect) job."""

  def __init__(self, api, bisect_config, revision_class):
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
        'dummy_regression_confidence', None)
    self.dummy_builds = bisect_config.get('dummy_builds', False)

    # Loading configuration items
    self.test_type = bisect_config.get('test_type', 'perf')
    self.improvement_direction = int(bisect_config.get(
        'improvement_direction', 0)) or None

    self.required_regression_confidence = bisect_config.get(
        'required_regression_confidence', 95)

    self.warnings = []

    # Status flags
    self.failed_confidence = False
    self.failed = False
    self.failed_direction = False
    self.lkgr = None  # Last known good revision
    self.fkbr = None  # First known bad revision
    self.culprit = None
    self.bisect_over = False

    # Initial revision range
    self.revisions = []
    self.bad_rev = revision_class(bisect_config['bad_revision'], self)
    self.bad_rev.bad = True
    self.good_rev = revision_class(bisect_config['good_revision'], self)
    self.good_rev.good = True
    self._expand_revision_range()

  @property
  def api(self):
    return self._api

  @staticmethod
  def _commit_pos_range(a, b):
    """Given 2 commit positions, returns a list with the ones between."""
    a, b = sorted(map(int, [a, b]))
    return xrange(a + 1, b)

  def _expand_revision_range(self, revision_to_expand=None):
    """This method populates the revisions attribute.

    After running method self.revisions should contain all the revisions
    between the good and bad revisions. If given a `revision_to_expand`, it'll
    insert the revisions from the external repos in the appropriate place.

    Args:
      revision_to_expand: A revision where there is a deps change.
    """
    if revision_to_expand is not None:
      # TODO: Implement this path (insert revisions when deps change)
      raise NotImplementedError()  # pragma: no cover
    rev_list = self._commit_pos_range(
        self.good_rev.commit_pos, self.bad_rev.commit_pos)
    intermediate_revs = [self.revision_class(str(x), self) for x in rev_list]
    self.revisions = [self.good_rev] + intermediate_revs + [self.bad_rev]
    for i, rev in enumerate(self.revisions):
      rev.list_index = i
    for i in xrange(len(self.revisions)):
      if i:
        self.revisions[i].previous_revision = self.revisions[i - 1]
      if i < len(self.revisions) - 1:
        self.revisions[i].next_revision = self.revisions[i + 1]

  def check_improvement_direction(self):  # pragma: no cover
    """Verifies that the change from 'good' to 'bad' is in the right direction.

    The change between the test results obtained for the given 'good' and 'bad'
    revisions is expected to be considered a regression. The `improvement_direction`
    attribute is positive if a larger number is considered better, and negative if a
    smaller number is considered better.
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
      regression_confidence = float(self.dummy_regression_confidence)
    else:  # pragma: no cover
      regression_confidence = self.api.m.math_utils.confidence_score(
          self.good_rev.values,
          self.bad_rev.values)
    if (regression_confidence <
        self.required_regression_confidence):  # pragma: no cover
      self._set_insufficient_confidence_warning(regression_confidence)
      return False
    return True

  def get_exception(self):
    raise NotImplementedError()  # pragma: no cover
    # TODO: should return an exception with the details of the failure.

  def _set_insufficient_confidence_warning(
      self, actual_confidence):  # pragma: no cover
    """Adds a warning about the lack of initial regression confidence."""
    self.failed_confidence = True
    self.warnings.append(('Bisect failed to reproduce the regression with '
                          'enough confidence. Needed {:.2f}%, got {:.2f}%.'
                          ).format(self.required_regression_confidence,
                                   actual_confidence))


  def print_result(self):
    results_json = bisect_results.BisectResults(self).to_json()
    self.api.m.python('results', self.api.resource('annotated_results.py'),
                      stdin=self.api.m.raw_io.input(data=results_json),
                      allow_subannotations=True)

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
        self._expand_revision_range(revision)
        return False
      self.culprit = revision
      return True
    if (revision.good and revision.next_revision and
        revision.next_revision.bad):
      if revision.next_revision.deps_change():  # pragma: no cover
        self._expand_revision_range(revision.next_revision)
        return False
      self.culprit = revision.next_revision
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
    name = 'Waiting for any of these revisions:' + ' '.join(
        [r.revision_string for r in revision_list])
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

