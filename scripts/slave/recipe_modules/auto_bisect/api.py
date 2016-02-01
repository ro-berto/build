# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""API for the bisect recipe module.

This API is meant to enable the bisect recipe to bisect any chromium-supported
platform for any test that can be run via buildbot, perf or otherwise.
"""

import os

from recipe_engine import recipe_api
from . import bisector
from . import perf_revision_state
from . import local_bisect

BISECT_CONFIG_FILE = 'tools/auto_bisect/bisect.cfg'


class AutoBisectApi(recipe_api.RecipeApi):
  """A module for bisect specific functions."""

  # Number of seconds to wait between polls for test results.
  POLLING_INTERVAL = 60
  # GS bucket to use for communicating results and job state between bisector
  # and tester bots.
  BUCKET = 'chrome-perf'
  # Directory within the above bucket to store results.
  RESULTS_GS_DIR = 'bisect-results'
  GS_RESULTS_URL = 'gs://%s/%s/' % (BUCKET, RESULTS_GS_DIR)
  # Repo for triggering build jobs.
  SVN_REPO_URL = 'svn://svn.chromium.org/chrome-try/try-perf'
  # Email to send on try jobs (for build requests) since git try will not
  # necessarily rely on a local checkout for that information.
  BOT_EMAIL = 'chrome_bot@chromium.org'

  def __init__(self, *args, **kwargs):
    super(AutoBisectApi, self).__init__(*args, **kwargs)
    self.override_poll_interval = None
    self.bot_db = None

  def perform_bisect(self):
    return local_bisect.perform_bisect(self)

  def create_bisector(self, bisect_config_dict, dummy_mode=False):
    """Passes the api and the config dictionary to the Bisector constructor.

    For details about the keys in the bisect config dictionary go to:
    http://chromium.org/developers/speed-infra/perf-try-bots-bisect-bots/config

    Args:
      bisect_config_dict (dict): Contains the configuration for the bisect job.
      dummy_mode (bool): In dummy mode we prevent the bisector for expanding
        the revision range at construction, to avoid the need for lots of step
        data when performing certain tests (such as results output).

    Returns:
      An instance of bisector.Bisector.
    """
    self.override_poll_interval = bisect_config_dict.get('poll_sleep')
    revision_class = self._get_revision_class()
    return bisector.Bisector(self, bisect_config_dict, revision_class,
                             init_revisions=not dummy_mode)

  def _get_revision_class(self):
    """Gets the particular subclass of Revision."""
    return perf_revision_state.PerfRevisionState

  def gsutil_file_exists(self, path):
    """Returns True if a file exists at the given GS path."""
    try:
      self.m.gsutil(['ls', path])
    except self.m.step.StepFailure:  # pragma: no cover
      return False
    return True

  def query_revision_info(self, revision, depot_name='chromium'):
    """Gathers information on a particular revision.

    Args:
      revision (str): A git commit hash.

    Returns:
      A dict with the keys "author", "email", "date", "subject" and "body",
      as output by fetch_revision_info.py.
    """
    result = self.m.python(
        'Reading culprit cl information.',
        self.resource('fetch_revision_info.py'),
        [revision, depot_name],
        stdout=self.m.json.output())
    return result.stdout

  def run_bisect_script(self, extra_src='', path_to_config='', **kwargs):
    """Executes src/tools/run-perf-bisect-regression.py to perform bisection.

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

  def run_local_test_run(self, api, test_config_params):  # pragma: no cover
    """Starts a test run on the same machine.

    This is for the merged director/tester flow.
    """
    if self.m.platform.is_win:
      self.m.chromium.taskkill()
    update_step = api.bot_update.ensure_checkout(
        root_solution_revision=test_config_params['revision'])
    self.start_test_run_for_bisect(api, update_step, self.bot_db,
                                   test_config_params, run_locally=True)

  def start_test_run_for_bisect(self, api, update_step, bot_db,
                                test_config_params, run_locally=False):
    mastername = api.properties.get('mastername')
    buildername = api.properties.get('buildername')
    bot_config = bot_db.get_bot_config(mastername, buildername)
    build_archive_url = test_config_params['parent_build_archive_url']
    if not run_locally:
      api.bisect_tester.upload_job_url()
    if api.chromium.c.TARGET_PLATFORM == 'android':
      # The best way to ensure the old build directory is not used is to
      # remove it.
      build_dir = self.m.chromium.c.build_dir.join(
          self.m.chromium.c.build_config_fs)
      self.m.file.rmtree('build directory', build_dir)

      # The way android builders on tryserver.chromium.perf are archived is
      # different from builders on chromium.perf. In order to support both
      # forms of archives, we added this temporary hack until builders are
      # fixed. See http://crbug.com/535218.
      zip_dir = self.m.path.join(self.m.path['checkout'], 'full-build-linux')
      if self.m.path.exists(zip_dir):  # pragma: no cover
        self.m.file.rmtree('full-build-linux directory', zip_dir)

      gs_bucket = 'gs://%s/' % bot_config['bucket']
      archive_path = build_archive_url[len(gs_bucket):]
      api.chromium_android.download_build(
          bucket=bot_config['bucket'],
          path=archive_path)

      # The way android builders on tryserver.chromium.perf are archived is
      # different from builders on chromium.perf. In order to support both
      # forms of archives, we added this temporary hack until builders are
      # fixed. See http://crbug.com/535218.
      if self.m.path.exists(zip_dir):  # pragma: no cover
        self.m.python.inline(
            'moving full-build-linux to out/Release',
            """
            import shutil
            import sys
            shutil.move(sys.argv[1], sys.argv[2])
            """,
            args=[zip_dir, build_dir])
    else:
      api.chromium_tests.download_and_unzip_build(
          mastername, buildername, update_step, bot_db,
          build_archive_url=build_archive_url,
          build_revision=test_config_params['parent_got_revision'],
          override_bot_type='tester')

    tests = [api.chromium_tests.steps.BisectTest(test_config_params)]

    if not tests:  # pragma: no cover
      return
    api.chromium_tests.configure_swarming(  # pragma: no cover
        'chromium', precommit=False, mastername=mastername)
    test_runner = api.chromium_tests.create_test_runner(api, tests)

    bot_config_object = api.chromium_tests.create_bot_config_object(
        mastername, buildername)
    with api.chromium_tests.wrap_chromium_tests(bot_config_object, tests):
      if api.chromium.c.TARGET_PLATFORM == 'android':
        api.chromium_android.adb_install_apk('ChromePublic.apk')
      test_runner()

  def start_try_job(self, api, update_step=None, bot_db=None, **kwargs):
    """Starts a recipe bisect job, perf test run, or legacy bisect run.

    This function is an entry point for:
      1. A legacy bisect job run (in this case, there will be a patch
         with a bisect config file).
      2. A recipe bisect job run (in this case, there will be a property
         called bisect_config which contains the config parameters).
      3. A single test run for a recipe bisect job (there will be a
         bisect_config property but it won't contain good/bad revisions).
      4. A perf try job run.

    Args:
      api: The recipe api object.
      update_step: Extra update_step to, used for some job types.
      bot_db: A BotConfigAndTestDB object, used for some job types.
      kwargs: Args to use only for legacy bisect.
    """
    if bot_db is None:  # pragma: no cover
      self.bot_db = api.chromium_tests.create_bot_db_from_master_dict(
          '', None, None)
    else:
      self.bot_db = bot_db
    affected_files = self.m.tryserver.get_files_affected_by_patch()
    if api.chromium.c.TARGET_PLATFORM == 'android':
      api.chromium_android.common_tests_setup_steps(perf_setup=True)
      api.chromium.runhooks()
    try:
      # Run legacy bisect script if the patch contains bisect.cfg.
      if BISECT_CONFIG_FILE in affected_files:
        kwargs['extra_src'] = ''
        kwargs['path_to_config'] = ''
        self.run_bisect_script(**kwargs)
      elif api.properties.get('bisect_config'):
        # We can distinguish between a config for a full bisect vs a single
        # test by checking for the presence of the good_revision key.
        if api.properties.get('bisect_config').get('good_revision'):
          local_bisect.perform_bisect(self)  # pragma: no cover
        else:
          self.start_test_run_for_bisect(api, update_step, self.bot_db,
                                         api.properties)
      else:
        self.m.perf_try.start_perf_try_job(
            affected_files, update_step, self.bot_db)
    finally:
      if api.chromium.c.TARGET_PLATFORM == 'android':
        api.chromium_android.common_tests_final_steps()
