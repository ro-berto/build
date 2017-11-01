
from recipe_engine import recipe_api

class DartApi(recipe_api.RecipeApi):
  """Recipe module for code commonly used in dart recipes. Shouldn't be used elsewhere."""

  def checkout(self, channel=None, clobber=False):
    """Checks out the dart code and prepares it for building."""
    self.m.gclient.set_config('dart')
    # TODO(athom): Remove channel parameter from this function and fix URL
    # in gclient 'dart' config, remove line below.
    self.m.gclient.c.solutions[0].url = 'https://dart.googlesource.com/sdk.git'

    with self.m.context(cwd=self.m.path['cache'].join('builder')):
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
    with self.m.context(cwd=self.m.path['checkout'],
                     env_prefixes={'PATH':[self.m.depot_tools.root]}):
      self.kill_tasks()
      try:
        self.m.python(name,
                   self.m.path['checkout'].join('tools', 'build.py'),
                   args=build_args,
                   timeout=20 * 60)
      except self.m.step.StepTimeout as e:
        raise self.m.step.StepFailure('Step "%s" timed out after 20 minutes' % name)

      if isolate is not None:
        self.m.swarming_client.checkout(
          revision='5c8043e54541c3cee7ea255e0416020f2e3a5904')
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
    self.m.swarming_client.checkout(
      revision='5c8043e54541c3cee7ea255e0416020f2e3a5904')
    step_result = self.m.python(
        'upload testing fileset %s' % isolate_fileset,
        self.m.swarming_client.path.join('isolate.py'),
        args= ['archive',
                 '--ignore_broken_items', # TODO(athom) find a way to avoid that
                 '-Ihttps://isolateserver.appspot.com',
                 '-i%s' % self.m.path['checkout'].join('%s' % isolate_fileset),
                 '-s%s' % self.m.path['checkout'].join('%s.isolated' % isolate_fileset)],
        stdout=self.m.raw_io.output('out'))
    isolate_hash = step_result.stdout.strip()[:40]
    step_result.presentation.step_text = 'swarming fileset hash: %s' % isolate_hash
    return isolate_hash

  def shard(self, title, isolate_hash, test_args, os=None, cpu='x86-64', pool='Dart.LUCI',
      num_shards=0):
    """Runs test.py in the given isolate, sharded over several swarming tasks.
       Requires the 'shards' build property to be set to the number of tasks.
       Returns the created task(s), which are meant to be passed into collect().
    """
    if 'shards' in self.m.properties:
      num_shards = int(self.m.properties['shards'])
    assert(num_shards > 0)
    tasks = []
    for shard in range(num_shards):
      # TODO(athom) collect all the triggers, and present as a single step
      task = self.m.swarming.task("%s_shard_%s" % (title, (shard + 1)),
                               isolate_hash,
                               extra_args= test_args +
                                 ['--shards=%s' % num_shards,
                                  '--shard=%s' % (shard + 1),
                                  '--output_directory=${ISOLATED_OUTDIR}'])
      if os is None:
        os = self.m.platform.name
      os_names = {
        'win': 'Windows',
        'linux': 'Linux',
        'mac': 'Mac'
      }
      if os in os_names:
        os = os_names[os]
      task.dimensions['os'] = os
      # TODO(athom) remove this once all linux machines have chrome
      if os == 'Linux' and not '-rd8' in test_args:
        task.dimensions['kvm'] = '0'
      task.dimensions['cpu'] = cpu
      task.dimensions['pool'] = pool
      task.dimensions.pop('gpu', None)
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
    isolate_hashes = {}
    for config in test_matrix['configurations']:
      if builder in config['builders']:
        self._write_file_sets(test_matrix['filesets'])
        self._run_steps(config, isolate_hashes)
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

  def _has_specific_argument(self, arguments, options):
    for arg in arguments:
      for option in options:
        if arg.startswith(option):
          return True
    return False

  def _run_steps(self, config, isolate_hashes):
    """Executes all steps from a json test-matrix builder entry"""
    # Find information from the builder name. It should be in the form
    # <info>-<os>-<mode>-<arch>-<runtime> or <info>-<os>-<mode>-<arch>.
    builder_name = self.m.properties['buildername']
    builder_fragments = builder_name.split('-')
    system = self._get_option(
      builder_fragments,
      ['linux', 'mac', 'win7', 'win8', 'win10'],
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
    test_py_path = 'tools/test.py'
    build_py_path = 'tools/build.py'
    # Indexes the number of test.py steps.
    test_py_index = 0;
    tasks = []
    with self.m.step.defer_results():
      for step in config['steps']:
        step_name = step['name']
        # If script is not defined, use test.py.
        script = step.get('script', test_py_path)
        args = step.get('arguments', [])
        is_build_step = script.endswith(build_py_path)
        is_test_py_step = script.endswith(test_py_path)
        script = self.m.path['checkout'].join(*script.split('/'))
        isolate_hash = None
        shards = 0
        if 'fileset' in step:
          # We build isolates here, every time we see fileset, to wait for the
          # building of Dart, which may be included in the fileset.
          self._build_isolates(config, isolate_hashes)
          isolate_hash = isolate_hashes[step['fileset']]
          shards = step['shards']
        channel = 'try'
        if 'branch' in self.m.properties:
          channels = {
            "refs/heads/master": "be",
            "refs/heads/stable": "stable",
            "refs/heads/dev": "dev"
          }
          channel = channels.get(self.m.properties['branch'], 'try');
        environment_variables = step.get('environment', {})
        environment_variables['BUILDBOT_BUILDERNAME'] = builder_name + "-%s" % channel
        with self.m.context(cwd=self.m.path['checkout'],
                            env=environment_variables,
                            env_prefixes={'PATH':[self.m.depot_tools.root]}):
          if is_build_step:
            if not self._has_specific_argument(args, ['-m', '--mode']):
              args = ['-m%s' % mode] + args
            if not self._has_specific_argument(args, ['-a', '--arch']):
              args = ['-a%s' % arch] + args
            self.build(name=step_name, build_args=args)
          elif is_test_py_step:
            self.run_test_py(step_name, args, test_py_index, step, isolate_hash,
                shards, environment, tasks)
            if shards == 0:
              # Only count indexes that are not sharded, to help with adding append-logs.
              test_py_index += 1
          else:
            self.run_script(step_name, script, args, isolate_hash, shards,
                environment, tasks)
      self.collect_all(tasks)

  def run_test_py(self, step_name, args, index, step, isolate_hash, shards,
      environment, tasks):
    """Runs test.py with default arguments, based on configuration from.
    Args:
      * step_name (str) - Name of the step
      * args ([str]) - Additional arguments to test.py
      * index (int) - Index of test.py calls. Used to append logs
      * step (dict) - Test-matrix step
      * environment (dict) - Environment with runtime, arch, system etc
      * tasks ([task]) - placeholder to put all swarming tasks in
    """

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
    if index > 0:
      args = args + ['--append_logs']
    if environment['system'] in ['win7', 'win8', 'win10']:
      args = args + ['--builder-tag=%s' % environment['system']]
    if 'exclude_tests' in step:
        args = args + ['--exclude_suite=' + ','.join(step['exclude_tests'])]
    if 'tests' in step:
      args = args + step['tests']
    self.run_script(step_name, 'tools/test.py', args, isolate_hash, shards, environment, tasks)
    if shards == 0:
      self.read_result_file('read results of %s' % step_name, 'result.log')

  def run_script(self, step_name, script, args, isolate_hash, shards, environment, tasks):
    """Runs a specific script with current working directory to be checkout. If
    the runtime (passed in environment) is a browser, and the system is linux,
    xvfb is used. If an isolate_hash is passed in, it will swarm the command.
    Args:
      * step_name (str) - Name of the step
      * script (str) - The script to invoke
      * args ([str]) - Additional arguments to test.py
      * isolate_hash (str) - The isolate hash if the script should be swarmed
      * environment (dict) - Environment with runtime, arch, system etc
      * tasks ([task]) - placeholder to put all swarming tasks in
    """
    runtime = environment.get('runtime', None)
    use_xvfb = (runtime in ['drt', 'chrome', 'ff'] and
                environment['system'] == 'linux')
    with self.m.step.defer_results():
      if use_xvfb:
        xvfb_cmd = ['/usr/bin/xvfb-run', '-a', '--server-args=-screen 0 1024x768x24']
        cmd = xvfb_cmd + ['python', '-u', script] + args
        if isolate_hash:
          tasks.append(self.shard(step_name, isolate_hash, cmd, num_shards=shards))
        else:
          self.m.step(step_name, cmd)
      else:
        if isolate_hash:
          tasks.append(self.shard(step_name, isolate_hash, [script] + args, num_shards=shards))
        elif '.py' in str(script):
          self.m.python(step_name, script, args=args)
        else:
          self.m.step(step_name, [script] + args)
