# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""API for the bisect recipe module.

This API is meant to enable the bisect recipe to bisect any chromium-supported
platform for any test that can be run via buildbot, perf or otherwise.
"""

import contextlib

from recipe_engine import recipe_api
from . import bisector
from . import depot_config
from . import revision_state
from . import local_bisect

BISECT_CONFIG_FILE = 'tools/auto_bisect/bisect.cfg'


class AutoBisectStagingApi(recipe_api.RecipeApi):
  """A module for bisect specific functions."""

  # Number of seconds to wait between polls for test results.
  POLLING_INTERVAL = 60
  # GS bucket to use for communicating results and job state between bisector
  # and tester bots.
  BUCKET = 'chrome-perf'
  # Directory within the above bucket to store results.
  RESULTS_GS_DIR = 'bisect-results'
  GS_RESULTS_URL = 'gs://%s/%s/' % (BUCKET, RESULTS_GS_DIR)
  # Email to send on try jobs (for build requests) since git try will not
  # necessarily rely on a local checkout for that information.
  BOT_EMAIL = 'chrome_bot@chromium.org'
  SERVICE_ACCOUNT = 'chromium-bisect'

  def __init__(self, *args, **kwargs):
    super(AutoBisectStagingApi, self).__init__(*args, **kwargs)
    self.override_poll_interval = None
    self.bot_db = None
    # Repo for triggering build jobs.
    self.svn_repo_url = 'svn://svn.chromium.org/chrome-try/try-perf'
    # The variable below are set and used for the internal bisects.
    self.buildurl_gs_prefix = None
    self.internal_bisect = False
    self.builder_bot = None
    self.full_deploy_script = None

    # Keep track of working directory (which contains the checkout).
    # None means "default value".
    self._working_dir = None

    @contextlib.contextmanager
    def noop_context_manager(_api):
      """This is a context manager that doesn't do anything.

      It is used for a placeholder for code that should be wrapped around ever
      test execution of a bisect iteration or full build. Replace it with a
      real context manager (one that accepts an api argument) to do something
      useful.
      """
      yield

    # build_context_mgr is run for each overall bisect run (i.e., once).
    self.build_context_mgr = noop_context_manager
    # test_context_mgr is run for each iteration of the bisect.
    self.test_context_mgr = noop_context_manager

  @property
  def working_dir(self):
   if not self._working_dir:
     self._working_dir = self.m.chromium_checkout.get_checkout_dir({})
   return self._working_dir or self.m.path['start_dir']

  def create_bisector(self, bisect_config_dict, dummy_mode=False, **flags):
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
    return bisector.Bisector(self, bisect_config_dict,
                             revision_state.RevisionState,
                             init_revisions=not dummy_mode, **flags)

  def set_platform_gs_prefix(self, gs_url):
    """Sets GS path for the platform."""
    self.buildurl_gs_prefix = gs_url  # pragma: no cover

  def set_builder_bot(self, builder_bot):
    """Sets builder name for building binaries."""
    self.builder_bot = builder_bot  # pragma: no cover

  def set_internal(self):
    """Sets bisector as internal only to process android-chrome."""
    self.internal_bisect = True  # pragma: no cover

  def set_additional_depot_info(self, depot_info):
    """Adds additional depot info to the global depot variables."""
    depot_config.add_addition_depot_into(depot_info)  # pragma: no cover

  def set_deploy_script(self, path):  # pragma: no cover
    """Sets apk deployment script path for android-chrome."""
    self.full_deploy_script = path

  def set_svn_repo(self, svn_repo_url):  # pragma: no cover
    """Sets SVN repo url for triggering build jobs."""
    self.svn_repo_url = svn_repo_url

  def gsutil_file_exists(self, path, **kwargs):
    """Returns True if a file exists at the given GS path."""
    try:
      self.m.gsutil( ['ls', path], **kwargs)
    except self.m.step.StepFailure:
      # A step failure here simply means that the file does not exist, and
      # should not be treated as an error.
      self.m.step.active_result.presentation.status = self.m.step.SUCCESS
      return False
    return True

  def query_revision_info(self, revision):
    """Gathers information on a particular revision.

    Args:
      revision (str): A git commit hash.

    Returns:
      A dict with the keys "author", "email", "date", "subject" and "body",
      as output by fetch_revision_info.py.
    """
    step_name = 'Reading culprit cl information.'
    # Use gitiles to get commit information.
    if revision.depot_name == 'android-chrome':  # pragma: no cover
      commit_url = depot_config.DEPOT_DEPS_NAME[revision.depot_name]['url']
      return self._commit_info(revision.commit_hash, commit_url, step_name)
    result = self.m.python(
        step_name,
        self.resource('fetch_revision_info.py'),
        [revision.commit_hash, revision.depot_name],
        stdout=self.m.json.output(),
        step_test_data=lambda: self._test_data['cl_info'][revision.commit_hash],
    )
    return result.stdout

  def _commit_info(self, commit_hash, url, step_name=None):  # pragma: no cover
    """Fetches information about a given commit.

    Args:
      commit_hash (str): A git commit hash.
      url (str): The URL of a repository, e.g.
    "https://chromium.googlesource.com/chromium/src".
      step_name (str): Optional step name.

    Returns:
     A dict with commit information.
    """
    try:
     step_name = step_name or 'gitiles commit info: %s' % commit_hash
     commit_info = self.m.gitiles.commit_log(
         url, commit_hash, step_name=step_name)
     if commit_info:
       message = commit_info.get('message', '').splitlines()
       subject = message[0]
       body = '\n'.join(message[1:])
       return {
            'author': commit_info['author']['name'],
            'email': commit_info['author']['email'],
            'subject': subject,
            'body': body,
            'date': commit_info['committer']['time'],
       }
     return None
    except self.m.step.StepFailure:  # pragma: no cover
     self.surface_result('BAD_REV')
     raise

  def run_local_test_run(self, test_config_params,
                         skip_download=False, **kwargs):
    """Starts a test run on the same machine.

    This is for the merged director/tester flow.
    """
    if self.m.platform.is_win:  # pragma: no cover
      self.m.chromium.taskkill()

    if skip_download:  # pragma: no cover
      update_step = None
    else:
      update_step = self._SyncRevisionToTest(test_config_params)
    return self.start_test_run_for_bisect(
        update_step, self.bot_db, test_config_params,
        skip_download=skip_download, **kwargs)

  def ensure_checkout(self, *args, **kwargs):
    kwargs.setdefault('disable_syntax_validation', True)
    with self.m.context(cwd=(self.m.context.cwd or self.working_dir)):
      return self.m.bot_update.ensure_checkout(*args, **kwargs)

  def _SyncRevisionToTest(self, test_config_params):
    if not self.internal_bisect:
      self.m.gclient.c.revisions.update(
          test_config_params['deps_revision_overrides'])
      return self.ensure_checkout(
          root_solution_revision=test_config_params['revision'])
    else:  # pragma: no cover
      return self._SyncRevisionsForAndroidChrome(
          test_config_params['revision_ladder'])

  def _SyncRevisionsForAndroidChrome(self, revision_ladder):  # pragma: no cover
    """Syncs android-chrome and chromium repos to particular revision."""
    revisions = []
    for d, r in revision_ladder.iteritems():
      revisions.append('%s@%s' % (depot_config.DEPOT_DEPS_NAME[d]['src'], r))
    params = ['sync', '--verbose', '--nohooks', '--force',
              '--delete_unversioned_trees']
    for revision in revisions:
      params.extend(['--revision', revision])
    self.m.gclient('sync %s' % '-'.join(revisions), params)
    return None

  def start_test_run_for_bisect(self, update_step, bot_db, test_config_params,
                                skip_download=False, **kwargs):
    mastername = self.m.properties.get('mastername')
    buildername = self.m.properties.get('buildername')
    bot_config = bot_db.get_bot_config(mastername, buildername)
    build_archive_url = test_config_params['parent_build_archive_url']
    if not skip_download:
      if self.m.chromium.c.TARGET_PLATFORM == 'android':
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
        self.m.chromium_android.download_build(
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
        self.m.chromium_tests.download_and_unzip_build(
            mastername, buildername, update_step, bot_db,
            build_archive_url=build_archive_url,
            build_revision=test_config_params['parent_got_revision'],
            override_bot_type='tester')

    tests = [
        self.m.chromium_tests.steps.BisectTestStaging(
            test_config_params, **kwargs)]

    if not tests:  # pragma: no cover
      return
    self.m.chromium_swarming.configure_swarming(
        'chromium', precommit=False, mastername=mastername,
        path_to_testing_dir=self.m.path['checkout'].join('testing'))
    test_runner = self.m.chromium_tests.create_test_runner(tests)

    with self.m.chromium_tests.wrap_chromium_tests(bot_config, tests):
      with self.test_context_mgr(self.m):
        if self.m.chromium.c.TARGET_PLATFORM == 'android' and not skip_download:
          deploy_apks = []
          deploy_args = []
          if self.internal_bisect:  # pragma: no cover
            deploy_args = list(bot_config['deploy_args'])
            deploy_apks = bot_config.get('deploy_apks')
            if deploy_apks:
              deploy_args.extend([
                '--apks',
                ','.join(str(self.m.chromium_android.apk_path(apk))
                         for apk in deploy_apks)])
          else:
            if bot_config.get('webview'):
              deploy_apks = ['SystemWebView.apk', 'SystemWebViewShell.apk']
            else:
              deploy_apks = ['ChromePublic.apk']
          self.deploy_apk_on_device(
              self.full_deploy_script, deploy_apks, deploy_args)
        test_runner()
        return tests[0].run_results

  def deploy_apk_on_device(self, deploy_script, deploy_apks, deploy_args):
    """Installs apk on the android device."""
    if deploy_script:  # pragma: no cover
      self.full_deploy_on_device(deploy_script, deploy_args)
    else:
      for apk in deploy_apks:
        self.m.chromium_android.adb_install_apk(apk)

  def full_deploy_on_device(self, deploy_script, args=None):  # pragma: no cover
    """Install android-chrome apk on device."""
    full_deploy_flags = [
        '-v',
        '--blacklist-file', self.m.chromium_android.blacklist_file,
        '--perfbot',
        '--release',
        '--adb-path', self.m.adb.adb_path(),
    ]
    if args:
      full_deploy_flags += args
    self.m.python(
        'Deploy on Device',
        deploy_script,
        full_deploy_flags,
        infra_step=True,
        env=self.m.chromium.get_env())

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
    flags = {}
    if kwargs.get('do_not_nest_wait_for_revision'):
      flags['do_not_nest_wait_for_revision'] = kwargs.pop(
          'do_not_nest_wait_for_revision')
    if bot_db is None:  # pragma: no cover
      self.bot_db = api.chromium_tests.create_bot_db_from_master_dict('', None)
    else:
      self.bot_db = bot_db

    with self.m.context(cwd=self.working_dir):
      with self.m.context(cwd=self.m.path['checkout']):
        affected_files = self.m.chromium_checkout.get_files_affected_by_patch()
      with self.build_context_mgr(self.m):
        if BISECT_CONFIG_FILE in affected_files:
          api.step('***LEGACY BISECT HAS BEEN DEPRECATED***', [])
          api.step.active_result.presentation.status = api.step.FAILURE
          return
        elif api.properties.get('bisect_config'):
          # We can distinguish between a config for a full bisect vs a single
          # test by checking for the presence of the good_revision key.
          if api.properties.get('bisect_config').get('good_revision'):
            api.step('***BISECT***', [])
            with api.m.step.nest('Clearing results directory'):
              results_dir = self.m.path['bisect_results']
              self.m.file.rmtree('old results directory', results_dir)
              self.m.file.ensure_directory('new results directory', results_dir)
            local_bisect.perform_bisect(self, **flags)
          else:
            api.step('***SINGLE TEST (deprecated)***', [])
            self.start_test_run_for_bisect(update_step, self.bot_db,
                                           api.properties)
        else:
          api.step('***PERF TRYJOB***', [])
          if self.internal_bisect:  # pragma: no cover
            self.m.perf_try_staging.set_internal()

          self.m.perf_try_staging.start_perf_try_job(
              api, affected_files, update_step, self.bot_db)

  def stat_compare(self, values_a, values_b, metric,
                   output_format='chartjson', **kwargs):
    """Compares samples using catapult's statistics implementation.

    Args:
      values_a, values_b: lists of paths to the json files containing the values
        produced by the test.
      metric: the name of the metric as sent by dashboard.
      output_format: 'chartjson', 'valueset' or 'buildbot'

    Returns:
      a dict containing 'result' which may be True, False or 'needMoreData', as
      well as details about each sample ('debug_values', 'mean' and 'std_dev').

    """
    values_a = self._make_copies(values_a)
    values_b = self._make_copies(values_b)

    args = [','.join(values_a),
            ','.join(values_b),
            metric,
            '--' + output_format]

    script = self.working_dir.join('catapult', 'tracing', 'bin',
                                   'compare_samples')
    return self.m.python(
        'Compare samples',
        script=script,
        args=args,
        stdout=self.m.json.output(),
        **kwargs).stdout

  def _make_copies(self, files):
    """Creates a copy of each file making sure to close the file handle.

    The reason why we need this is to allow compare_samples to open the files.
    An issue with this is suspected to cause http://crbug.com/659908

    Args:
      files: A list of strings or Path objects.

    Returns:
      A list of paths as strings.
    """
    copy_paths = []
    for path in files:
      new_path = str(path) + '.copy'
      if not self._test_data.enabled:  # pragma: no cover
        with open(new_path, 'w') as f:
            f.write(open(str(path)).read())
      copy_paths.append(new_path)
    return copy_paths
