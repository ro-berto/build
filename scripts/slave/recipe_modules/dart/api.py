
from recipe_engine import recipe_api

class DartApi(recipe_api.RecipeApi):
  """Recipe module for code commonly used in dart recipies. Shouldn't be used elsewhere."""

  def checkout(self, channel=None, clobber=False):
    """Checks out the dart code and prepares it for building."""
    self.m.gclient.set_config('dart')
    if channel == 'try':
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

  def build(self, build_args=[], isolate=None):
    """Builds dart using the specified build_args
       and optionally isolates the sdk for testing using the specified isolate.
       If an isolate is specified, it returns the hash of the isolated archive.
    """
    with self.m.context(cwd=self.m.path['checkout'],
                     env_prefixes={'PATH':[self.m.depot_tools.root]}):
      self.kill_tasks()
      self.m.python('build dart',
                 self.m.path['checkout'].join('tools', 'build.py'),
                 args=build_args)
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

  def shard(self, title, isolate_hash, test_args, os=None, cpu='x86-64', pool='Dart.LUCI'):
    """Runs test.py in the given isolate, sharded over several swarming tasks.
       Requires the 'shards' build property to be set to the number of tasks.
       Returns the created task(s), which are meant to be passed into collect().
    """
    num_shards = int(self.m.properties['shards'])
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
      task.dimensions['cpu'] = cpu
      task.dimensions['pool'] = pool
      task.dimensions.pop('gpu', None)
      self.m.swarming.trigger_task(task)
      tasks.append(task)
    return tasks

  def collect(self, tasks):
    """Collects the results of a sharded test run."""
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
            self.m.step.active_result.presentation.logs['shard_%s_result.log' % (shard + 1)] = [contents]

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
    read_data = self.m.file.read_text(name,
                                      self.m.path['checkout'].join('logs',
                                                                  'result.log'),
                                      test_data)
    self.m.step.active_result.presentation.logs[log_name] = [read_data]

  def read_debug_log(self):
    """Reads the debug.log file"""
    if self.m.platform.name == 'win':
      self.m.step('debug log',
                  ['cmd.exe', '/c', 'type', '.debug.log'])
    else:
      self.m.step('debug log',
                  ['cat', '.debug.log'])
