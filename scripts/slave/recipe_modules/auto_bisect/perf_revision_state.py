# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import uuid

from . import revision_state


class PerfRevisionState(revision_state.RevisionState):

  """Contains the state and results for one revision in a perf bisect job."""
  def __init__(self, *args, **kwargs):
    super(PerfRevisionState, self).__init__(*args, **kwargs)
    self.values = []
    self.mean_value = None
    self.std_err = None

  def test_info(self):
    """Returns a dictionary with information that describes this test.

    It is meant to be used by the bisector to describe the test being run for
    each revision evaluated.
    """
    return {
        'command': self._test_config['command'],
        'metric': self._test_config['metric'],
    }

  def _read_test_results(self):
    """Gets the test results from GS and checks if the rev is good or bad."""
    results = self._get_test_results()
    # Results will contain the keys 'results' and 'output' where output is the
    # stdout of the command, and 'results' is itself a dict with the keys:
    # 'mean', 'values', 'std_err'
    results = results['results']
    self.mean_value = results['mean']
    self.values = results['values']
    self.std_err = results['std_err']
    # We cannot test the goodness of the initial rev range.
    if self.bisector.good_rev != self and self.bisector.bad_rev != self:
      if self._check_revision_good():
        self.good = True
      else:
        self.bad = True

  def _request_build(self):
    """Posts a request to buildbot to build this revision and archive it."""
    # TODO: Rewrite using the trigger module.
    # TODO: Send a diff patch when appropriate
    api = self.bisector.api
    bot_name = self.bisector.get_builder_bot_for_this_platform()
    if self.bisector.dummy_builds:
      self.build_job_name = self.commit_hash + '-build'
    else:  # pragma: no cover
      self.build_job_name = uuid.uuid4().hex
    try_cmd = [
        'try',
        '--bot=%s' % bot_name,
        '--revision=%s' % self.commit_hash,
        '--name=%s' % self.build_job_name,
        '--svn_repo=%s' % api.SVN_REPO_URL,
        '--diff',
        '/dev/null',
    ]
    api.m.git(*try_cmd, name='Requesting build for %s via git try.'
              % str(self.commit_hash))

  def _get_bisect_config_for_tester(self):
    """Copies the key-value pairs required by a tester bot to a new dict."""
    result = {}
    required_test_properties = {
        'truncate_percent',
        'metric',
        'max_time_minutes',
        'command',
        'repeat_count',
        'test_type'
    }
    for k, v in self.bisector.bisect_config.iteritems():
      if k in required_test_properties:
        result[k] = v
    self._test_config = result
    return result

  def _do_test(self):
    """Posts a request to buildbot to download and perf-test this build."""
    if self.bisector.dummy_builds:
      self.test_job_name = self.commit_hash + '-test'
    else:  # pragma: no cover
      self.test_job_name = uuid.uuid4().hex
    api = self.bisector.api
    perf_test_properties = {
        'buildername': self.bisector.get_perf_tester_name(),
        'revision': self.revision_string,
        'parent_build_archive_url': self.build_url,
        'bisect_config': self._get_bisect_config_for_tester(),
        'job_name': self.test_job_name,
    }
    step_name = 'Triggering test job for ' + str(self.revision_string)
    api.m.trigger(perf_test_properties, name=step_name)

  def _get_build_status(self):
    """Queries buildbot through the json API to check if the job is done."""
    api = self.bisector.api
    try:
      stdout = api.m.raw_io.output()
      name = 'Get test status for build ' + self.commit_hash
      step_result = api.m.python(name, api.resource('check_job_status.py'),
                                 args=[self.build_status_url], stdout=stdout)
    except api.m.step.StepFailure:  # pragma: no cover
      return None
    else:
      return step_result.stdout

  def _get_build_status_url(self):
    """Fetches the job URL from cloud storage.

    Note that when we post the request for a build or a test to buildbot, the
    job is not scheduled yet so there's no way to query its status. That's why
    we have made build and test jobs using the 'chromium' recipe upload a file
    with their status' URL as soon as possible.

    Returns:
      The URL (the verbatim content of the file in GS) or None if it could not
      be read.
    """
    api = self.bisector.api
    url_file_url = api.GS_RESULTS_URL + self.test_job_name
    try:
      stdout = api.m.raw_io.output()
      name = 'Get test status url for build ' + self.commit_hash
      step_result = api.m.gsutil.cat(url_file_url, stdout=stdout, name=name)
    except api.m.step.StepFailure:  # pragma: no cover
      return None
    else:
      return step_result.stdout

  def get_next_url(self):
    if not self.in_progress:
      return None
    if not self.built:
      return self.build_url
    if not self.build_status_url:
      # The file that will eventually contain the buildbot job url
      return self.bisector.api.GS_RESULTS_URL + self.test_job_name
    return self.build_status_url  # pragma: no cover

  def _get_test_results(self):
    """Tries to get the results of a test job from cloud storage."""
    api = self.bisector.api
    job_name = self.test_job_name
    results_file_url = api.GS_RESULTS_URL + job_name + '.results'
    try:
      stdout = api.m.raw_io.output()
      name = 'Get test results for build ' + self.commit_hash
      step_result = api.m.gsutil.cat(results_file_url, stdout=stdout,
                                     name=name)
    except api.m.step.StepFailure:  # pragma: no cover
      return None
    else:
      return json.loads(step_result.stdout)

  def _check_revision_good(self):
    """Determines if a revision is good or bad.

    Note that our current approach is to determine whether it is closer to
    either the 'good' and 'bad' revisions given for the bisect job.

    Returns:
      True if this revision is closer to the initial good revision's value than
      to the initial bad revision's value. False otherwise.
    """
    # TODO: Reevaluate this approach
    bisector = self.bisector
    distance_to_good = abs(self.mean_value - bisector.good_rev.mean_value)
    distance_to_bad = abs(self.mean_value - bisector.bad_rev.mean_value)
    if distance_to_good < distance_to_bad:
      return True
    return False
