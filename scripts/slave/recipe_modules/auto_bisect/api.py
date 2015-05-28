# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""API for the bisect recipe module.

This API is meant to enable the bisect recipe to bisect any chromium-supported
platform for any test that can be run via buildbot, perf or otherwise.
"""

from recipe_engine import recipe_api
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

  def create_bisector(self, bisect_config_dict, dummy_mode=False):
    """Passes the api and the config dictionary to the Bisector constructor.
  
    For details about the keys in the bisect config dictionary go to:
    http://chromium.org/developers/speed-infra/perf-try-bots-bisect-bots/config

    Args:
      bisect_config_dict (dict): Contains the configuration for the bisect job.
      dummy_mode (bool): In dummy mode we prevent the bisector for expanding
        the revision range at construction, to avoid the need for lots of step
        data when performing certain tests (such as results output).
    """
    self.override_poll_interval = bisect_config_dict.get('poll_sleep')
    revision_class = self._get_revision_class(bisect_config_dict['test_type'])
    return bisector.Bisector(self, bisect_config_dict, revision_class,
                             init_revisions=not dummy_mode)

  def _get_revision_class(self, test_type):
    """Gets the particular subclass of Revision needed for the test type."""
    if test_type == 'perf':
      return perf_revision_state.PerfRevisionState
    else:  # pragma: no cover
      raise NotImplementedError()

  def gsutil_file_exists(self, path):
    """Returns True if a file exists at the given GS path."""
    try:
      self.m.gsutil(['ls', path])
    except self.m.step.StepFailure:  # pragma: no cover
      return False
    return True

  def query_revision_info(self, revision, git_checkout_dir=None):
    """Gathers information on a particular revision, such as author's name,
    email, subject, and date.

    Args:
      revision (str): Revision you want to gather information on; a git
        commit hash.
      git_checkout_dir (slave.recipe_config_types.Path): A path to run git
        from.

    Returns:
      A dict in the following format:
      {
        'author': %s,
        'email': %s,
        'date': %s,
        'subject': %s,
        'body': %s,
      }
    """
    if not git_checkout_dir:
      git_checkout_dir = self.m.path['checkout']

    separator = 'S3P4R4T0R'
    formats = separator.join(['%aN', '%aE', '%s', '%cD', '%b'])
    targets = ['author', 'email', 'subject', 'date', 'body']
    command_parts = ['log', '--format=%s' % formats, '-1', revision]

    step_result = self.m.git(*command_parts,
                             name='Reading culprit cl information.',
                             cwd=git_checkout_dir,
                             stdout=self.m.raw_io.output())
    return dict(zip(targets, step_result.stdout.split(separator)))

  def run_bisect_script(self, extra_src='', path_to_config='', **kwargs):
    """Executes run-perf-bisect-regression.py to perform bisection.

    Args:
      extra_src (str): Path to extra source file. If this is supplied,
        bisect script will use this to override default behavior.
      path_to_config (str): Path to the config file to use. If this is supplied,
        the bisect script will use this to override the default config file
        path.
    """
    self.m.python(
        'Preparing for Bisection',
        script=self.m.path['checkout'].join(
            'tools', 'prepare-bisect-perf-regression.py'),
        args=['-w', self.m.path['slave_build']])
    args = []

    kwargs['allow_subannotations'] = True

    if extra_src:
      args = args + ['--extra_src', extra_src]
    if path_to_config:
      args = args + ['--path_to_config', path_to_config]

    if self.m.chromium.c.TARGET_PLATFORM != 'android':
      args += ['--path_to_goma', self.m.path['build'].join('goma')]
    args += [
        '--build-properties',
         self.m.json.dumps(dict(self.m.properties.legacy())),
      ]
    self.m.chromium.runtest(
        self.m.path['checkout'].join('tools', 'run-bisect-perf-regression.py'),
        ['-w', self.m.path['slave_build']] + args,
        name='Running Bisection',
        xvfb=True, **kwargs)
