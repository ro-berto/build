# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

BLACKLIST = (
    '^(out|xcodebuild)[/\\\\](Release|Debug|Product)\w*[/\\\\]generated_tests')
# TODO(athom): move to third_party when swarming_client.path has a setter
SWARMING_CLIENT_PATH = 'tools/swarming_client'
SWARMING_CLIENT_REPO = (
    'https://chromium.googlesource.com/infra/luci/client-py.git')
SWARMING_CLIENT_REV = '88229872dd17e71658fe96763feaa77915d8cbd6'

CHROME_PATH_ARGUMENT = {
  'linux': '--chrome=browsers/chrome/google-chrome',
  'mac': '--chrome=browsers/Google Chrome.app/Contents/MacOS/Google Chrome',
  'win7': '--chrome=browsers\\Chrome\\Application\\chrome.exe',
  'win10': '--chrome=browsers\\Chrome\\Application\\chrome.exe',
  'win': '--chrome=browsers\\Chrome\\Application\\chrome.exe'
}

FIREFOX_PATH_ARGUMENT = {
  'linux': '--firefox=browsers/firefox/firefox',
  'mac': '--firefox=browsers/Firefox.app/Contents/MacOS/firefox',
  'win7': '--firefox=browsers\\firefox\\firefox.exe',
  'win10': '--firefox=browsers\\firefox\\firefox.exe',
  'win': '--firefox=browsers\\firefox\\firefox.exe'
}

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

    with self.m.context(cwd=self.m.path['cache'].join('builder'),
                        env={'GOMA_DIR':self.m.goma.goma_dir}):
      try:
        self.m.bot_update.ensure_checkout(with_branch_heads=True,
                                          with_tags=True)
      except self.m.step.InfraFailure:
        # TODO(athom): Remove this retry once root cause is fixed
        self.m.bot_update.ensure_checkout(with_branch_heads=True,
                                          with_tags=True)

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

  def kill_tasks(self):
    """Kills leftover tasks from previous runs or steps."""
    self.m.python('kill processes',
               self.m.path['checkout'].join('tools', 'task_kill.py'),
               args=['--kill_browsers=True', '--kill_vsbuild=True'],
               ok_ret='any')

  def dart_executable(self):
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
            cipd_packages=None):
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
      task = self.m.swarming.task("%s_shard_%s" % (title, (shard + 1)),
                               isolate_hash,
                               cipd_packages=cipd_packages,
                               raw_cmd=test_args +
                                 ['--shards=%s' % num_shards,
                                  '--shard=%s' % (shard + 1),
                                  '--output_directory=${ISOLATED_OUTDIR}'])
      os_names = {
        'win': 'Windows',
        'linux': 'Linux',
        'mac': 'Mac'
      }
      task.dimensions['os'] = os_names.get(os, os)
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

  def collect_all(self, deferred_tasks):
    """Collects the results of a sharded test run."""
    with self.m.step.defer_results():
      # TODO(athom) collect all the output, and present as a single step
      for index_step,info in enumerate(deferred_tasks):
        if info['shards'].is_ok:
          shards = info['shards'].get_result()
          results = ''
          run = ''
          output_dir = None
          for index_task,task in enumerate(shards):
            path = self.m.path['cleanup'].join(
                str(index_step) + '_' + str(index_task))
            task.task_output_dir = self.m.raw_io.output_dir(
                leak_to=path, name="results")
            self.m.swarming.collect_task(task)
            output_dir = self.m.step.active_result.raw_io.output_dir
            for filepath in output_dir:
              filename = filepath.split('/')[-1]  # pragma: no cover
              if filename in (
                  "result.log", "results.json", "run.json"): # pragma: no cover
                contents = output_dir[filepath]
                self.m.step.active_result.presentation.logs[
                    filename] = [contents]
                if filename == 'results.json':
                  results += contents
                  self.m.step.active_result.presentation.logs[
                      'accumulated_results'] = [results]
                if filename == 'run.json':
                  run = contents
          results_path = self.m.path['checkout'].join('logs', 'results.json')
          self.m.file.write_text("Write results file", results_path, results)
          run_path = self.m.path['checkout'].join('logs', 'run.json')
          self.m.file.write_text("Write run file", run_path, run)
          step_name = 'sharded %s' % info['step_name']
          self.download_results(step_name)
          self.deflake_results(step_name, info['args'], info['environment'])
          self.upload_results(step_name)
          self.present_results(step_name)

  def download_results(self,  name):
    builder = self.m.buildbucket.builder_name
    if builder.endswith(('-try', '-stable', '-dev')):
      return # pragma: no cover
    results_path = self.m.path['checkout'].join('LATEST')
    self.m.file.ensure_directory('ensure LATEST dir', results_path)
    for filename in ['results.json', 'flaky.json', 'approved_results.json']:
      self.m.file.write_text(
        'ensure %s exists' % filename, results_path.join(filename), '')
      self.m.gsutil.download(
        'dart-test-results',
        '/'.join(['results', builder, 'LATEST', name, filename]),
        results_path,
        name='download previous %s' % filename,
        ok_ret='any')

  def deflake_results(self, step_name, args, environment):
    step_result = self.m.step('list tests that should be deflaked',
                [self.dart_executable(),
                 'tools/bots/compare_results.dart',
                 '--flakiness-data',
                 'LATEST/flaky.json',
                 '--changed',
                 '--passing',
                 '--failing',
                 '--count',
                 '100',
                'LATEST/results.json',
                 'logs/results.json'],
                stdout=self.m.raw_io.output_text(
                    leak_to=self.m.path['checkout']
                    .join('logs','deflake.list')),
                ok_ret='any')
    contents = step_result.stdout
    self.m.step.active_result.presentation.logs['deflake_list'] = [contents]
    self.run_script(
        step_name + ' deflaking', 'tools/test.py',
        args + ['--repeat=5', '--test-list', 'logs/deflake.list',
                '--output_directory', 'deflaking_logs'],
        None, None,
        False, environment, None, ok_ret='any')
    self.m.step('Update flakiness information',
                [self.dart_executable(),
                 'tools/bots/update_flakiness.dart',
                 '-i',
                 'LATEST/flaky.json',
                 '-o',
                 'deflaking_logs/flaky.json',
                'logs/results.json',
                 'deflaking_logs/results.json'], ok_ret='any')

  def upload_results(self,  name):
    commit_hash = self.m.buildbucket.gitiles_commit.id
    commit_time = self.m.git.get_timestamp(test_data='1234567')
    self.m.step('Add commit hash to run.json',
                [self.dart_executable(),
                 'tools/bots/add_fields.dart',
                 'logs/run.json',
                 commit_time,
                 commit_hash])

    builder = self.m.buildbucket.builder_name
    build_number = self.m.buildbucket.build.number
    self.m.file.move('Rename deflaking_results',
      self.m.path['checkout'].join('deflaking_logs', 'results.json'),
      self.m.path['checkout'].join('deflaking_logs', 'deflaking_results.json'))

    for filepath in [('logs','results.json'),
                 ('logs', 'run.json'),
                 ('deflaking_logs', 'flaky.json'),
                 ('deflaking_logs', 'deflaking_results.json')]:
      results_path = self.m.path['checkout'].join(*filepath)
      filename = filepath[-1]
      self.m.gsutil.upload(
        results_path,
        'dart-test-results',
        '/'.join(['results', builder, str(build_number), name, filename]),
        name='upload %s %s' % filepath, ok_ret='all')
      self.m.gsutil.copy(
        'dart-test-results',
        '/'.join(['results', builder, str(build_number), name, filename]),
        'dart-test-results',
        '/'.join(['results', builder, 'LATEST', name, filename]),
        name='copy %s %s to LATEST' % filepath, ok_ret='all')
      self.m.gsutil.copy(
        'dart-test-results',
        '/'.join(['results', builder, 'LATEST', name, 'approved_results.json']),
        'dart-test-results',
        '/'.join(['results', builder, str(build_number), name,
                  'approved_results.json']),
        ok_ret='all')

  def present_results(self, step_name):
        self.m.step('deflaked status of %s' % step_name,
                    [self.dart_executable(),
                     'tools/bots/compare_results.dart',
                     '--flakiness-data',
                     'deflaking_logs/flaky.json',
                     '--judgement',
                     '--human',
                     '--verbose',
                     '--changed',
                     '--flaky',
                     '--failing',
                     '--passing',
                     'LATEST/results.json',
                     'logs/results.json'],
                    ok_ret='any')

  def read_result_file(self,  name, log_name, test_data=''):
    """Reads the result.log file
    Args:
      * name (str) - Name of step
      * log_name (str) - Name of log
      * test_data (str) - Some default data for this step to return when running
        under simulation.
    Returns (str) - The content of the file.
    Raises file.Error
    """
    result_log_path = self.m.path['checkout'].join('logs', 'result.log')
    try:
      read_data = self.m.file.read_text(
        name, result_log_path, test_data)
      self.m.step.active_result.presentation.logs[log_name] = [read_data]
      self.m.file.remove("delete result.log", result_log_path)
    except self.m.file.Error: # pragma: no cover
      pass

  def read_debug_log(self):
    """Reads the debug.log file"""
    if self.m.platform.name == 'win':
      self.m.step('debug log',
                  ['cmd.exe', '/c', 'type', '.debug.log'],
                  ok_ret='any')
    else:
      self.m.step('debug log',
                  ['cat', '.debug.log'],
                  ok_ret='any')

  def test(self, test_data):
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
    builder = self.m.properties["buildername"]
    if builder.endswith(('-be', '-try', '-stable', 'dev')):
      builder = builder[0:builder.rfind('-')]
    isolate_hashes = {}
    global_config = test_matrix['global']
    for config in test_matrix['builder_configurations']:
      if builder in config['builders']:
        self._write_file_sets(test_matrix['filesets'])
        self._run_steps(config, isolate_hashes, builder, global_config)
        return
    raise self.m.step.StepFailure(
        'Error, could not find builder by name %s in test-matrix' % builder)

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
          arguments[index] = replacement;
          return None

  def _run_steps(self, config, isolate_hashes, builder_name, global_config):
    """Executes all steps from a json test-matrix builder entry"""
    # Find information from the builder name. It should be in the form
    # <info>-<os>-<mode>-<arch>-<runtime> or <info>-<os>-<mode>-<arch>.
    builder_fragments = builder_name.split('-')
    system = self._get_option(
      builder_fragments,
      ['linux', 'mac', 'win7', 'win8', 'win10', 'win'],
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
    environment = {'system': system,
                   'mode': mode,
                   'arch': arch}
    if runtime is not None:
      if runtime == 'ff':
        runtime = 'firefox' # pragma: no cover
      environment['runtime'] = runtime
      if runtime == 'chrome' or runtime == 'firefox':
        self._download_browser(runtime, global_config[runtime])
    channel = 'try'
    if 'branch' in self.m.properties:
      channels = {
        "refs/heads/master": "be",
        "refs/heads/stable": "stable",
        "refs/heads/dev": "dev"
      }
      channel = channels.get(self.m.properties['branch'], 'try');
    test_py_path = 'tools/test.py'
    build_py_path = 'tools/build.py'
    # Indexes the number of test.py steps.
    test_py_index = 0;
    tasks = []
    with self.m.step.defer_results():
      for index,step in enumerate(config['steps']):
        step_name = step['name']
        # If script is not defined, use test.py.
        script = step.get('script', test_py_path)
        args = step.get('arguments', [])
        is_build_step = script.endswith(build_py_path)
        is_trigger = 'trigger' in step
        is_test_py_step = script.endswith(test_py_path)

        if self.m.platform.name == 'mac' and script.startswith('out/'):
          script = script.replace('out/', 'xcodebuild/', 1)

        is_dart = script.endswith('/dart')
        if is_dart:
          executable_suffix = '.exe' if self.m.platform.name == 'win' else ''
          script += executable_suffix

        script = self.m.path['checkout'].join(*script.split('/'))
        isolate_hash = None
        shards = step.get('shards', 0)
        local_shard = shards > 0 and index == len(config['steps']) - 1
        if 'fileset' in step:
          # We build isolates here, every time we see fileset, to wait for the
          # building of Dart, which may be included in the fileset.
          self._build_isolates(config, isolate_hashes)
          isolate_hash = isolate_hashes[step['fileset']]

        environment_variables = step.get('environment', {})
        environment_variables['BUILDBOT_BUILDERNAME'] = (
            builder_name + "-%s" % channel)
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
            elif is_test_py_step:
              append_logs = test_py_index > 0
              self.run_test_py(step_name, append_logs, step,
                               isolate_hash, shards, local_shard,
                               environment, tasks, global_config)
              if shards == 0 or local_shard:
                # Only count indexes that are not sharded, to help with adding
                # append-logs.
                test_py_index += 1
            else:
              self.run_script(step_name, script, args, isolate_hash, shards,
                  local_shard, environment, tasks)
      with self.m.context(cwd=self.m.path['checkout']):
        self.collect_all(tasks)

  def _copy_property(self, src, dest, key):
    if key in src:
      dest[key] = src[key]

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

  def run_trigger(self, step_name, step, isolate_hash):
    trigger_props = {}
    self._copy_property(self.m.properties, trigger_props, 'git_revision')
    self._copy_property(self.m.properties, trigger_props, 'revision')
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

  def run_test_py(self, step_name, append_logs, step, isolate_hash, shards,
                  local_shard, environment, tasks, global_config):
    """Runs test.py with default arguments, based on configuration from.
    Args:
      * step_name (str) - Name of the step
      * append_logs (bool) - Add append_log to arguments
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
                 '--write-result-log',
                 '--write-test-outcome-log']
    template = self._get_specific_argument(args, ['-n'])
    if template is not None:
      for term in ['runtime', 'system', 'mode', 'arch']:
        if '${%s}' % term in template:
          template = template.replace('${%s}' % term, environment.get(term, ''))
      self._replace_specific_argument(args, ['-n'], "-n%s" % template)
    if not self._has_specific_argument(args, ['-m', '--mode']):
      test_args = ['-m%s' % environment['mode']] + test_args
    if not self._has_specific_argument(args, ['-a', '--arch']):
      test_args = ['-a%s' % environment['arch']] + test_args
    if 'runtime' in environment and not self._has_specific_argument(
        args, ['-r', '--runtime']):
      test_args = test_args + ['-r%s' % environment['runtime']]
    args = test_args + args
    if append_logs:
      args = args + ['--append_logs']
    if environment['system'] in ['win7', 'win8', 'win10']:
      args = args + ['--builder-tag=%s' % environment['system']]
    if environment['system'] in ['linux']:
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
    if any(arg in ['-rchrome', '--runtime=chrome'] for arg in args):
      version_tag = 'version:%s' % global_config['chrome']
      cipd_packages.append(('browsers',
                            'dart/browsers/chrome/${platform}',
                            version_tag))
      args = args + [CHROME_PATH_ARGUMENT[environment['system']]]
    if any(arg in ['-rfirefox', '--runtime=firefox'] for arg in args):
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
      self.run_script(step_name, 'tools/test.py', args, isolate_hash, shards,
                      local_shard, environment, tasks,
                      cipd_packages=cipd_packages)
      if shards == 0 or local_shard:
        self.read_result_file('read results of %s' % step_name, 'result.log')

      # The new deflaking workflow is being developed and currently runs on the
      # local builder, not shards, and only on the master CI, not CQ.
      run_new_workflow = ((shards == 0 or local_shard) and
                          not self.m.buildbucket.builder_name.endswith(
                              ('-try', '-stable', '-dev')))
      if run_new_workflow:
        self.download_results(step_name)
        self.deflake_results(step_name, args, environment)
        self.upload_results(step_name)
        self.present_results(step_name)

  def run_script(self, step_name, script, args, isolate_hash, shards,
                 local_shard, environment, tasks,
                 cipd_packages=None, ok_ret=None):
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
      * ok_ret(str or [int]) - optional accepted exit codes passed to
        non-sharded script runs.
    """
    if not cipd_packages: # pragma: no cover
      cipd_packages = []
    runtime = self._get_specific_argument(args, ['-r', '--runtime'])
    if runtime is None:
      runtime = environment.get('runtime', None)
    use_xvfb = (runtime in ['chrome', 'firefox'] and
                environment['system'] == 'linux')
    is_python = str(script).endswith('.py')

    with self.m.step.defer_results():
      if use_xvfb:
        xvfb_cmd = [
          '/usr/bin/xvfb-run',
          '-a',
          '--server-args=-screen 0 1024x768x24']
        if is_python:
          xvfb_cmd += ['python', '-u']
        cmd = xvfb_cmd + [script] + args
        if isolate_hash:
          tasks.append({
              'shards': self.shard(step_name, isolate_hash, cmd,
                                   num_shards=shards,
                                   last_shard_is_local=local_shard,
                                   cipd_packages=cipd_packages),
              'args': args,
              'environment': environment,
              'step_name': step_name})
        else:
          self.m.step(step_name, cmd, ok_ret=ok_ret)
      else:
        if isolate_hash:
          tasks.append({
              'shards': self.shard(step_name, isolate_hash, [script] + args,
                                   num_shards=shards,
                                   last_shard_is_local=local_shard,
                                   cipd_packages=cipd_packages),
              'args': args,
              'environment': environment,
              'step_name': step_name})
        elif is_python:
          self.m.python(step_name, script, args=args, ok_ret=ok_ret)
        else:
          self.m.step(step_name, [script] + args, ok_ret=ok_ret)

      if local_shard:
        args = args + [
          '--shards=%s' % shards,
          '--shard=%s' % shards
        ]
        self.run_script("%s_shard_%s" % (step_name, shards), script,
                        args, None, 0, False, environment, None,
                        ok_ret=ok_ret)
