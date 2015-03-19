# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""API for the bisect recipe module.

This API is meant to enable the bisect recipe to bisect any chromium-supported
platform for any test that can be run via buildbot, perf or otherwise.
"""

from slave import recipe_api
from . import bisector
from . import perf_revision_state


class AutoBisectApi(recipe_api.RecipeApi):
  """A module for bisect specific functions."""

  # Number of seconds to wait between polls for test results
  POLLING_INTERVAL = 60
  # GS bucket to use for communicating results and job state between bisector
  # and tester bots
  BUCKET = 'chrome-perf'
  # Directory within the above bucket to store results
  RESULTS_GS_DIR = 'bisect-results'
  GS_RESULTS_URL = 'gs://%s/%s/' % (BUCKET, RESULTS_GS_DIR)
  # Repo for triggering build jobs
  SVN_REPO_URL = 'svn://svn.chromium.org/chrome-try/try-perf'
  # Email to send on try jobs (for build requests) since git try will not
  # necessarily rely on a local checkout for that information
  BOT_EMAIL = 'chrome_bot@chromium.org'

  def __init__(self, *args, **kwargs):
    super(AutoBisectApi, self).__init__(*args, **kwargs)
    self.override_poll_interval = None

  def create_bisector(self, bisect_config_dict):
    """Passes the api and the config dictionary to the Bisector constructor."""
    self.override_poll_interval = bisect_config_dict.get('poll_sleep')
    revision_class = self._get_revision_class(bisect_config_dict['test_type'])
    return bisector.Bisector(self, bisect_config_dict, revision_class)

  def _get_revision_class(self, test_type):
    """Gets the particular subclass of Revision needed for the test type."""
    if test_type == 'perf':
      return perf_revision_state.PerfRevisionState
    else: #pragma: no cover
      raise NotImplementedError()

  def gsutil_file_exists(self, path):
    """Returns True if a file exists at the given GS path."""
    try:
      self.m.gsutil(['ls', path])
    except self.m.step.StepFailure: #pragma: no cover
      return False
    return True
