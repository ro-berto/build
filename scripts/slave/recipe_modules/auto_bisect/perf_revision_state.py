# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import math
import tempfile
import os
import uuid

from . import revision_state

if 'CACHE_TEST_RESULTS' in os.environ:  # pragma: no cover
  from . import test_results_cache

# These relate to how to increase the number of repetitions during re-test
MINIMUM_SAMPLE_SIZE = 5
INCREASE_FACTOR = 1.5

class PerfRevisionState(revision_state.RevisionState):
  """Contains the state and results for one revision in a perf bisect job."""

  def __init__(self, *args, **kwargs):
    super(PerfRevisionState, self).__init__(*args, **kwargs)
    self.values = []
    self.mean_value = None
    self.std_dev = None
    self.repeat_count = MINIMUM_SAMPLE_SIZE
    self._test_config = None

  def _read_test_results(self, check_revision_goodness=True):
    """Gets the test results from GS and checks if the rev is good or bad."""
    test_results = self._get_test_results()
    # Results will contain the keys 'results' and 'output' where output is the
    # stdout of the command, and 'results' is itself a dict with the key
    # 'values' unless the test failed, in which case 'results' will contain
    # the 'error' key explaining the type of error.
    results = test_results['results']
    if results.get('errors'):
      self.status = PerfRevisionState.FAILED
      if 'MISSING_METRIC' in results.get('errors'):  # pragma: no cover
        self.bisector.surface_result('MISSING_METRIC')
      return
    self.values += results['values']
    if self.bisector.is_return_code_mode():
      retcodes = test_results['retcodes']
      overall_return_code = 0 if all(v == 0 for v in retcodes) else 1
      self.mean_value = overall_return_code
    elif self.values:
      api = self.bisector.api
      self.mean_value = api.m.math_utils.mean(self.values)
      self.std_dev = api.m.math_utils.standard_deviation(self.values)
    # Values were not found, but the test did not otherwise fail.
    else:
      self.status = PerfRevisionState.FAILED
      self.bisector.surface_result('MISSING_METRIC')
      return
    # If we have already decided on the goodness of this revision, we shouldn't
    # recheck it.
    if self.good or self.bad:
      check_revision_goodness = False
    # We cannot test the goodness of the initial rev range.
    if (self.bisector.good_rev != self and self.bisector.bad_rev != self and
        check_revision_goodness):
      if self._check_revision_good():
        self.good = True
      else:
        self.bad = True

  def _write_deps_patch_file(self, build_name):
    """Saves the DEPS patch in a temp location and returns the file path."""
    api = self.bisector.api
    file_name = str(api.m.path['tmp_base'].join(build_name + '.diff'))
    api.m.file.write('Saving diff patch for ' + str(self.revision_string),
                     file_name, self.deps_patch + self.deps_sha_patch)
    return file_name

  def _request_build(self):
    """Posts a request to buildbot to build this revision and archive it."""
    # TODO: Rewrite using the trigger module.
    api = self.bisector.api
    bot_name = self.bisector.get_builder_bot_for_this_platform()
    if self.bisector.dummy_builds:
      self.job_name = self.commit_hash + '-build'
    else:  # pragma: no cover
      self.job_name = uuid.uuid4().hex
    if self.needs_patch:
      self.patch_file = self._write_deps_patch_file(
          self.job_name)
    else:
      self.patch_file = '/dev/null'
    try_cmd = [
        'try',
        '--bot', bot_name,
        '--revision', self.commit_hash,
        '--name', self.job_name,
        '--clobber',
        '--svn_repo', api.SVN_REPO_URL,
        '--diff', self.patch_file,
    ]
    try:
      if not self.bisector.bisect_config.get('skip_gclient_ops'):
        self.bisector.ensure_sync_master_branch()
      api.m.git(
          *try_cmd, name='Requesting build for %s via git try.'
          % str(self.commit_hash), git_config_options={
              'user.email': 'FAKE_PERF_PUMPKIN@chromium.org',
          })
    except:  # pragma: no cover
      self.bisector.surface_result('BUILD_FAILURE')
      raise
    finally:
      if (self.patch_file != '/dev/null' and
          'TESTING_SLAVENAME' not in os.environ):
        try:
          api.m.file.remove('cleaning up patch', self.patch_file)
        except api.m.step.StepFailure:  # pragma: no cover
          print 'Could not clean up ' + self.patch_file

  def _get_bisect_config_for_tester(self):
    """Copies the key-value pairs required by a tester bot to a new dict."""
    result = {}
    required_test_properties = {
        'truncate_percent',
        'metric',
        'command',
        'test_type'
    }
    for k, v in self.bisector.bisect_config.iteritems():
      if k in required_test_properties:
        result[k] = v
    result['repeat_count'] = self.repeat_count
    self._test_config = result
    return result

  def _do_test(self):
    """Triggers tests for a revision, either locally or via try job.

    If local testing is enabled (i.e. director/tester merged) then
    the test will be run on the same machine. Otherwise, this posts
    a request to buildbot to download and perf-test this build.
    """
    if self.bisector.dummy_builds:
      self.job_name = self.commit_hash + '-test'
    elif 'CACHE_TEST_RESULTS' in os.environ:  # pragma: no cover
      self.job_name = test_results_cache.make_id(
          self.revision_string, self._get_bisect_config_for_tester())
    else:  # pragma: no cover
      self.job_name = uuid.uuid4().hex
    api = self.bisector.api
    perf_test_properties = {
        'builder_name': self.bisector.get_perf_tester_name(),
        'properties': {
            'revision': self.commit_hash,
            'parent_got_revision': self.commit_hash,
            'parent_build_archive_url': self.build_url,
            'bisect_config': self._get_bisect_config_for_tester(),
            'job_name': self.job_name,
        },
    }
    if 'CACHE_TEST_RESULTS' in os.environ and test_results_cache.has_results(
        self.job_name):  # pragma: no cover
      return
    self.test_results_url = (self.bisector.api.GS_RESULTS_URL +
                             self.job_name + '.results')
    if api.m.bisect_tester.local_test_enabled():  # pragma: no cover
      skip_download = self.bisector.last_tested_revision == self
      self.bisector.last_tested_revision = self
      overrides = perf_test_properties['properties']
      api.run_local_test_run(api.m, overrides, skip_download=skip_download)
    else:
      step_name = 'Triggering test job for ' + str(self.revision_string)
      api.m.trigger(perf_test_properties, name=step_name)

  def get_next_url(self):
    """Returns a GS URL for checking progress of a build or test."""
    if self.status == PerfRevisionState.BUILDING:
      return self.build_url
    if self.status == PerfRevisionState.TESTING:
      return self.test_results_url

  def get_buildbot_locator(self):
    """Returns information about the buildbot job that we're waiting for.

    This is used to check on the progress of a build or test that we're
    waiting for. If we're not waiting for a build or test job, this should
    return None.
    """
    if self.status not in (PerfRevisionState.BUILDING,
                           PerfRevisionState.TESTING):  # pragma: no cover
      return None
    # TODO(robertocn): Remove hardcoded master.
    master = 'tryserver.chromium.perf'
    if self.status == PerfRevisionState.BUILDING:
      builder = self.bisector.get_builder_bot_for_this_platform()
    if self.status == PerfRevisionState.TESTING:
      builder = self.bisector.get_perf_tester_name()
    return {
        'type': 'buildbot',
        'master': master,
        'builder': builder,
        'job_name': self.job_name,
    }

  def retest(self):  # pragma: no cover
    # We need at least 5 samples for applying Mann-Whitney U test
    # with P < 0.01, two-tailed .
    target_sample_size =  max(5, math.ceil(len(self.values) * 1.5))
    self.status = PerfRevisionState.NEED_MORE_DATA
    self.repeat_count = target_sample_size - len(self.values)
    self.start_job()
    self.bisector.wait_for_any([self])

  def _get_test_results(self):
    """Tries to get the results of a test job from cloud storage."""
    api = self.bisector.api
    try:
      stdout = api.m.raw_io.output()
      name = 'Get test results for build ' + self.commit_hash
      step_result = api.m.gsutil.cat(self.test_results_url, stdout=stdout,
                                     name=name)
    except api.m.step.StepFailure:  # pragma: no cover
      self.bisector.surface_result('TEST_FAILURE')
      return None
    else:
      return json.loads(step_result.stdout)

  def _check_revision_good(self):
    """Determines if a revision is good or bad.

    Iteratively increment the sample size of the revision being tested, the last
    known good revision, and the first known bad revision until a relationship
    of significant difference can be established betweeb the results of the
    revision being tested and one of the other two.

    If the results do not converge towards finding a significant difference in
    either direction, this is expected to timeout eventually. This scenario
    should be rather rare, since it is expected that the fkbr and lkgr are
    significantly different as a precondition.

    Returns:
      True if the results of testing this revision are significantly different
      from those of testing the earliest known bad revision.
      False if they are instead significantly different form those of testing
      the latest knwon good revision.
    """

    while True:
      diff_from_good = self.bisector.significantly_different(
          self.bisector.lkgr.values, self.values)
      diff_from_bad = self.bisector.significantly_different(
          self.bisector.fkbr.values, self.values)

      if diff_from_good and diff_from_bad:
        # Multiple regressions.
        # For now, proceed bisecting the biggest difference of the means.
        dist_from_good = abs(self.mean_value - self.bisector.lkgr.mean_value)
        dist_from_bad = abs(self.mean_value - self.bisector.fkbr.mean_value)
        if dist_from_good > dist_from_bad:
          # TODO(robertocn): Add way to handle the secondary regression
          #self.bisector.handle_secondary_regression(self, self.bisector.fkbr)
          return False
        else:
          #self.bisector.handle_secondary_regression(self.bisector.lkgr, self)
          return True

      if diff_from_good or diff_from_bad:  # pragma: no cover
        return diff_from_bad

      self._next_retest()  # pragma: no cover


  def _next_retest(self):  # pragma: no cover
    """Chooses one of current, lkgr, fkbr to retest.

    Look for the smallest sample and retest that. If the last tested revision
    is tied for the smallest sample, use that to take advantage of the fact
    that it is already downloaded and unzipped.
    """
    next_revision_to_test = min(self.bisector.lkgr, self, self.bisector.fkbr,
        key=lambda x: len(x.values))
    if (len(self.bisector.last_tested_revision.values) ==
        next_revision_to_test.values):
      self.bisector.last_tested_revision.retest()
    else:
      next_revision_to_test.retest()

  def __repr__(self):
    return ('PerfRevisionState(cp=%s, values=%r, mean_value=%r, std_dev=%r)' %
            (self.commit_pos, self.values, self.mean_value, self.std_dev))
