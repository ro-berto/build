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

  POLLING_INTERVAL = 60
  BUCKET = 'chrome-perf'
  RESULTS_GS_DIR = 'bisect-results'
  GS_RESULTS_URL = 'gs://%s/%s/' % (BUCKET, RESULTS_GS_DIR)
  SVN_REPO_URL = 'svn://svn.chromium.org/chrome-try/try-perf'

  def __init__(self, *args, **kwargs):
    super(AutoBisectApi, self).__init__(*args, **kwargs)
    self.override_poll_interval = None

  def create_bisector(self, bisect_config):
    """Passes the api and the config dictionary to the Bisector constructor."""
    bisect_config_dict = bisect_config
    self.override_poll_interval = bisect_config_dict.get('poll_sleep', None)
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
