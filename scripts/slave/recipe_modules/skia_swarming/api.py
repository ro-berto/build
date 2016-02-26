# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from recipe_engine import recipe_api


class SkiaSwarmingApi(recipe_api.RecipeApi):
  """Provides steps to run Skia tasks on swarming bots."""

  @property
  def swarming_temp_dir(self):
    """Path where artifacts like isolate file and json output will be stored."""
    return self.m.path['slave_build'].join('swarming_temp_dir')

  @property
  def tasks_output_dir(self):
    """Directory where the outputs of the swarming tasks will be stored."""
    return self.swarming_temp_dir.join('outputs')

  # TODO(rmistry): Remove once the Go binaries are moved to recipes or buildbot.
  def setup_go_isolate(self, luci_go_dir):
    """Generates and puts in place the isolate Go binary."""
    self.m.step('download luci-go linux',
                ['download_from_google_storage', '--no_resume',
                 '--platform=linux*', '--no_auth', '--bucket', 'chromium-luci',
                 '-d', luci_go_dir.join('linux64')])
    self.m.step('download luci-go mac',
                ['download_from_google_storage', '--no_resume',
                 '--platform=darwin', '--no_auth', '--bucket', 'chromium-luci',
                 '-d', luci_go_dir.join('mac64')])
    self.m.step('download luci-go win',
                ['download_from_google_storage', '--no_resume',
                 '--platform=win32', '--no_auth', '--bucket', 'chromium-luci',
                 '-d', luci_go_dir.join('win64')])
    # Copy binaries to the expected location.
    dest = self.m.path['slave_build'].join('luci-go')
    self.m.file.rmtree('Go binary dir', dest)
    self.m.file.copytree('Copy Go binary',
                         source=luci_go_dir,
                         dest=dest)

  def create_isolated_gen_json(self, isolate_path, base_dir, os_type,
                               task_name, extra_variables, blacklist=None):
    """Creates an isolated.gen.json file (used by the isolate recipe module).

    Args:
      isolate_path: path obj. Path to the isolate file.
      base_dir: path obj. Dir that is the base of all paths in the isolate file.
      os_type: str. The OS type to use when archiving the isolate file.
          Eg: linux.
      task_name: str. The isolated.gen.json file will be suffixed by this str.
      extra_variables: dict of str to str. The extra vars to pass to isolate.
          Eg: {'SLAVE_NUM': '1', 'MASTER': 'ChromiumPerfFYI'}
      blacklist: list of regular expressions indicating which files/directories
          not to archive.
    """
    self.m.file.makedirs('swarming tmp dir', self.swarming_temp_dir)
    isolated_path = self.swarming_temp_dir.join(
        'skia-task-%s.isolated' % task_name)
    isolate_args = [
      '--isolate', isolate_path,
      '--isolated', isolated_path,
      '--config-variable', 'OS', os_type,
    ]
    if blacklist:
      for b in blacklist:
        isolate_args.extend(['--blacklist', b])
    for k, v in extra_variables.iteritems():
      isolate_args.extend(['--extra-variable', k, v])
    isolated_gen_dict = {
      'version': 1,
      'dir': base_dir,
      'args': isolate_args,
    }
    isolated_gen_json = self.swarming_temp_dir.join(
        '%s.isolated.gen.json' % task_name)
    self.m.file.write(
        'Write %s.isolated.gen.json' % task_name,
        isolated_gen_json,
        self.m.json.dumps(isolated_gen_dict, indent=4),
    )

  def batcharchive(self, targets):
    """Calls batcharchive on the skia.isolated.gen.json file.

    Args:
      targets: list of str. The suffixes of the isolated.gen.json files to
               archive.
    """
    self.m.isolate.isolate_tests(
        verbose=True,  # To avoid no output timeouts.
        build_dir=self.swarming_temp_dir,
        targets=targets)

  def trigger_swarming_tasks(self, swarm_hashes, dimensions, idempotent=False):
    """Triggers swarming tasks using swarm hashes.

    Args:
      swarm_hashes: list of str. List of swarm hashes from the isolate server.
      dimensions: dict of str to str. The dimensions to run the task on.
                  Eg: {'os': 'Ubuntu', 'gpu': '10de', 'pool': 'Skia'}
      idempotent: whether or not to de-duplicate tasks.
    Returns:
      List of swarming.SwarmingTask instances.
    """
    swarming_tasks = []
    for task_name, swarm_hash in swarm_hashes:
      swarming_task = self.m.swarming.task(
          title=task_name,
          isolated_hash=swarm_hash,
          task_output_dir=self.tasks_output_dir.join(task_name))
      swarming_task.dimensions = dimensions
      swarming_task.idempotent = idempotent
      swarming_task.priority = 90
      swarming_task.expiration = 4*60*60
      swarming_tasks.append(swarming_task)
    self.m.swarming.trigger(swarming_tasks)
    return swarming_tasks

  def collect_swarming_task(self, swarming_task):
    """Collects the specified swarming task.

    Args:
      swarming_task: An instance of swarming.SwarmingTask.
    """
    return self.m.swarming.collect_task(swarming_task)

