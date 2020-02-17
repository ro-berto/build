# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api
from collections import OrderedDict
import json, re

BLACKLIST = (
    r'(^(out|xcodebuild)[/\\](Release|Debug|Product)\w*[/\\]' +
    r'(clang_\w*[/\\])?(generated_tests|obj)[/\\])' +
    r'|(^tools[/\\]sdks)')
# TODO(athom): move to third_party when swarming_client.path has a setter
SWARMING_CLIENT_PATH = 'tools/swarming_client'
SWARMING_CLIENT_REPO = (
    'https://chromium.googlesource.com/infra/luci/client-py.git')
SWARMING_CLIENT_REV = '88229872dd17e71658fe96763feaa77915d8cbd6'

TEST_PY_PATH = 'tools/test.py'
BUILD_PY_PATH = 'tools/build.py'
GN_PY_PATH = 'tools/gn.py'

CHROME_PATH_ARGUMENT = {
  'linux': '--chrome=browsers/chrome/google-chrome',
  'mac': '--chrome=browsers/Google Chrome.app/Contents/MacOS/Google Chrome',
  'win': '--chrome=browsers\\Chrome\\Application\\chrome.exe'
}

FIREFOX_PATH_ARGUMENT = {
  'linux': '--firefox=browsers/firefox/firefox',
  'mac': '--firefox=browsers/Firefox.app/Contents/MacOS/firefox',
  'win': '--firefox=browsers\\firefox\\firefox.exe'
}

CO19_PACKAGE = 'dart/third_party/co19'
CO19_LEGACY_PACKAGE = 'dart/third_party/co19/legacy'
CIPD_SERVER_URL = 'https://chrome-infra-packages.appspot.com'


