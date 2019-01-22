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


class DartApi(recipe_api.RecipeApi):
  """Recipe module for code commonly used in dart recipes.

  Shouldn't be used elsewhere."""
  def checkout(self, clobber=False, revision=None):
    """Checks out the dart code and prepares it for building."""
    self.m.gclient.set_config('dart')
    sdk = self.m.gclient.c.solutions[0]
    sdk.custom_deps['sdk/%s' % SWARMING_CLIENT_PATH] = \
        '%s@%s' % (SWARMING_CLIENT_REPO, SWARMING_CLIENT_REV)
    self.m.goma.ensure_goma()

    with self.m.context(cwd=self.m.path['cache'].join('builder'),
                        env={'GOMA_DIR':self.m.goma.goma_dir,
                             'GIT_TRACE_CURL': '1',
                             'GIT_TRACE_CURL_NO_DATA': '1',
                             'GIT_REDACT_COOKIES': 'o,SSO,GSSO_UberProxy'}):
      try:
        self.m.bot_update.ensure_checkout(root_solution_revision=revision)
      except self.m.step.InfraFailure:
        if not revision:
          raise
        # Maybe we failed to because of the revision, try the latest instead.
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
    self.m.cipd.ensure(cloudkms_dir,
                    {'infra/tools/luci/cloudkms/${platform}': 'latest'})

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


  def build(self, build_args=None, name='build dart'):
    """Builds dart using the specified build_args
       and optionally isolates the sdk for testing using the specified isolate.
       If an isolate is specified, it returns the hash of the isolated archive.
    """
    if not build_args: # pragma: no cover
      build_args = []
    build_args = build_args + ['--no-start-goma', '-j200']
    with self.m.context(cwd=self.m.path['checkout'],
                        env={'GOMA_DIR':self.m.goma.goma_dir}):
      with self.m.depot_tools.on_path():
        self.kill_tasks()
        build_exit_status = None
        try:
          self.m.goma.start()
          self.m.python(name,
                        self.m.path['checkout'].join('tools', 'build.py'),
                        args=build_args,
                        timeout=20 * 60)
          build_exit_status = 0
        except self.m.step.StepTimeout as e:
          raise self.m.step.StepFailure(
              'Step "%s" timed out after 20 minutes' % name)
        except self.m.step.StepFailure as e:
          build_exit_status = e.retcode
          raise e
        finally:
          self.m.goma.stop(build_exit_status=build_exit_status)


  def upload_isolate(self, isolate_fileset):
    """Builds an isolate"""
    if isolate_fileset == self.m.properties.get('parent_fileset_name', None):
      return self.m.properties.get('parent_fileset')
    step_result = self.m.python(
        'upload testing fileset %s' % isolate_fileset,
        self.m.swarming_client.path.join('isolate.py'),
        args= ['archive',
                 '--blacklist=%s' % BLACKLIST,
                 '--ignore_broken_items', # TODO(athom) find a way to avoid that
                 '-Ihttps://isolateserver.appspot.com',
                 '-i%s' % self.m.path['checkout'].join('%s' % isolate_fileset),
                 '-s%s' % self.m.path['checkout'].join(
                     '%s.isolated' % isolate_fileset)],
        stdout=self.m.raw_io.output('out'))
    isolate_hash = step_result.stdout.strip()[:40]
    step_result.presentation.step_text = 'swarming fileset hash: %s' % (
        isolate_hash)
    return isolate_hash


  def download_parent_isolate(self):
    self.m.path['checkout'] = self.m.path['cleanup']
    isolate_hash = self.m.properties['parent_fileset']
    fileset_name = self.m.properties['parent_fileset_name']
    with self.m.context(cwd=self.m.path['cleanup']):
      self.m.python(
        'downloading fileset %s' % fileset_name,
        self.m.swarming_client.path.join('isolateserver.py'),
        args= ['download',
                 '-Ihttps://isolateserver.appspot.com',
                 '-s%s' % isolate_hash,
                 '--target=.'],
        stdout=self.m.raw_io.output('out'))


  def shard(self, title, isolate_hash, test_args, os=None, cpu='x86-64',
            pool='dart.tests', num_shards=0, last_shard_is_local=False,
            cipd_packages=None, ignore_failure=False):
    """Runs test.py in the given isolate, sharded over several swarming tasks.
       Requires the 'shards' build property to be set to the number of tasks.
       Returns the created task(s), which are meant to be passed into collect().
    """
    if not cipd_packages: # pragma: no cover
      cipd_packages = []
    if 'shards' in self.m.properties:
      num_shards = int(self.m.properties['shards'])
    assert(num_shards > 0)
    tasks = []
    if os is None:
      os = self.m.platform.name
    for shard in range(num_shards):
      # TODO(athom) collect all the triggers, and present as a single step
      if last_shard_is_local and shard == num_shards - 1:
        break
      task = self.m.swarming.task('%s_shard_%s' % (title, (shard + 1)),
                                  isolate_hash,
                                  cipd_packages=cipd_packages,
                                  raw_cmd=test_args +
                                  ['--shards=%s' % num_shards,
                                   '--shard=%s' % (shard + 1),
                                   '--output_directory=${ISOLATED_OUTDIR}'],
                                  ignore_task_failure=ignore_failure)
      os_names = {
        'android': 'Android',
        'linux': 'Linux',
        'mac': 'Mac',
        'win': 'Windows',
      }
      task.dimensions['os'] = os_names.get(os, os)
      if not cpu:
        task.dimensions.pop('cpu', None)
      else:
        task.dimensions['cpu'] = cpu
      task.dimensions['pool'] = pool
      task.dimensions.pop('gpu', None)
      if 'shard_timeout' in self.m.properties:
        task.hard_timeout = int(self.m.properties['shard_timeout'])
      # Set a priority lower than any builder, to prioritize shards.
      task.priority = 25
      self.m.swarming.trigger_task(task)
      tasks.append(task)
    return tasks


  def _report_new_results(self):
    """Boolean that controls whether to report status of
       deflaked tests measured against
       latest or approved results as buildbot status,
       instead of the status-file based exit code of test.py."""
    return 'new_workflow_enabled' in self.m.properties


  def _run_new_steps(self):
    """Boolean that controls whether to run the new
       workflow that uploads test results to cloud
       storage and deflakes changed tests."""
    return (self._report_new_results or
        not self.m.buildbucket.builder_name.endswith('-try'))


  def collect_all(self, tasks, commit, all_results):
    """Collects the results of a sharded test run."""
    # Defer results in case one of the shards has a non-zero exit code.
    with self.m.step.defer_results():
      # TODO(athom) collect all the output, and present as a single step
      for task in tasks:
        shards = task['shards']
        # All shards share the same step name, so just use the first
        step_name = shards[0].title.split('_shard')[0]
        results = StepResults(step_name, self.m, commit)
        for shard in shards:
          shard.task_output_dir = self.m.raw_io.output_dir()
          self.m.swarming.collect_task(shard)
          active_result = self.m.step.active_result
          # Every shard is only a single task in swarming
          bot_name = active_result.swarming.summary['shards'][0]['bot_id']
          active_result.presentation.links['test stdout of shard #0'] = (
            shard.get_shard_view_url(index=0))
          self._add_results_and_links(bot_name, results)
        if results.runs or results.results:
          self._add_to_all_results(all_results, results)


  def _add_results_and_links(self, bot_name, results):
    output_dir = self.m.step.active_result.raw_io.output_dir
    for filepath in output_dir:
      filename = filepath.split('/')[-1]
      filename = filename.split('\\')[-1]
      if filename in (
          'logs.json', 'results.json', 'run.json'):
        contents = output_dir[filepath]
        self.m.step.active_result.presentation.logs[
            filename] = [contents]
        if filename == 'results.json':
          results.add_results(bot_name, contents)
        if filename == 'logs.json':
          results.logs += contents
        if filename == 'run.json':
          results.add_run(bot_name, contents)


  def get_latest_tested_commit(self):
    builder = self._get_builder_dir()
    latest_result = self.m.gsutil.download(
        'dart-test-results',
        'builders/%s/latest' % builder,
        self.m.raw_io.output_text(name='latest', add_output_log=True),
        name='find latest build',
        ok_ret='any') # todo(athom): succeed only if file does not exist
    latest = latest_result.raw_io.output_texts.get('latest')
    revision = None
    if latest:
      latest = latest.strip()
      revision_result = self.m.gsutil.download(
          'dart-test-results',
          'builders/%s/%s/revision' % (builder, latest),
          self.m.raw_io.output_text(name='revision', add_output_log=True),
          name='get revision for latest build',
          ok_ret='any') # todo(athom): succeed only if file does not exist
      revision = revision_result.raw_io.output_texts.get('revision')

    return (latest, revision)


  def _get_builder_dir(self):
    builder = self.m.buildbucket.builder_name
    if builder.endswith('-try'):
      builder = builder[:-4]
    return builder


  def _download_results(self, latest):
    filenames = ['results.json', 'flaky.json']
    builder = self._get_builder_dir()
    results_path = self.m.path['checkout'].join('LATEST')
    self.m.file.ensure_directory('ensure LATEST dir', results_path)
    for filename in filenames + ['approved_results.json']:
      self.m.file.write_text(
        'ensure %s exists' % filename, results_path.join(filename), '')
    if latest:
      self.m.gsutil.download(
        'dart-test-results',
        'builders/%s/%s/*.json' % (builder, latest),
        results_path,
        name='download previous results',
        ok_ret='any' if self._report_new_results() else {0})
    self.m.gsutil.download(
        'dart-test-results-approved-results',
        'builders/%s/approved_results.json' % builder,
        'LATEST/approved_results.json',
        name='download approved results',
        ok_ret='any')


  def _deflake_results(self, results):
    step_name = results.step_name
    environment = results.environment
    deflake_list = self.m.step('list tests to deflake (%s)' % step_name,
                [self.dart_executable(),
                 'tools/bots/compare_results.dart',
                 '--flakiness-data',
                 'LATEST/flaky.json',
                 '--changed',
                 '--passing',
                 '--failing',
                 '--count',
                 '50',
                 'LATEST/results.json',
                 self.m.raw_io.input_text(results.results)],
                stdout=self.m.raw_io.output_text(add_output_log=True),
                ok_ret='any' if self._report_new_results() else {0}).stdout
    args = results.args + ['--repeat=5', '--test-list',
                           self.m.raw_io.input_text(deflake_list)]
    self.run_script(
        'deflake %s' % step_name, TEST_PY_PATH,
        args,
        None, None,
        False, environment, None, ignore_failure=True)
    self._add_results_and_links(self.m.properties.get('bot_id'), results)


  def _update_flakiness_information(self, results_str):
    flaky_json = self.m.step('update flakiness information',
           [self.dart_executable(),
            'tools/bots/update_flakiness.dart',
            '-i',
            'LATEST/flaky.json',
            '-o',
            self.m.raw_io.output_text(name='flaky.json', add_output_log=True),
            '--build-id',
            self.m.buildbucket.build.id,
            '--commit',
            self.m.buildbucket.gitiles_commit.id,
            self.m.raw_io.input_text(results_str, name='results.json')],
            ok_ret='any' if self._report_new_results() else {0})
    return flaky_json.raw_io.output_texts.get('flaky.json')


  def _upload_results(self, flaky_json_str, logs_str, results_str, runs_str):
    # Try builders do not upload results.
    builder = str(self.m.buildbucket.builder_name)
    if builder.endswith('try'):
      return # pragma: no cover

    build_revision = str(self.m.buildbucket.gitiles_commit.id)
    build_number = str(self.m.buildbucket.build.number)


    self._upload_result(builder, build_number, 'revision', build_revision)
    self._upload_result(builder, build_number, 'logs.json', logs_str)
    self._upload_result(builder, build_number, 'results.json', results_str)
    self._upload_result(builder, build_number, 'flaky.json', flaky_json_str)
    self._upload_result('current_flakiness', 'single_directory',
                        'flaky_current_%s.json' % builder, flaky_json_str)
    self.m.gsutil.upload(
      'LATEST/approved_results.json',
      'dart-test-results',
      'builders/%s/%s/approved_results.json' % (builder, build_number),
      ok_ret='any' if self._report_new_results() else {0})
    self._upload_result(builder, build_number, 'runs.json', runs_str)
    # Update "latest" file
    new_latest = self.m.raw_io.input_text(build_number, name='latest')
    self.m.gsutil.upload(
      new_latest,
      'dart-test-results',
      'builders/%s/%s' % (builder, 'latest'),
      name='update "latest" reference',
      ok_ret='any' if self._report_new_results() else {0})
    self._upload_results_to_bq(results_str)


  def _upload_result(self, builder, build_number, filename, result_str):
    self.m.gsutil.upload(
      self.m.raw_io.input_text(result_str, name=filename),
      'dart-test-results',
      'builders/%s/%s/%s' % (builder, build_number, filename),
      name='upload %s' % filename, ok_ret='any'
      if self._report_new_results() else {0})


  def _present_results(self, logs_str, results_str, flaky_json_str):
    # CQ:
    #   unapproved new test failures
    #   unapproved new test failures (logs)
    #   approved new test failures
    #   approved new test failures (logs)
    #   tests that began passing
    # CI:
    #   tests that began failing
    #   tests that began failing (logs)
    #   tests that began passing
    #   unapproved failing tests
    #   unapproved failing tests (logs)
    #   unapproved passing tests
    args = [self.dart_executable(),
            'tools/bots/compare_results.dart',
            '--flakiness-data',
            self.m.raw_io.input_text(flaky_json_str, name='flaky.json'),
            '--human',
            '--verbose',
            self.m.path['checkout'].join('LATEST', 'results.json'),
            self.m.raw_io.input_text(results_str),
            self.m.path['checkout'].join('LATEST', 'approved_results.json'),
    ]
    args_logs = ["--logs",
                 self.m.raw_io.input_text(logs_str, name='logs.json'),
                 "--logs-only"]
    links = OrderedDict()
    judgement_args = list(args)
    if self._report_new_results():
      judgement_args.append('--judgement')
    builder_name = self.m.buildbucket.builder_name
    if builder_name.endswith('-try'):
      links["unapproved new test failures"] = self.m.step(
          'find unapproved new test failures',
          args + ["--changed", "--failing", "--unapproved"],
          stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
      links["unapproved new test failures (logs)"] = self.m.step(
          'find unapproved new test failures (logs)',
          args + args_logs + ["--changed", "--failing", "--unapproved"],
          stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
      links["approved new test failures"] = self.m.step(
          'find approved new test failures',
          args + ["--changed", "--failing", "--approved"],
          stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
      links["approved new test failures (logs)"] = self.m.step(
          'find approved new test failures (logs)',
          args + args_logs + ["--changed", "--failing", "--approved"],
          stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
      links["tests that began passing"] = self.m.step(
          'find tests that began passing',
          args + ["--changed", "--passing", "--approved", "--unapproved"],
          stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
      judgement_args += ["--changed", "--passing", "--failing", "--approved",
                         "--unapproved"]
    else:
      links["tests that began failing"] = self.m.step(
          'find tests that began failing',
          args + ["--changed", "--failing", "--approved", "--unapproved"],
          stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
      links["tests that began failing (logs)"] = self.m.step(
          'find tests that began failing (logs)',
          args + args_logs + ["--changed", "--failing"],
          stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
      links["tests that began passing"] = self.m.step(
          'find tests that began passing',
          args + ["--changed", "--passing", "--approved", "--unapproved"],
          stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
      links["unapproved failing tests"] = self.m.step(
          'find unapproved failing tests',
          args + ["--unapproved", "--failing"],
          stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
      links["unapproved failing tests (logs)"] = self.m.step(
          'find unapproved failing tests (logs)',
          args + args_logs + ["--unapproved", "--failing"],
          stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
      links["unapproved passing tests"] = self.m.step(
          'find unapproved passing tests',
          args + ["--unapproved", "--passing"],
          stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
      links["ignored flaky test failure logs"] = self.m.step(
          'find ignored flaky test failure logs',
          args + args_logs + ["--flaky"],
          stdout=self.m.raw_io.output_text(add_output_log=True)).stdout
      judgement_args += ["--failing", "--unapproved"]
    with self.m.step.defer_results():
      self.m.step('test results', judgement_args)
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


  def test(self, latest, test_data):
    """Reads the test-matrix.json file in checkout and performs each step listed
    in the file

    Raises StepFailure.
    """
    test_matrix_path = self.m.path['checkout'].join('tools',
                                                    'bots',
                                                    'test_matrix.json')
    read_json = self.m.json.read(
      'read test-matrix.json',
      test_matrix_path,
      step_test_data=lambda: self.m.json.test_api.output(test_data))
    test_matrix = read_json.json.output
    builder = str(self.m.buildbucket.builder_name)
    if builder.endswith(('-be', '-try', '-stable', 'dev')):
      builder = builder[0:builder.rfind('-')]
    isolate_hashes = {}
    global_config = test_matrix['global']
    config = None
    for c in test_matrix['builder_configurations']:
      if builder in c['builders']:
        config = c
        break
    if config is None:
      raise self.m.step.StepFailure(
          'Error, could not find builder by name %s in test-matrix' % builder)
    self.delete_debug_log()
    self._write_file_sets(test_matrix['filesets'])
    self._run_steps(config, isolate_hashes, builder, global_config, latest)


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
    """Isolate filesets from all steps in config and returns a dictionary with a
    mapping from fileset to isolate_hash.
    Args:
      * config (dict) - Configuration of the builder, including the steps

    Returns (dict) - A mapping from fileset to isolate_hashes
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


  def _replace_specific_argument(self, arguments, options, replacement):
    for index,arg in enumerate(arguments):
      for option in options:
        if arg.startswith(option):
          arguments[index] = replacement
          return None


  def _run_steps(self, config, isolate_hashes, builder_name, global_config, latest):
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
    arch = self._get_option(
      builder_fragments,
      ['ia32', 'x64', 'arm', 'armv6', 'armv5te', 'arm64', 'simarm', 'simarmv6',
      'simarmv5te', 'simarm64', 'simdbc', 'simdbc64'],
      'x64')
    runtime = self._get_option(
      builder_fragments,
      ['none', 'd8', 'jsshell', 'edge', 'ie11', 'firefox', 'safari', 'chrome'],
      None)
    with self.m.context(cwd=self.m.path['checkout']):
      result = self.m.gclient('get checked-in SDK version',
          ['getdep', '-r', 'sdk/tools/sdks:dart/dart-sdk/${platform}'],
          stdout=self.m.raw_io.output_text(add_output_log=True))
    environment = {'system': system,
                   'mode': mode,
                   'arch': arch,
                   'copy-coredumps': False,
                   'checked_in_sdk_version': result.stdout}
    environment['commit'] = {
      'commit_hash': self.m.buildbucket.gitiles_commit.id,
      'commit_time': self.m.git.get_timestamp(test_data='1234567')
    }
    # Linux and vm-*-win builders should use copy-coredumps
    environment['copy-coredumps'] = (system == 'linux' or system == 'mac' or
            (system.startswith('win') and builder_name.startswith('vm-')))

    if runtime is not None:
      if runtime == 'ff':
        runtime = 'firefox' # pragma: no cover
      environment['runtime'] = runtime
      if runtime == 'chrome' or runtime == 'firefox':
        self._download_browser(runtime, global_config[runtime])
    channels = {
      "refs/heads/master": "be",
      "refs/heads/stable": "stable",
      "refs/heads/dev": "dev"
    }
    channel = channels.get(self.m.buildbucket.gitiles_commit.ref, 'try')
    build_py_path = 'tools/build.py'
    tasks = []
    all_results = {}
    with self.m.step.defer_results():
      for index,step in enumerate(config['steps']):
        step_name = step['name']
        # If script is not defined, use test.py.
        script = step.get('script', TEST_PY_PATH)
        args = step.get('arguments', [])
        is_build_step = script.endswith(build_py_path)
        is_trigger = 'trigger' in step

        if self.m.platform.name == 'mac' and script.startswith('out/'):
          script = script.replace('out/', 'xcodebuild/', 1)

        is_dart = script.endswith('/dart')
        if is_dart:
          executable_suffix = '.exe' if self.m.platform.name == 'win' else ''
          script += executable_suffix

        isolate_hash = None
        shards = step.get('shards', 0)
        local_shard = (shards > 1 and index == len(config['steps']) - 1
            and not environment['system'] == 'android')
        if 'fileset' in step:
          # We build isolates here, every time we see fileset, to wait for the
          # building of Dart, which may be included in the fileset.
          self._build_isolates(config, isolate_hashes)
          isolate_hash = isolate_hashes[step['fileset']]

        environment_variables = step.get('environment', {})
        environment_variables['BUILDBOT_BUILDERNAME'] = (
            builder_name + "-%s" % channel)

        # Enable Crashpad integration if a Windows bot wants to copy coredumps.
        if environment['copy-coredumps'] and self.m.platform.name == 'win':
          environment_variables['DART_USE_CRASHPAD'] = '1'

        with self.m.context(cwd=self.m.path['checkout'],
                            env=environment_variables):
          with self.m.depot_tools.on_path():
            if is_build_step:
              if not self._has_specific_argument(args, ['-m', '--mode']):
                args = ['-m%s' % mode] + args
              if not self._has_specific_argument(args, ['-a', '--arch']):
                args = ['-a%s' % arch] + args
              deferred_result = self.build(name=step_name, build_args=args)
              deferred_result.get_result() # raises build errors
            elif is_trigger:
              self.run_trigger(step_name, step, isolate_hash)
            elif self._is_test_py_step(script):
              self.run_test_py(step_name, step, isolate_hash,
                               shards, local_shard, environment,
                               tasks, global_config, all_results)
            else:
              self.run_script(step_name, script, args, isolate_hash, shards,
                  local_shard, environment, tasks)
      self.collect_all(tasks, environment['commit'], all_results)
      # todo(athom): remove this when the new workflow is fully rolled out.
      # Old workflow test.py steps throw on failing tests and results need to
      # be processed in the defer_results block.
      if not self._report_new_results():
        self._process_test_results(all_results, latest)
    if self._report_new_results():
      self._process_test_results(all_results, latest)


  def _process_test_results(self, all_results, latest):
    # If there are no test steps, all_results will be empty.
    if self._run_new_steps() and all_results:
      with self.m.context(cwd=self.m.path['checkout']):
        with self.m.step.nest('download previous results'):
          self._download_results(latest)
        for results in all_results.itervalues():
          self._deflake_results(results)
        logs_str = ''.join(
            (results.logs for results in all_results.itervalues()))
        results_str = ''.join(
            (results.results for results in all_results.itervalues()))
        flaky_json_str = self._update_flakiness_information(results_str)
        try:
          self._present_results(logs_str, results_str, flaky_json_str)
        finally:
          # Upload even if present_results fails the build
          with self.m.step.nest('upload new results'):
            runs_str = ''.join(
                (results.runs for results in all_results.itervalues()))
            self._upload_results(
                flaky_json_str, logs_str, results_str, runs_str)


  def _is_test_py_step(self, script):
    return script.endswith(TEST_PY_PATH)


  def _add_to_all_results(self, all_results, results):
    step_name = results.step_name
    if all_results.get(step_name) is None:
      all_results[step_name] = results
    else:
      all_results[step_name].merge(results)


  def _download_browser(self, runtime, version):
    # Download CIPD package
    #  dart/browsers/<runtime>/${platform} <version>
    # to directory
    #  [sdk root]/browsers
    # Shards must install this CIPD package to the same location -
    # there is an argument to the swarming module task creation api for this.
    browser_path = self.m.path['checkout'].join('browsers')
    self.m.file.ensure_directory('create browser cache', browser_path)
    self.m.cipd.set_service_account_credentials(None)
    version_tag = 'version:%s' % version
    package = 'dart/browsers/%s/${platform}' % runtime
    self.m.cipd.ensure(browser_path, { package: version_tag })


  def _upload_results_to_bq(self, results_str):
    if not results_str:
      return
    assert(results_str[-1] == '\n')

    bqupload_path = self.m.path['checkout'].join('bqupload')
    package = r'infra/tools/bqupload/${platform}'
    self.m.cipd.ensure(bqupload_path, {package: 'latest'})

    bqupload = bqupload_path.join('bqupload')
    cmd = [bqupload , 'dart-ci.results.results']
    with self.m.step.nest('upload test results to big query'):
      # Upload at most 1000 lines at once
      for match in re.finditer(r'(?:.*\n){1,1000}', results_str):
        chunk = match.group(0)
        self.m.step('upload results chunk to big query', cmd,
            stdin=self.m.raw_io.input_text(chunk), infra_step=True,
            ok_ret='any' if self._report_new_results() else {0})


  def run_trigger(self, step_name, step, isolate_hash):
    trigger_props = {}
    trigger_props['revision'] = self.m.buildbucket.gitiles_commit.id
    trigger_props['parent_buildername'] = self.m.buildbucket.builder_name
    trigger_props['parent_build_id'] = self.m.properties.get('build_id', '')
    if isolate_hash:
      trigger_props['parent_fileset'] = isolate_hash
      trigger_props['parent_fileset_name'] = step['fileset']
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
          for builder_name in step['trigger']
        ])
    self.m.step.active_result.presentation.step_text = step_name
    for build in put_result.stdout['results']:
      builder_tag = (
          x for x in build['build']['tags'] if x.startswith('builder:')).next()
      builder_name = builder_tag[len('builder:'):]
      self.m.step.active_result.presentation.links[builder_name] = (
          build['build']['url'])


  def run_test_py(self, step_name, step, isolate_hash, shards, local_shard,
                  environment, tasks, global_config, all_results):
    """Runs test.py with default arguments, based on configuration from.
    Args:
      * step_name (str) - Name of the step
      * step (dict) - Test-matrix step
      * isolate_hash (String) - Hash of uploadet fileset/isolate if the
        process is to be sharded
      * shards (int) - The number of shards
      * local_shard (bool) - Should the current builder be one of the shards.
      * environment (dict) - Environment with runtime, arch, system etc
      * tasks ([task]) - placeholder to put all swarming tasks in
      * global_config (dict) - The global section from test_matrix.json.
        Contains version tags for the pinned browsers Firefox and Chrome.
    """
    args = step.get('arguments', [])
    test_args = ['--progress=status',
                 '--report',
                 '--time',
                 '--write-debug-log',
                 '--write-results',
                 '--write-logs']
    if self._report_new_results():
      test_args.append("--clean-exit")
    template = self._get_specific_argument(args, ['-n'])
    if template is not None:
      for term in ['runtime', 'system', 'mode', 'arch']:
        if '${%s}' % term in template:
          template = template.replace('${%s}' % term, environment.get(term, ''))
      self._replace_specific_argument(args, ['-n'], "-n%s" % template)
    else:
      if not self._has_specific_argument(args, ['-m', '--mode']):
        test_args = ['-m%s' % environment['mode']] + test_args
      if not self._has_specific_argument(args, ['-a', '--arch']):
        test_args = ['-a%s' % environment['arch']] + test_args
      if 'runtime' in environment and not self._has_specific_argument(
          args, ['-r', '--runtime']):
        test_args = test_args + ['-r%s' % environment['runtime']]
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
    cipd_packages = []
    if any('chrome' in arg for arg in args):
      version_tag = 'version:%s' % global_config['chrome']
      cipd_packages.append(('browsers',
                            'dart/browsers/chrome/${platform}',
                            version_tag))
      args = args + [CHROME_PATH_ARGUMENT[environment['system']]]
    if any('firefox' in arg for arg in args):
      version_tag = 'version:%s' % global_config['firefox']
      cipd_packages.append(('browsers',
                            'dart/browsers/firefox/${platform}',
                            version_tag))
      args = args + [FIREFOX_PATH_ARGUMENT[environment['system']]]
    if 'exclude_tests' in step:
        args = args + ['--exclude_suite=' + ','.join(step['exclude_tests'])]
    if 'tests' in step:
      args = args + step['tests']

    with self.m.step.defer_results():
      # TODO(https://github.com/dart-lang/sdk/issues/34158): The Firefox
      # processes are not exiting properly, causing the step to fail at the end,
      # despite the results having been written out. Temporarily ignore failures
      # on firefox.
      firefox_bug = 'firefox' in self.m.buildbucket.builder_name
      self.run_script(step_name, TEST_PY_PATH, args, isolate_hash, shards,
                      local_shard, environment, tasks,
                      cipd_packages=cipd_packages,
                      ignore_failure=firefox_bug)
      results = StepResults(step_name, self.m, environment['commit'])
      results.args = args
      results.environment = environment
      if shards == 0 or local_shard:
        self._add_results_and_links(self.m.properties.get('bot_id'), results)
      # Add even if we don't have a local shard to record args and environment
      self._add_to_all_results(all_results, results)


  def run_script(self, step_name, script, args, isolate_hash, shards,
                 local_shard, environment, tasks,
                 cipd_packages=None, ignore_failure=False):
    """Runs a specific script with current working directory to be checkout. If
    the runtime (passed in environment) is a browser, and the system is linux,
    xvfb is used. If an isolate_hash is passed in, it will swarm the command.
    Args:
      * step_name (str) - Name of the step
      * script (str) - The script to invoke
      * args ([str]) - Additional arguments to test.py
      * isolate_hash (str) - The isolate hash if the script should be swarmed
      * shards (int) - The number of shards to invoke
      * local_shard (bool) - Should the current builder be used as a shard
      * environment (dict) - Environment with runtime, arch, system etc
      * tasks ([task]) - placeholder to hold swarming tasks
      * cipd_packages ([tuple]) - list of 3-tuples specifying a cipd package
        to be downloaded
      * ignore_failure - Do not turn step red if this script fails.
    """
    if not cipd_packages: # pragma: no cover
      cipd_packages = []
    cipd_packages.append(('tools/sdks',
        'dart/dart-sdk/${platform}',
        environment['checked_in_sdk_version']))
    ok_ret = 'any' if ignore_failure else {0}
    runtime = self._get_specific_argument(args, ['-r', '--runtime'])
    if runtime is None:
      runtime = environment.get('runtime', None)
    use_xvfb = (runtime in ['chrome', 'firefox'] and
                environment['system'] == 'linux')
    is_python = str(script).endswith('.py')
    xvfb_cmd = []
    if use_xvfb:
      xvfb_cmd = [
        '/usr/bin/xvfb-run',
        '-a',
        '--server-args=-screen 0 1024x768x24']
      if is_python:
        xvfb_cmd += ['python', '-u']

    if isolate_hash:
      with self.m.step.nest('trigger shards for %s' % step_name):
        cpu = 'arm64' if environment['arch'] == 'arm64' else 'x86-64'
        # Android bots don't have a "cpu" dimension
        cpu = None if environment['system'] == 'android' else cpu
        tasks.append({
            'shards': self.shard(step_name, isolate_hash,
                                  xvfb_cmd + [script] + args,
                                  num_shards=shards,
                                  last_shard_is_local=local_shard,
                                  cipd_packages=cipd_packages,
                                  ignore_failure=ignore_failure,
                                  cpu=cpu,
                                  os=environment['system']),
            'args': args,
            'environment': environment,
            'step_name': step_name})
      if local_shard:
        args = args + [
          '--shards=%s' % shards,
          '--shard=%s' % shards,
        ]
        step_name = '%s_shard_%s' % (step_name, shards)
      else:
        return # Shards have been triggered, no local shard to run.

    if self._is_test_py_step(script):
      args = args + [
          '--output_directory',
          self.m.raw_io.output_dir(),
      ]

    cmd = self.m.path['checkout'].join(*script.split('/'))
    if is_python and not use_xvfb:
      self.m.python(step_name, cmd, args=args, ok_ret=ok_ret)
    else:
      self.m.step(step_name, xvfb_cmd + [cmd] + args, ok_ret=ok_ret)


class StepResults:
  def __init__(self, step_name, m, commit):
    self.step_name = step_name
    self.logs = ''
    self.results = ''
    self.runs = ''
    self.args = None
    self.environment = None
    self.commit = commit
    self.builder_name = str(m.buildbucket.builder_name)
    self.build_number = str(m.buildbucket.build.number)


  TEMPLATE = (',"commit_time":%s,"commit_hash":"%s",' +
      '"build_number":%s,"builder_name":"%s","bot_name":"%s"}\n')


  def add_results(self, bot_name, results_str):
    extra = self.TEMPLATE % (str(self.commit['commit_time']),
        str(self.commit['commit_hash']), self.build_number,
        self.builder_name, bot_name)
    all_matches = re.finditer(r'(^{.*)(?:})', results_str, flags=re.MULTILINE)
    all_chunks = (chunk for match in all_matches for chunk in (match.group(1), extra))
    self.results += ''.join(all_chunks)


  def add_run(self, bot_name, run_json):
    run = json.loads(run_json)
    run['commit_time'] = self.commit['commit_time']
    run['commit_hash'] = self.commit['commit_hash']
    run['builder_name'] = self.builder_name
    run['bot_name'] = bot_name
    self.runs += json.dumps(run) + '\n'


  def merge(self, other):
    self.logs += other.logs
    self.results += other.results
    self.runs += other.runs
    # Environment and Args are the same for all shards
    self.args = self.args or other.args
    self.environment = self.environment or other.environment
