# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

BLACKLIST = '^(out|xcodebuild)[/\\\\](Release|Debug|Product)\w*[/\\\\]generated_tests'
# TODO(athom): move to third_party when swarming_client.path has a setter
SWARMING_CLIENT_PATH = 'tools/swarming_client'
SWARMING_CLIENT_REPO = 'https://chromium.googlesource.com/infra/luci/client-py.git'
SWARMING_CLIENT_REV = '88229872dd17e71658fe96763feaa77915d8cbd6'

CHROME_PATH_ARGUMENT = {
  'linux': '--chrome=browsers/chrome/google-chrome',
  'mac': '--chrome=browsers/Google Chrome.app/Contents/MacOS/Google Chrome',
  'win7': '--chrome=browsers\\Chrome\\Application\\chrome.exe',
  'win10': '--chrome=browsers\\Chrome\\Application\\chrome.exe',
  'win': '--chrome=browsers\\Chrome\\Application\\chrome.exe'
}

class DartApi(recipe_api.RecipeApi):
  """Recipe module for code commonly used in dart recipes. Shouldn't be used elsewhere."""

  def checkout(self, clobber=False):
    """Checks out the dart code and prepares it for building."""
    self.m.gclient.set_config('dart')
    sdk = self.m.gclient.c.solutions[0]
    sdk.custom_deps['sdk/%s' % SWARMING_CLIENT_PATH] = \
        '%s@%s' % (SWARMING_CLIENT_REPO, SWARMING_CLIENT_REV)
    self.m.goma.ensure_goma()

    with self.m.context(cwd=self.m.path['cache'].join('builder'),
                        env={'GOMA_DIR':self.m.goma.goma_dir}):
      self.m.bot_update.ensure_checkout()
      with self.m.context(cwd=self.m.path['checkout']):
        if clobber:
          self.m.python('clobber',
                        self.m.path['checkout'].join('tools', 'clean_output_directory.py'))
      self.m.gclient.runhooks()

  def kill_tasks(self):
    """Kills leftover tasks from previous runs or steps."""
    self.m.python('kill processes',
               self.m.path['checkout'].join('tools', 'task_kill.py'),
               args=['--kill_browsers=True', '--kill_vsbuild=True'],
               ok_ret='any')

  def build(self, build_args=[], isolate=None, name='build dart'):
    """Builds dart using the specified build_args
       and optionally isolates the sdk for testing using the specified isolate.
       If an isolate is specified, it returns the hash of the isolated archive.
    """
    build_args = build_args + ['--no-start-goma', '-j200']
    with self.m.context(cwd=self.m.path['checkout']):
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
          raise self.m.step.StepFailure('Step "%s" timed out after 20 minutes' % name)
        except self.m.step.StepFailure as e:
          build_exit_status = e.retcode
          raise e
        finally:
          self.m.goma.stop(build_exit_status=build_exit_status)

        if isolate is not None:
          bots_path = self.m.path['checkout'].join('tools', 'bots')
          isolate_paths = self.m.file.glob_paths("find isolate files", bots_path, '*.isolate',
                                            test_data=[bots_path.join('a.isolate'),
                                                       bots_path.join('b.isolate')])
          for path in isolate_paths:
            self.m.file.copy('copy %s to sdk root' % path.pieces[-1],
                             path,
                             self.m.path['checkout'])

          step_result = self.m.python(
            'upload testing isolate',
            self.m.swarming_client.path.join('isolate.py'),
            args= ['archive',
                   '--ignore_broken_items', # TODO(athom) find a way to avoid that
                   '-Ihttps://isolateserver.appspot.com',
                   '-i%s' % self.m.path['checkout'].join('%s.isolate' % isolate),
                   '-s%s' % self.m.path['checkout'].join('%s.isolated' % isolate)],
            stdout=self.m.raw_io.output('out'))
          isolate_hash = step_result.stdout.strip()[:40]
          step_result.presentation.step_text = 'isolate hash: %s' % isolate_hash
          return isolate_hash

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
                 '-s%s' % self.m.path['checkout'].join('%s.isolated' % isolate_fileset)],
        stdout=self.m.raw_io.output('out'))
    isolate_hash = step_result.stdout.strip()[:40]
    step_result.presentation.step_text = 'swarming fileset hash: %s' % isolate_hash
    return isolate_hash

  def download_parent_isolate(self):
    self.m.path['checkout'] = self.m.path['cleanup']
    isolate_hash = self.m.properties['parent_fileset']
    fileset_name = self.m.properties['parent_fileset_name']
    with self.m.context(cwd=self.m.path['cleanup']):
      step_result = self.m.python(
        'downloading fileset %s' % fileset_name,
        self.m.swarming_client.path.join('isolateserver.py'),
        args= ['download',
                 '-Ihttps://isolateserver.appspot.com',
                 '-s%s' % isolate_hash,
                 '--target=.'],
        stdout=self.m.raw_io.output('out'))

  def shard(self, title, isolate_hash, test_args, os=None, cpu='x86-64',
      pool='dart.tests', num_shards=0, last_shard_is_local=False):
    """Runs test.py in the given isolate, sharded over several swarming tasks.
       Requires the 'shards' build property to be set to the number of tasks.
       Returns the created task(s), which are meant to be passed into collect().
    """
    if 'shards' in self.m.properties:
      num_shards = int(self.m.properties['shards'])
    assert(num_shards > 0)
    tasks = []
    if os is None:
      os = self.m.platform.name
    cipd_packages = []
    if '-rchrome' in test_args or '--runtime=chrome' in test_args:
      cipd_packages.append(('browsers',
                            'dart/browsers/chrome/${platform}',
                            'stable'))
    for shard in range(num_shards):
      # TODO(athom) collect all the triggers, and present as a single step
      if last_shard_is_local and shard == num_shards - 1: break
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
      self.m.swarming.trigger_task(task)
      tasks.append(task)
    return tasks

  def collect(self, tasks):
    """Collects the results of a sharded test run."""
    # TODO(mkroghj) remove when all swarming recipes has been converted to neo.
    with self.m.step.defer_results():
      # TODO(athom) collect all the output, and present as a single step
      num_shards = int(self.m.properties['shards'])
      for shard in range(num_shards):
        task = tasks[shard]
        path = self.m.path['cleanup'].join(str(shard))
        task.task_output_dir = self.m.raw_io.output_dir(leak_to=path, name="results")
        collect = self.m.swarming.collect_task(task)
        output_dir = self.m.step.active_result.raw_io.output_dir
        for filename in output_dir:
          if "result.log" in filename: # pragma: no cover
            contents = output_dir[filename]
            self.m.step.active_result.presentation.logs['result.log'] = [contents]

  def collect_all(self, deferred_tasks):
    """Collects the results of a sharded test run."""
    with self.m.step.defer_results():
      # TODO(athom) collect all the output, and present as a single step
      for index_step,deferred_task in enumerate(deferred_tasks):
        if deferred_task.is_ok:
          for index_task,task in enumerate(deferred_task.get_result()):
            path = self.m.path['cleanup'].join(str(index_step) + '_' + str(index_task))
            task.task_output_dir = self.m.raw_io.output_dir(leak_to=path, name="results")
            collect = self.m.swarming.collect_task(task)
            output_dir = self.m.step.active_result.raw_io.output_dir
            for filename in output_dir:
              if "result.log" in filename: # pragma: no cover
                contents = output_dir[filename]
                self.m.step.active_result.presentation.logs['result.log'] = [contents]

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
    builder = self.m.properties['buildername']
    if builder.endswith(('-be', '-try', '-stable', 'dev')):
      builder = builder[0:builder.rfind('-')]
    isolate_hashes = {}
    global_config = test_matrix['global']
    for config in test_matrix['configurations']:
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
      ['none', 'd8', 'jsshell', 'ie9', 'ie10', 'ie11', 'ff',
            'safari', 'chrome', 'safarimobilesim', 'drt', 'ie10', 'ie11'],
      None)
    environment = {'system': system,
                   'mode': mode,
                   'arch': arch}
    if runtime is not None:
      environment['runtime'] = runtime
      if runtime == 'chrome' or runtime == 'ff':
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
        environment_variables['BUILDBOT_BUILDERNAME'] = builder_name + "-%s" % channel
        with self.m.context(cwd=self.m.path['checkout'], env=environment_variables):
          with self.m.depot_tools.on_path():
            if is_build_step:
              if not self._has_specific_argument(args, ['-m', '--mode']):
                args = ['-m%s' % mode] + args
              if not self._has_specific_argument(args, ['-a', '--arch']):
                args = ['-a%s' % arch] + args
              self.build(name=step_name, build_args=args)
            elif is_trigger:
              self.run_trigger(step_name, step, isolate_hash)
            elif is_test_py_step:
              append_logs = test_py_index > 0
              self.run_test_py(step_name, append_logs, step,
                  isolate_hash, shards, local_shard, environment, tasks)
              if shards == 0 or local_shard:
                # Only count indexes that are not sharded, to help with adding
                # append-logs.
                test_py_index += 1
            else:
              self.run_script(step_name, script, args, isolate_hash, shards,
                  local_shard, environment, tasks)
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
    trigger_props['parent_buildername'] = self.m.properties['buildername']
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
      builder_tag = (x for x in build['build']['tags'] if x.startswith('builder:')).next()
      builder_name = builder_tag[len('builder:'):]
      self.m.step.active_result.presentation.links[builder_name] = build['build']['url']

  def run_test_py(self, step_name, append_logs, step, isolate_hash, shards,
      local_shard, environment, tasks):
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
    """
    args = step.get('arguments', [])
    test_args = ['--progress=buildbot',
                 '-v',
                 '--report',
                 '--time',
                 '--write-debug-log',
                 '--write-result-log',
                 '--write-test-outcome-log']
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
    # The --chrome flag is added here if the runtime for the bot is
    # chrome. This misses the case where there is a specific
    # argument -r or --runtime. It also misses the case where
    # a recipe calls run_script directly with a test.py command.
    # The download of the browser from CIPD should also be moved
    # here (perhaps checking if it is already done) so we catch
    # specific test steps with runtime chrome in a bot without that
    # global runtime.
    if environment.get('runtime') == 'chrome':
      args = args + [CHROME_PATH_ARGUMENT[environment['system']]]
    if 'exclude_tests' in step:
        args = args + ['--exclude_suite=' + ','.join(step['exclude_tests'])]
    if 'tests' in step:
      args = args + step['tests']
    with self.m.step.defer_results():
      self.run_script(step_name, 'tools/test.py', args, isolate_hash, shards,
          local_shard, environment, tasks)
      if shards == 0 or local_shard:
        self.read_result_file('read results of %s' % step_name, 'result.log')

  def run_script(self, step_name, script, args, isolate_hash, shards,
      local_shard, environment, tasks):
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
      * tasks ([task]) - placeholder to put all swarming tasks in
    """
    runtime = self._get_specific_argument(args, ['-r', '--runtime'])
    if runtime is None:
      runtime = environment.get('runtime', None)
    use_xvfb = (runtime in ['drt', 'chrome', 'ff'] and
                environment['system'] == 'linux')
    with self.m.step.defer_results():
      if use_xvfb:
        xvfb_cmd = [
          '/usr/bin/xvfb-run',
          '-a',
          '--server-args=-screen 0 1024x768x24']
        cmd = xvfb_cmd + ['python', '-u', script] + args
        if isolate_hash:
          tasks.append(self.shard(step_name, isolate_hash, cmd,
              num_shards=shards, last_shard_is_local=local_shard))
        else:
          self.m.step(step_name, cmd)
      else:
        if isolate_hash:
          tasks.append(self.shard(step_name, isolate_hash, [script] + args,
              num_shards=shards, last_shard_is_local=local_shard))
        elif '.py' in str(script):
          self.m.python(step_name, script, args=args)
        else:
          self.m.step(step_name, [script] + args)

      if local_shard:
        args = args + [
          '--shards=%s' % shards,
          '--shard=%s' % shards
        ]
        self.run_script("%s_shard_%s" % (step_name, shards), script,
            args, None, 0, False, environment, tasks)