class DartApi(recipe_api.RecipeApi):
  """Recipe module for code commonly used in dart recipes.

  Shouldn't be used elsewhere."""
  def checkout(self, clobber=False):
    """Checks out the dart code and prepares it for building."""
    self.m.gclient.set_config('dart')
    sdk = self.m.gclient.c.solutions[0]
    sdk.custom_deps['sdk/%s' % SWARMING_CLIENT_PATH] = \
        '%s@%s' % (SWARMING_CLIENT_REPO, SWARMING_CLIENT_REV)
    self.m.goma.ensure_goma()

    with self.m.context(
        cwd=self.m.path['cache'].join('builder'),
        env={'GOMA_DIR': self.m.goma.goma_dir}):
      self.m.bot_update.ensure_checkout()
      with self.m.context(cwd=self.m.path['checkout']):
        if clobber:
          self.m.python('clobber',
                        self.m.path['checkout'].join(
                            'tools', 'clean_output_directory.py'))
      self.m.gclient.runhooks()


  def get_secret(self, name):
    """Decrypts the specified secret and returns the location of the result"""
    cloudkms_dir = self.m.path['start_dir'].join('cloudkms')
    cloudkms_package = 'infra/tools/luci/cloudkms/${platform}'
    self.m.cipd.ensure(
        cloudkms_dir,
        self.m.cipd.EnsureFile().add_package(cloudkms_package, 'latest'))

    with self.m.context(cwd=self.m.path['cleanup']):
      file_name = '%s.encrypted' % name
      self.m.gsutil.download('dart-ci-credentials', file_name, file_name)

      executable_suffix = '.exe' if self.m.platform.name == 'win' else ''
      secret_key = self.m.path['cleanup'].join('%s.key' % name)
      self.m.step('cloudkms get key',
               [cloudkms_dir.join('cloudkms%s' % executable_suffix), 'decrypt',
               '-input', file_name,
               '-output', secret_key,
               'projects/dart-ci/locations/'
                 'us-central1/keyRings/dart-ci/cryptoKeys/dart-ci'])
      return secret_key


  def kill_tasks(self, ok_ret='any'):
    """Kills leftover tasks from previous runs or steps."""
    self.m.python('kill processes',
               self.m.path['checkout'].join('tools', 'task_kill.py'),
               args=['--kill_browsers=True', '--kill_vsbuild=True'],
               ok_ret=ok_ret)


  def dart_executable(self):
    """Returns the path to the checked-in SDK dart executable."""
    executable = 'dart.exe' if self.m.platform.name == 'win' else 'dart'
    return self.m.path['checkout'].join(
      'tools','sdks', 'dart-sdk', 'bin', executable)

  def commit_id(self):
    """The commit hash of a CI build or the patch set of a CQ build"""
    return str(self.m.buildbucket.gitiles_commit.id or 'refs/changes/%s/%s' %
               (self.m.buildbucket.build.input.gerrit_changes[0].change,
                self.m.buildbucket.build.input.gerrit_changes[0].patchset))


  def build(self, build_args=None, name='build dart'):
    """Builds dart using the specified build_args"""
    if not build_args: # pragma: no cover
      build_args = []
    build_args = build_args + ['--no-start-goma', '-j200']
    with self.m.depot_tools.on_path(), self.m.context(
        cwd=self.m.path['checkout'], env={'GOMA_DIR': self.m.goma.goma_dir}):
      self.kill_tasks()
      build_exit_status = None
      try:
        self.m.goma.start()
        try:
          with self.m.context(infra_steps=False):
            self.m.python(
                name,
                self.m.path['checkout'].join('tools', 'build.py'),
                args=build_args,
                timeout=50 * 60)
        finally:
          build_exit_status = self.m.step.active_result.retcode
      finally:
        self.m.goma.stop(build_exit_status=build_exit_status)


  def upload_isolate(self, isolate_fileset):
    """Builds an isolate"""
    # TODO(athom): Use upstream isolated recipe. https://crbug.com/944902
    if isolate_fileset == self.m.properties.get('parent_fileset_name', None):
      return self.m.properties.get('parent_fileset')
    step_result = self.m.python(
        'upload testing fileset %s' % isolate_fileset,
        self.m.swarming_client.path.join('isolate.py'),
        args= ['archive',
                 '--blacklist=%s' % BLACKLIST,
                 '--ignore_broken_items', # TODO(athom) find a way to avoid that
                 '-I', 'isolateserver.appspot.com',
                 '--namespace', 'default-gzip',
                 '-i%s' % self.m.path['checkout'].join('%s' % isolate_fileset),
                 '-s%s' % self.m.path['checkout'].join(
                     '%s.isolated' % isolate_fileset)],
        stdout=self.m.raw_io.output('out'))
    isolate_hash = step_result.stdout.strip()[:40]
    step_result.presentation.step_text = 'swarming fileset hash: %s' % (
        isolate_hash)
    return isolate_hash


  def download_parent_isolate(self):
    # TODO(athom): Use upstream isolated recipe. https://crbug.com/944902
    self.m.path['checkout'] = self.m.path['cleanup']
    isolate_hash = self.m.properties['parent_fileset']
    fileset_name = self.m.properties['parent_fileset_name']
    with self.m.context(cwd=self.m.path['cleanup']):
      self.m.python(
        'downloading fileset %s' % fileset_name,
        self.m.swarming_client.path.join('isolateserver.py'),
        args= ['download',
                 '-I', 'isolateserver.appspot.com',
                 '--namespace', 'default-gzip',
                 '-s%s' % isolate_hash,
                 '--target=.'],
        stdout=self.m.raw_io.output('out'))


  def shard(self,
            name,
            isolate_hash,
            test_args,
            os,
            cpu='x86-64',
            pool='dart.tests',
            num_shards=0,
            last_shard_is_local=False,
            cipd_ensure_file=None,
            ignore_failure=False):
    """Runs test.py in the given isolate, sharded over several swarming tasks.
       Returns the created tasks, which can be collected with collect_all().
    """
    assert(num_shards > 0)
    if not cipd_ensure_file:  # pragma: no cover
      cipd_ensure_file = self.m.cipd.EnsureFile()
    cipd_ensure_file.add_package(
        'infra/tools/luci/vpython/${platform}',
        'git_revision:e317c7d2c17d4c3460ee37524dfce4e1dee4306a',
        'cipd_bin_packages')
    cipd_ensure_file.add_package(
        'infra/tools/luci/vpython-native/${platform}',
        'git_revision:e317c7d2c17d4c3460ee37524dfce4e1dee4306a',
        'cipd_bin_packages')
    cipd_ensure_file.add_package('infra/3pp/tools/cpython/${platform}',
                                 'version:2.7.17.chromium.24',
                                 'cipd_bin_packages/cpython')
    cipd_ensure_file.add_package('infra/3pp/tools/cpython3/${platform}',
                                 'version:3.8.1rc1.chromium.10',
                                 'cipd_bin_packages/cpython3')
    path_prefixes = [
        'cipd_bin_packages',
        'cipd_bin_packages/bin',
        'cipd_bin_packages/cpython',
        'cipd_bin_packages/cpython/bin',
        'cipd_bin_packages/cpython3',
        'cipd_bin_packages/cpython3/bin',
    ]

    tasks = []
    # TODO(athom) use built-in sharding to remove for loop
    for shard in range(num_shards):
      if last_shard_is_local and shard == num_shards - 1:
        break

      cmd = ((test_args or []) + [
          '--shards=%s' % num_shards,
          '--shard=%s' % (shard + 1), '--output-directory=${ISOLATED_OUTDIR}'
      ])

      # TODO(crbug/1018836): Use distro specific name instead of Linux.
      os_names = {
        'android': 'Android',
        'linux': 'Linux',
        'mac': 'Mac',
        'win': 'Windows',
      }

      dimensions = {
          'os': os_names.get(os, os),
          'cpu': cpu,
          'pool': pool,
          'gpu': None,
      }

      task_request = (
          self.m.swarming.task_request().with_name(
              '%s_shard_%s' % (name, (shard + 1))).
          # Set a priority lower than any builder, to prioritize shards.
          with_priority(25))
      if ignore_failure:
        task_request = task_request.with_tags({'optional': ['true']})

      task_slice = task_request[0] \
        .with_cipd_ensure_file(cipd_ensure_file) \
        .with_command(cmd) \
        .with_containment_type('AUTO') \
        .with_dimensions(**dimensions) \
        .with_env_prefixes(PATH=path_prefixes) \
        .with_env_vars(VPYTHON_VIRTUALENV_ROOT='cache/vpython') \
        .with_execution_timeout_secs(3600) \
        .with_expiration_secs(3600) \
        .with_isolated(isolate_hash) \
        .with_io_timeout_secs(1200) \
        .with_named_caches({ 'vpython' : 'cache/vpython' })

      if 'shard_timeout' in self.m.properties:
        task_slice = (task_slice.with_execution_timeout_secs(
          int(self.m.properties['shard_timeout'])))

      task_request = task_request.with_slice(0, task_slice)
      tasks.append(task_request)
    return self.m.swarming.trigger('trigger shards for %s' % name, tasks)


  def _release_builder(self):
    """Boolean that reports whether the builder is on the
       dev or stable channel. Some steps are only run on the
       master and try builders."""
    return (self.m.buildbucket.builder_name.endswith('-dev') or
            self.m.buildbucket.builder_name.endswith('-stable'))

  def _try_builder(self):
    """Boolean that reports whether this a try builder.
       Some steps are not run on the try builders."""
    return self.m.buildbucket.builder_name.endswith('-try')


  def collect_all(self, steps):
    """Collects the results of a sharded test run."""
    # Defer results in case one of the shards has a non-zero exit code.
    with self.m.step.defer_results():
      # TODO(athom) collect all the output, and present as a single step
      for step in steps:
        tasks = step.tasks
        step.tasks = []
        for shard in tasks:
          self._collect(step, shard)

  def _collect(self, step, task):
    output_dir = self.m.path.mkdtemp()
    # Every shard is only a single task in swarming
    task_result = self.m.swarming.collect(task.name, [task], output_dir)[0]
    # Swarming uses the task's id as a subdirectory name
    output_dir = output_dir.join(task.id)
    try:
      task_result.analyze()
    except self.m.step.InfraFailure as failure:
      if (task_result.state == self.m.swarming.TaskState.COMPLETED and
          not step.is_test_step):
        self.m.step.active_result.presentation.status = 'FAILURE'
        raise self.m.step.StepFailure(failure.reason)
      else:
        self.m.step.active_result.presentation.status = 'EXCEPTION'
        raise
    except self.m.step.StepFailure as failure:
      assert (task_result.state == self.m.swarming.TaskState.TIMED_OUT)
      self.m.step.active_result.presentation.status = 'EXCEPTION'
      raise self.m.step.InfraFailure(failure.reason)

    bot_name = task_result.bot_id
    task_name = task_result.name
    self._add_results_and_links(output_dir, bot_name, task_name, step.results)

  def _add_results_and_links(self, output_dir, bot_name, task_name, results):
    filenames = ('logs.json', 'results.json')
    for filename in filenames:
      file_path = output_dir.join(filename)
      self.m.path.mock_add_paths(file_path)
      if self.m.path.exists(file_path):
        contents = self.m.file.read_text(
            'read %s for %s' % (filename, task_name), file_path)
        if filename == 'results.json':
          results.add_results(bot_name, contents)
        if filename == 'logs.json':
          results.logs += contents


  def _get_latest_tested_commit(self):
    builder = self._get_builder_dir()
    # Note: The pre-approval script relies on this step being named
    # gsutil_find_latest_build inside the nested step download_previous_results.
    latest_result = self.m.gsutil.download(
        'dart-test-results',
        'builders/%s/latest' % builder,
        self.m.raw_io.output_text(name='latest', add_output_log=True),
        name='find latest build',
        ok_ret='any') # TODO(athom): succeed only if file does not exist
    latest = latest_result.raw_io.output_texts.get('latest')
    revision = None
    if latest:
      latest = latest.strip()
      revision_result = self.m.gsutil.download(
          'dart-test-results',
          'builders/%s/%s/revision' % (builder, latest),
          self.m.raw_io.output_text(name='revision', add_output_log=True),
          name='get revision for latest build',
          ok_ret='any') # TODO(athom): succeed only if file does not exist
      revision = revision_result.raw_io.output_texts.get('revision')

    return (latest, revision)


  def _get_builder_dir(self):
    builder = self.m.buildbucket.builder_name
    if builder.endswith('-try'):
      builder = builder[:-4]
    return str(builder)


  def _download_results(self, latest):
    filenames = ['results.json', 'flaky.json']
    builder = self._get_builder_dir()
    results_path = self.m.path['checkout'].join('LATEST')
    self.m.file.ensure_directory('ensure LATEST dir', results_path)
    for filename in filenames:
      self.m.file.write_text(
        'ensure %s exists' % filename, results_path.join(filename), '')
    if latest:
      self.m.gsutil.download(
          'dart-test-results',
          'builders/%s/%s/*.json' % (builder, latest),
          results_path,
          name='download previous results')


  def _deflake_results(self, step, global_config):
    step.deflake_list = self.m.step(
        'list tests to deflake (%s)' % step.name, [
            self.dart_executable(), 'tools/bots/compare_results.dart',
            '--flakiness-data', 'LATEST/flaky.json', '--changed', '--passing',
            '--failing', '--count', '50', 'LATEST/results.json',
            self.m.raw_io.input_text(step.results.results)
        ],
        stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
    if step.deflake_list:
      self._run_step(step, global_config)


  def _update_flakiness_information(self, results_str):
    flaky_json = self.m.step('update flakiness information', [
        self.dart_executable(), 'tools/bots/update_flakiness.dart', '-i',
        'LATEST/flaky.json', '-o',
        self.m.raw_io.output_text(name='flaky.json', add_output_log=True),
        '--build-id', self.m.buildbucket.build.id, '--commit',
        self.m.buildbucket.gitiles_commit.id,
        self.m.raw_io.input_text(results_str, name='results.json')
    ])
    return flaky_json.raw_io.output_texts.get('flaky.json')


  def _upload_results_to_cloud(self, flaky_json_str, logs_str, results_str):
    builder = str(self.m.buildbucket.builder_name)
    build_revision = str(self.m.buildbucket.gitiles_commit.id)
    build_number = str(self.m.buildbucket.build.number)
    self._upload_result(builder, build_number, 'revision', build_revision)
    self._upload_result(builder, build_number, 'logs.json', logs_str)
    self._upload_result(builder, build_number, 'results.json', results_str)
    self._upload_result(builder, build_number, 'flaky.json', flaky_json_str)
    if not (builder.endswith('dev') or builder.endswith('stable')):
      self._upload_result('current_flakiness', 'single_directory',
                          'flaky_current_%s.json' % builder, flaky_json_str)
    # Update "latest" file
    new_latest = self.m.raw_io.input_text(build_number, name='latest')
    self.m.gsutil.upload(
        new_latest,
        'dart-test-results',
        'builders/%s/%s' % (builder, 'latest'),
        name='update "latest" reference')


  def _upload_result(self, builder, build_number, filename, result_str):
    self.m.gsutil.upload(
        self.m.raw_io.input_text(str(result_str), name=filename),
        'dart-test-results',
        'builders/%s/%s/%s' % (builder, build_number, filename),
        name='upload %s' % filename)


  def _publish_results(self, results_str):
    if self._release_builder():
      return
    access_token = self.m.service_account.default().get_access_token(
      ['https://www.googleapis.com/auth/cloud-platform'])
    self.m.step('publish results to pub/sub', [
        self.dart_executable(), self.m.path['checkout'].join(
            'tools', 'bots', 'post_results_to_pubsub.dart'), '--result_file',
        self.m.raw_io.input_text(results_str), '--auth_token',
        self.m.raw_io.input_text(access_token), '--id',
        self.m.buildbucket.build.id
    ])


  def _report_success(self, results_str):
    if results_str:
      access_token = self.m.service_account.default().get_access_token(
          ['https://www.googleapis.com/auth/cloud-platform'])
      try:
        with self.m.context(infra_steps=False):
          self.m.step('test results', [
              self.dart_executable(), self.m.path['checkout'].join(
                  'tools', 'bots', 'get_builder_status.dart'), '-b',
              self.m.buildbucket.builder_name, '-n',
              self.m.buildbucket.build.number, '-a',
              self.m.raw_io.input_text(access_token)
          ])
      except self.m.step.StepFailure:
        result = self.m.step.active_result
        if result.retcode > 1:
          # Returns codes other than 1 are infra failures
          self.m.step.active_result.presentation.status = 'EXCEPTION'
          raise self.m.step.InfraFailure('failed to get test results')
        raise


  def _extend_results_records(self, results_str, prior_results_path,
                              flaky_json_str, prior_flaky_path, builder_name,
                              build_number, commit_time, commit_id):
    return self.m.step('add fields to result records', [
        self.dart_executable(), self.m.path['checkout'].join(
            'tools', 'bots', 'extend_results.dart'),
        self.m.raw_io.input_text(results_str,
                                 name='results.json'), prior_results_path,
        self.m.raw_io.input_text(flaky_json_str, name='flaky.json'),
        prior_flaky_path, builder_name, build_number, commit_time, commit_id,
        self.m.raw_io.output_text()
    ]).raw_io.output_text


  def _present_results(self, logs_str, results_str, flaky_json_str):
    args = [self.dart_executable(),
            'tools/bots/compare_results.dart',
            '--flakiness-data',
            self.m.raw_io.input_text(flaky_json_str, name='flaky.json'),
            '--human',
            '--verbose',
            self.m.path['checkout'].join('LATEST', 'results.json'),
            self.m.raw_io.input_text(results_str),
    ]
    args_logs = ["--logs",
                 self.m.raw_io.input_text(logs_str, name='logs.json'),
                 "--logs-only"]
    links = OrderedDict()
    judgement_args = list(args)
    judgement_args.append('--judgement')
    links["new test failures"] = self.m.step(
        'find new test failures',
        args + ["--changed", "--failing"],
        stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
    links["new test failures (logs)"] = self.m.step(
        'find new test failures (logs)',
        args + args_logs + ["--changed", "--failing"],
        stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
    links["tests that began passing"] = self.m.step(
        'find tests that began passing',
        args + ["--changed", "--passing"],
        stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
    judgement_args += ["--changed", "--failing"]
    if self._try_builder():  # pragma: no cover
      judgement_args += ["--passing"]
    else:
      links["ignored flaky test failure logs"] = self.m.step(
          'find ignored flaky test failure logs',
          args + args_logs + ["--flaky"],
          stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
    with self.m.step.defer_results():
      if self._release_builder():
        with self.m.context(infra_steps=False):
          self.m.step('test results', judgement_args)
      else:
        # This call runs a step that the following links get added to.
        self._report_success(results_str)

      # Add more links and logs to the 'test results' step
      if self._try_builder():
        # Construct different results links for tryjobs and CI jobs
        patchset = self.commit_id().replace('refs/changes/', '')
        log_url = 'https://dart-ci.firebaseapp.com/cl/%s' % patchset
      else:
        log_url = (
            'https://dart-ci.firebaseapp.com/#commit=%s' % self.commit_id())
      self.m.step.active_result.presentation.links['Test Results'] = log_url
      doc_url = 'https://goto.google.com/dart-status-file-free-workflow'
      self.m.step.active_result.presentation.links['Documentation'] = doc_url
      # Show only the links with non-empty output (something happened).
      for link, contents in links.iteritems():
        if contents != '': # pragma: no cover
          self.m.step.active_result.presentation.logs[link] = [contents]
      self.m.step.active_result.presentation.logs['results.json'] = [
          results_str]

  def read_debug_log(self):
    """Reads the debug log file"""
    if self.m.platform.name == 'win':
      self.m.step('debug log',
                  ['cmd.exe', '/c', 'type', '.debug.log'],
                  ok_ret='any')
    else:
      self.m.step('debug log',
                  ['cat', '.debug.log'],
                  ok_ret='any')


  def delete_debug_log(self):
    """Deletes the debug log file"""
    self.m.file.remove('delete debug log',
                       self.m.path['checkout'].join('.debug.log'))


  def test(self, test_data):
    """Reads the test-matrix.json file in checkout and runs each step listed
    in the file.
    """
    with self.m.context(infra_steps=True):
      test_matrix_path = self.m.path['checkout'].join('tools', 'bots',
                                                      'test_matrix.json')
      read_json = self.m.json.read(
          'read test-matrix.json',
          test_matrix_path,
          step_test_data=lambda: self.m.json.test_api.output(test_data))
      test_matrix = read_json.json.output
      builder = str(self.m.buildbucket.builder_name)
      if builder.endswith(('-be', '-try', '-stable', '-dev')):
        builder = builder[0:builder.rfind('-')]
      isolate_hashes = {}
      global_config = test_matrix['global']
      config = None
      for c in test_matrix['builder_configurations']:
        if builder in c['builders']:
          config = c
          break
      if config is None:
        raise self.m.step.InfraFailure(
            'Error, could not find builder by name %s in test-matrix' % builder)
      self.delete_debug_log()
      self._write_file_sets(test_matrix['filesets'])
      self._run_steps(config, isolate_hashes, builder, global_config)


  def _write_file_sets(self, filesets):
    """Writes the fileset to the root of the sdk to allow for swarming to pick
    up the files and isolate the files.
    Args:
      * filesets - Filesets from the test-matrix
    """
    for fileset,files in filesets.iteritems():
      isolate_fileset = { 'variables': { 'files': files } }
      destination_path = self.m.path['checkout'].join(fileset)
      self.m.file.write_text('write fileset %s to sdk root' % fileset,
                            destination_path,
                            str(isolate_fileset))


  def _build_isolates(self, config, isolate_hashes):
    """Isolate filesets from all steps in config and populates a dictionary
    with a mapping from fileset to isolate_hash.
    Args:
      * config (dict) - Configuration of the builder, including the steps
      * isolate_hashes (dict) - A dict that will contain a mapping from
            fileset name to isolate hash upon completion of this method.
    """
    for step in config['steps']:
      if 'fileset' in step and step['fileset'] not in isolate_hashes:
        isolate_hash = self.upload_isolate(step['fileset'])
        isolate_hashes[step['fileset']] = isolate_hash


  def _get_option(self, builder_fragments, options, default_value):
    """Gets an option from builder_fragments in options, or returns the default
    value."""
    intersection = set(builder_fragments) & set(options)
    if len(intersection) == 1:
      return intersection.pop()
    return default_value


  def _get_specific_argument(self, arguments, options):
    for arg in arguments:
      if isinstance(arg, basestring):
        for option in options:
          if arg.startswith(option):
            return arg[len(option):]
    return None


  def _has_specific_argument(self, arguments, options):
    return self._get_specific_argument(arguments, options) is not None


  def _run_steps(self, config, isolate_hashes, builder_name, global_config):
    """Executes all steps from a json test-matrix builder entry"""
    # Find information from the builder name. It should be in the form
    # <info>-<os>-<mode>-<arch>-<runtime> or <info>-<os>-<mode>-<arch>.
    builder_fragments = builder_name.split('-')
    system = self._get_option(
      builder_fragments,
      ['android', 'linux', 'mac', 'win'],
      'linux')
    mode = self._get_option(
      builder_fragments,
      ['debug', 'release', 'product'],
      'release')
    arch = self._get_option(builder_fragments, [
        'ia32', 'x64', 'arm', 'armv6', 'armv5te', 'arm64', 'arm_x64', 'simarm',
        'simarmv6', 'simarmv5te', 'simarm64', 'simdbc', 'simdbc64', 'armsimdbc',
        'armsimdbc64', 'simarm_x64'
    ], 'x64')
    runtime = self._get_option(
      builder_fragments,
      ['none', 'd8', 'jsshell', 'edge', 'ie11', 'firefox', 'safari', 'chrome'],
      None)
    with self.m.context(cwd=self.m.path['checkout']):
      checked_in_sdk_version = self.m.gclient('get checked-in SDK version',
          ['getdep', '-r', 'sdk/tools/sdks:dart/dart-sdk/${platform}'],
          stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
      # TODO(athom): Remove co19_2 legacy support when the test suite has been
      #              deleted from all release branches.
      filter_arg = '--filter=%s/%s' % (CIPD_SERVER_URL, CO19_PACKAGE)
      result = self.m.gclient(
          'get co19 versions', [
              'revinfo', filter_arg, filter_arg + '/legacy', '--output-json',
              self.m.json.output(name='revinfo')
          ],
          step_test_data=self._canned_revinfo)
      revinfo = result.json.outputs.get('revinfo')
      if not revinfo:
        raise recipe_api.InfraFailure('failed to retrieve co19 versions')
      co19_version = None
      if 'sdk/tests/co19_2/src:' + CO19_PACKAGE in revinfo:
        # legacy mode, DEPS doesn't have co19, only co19_2
        co19_2_version = revinfo['sdk/tests/co19_2/src:' + CO19_PACKAGE]['rev']
        co19_2_package = CO19_PACKAGE
      else:
        co19_2_package = CO19_LEGACY_PACKAGE
        co19_2_version = revinfo['sdk/tests/co19_2/src:' +
                                 CO19_LEGACY_PACKAGE]['rev']
        co19_version = revinfo['sdk/tests/co19/src:' + CO19_PACKAGE]['rev']

    out = 'xcodebuild' if self.m.platform.name == 'mac' else 'out'
    build_root = out + '/' + mode.capitalize() + arch.upper()
    environment = {
        'system': system,
        'mode': mode,
        'arch': arch,
        'build_root': build_root,
        'copy-coredumps': False,
        'checked_in_sdk_version': checked_in_sdk_version,
        'co19_version': co19_version,
        'co19_2_version': co19_2_version,
        'co19_2_package': co19_2_package,
        'out': out
    }
    # Linux and vm-*-win builders should use copy-coredumps
    environment['copy-coredumps'] = (system == 'linux' or system == 'mac' or
            (system.startswith('win') and builder_name.startswith('vm-')))

    if runtime is not None:
      if runtime == 'ff':
        runtime = 'firefox' # pragma: no cover
      environment['runtime'] = runtime
      if runtime == 'chrome' or runtime == 'firefox':
        self.download_browser(runtime, global_config[runtime])
    test_steps = []
    sharded_steps = []
    with self.m.step.defer_results():
      for index, step_json in enumerate(config['steps']):
        step = self.TestMatrixStep(self.m, builder_name, config, step_json,
                                   environment, index)
        if step.fileset:
          # We build isolates here, every time we see fileset, to wait for the
          # building of Dart, which may be included in the fileset.
          self._build_isolates(config, isolate_hashes)
          step.isolate_hash = isolate_hashes[step.fileset]

        if not step.is_trigger and step.is_test_step:
          test_steps.append(step)
        if step.isolate_hash and not (step.local_shard and step.shards < 2):
          sharded_steps.append(step)
        self._run_step(step, global_config)
      self.collect_all(sharded_steps)
    self._process_test_results(test_steps, global_config)


  @recipe_api.non_step
  def _run_step(self, step, global_config):
    with self.m.depot_tools.on_path(), self.m.context(
        cwd=self.m.path['checkout'],
        env=step.environment_variables):
      if step.is_gn_step:
        with self.m.context(infra_steps=False):
          self._run_gn(step)
      elif step.is_build_step:
        self._run_build(step)
      elif step.is_trigger:
        self._run_trigger(step)
      elif step.is_test_py_step:
        self._run_test_py(step, global_config)
      else:
        with self.m.context(infra_steps=False):
          self._run_script(step)


  @recipe_api.non_step
  def _run_gn(self, step):
    mode = step.environment['mode']
    arch = step.environment['arch']
    args = step.args
    if not self._has_specific_argument(args, ['-m', '--mode']):
      args = ['-m%s' % mode] + args
    if not self._has_specific_argument(args, ['-a', '--arch']):
      args = ['-a%s' % arch] + args
    with self.m.context(env={'GOMA_DIR': self.m.goma.goma_dir}):
      self.m.python(step.name,
                    self.m.path['checkout'].join('tools', 'gn.py'),
                    args=args)


  @recipe_api.non_step
  def _run_build(self, step):
    mode = step.environment['mode']
    arch = step.environment['arch']
    args = step.args
    if not self._has_specific_argument(args, ['-m', '--mode']):
      args = ['-m%s' % mode] + args
    if not self._has_specific_argument(args, ['-a', '--arch']):
      args = ['-a%s' % arch] + args
    deferred_result = self.build(name=step.name, build_args=args)
    deferred_result.get_result() # raises build errors


  def _process_test_results(self, steps, global_config):
    # If there are no test steps, steps will be empty.
    if steps:
      with self.m.context(cwd=self.m.path['checkout']):
        # Note: The pre-approval script relies on this being a nested step named
        # download_previous_results that contains gsutil_find_latest_build.
        with self.m.step.nest('download previous results'):
          latest, _ = self._get_latest_tested_commit()
          self._download_results(latest)
        with self.m.step.nest('deflaking'):
          for step in steps:
            if step.is_test_py_step:
              self._deflake_results(step, global_config)
          self.collect_all(steps)
        logs_str = ''.join(
            (step.results.logs for step in steps))
        results_str = ''.join(
            (step.results.results for step in steps))
        flaky_json_str = self._update_flakiness_information(results_str)
        results_str = self._extend_results_records(
            results_str, self.m.path['checkout'].join('LATEST', 'results.json'),
            flaky_json_str, self.m.path['checkout'].join(
                'LATEST', 'flaky.json'), self.m.buildbucket.builder_name,
            self.m.buildbucket.build.number,
            self.m.git.get_timestamp(test_data='1234567'), self.commit_id())
        try:
          # Try builders do not upload results, only publish to pub/sub
          with self.m.step.nest('upload new results'):
            if results_str:
              self._publish_results(results_str)
            if not self._try_builder():
              self._upload_results_to_cloud(flaky_json_str, logs_str,
                                            results_str)
              self._upload_results_to_bq(results_str)
        finally:
          self._present_results(logs_str, results_str, flaky_json_str)


  def download_browser(self, runtime, version):
    # Download CIPD package
    #  dart/browsers/<runtime>/${platform} <version>
    # to directory
    #  [sdk root]/browsers
    # Shards must install this CIPD package to the same location -
    # there is an argument to the swarming module task creation api for this.
    browser_path = self.m.path['checkout'].join('browsers')
    self.m.file.ensure_directory('create browser cache', browser_path)
    version_tag = 'version:%s' % version
    package = 'dart/browsers/%s/${platform}' % runtime
    ensure_file = self.m.cipd.EnsureFile().add_package(package, version_tag)
    self.m.cipd.ensure(browser_path, ensure_file)
    return browser_path


  def _upload_results_to_bq(self, results_str):
    if not results_str:
      return  # pragma: no cover
    assert(results_str[-1] == '\n')

    bqupload_path = self.m.path['checkout'].join('bqupload')
    package = r'infra/tools/bqupload/${platform}'
    ensure_file = self.m.cipd.EnsureFile().add_package(package, 'latest')
    self.m.cipd.ensure(bqupload_path, ensure_file)

    bqupload = bqupload_path.join('bqupload')
    cmd = [bqupload , 'dart-ci.results.results']
    with self.m.step.nest('upload test results to big query'):
      # Upload at most 1000 lines at once
      for match in re.finditer(r'(?:.*\n){1,1000}', results_str):
        chunk = match.group(0)
        self.m.step(
            'upload results chunk to big query',
            cmd,
            stdin=self.m.raw_io.input_text(chunk))


  def _run_trigger(self, step):
    trigger_props = {}
    trigger_props['revision'] = self.m.buildbucket.gitiles_commit.id
    trigger_props['parent_buildername'] = self.m.buildbucket.builder_name
    trigger_props['parent_build_id'] = self.m.properties.get('build_id', '')
    if step.isolate_hash:
      trigger_props['parent_fileset'] = step.isolate_hash
      trigger_props['parent_fileset_name'] = step.fileset
    put_result = self.m.buildbucket.put(
        [
          {
            'bucket': 'luci.dart.ci',
            'parameters': {
              'builder_name': builder_name,
              'properties': trigger_props,
              'changes': [
                {
                  'author': {
                    'email': author,
                  },
                }
                for author in self.m.properties.get('blamelist', [])
              ],
            },
          }
          for builder_name in step.triggered_builders
        ])
    self.m.step.active_result.presentation.step_text = step.name
    for build in put_result.stdout['results']:
      builder_tag = (
          x for x in build['build']['tags'] if x.startswith('builder:')).next()
      builder_name = builder_tag[len('builder:'):]
      self.m.step.active_result.presentation.links[builder_name] = (
          build['build']['url'])


  def _run_test_py(self, step, global_config):
    """Runs test.py with default arguments, based on configuration from.
    Args:
      * step (TestMatrixStep) - The test-matrix step.
      * global_config (dict) - The global section from test_matrix.json.
        Contains version tags for the pinned browsers Firefox and Chrome.
    """
    environment = step.environment
    args = step.args
    shards = step.shards
    if step.deflake_list:
      args = args + ['--repeat=5', '--tests', step.deflake_list]
      shards = min(shards, 1)

    test_args = [
        '--progress=status', '--report', '--time', '--silent-failures',
        '--write-results', '--write-logs'
    ]
    test_args.append('--clean-exit')
    args = test_args + args
    if environment['copy-coredumps']:
      args = args + ['--copy-coredumps']
    # The --chrome flag is added here if the runtime for the bot is
    # chrome. This also catches the case where there is a specific
    # argument -r or --runtime. It misses the case where
    # a recipe calls run_script directly with a test.py command.
    # The download of the browser from CIPD should also be moved
    # here (perhaps checking if it is already done) so we catch
    # specific test steps with runtime chrome in a bot without that
    # global runtime.
    ensure_file = self.m.cipd.EnsureFile()

    if any('chrome' in arg for arg in args if isinstance(arg, basestring)):
      version_tag = 'version:%s' % global_config['chrome']
      ensure_file.add_package('dart/browsers/chrome/${platform}', version_tag,
                              'browsers')
      args = args + [CHROME_PATH_ARGUMENT[environment['system']]]
    if any('firefox' in arg for arg in args if isinstance(arg, basestring)):
      version_tag = 'version:%s' % global_config['firefox']
      ensure_file.add_package('dart/browsers/firefox/${platform}', version_tag,
                              'browsers')
      args = args + [FIREFOX_PATH_ARGUMENT[environment['system']]]

    with self.m.step.defer_results():
      self._run_script(
          step,
          args,
          cipd_ensure_file=ensure_file,
          ignore_failure=step.deflake_list,
          shards=shards)

  def _run_script(self,
                  step,
                  args=None,
                  cipd_ensure_file=None,
                  ignore_failure=False,
                  shards=None):
    """Runs a specific script with current working directory to be checkout. If
    the runtime (passed in environment) is a browser, and the system is linux,
    xvfb is used. If an isolate_hash is passed in, it will swarm the command.
    Args:
      * step (TestMatrixStep) - The test-matrix step.
      * args ([str]) - Overrides the arguments specified in the step.
      * cipd_packages ([tuple]) - list of 3-tuples specifying a cipd package
        to be downloaded
      * ignore_failure ([bool]) - Do not turn step red if this script fails.
      * shards ([int]) - Overrides the number of shards specified in the step.
    """
    environment = step.environment
    if not args:
      args = step.args
    if not cipd_ensure_file:  # pragma: no cover
      cipd_ensure_file = self.m.cipd.EnsureFile()
    cipd_ensure_file.add_package('dart/dart-sdk/${platform}',
                                 environment['checked_in_sdk_version'],
                                 'tools/sdks')
    if any(arg.startswith('co19_2') for arg in args):
      cipd_ensure_file.add_package(environment['co19_2_package'],
                                   environment['co19_2_version'],
                                   'tests/co19_2/src')
    if any(arg.startswith('co19/') or arg == 'co19' for arg in args):
      cipd_ensure_file.add_package(CO19_PACKAGE, environment['co19_version'],
                                   'tests/co19/src')

    ok_ret = 'any' if ignore_failure else {0}
    runtime = environment.get('runtime', None)
    use_xvfb = (runtime in ['chrome', 'firefox'] and
                environment['system'] == 'linux')
    script = step.script
    is_python = str(script).endswith('.py')
    xvfb_cmd = []
    if use_xvfb:
      xvfb_cmd = [
        '/usr/bin/xvfb-run',
        '-a',
        '--server-args=-screen 0 1024x768x24']
      if is_python:
        xvfb_cmd += ['python', '-u']

    step_name = step.name
    shards = shards or step.shards
    if step.isolate_hash and not (step.local_shard and shards < 2):
      with self.m.step.nest('trigger shards for %s' % step_name):
        arch = environment['arch']
        cpu = arch if arch.startswith('arm') else 'x86-64'
        # armsimdbc64 -> arm64 because simdbc isn't a real architecture.
        cpu = cpu.replace('simdbc', '')
        # arm_x64 -> arm (x64 gen_snapshot creating 32bit arm code).
        cpu = cpu.replace('_x64', '')
        step.tasks += self.shard(
            step_name,
            step.isolate_hash,
            xvfb_cmd + [script] + args,
            num_shards=shards,
            last_shard_is_local=step.local_shard,
            cipd_ensure_file=cipd_ensure_file,
            ignore_failure=ignore_failure,
            cpu=cpu,
            os=environment['system'])
      if step.local_shard:
        args = args + [
          '--shards=%s' % shards,
          '--shard=%s' % shards,
        ]
        step_name = '%s_shard_%s' % (step_name, shards)
      else:
        return # Shards have been triggered, no local shard to run.

    output_dir = None
    if step.is_test_step:
      output_dir = self.m.path.mkdtemp()
      args = args + [
          '--output-directory',
          output_dir,
      ]

    cmd = self.m.path['checkout'].join(*script.split('/'))
    if is_python and not use_xvfb:
      self.m.python(step_name, cmd, args=args, ok_ret=ok_ret)
    else:
      self.m.step(step_name, xvfb_cmd + [cmd] + args, ok_ret=ok_ret)
    if output_dir:
      self._add_results_and_links(output_dir, self.m.properties.get('bot_id'),
                                  step_name, step.results)


  def _canned_revinfo(self):
    revinfo = {
        "sdk/tests/co19/src:dart/third_party/co19": {
            "url": "%s/dart/third_party/co19" % CIPD_SERVER_URL,
            "rev": "git_revision:co19_hash"
        },
        "sdk/tests/co19_2/src:dart/third_party/co19/legacy": {
            "url": "%s/dart/third_party/co19/legacy" % CIPD_SERVER_URL,
            "rev": "git_revision:co19_2_hash"
        }
    }
    return self.m.json.test_api.output(name='revinfo', data=revinfo)

  class TestMatrixStep:
    def __init__(self, m, builder_name, config, step_json, environment, index):
      self.m = m
      self.name = step_json['name']
      self.results = StepResults(m)
      self.deflake_list = []
      self.args = step_json.get('arguments', [])
      self.environment = environment
      self.tasks = []
      self.is_trigger = 'trigger' in step_json
      self.triggered_builders = step_json.get('trigger', [])
      # If script is not defined, use test.py.
      self.script = step_json.get('script', TEST_PY_PATH)
      if self.m.platform.name == 'mac' and self.script.startswith('out/'):
        self.script = self.script.replace('out/', 'xcodebuild/', 1)
      is_dart = self.script.endswith('/dart')
      if is_dart:
        executable_suffix = '.exe' if self.m.platform.name == 'win' else ''
        self.script += executable_suffix

      self.is_build_step = self.script.endswith(BUILD_PY_PATH)
      self.is_gn_step = self.script.endswith(GN_PY_PATH)
      self.is_test_py_step = self.script.endswith(TEST_PY_PATH)
      self.is_test_step = (self.is_test_py_step
          or step_json.get('testRunner', False))

      self.isolate_hash = None
      self.fileset = step_json.get('fileset')
      self.shards = step_json.get('shards', 0)
      self.local_shard = (self.shards > 1 and index == len(config['steps']) - 1
          and not environment['system'] == 'android')

      self.environment_variables = step_json.get('environment', {})

      channels = {
        "refs/heads/master": "be",
        "refs/heads/stable": "stable",
        "refs/heads/dev": "dev"
      }
      channel = channels.get(self.m.buildbucket.gitiles_commit.ref, 'try')
      self.environment_variables['BUILDBOT_BUILDERNAME'] = (
          builder_name + "-%s" % channel)

      # Enable Crashpad integration if a Windows bot wants to copy coredumps.
      if self.environment['copy-coredumps'] and self.m.platform.name == 'win':
        self.environment_variables['DART_USE_CRASHPAD'] = '1'

      def _expand_environment(arg):
        for k, v in environment.iteritems():
          arg = arg.replace('${%s}' % k, str(v))
        return arg

      self.args = [_expand_environment(arg) for arg in self.args]


class StepResults:

  def __init__(self, m):
    self.logs = ''
    self.results = ''
    self.builder_name = str(m.buildbucket.builder_name) # Returned as unicode
    self.build_number = str(m.buildbucket.build.number)


  def add_results(self, bot_name, results_str):
    extra = ',"bot_name":"%s"}\n' % bot_name
    all_matches = re.finditer(r'(^{.*)(?:})', results_str, flags=re.MULTILINE)
    all_chunks = (chunk for match in all_matches for chunk in (
        match.group(1), extra))
    self.results += ''.join(all_chunks)
