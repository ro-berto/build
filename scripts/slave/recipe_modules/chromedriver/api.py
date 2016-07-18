# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

GS_CHROMEDRIVER_DATA_BUCKET = 'chromedriver-data'
GS_PREBUILTS_URL = GS_CHROMEDRIVER_DATA_BUCKET + '/prebuilts'
GS_SERVER_LOGS_URL = GS_CHROMEDRIVER_DATA_BUCKET + '/server_logs'

TEST_LOG_FORMAT = '%s_log.json'
TEST_LOG_MAX_LENGTH = 500

class ChromedriverApi(recipe_api.RecipeApi):

  def __init__(self, *args, **kwargs):
    super(ChromedriverApi, self).__init__(*args, **kwargs)
    self._chromedriver_log_dir = None

  def download_prebuilts(self):
    """Downloads the most recent prebuilts from Google storage."""
    with self.m.step.nest('Download Prebuilts'):
      try:
        prebuilt_dir = self.m.path.mkdtemp('prebuilt')
        zipfile = prebuilt_dir.join('build.zip')
        unzip_dir = prebuilt_dir.join('unzipped')
        self.m.gsutil.download_latest_file(
            base_url='gs://%s' % GS_PREBUILTS_URL,
            partial_name='gs://%s/r' % GS_PREBUILTS_URL,
            destination=zipfile,
            name='download latest prebuilt')
        self.m.zip.unzip(step_name='unzip prebuilt',
                         zip_file=zipfile,
                         output=unzip_dir)
        self.m.file.move(name='move prebuilt',
                         source=unzip_dir.join('chromedriver'),
                         dest=self.m.chromium.output_dir,
                         infra_step=False)
      finally:
        self.m.file.rmtree(name='remove temp dir', path=prebuilt_dir)

  def archive_server_log(self, server_log):
    """Uploads chromedriver server log to Google storage.

    Args:
      chromedriver_log: Path to the Chromedriver server log.
    """
    self.m.gsutil.upload(name='Upload Server Log, %s' % server_log,
                         source=server_log,
                         bucket=GS_SERVER_LOGS_URL,
                         dest=self.m.path.basename(server_log),
                         link_name='server log %s' % server_log)

  def download_test_results_log(self, chromedriver_platform):
    """Downloads the test results log for the given Chromedriver platform.

    Args:
      chromedriver_platform: The platform of the test results log.

    Returns:
      A dictionary where the keys are commit positions and the values are
      booleans indicating whether the tests passed.
    """
    with self.m.step.nest('Download Test Results Log'):
      try:
        log_name = TEST_LOG_FORMAT % chromedriver_platform
        temp_log_dir = self.m.path.mkdtemp('results_log')
        temp_log_file = temp_log_dir.join(log_name)
        self.m.gsutil.download(name='download results log',
                               source=log_name,
                               bucket=GS_CHROMEDRIVER_DATA_BUCKET,
                               dest=temp_log_file)
        json_data = self.m.file.read(name='read results log file',
                                     path=temp_log_file,
                                     test_data='{}')
        json_dict = self.m.json.loads(json_data)
      except self.m.step.StepFailure:
        json_dict = {}
      finally:
        self.m.file.rmtree(name='remove temp dir', path=temp_log_dir)
    return {int(k): v for k, v in json_dict.iteritems()}

  def upload_test_results_log(self, chromedriver_platform, test_results_log):
    """Uploads the given test results log to Google storage."""
    with self.m.step.nest('Upload Test Results Log'):
      try:
        log_name = TEST_LOG_FORMAT % chromedriver_platform
        temp_log_dir = self.m.path.mkdtemp('results_log')
        temp_log_file = temp_log_dir.join(log_name)
        self.m.file.write(name='write results log to file %s' % log_name,
                          path=temp_log_file,
                          data=self.m.json.dumps(test_results_log))
        self.m.gsutil.upload(name='upload results log %s' % log_name,
                             source=temp_log_file,
                             bucket=GS_CHROMEDRIVER_DATA_BUCKET,
                             dest=log_name,
                             link_name='results log')
      finally:
        self.m.file.rmtree(name='remove temp dir', path=temp_log_dir)

  def update_test_results_log(self, chromedriver_platform,
                              commit_position, passed):
    """Updates the test results log stored in GS for the given platform.

    Args:
      chromedriver_platform: The platform name.
      commit_position: The commit position number.
      passed: Boolean indicating whether the tests passed at this
          commit position.
    """
    log = self.download_test_results_log(chromedriver_platform)
    while len(log) > TEST_LOG_MAX_LENGTH: # pragma: no cover
      del log[min(log.keys())]
    if commit_position not in log:
      log[commit_position] = bool(passed)
      self.upload_test_results_log(chromedriver_platform, log)
    else:
      raise self.m.step.StepFailure(
          'Results already exist for commit position %s' % commit_position)

  def _generate_test_command(self, script, chromedriver, log_path,
                            ref_chromedriver=None, android_package=None,
                            verbose=None):
    cmd = [
      script, 
      '--chromedriver', chromedriver,
      '--log-path', str(log_path)
    ]
    if ref_chromedriver:
      cmd.extend(['--reference-chromedriver', ref_chromedriver])
    if verbose:
      cmd.extend(['--verbose'])
    if self.m.platform.is_linux:
      cmd = ['xvfb-run', '-a'] + cmd
    if android_package:
      cmd.extend(['--android-package', android_package])
    return cmd

  def run_python_tests(self, chromedriver, ref_chromedriver, chrome=None,
                       chrome_version_name=None, android_package=None,
                       archive_server_log=True, **kwargs):
    """Run the Chromedriver Python tests."""
    version_info = ''
    if chrome_version_name:
      version_info = '(%s)' % chrome_version_name
    with self.m.tempfile.temp_dir('server_log') as log_dir:
      server_log = log_dir.join('server_log')
      test_script_path = self.m.path['checkout'].join(
          'chrome', 'test', 'chromedriver', 'test', 'run_py_tests.py')
      self.m.step('python_tests%s' % version_info,
                  self._generate_test_command(
                      test_script_path, chromedriver, server_log,
                      ref_chromedriver=ref_chromedriver,
                      android_package=android_package),
                  **kwargs)
      if archive_server_log:
        self.archive_server_log(server_log)

  def run_java_tests(self, chromedriver, chrome=None, chrome_version_name=None,
                     android_package=None, verbose=False,
                     archive_server_log=True, **kwargs):
    """Run the Chromedriver Java tests."""
    version_info = ''
    if chrome_version_name:
      version_info = '(%s)' % chrome_version_name
    with self.m.tempfile.temp_dir('server_log') as log_dir:
      server_log = log_dir.join('server_log')
      test_script_path = self.m.path['checkout'].join(
          'chrome', 'test', 'chromedriver', 'test', 'run_java_tests.py')
      self.m.step('java_tests%s' % version_info,
                  self._generate_test_command(
                      test_script_path, chromedriver, server_log,
                      ref_chromedriver=None, android_package=android_package,
                      verbose=verbose),
                  **kwargs)
      if archive_server_log:
        self.archive_server_log(server_log)

  def run_all_tests(self, android_packages=None, archive_server_logs=True):
    """Run all Chromedriver tests."""
    server_name = 'chromedriver'
    chromedriver = self.m.chromium.output_dir.join(server_name)

    platform_name = self.m.platform.name
    if self.m.platform.is_linux and self.m.platform.bits == 64:
      platform_name = 'linux64'
    ref_chromedriver = self.m.path['checkout'].join(
        'chrome', 'test', 'chromedriver', 'third_party', 'java_tests',
        'reference_builds', 'chromedriver_%s' % platform_name)

    test_env = {'PATH': '%(PATH)s'}
    test_env['PATH'] = self.m.path.pathsep.join([
        test_env['PATH'],
        str(self.m.path['checkout'].join(
            'chrome', 'test', 'chromedriver', 'chrome'))])
    with self.m.step.defer_results():
      for package in android_packages or []:
        self.run_python_tests(chromedriver,
                              ref_chromedriver,
                              chrome_version_name=package,
                              android_package=package,
                              env=test_env,
                              archive_server_log=archive_server_logs)
        self.run_java_tests(chromedriver,
                            chrome_version_name=package,
                            android_package=package,
                            verbose=True,
                            env=test_env,
                            archive_server_log=archive_server_logs)
