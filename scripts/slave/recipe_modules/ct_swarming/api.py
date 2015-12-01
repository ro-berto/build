# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from recipe_engine import recipe_api


CT_GS_BUCKET = 'cluster-telemetry'


class CTSwarmingApi(recipe_api.RecipeApi):
  """Provides steps to run CT tasks on swarming bots."""

  @property
  def downloads_dir(self):
    """Path to where artifacts should be downloaded from Google Storage."""
    return self.m.path['checkout'].join('content', 'test', 'ct')

  @property
  def swarming_temp_dir(self):
    """Path where artifacts like isolate file and json output will be stored."""
    return self.m.path['tmp_base'].join('swarming_temp_dir')

  @property
  def tasks_output_dir(self):
    """Directory where the outputs of the swarming tasks will be stored."""
    return self.swarming_temp_dir.join('outputs')

  def checkout_dependencies(self):
    """Checks out all repositories required for CT to run on swarming bots."""
    # Checkout chromium and swarming.
    self.m.chromium.set_config('chromium')
    self.m.gclient.set_config('chromium')
    self.m.bot_update.ensure_checkout(force=True)
    self.m.swarming_client.checkout()
    # Ensure swarming_client is compatible with what recipes expect.
    self.m.swarming.check_client_version()

  def download_CT_binary(self, ct_binary_name):
    """Downloads the specified CT binary from GS into the downloads_dir."""
    binary_dest = self.downloads_dir.join(ct_binary_name)
    self.m.gsutil.download(
        name="download %s" % ct_binary_name,
        bucket=CT_GS_BUCKET,
        source='swarming/binaries/%s' % ct_binary_name,
        dest=binary_dest)
    # Set executable bit on the binary.
    self.m.python.inline(
        name='Set executable bit on %s' % ct_binary_name,
        program='''
import os
import stat

os.chmod('%s', os.stat('%s').st_mode | stat.S_IEXEC)
''' % (str(binary_dest), str(binary_dest))
    )

  def download_page_artifacts(self, page_type, slave_num):
    """Downloads all the artifacts needed to run benchmarks on a page.

    The artifacts are downloaded into subdirectories in the downloads_dir.

    Args:
      page_type: str. The CT page type. Eg: 1k, 10k.
      slave_num: int. The number of the slave used to determine which GS
                 directory to download from. Eg: for the top 1k, slave1 will
                 contain webpages 1-10, slave2 will contain 11-20.
    """
    # Download page sets.
    page_sets_dir = self.downloads_dir.join('slave%s' % slave_num, 'page_sets')
    self.m.file.makedirs('page_sets dir', page_sets_dir)
    self.m.gsutil.download(
        bucket=CT_GS_BUCKET,
        source='swarming/page_sets/%s/slave%s/*' % (page_type, slave_num),
        dest=page_sets_dir)

    # Download archives.
    wpr_dir = page_sets_dir.join('data')
    self.m.file.makedirs('WPR dir', wpr_dir)
    self.m.gsutil.download(
        bucket=CT_GS_BUCKET,
        source='swarming/webpage_archives/%s/slave%s/*' % (page_type,
                                                           slave_num),
        dest=wpr_dir)

  def download_skps(self, page_type, slave_num, skps_chromium_build):
    """Downloads SKPs corresponding to the specified page type, slave and build.

    The SKPs are downloaded into subdirectories in the downloads_dir.

    Args:
      page_type: str. The CT page type. Eg: 1k, 10k.
      slave_num: int. The number of the slave used to determine which GS
                 directory to download from. Eg: for the top 1k, slave1 will
                 contain SKPs from webpages 1-10, slave2 will contain 11-20.
      skps_chromium_build: str. The build the SKPs were captured from.
    """
    skps_dir = self.downloads_dir.join('slave%s' % slave_num, 'skps')
    self.m.file.makedirs('SKPs dir', skps_dir)
    full_source = 'gs://%s/skps/%s/%s/slave%s' % (
        CT_GS_BUCKET, page_type, skps_chromium_build, slave_num)
    self.m.gsutil(['-m', 'rsync', '-d', '-r', full_source, skps_dir])

  def create_isolated_gen_json(self, isolate_path, base_dir, os_type,
                               slave_num, extra_variables):
    """Creates an isolated.gen.json file.

    Args:
      isolate_path: path obj. Path to the isolate file.
      base_dir: path obj. Dir that is the base of all paths in the isolate file.
      os_type: str. The OS type to use when archiving the isolate file.
               Eg: linux.
      slave_num: int. The slave we want to create isolated.gen.json file for.
      extra_variables: dict of str to str. The extra vars to pass to isolate.
                      Eg: {'SLAVE_NUM': '1', 'MASTER': 'ChromiumPerfFYI'}

    Returns:
      Path to the isolated.gen.json file.
    """
    self.m.file.makedirs('swarming tmp dir', self.swarming_temp_dir)
    isolated_path = self.swarming_temp_dir.join(
        'ct-task-%s.isolated' % slave_num)
    isolate_args = [
      '--isolate', isolate_path,
      '--isolated', isolated_path,
      '--config-variable', 'OS', os_type,
    ]
    for k, v in extra_variables.iteritems():
      isolate_args.extend(['--extra-variable', k, v])
    isolated_gen_dict = {
      'version': 1,
      'dir': base_dir,
      'args': isolate_args,
    }
    isolated_gen_json = self.swarming_temp_dir.join(
        'slave%s.isolated.gen.json' % slave_num)
    self.m.file.write(
        'Write slave%s.isolated.gen.json' % slave_num,
        isolated_gen_json,
        self.m.json.dumps(isolated_gen_dict, indent=4),
    )

  def batcharchive(self, num_slaves):
    """Calls batcharchive on the specified isolated.gen.json files.

    Args:
      num_slaves: int. The number of slaves we will batcharchive
                  isolated.gen.json files for.
    """
    self.m.isolate.isolate_tests(
        build_dir=self.swarming_temp_dir,
        targets=['slave%s' % num for num in range(1, num_slaves+1)])

  def trigger_swarming_tasks(self, swarm_hashes, task_name_prefix, dimensions):
    """Triggers swarming tasks using swarm hashes.

    Args:
      swarm_hashes: list of str. List of swarm hashes from the isolate server.
      task_name_prefix: The prefix to use when creating task_name.
      dimensions: dict of str to str. The dimensions to run the task on.
                  Eg: {'os': 'Ubuntu', 'gpu': '10de'}
    Returns:
      List of swarming.SwarmingTask instances.
    """
    swarming_tasks = []
    for task_num, swarm_hash in enumerate(swarm_hashes):
      swarming_task = self.m.swarming.task(
          title='%s-%s' % (task_name_prefix, task_num+1),
          isolated_hash=swarm_hash,
          task_output_dir=self.tasks_output_dir.join('slave%s' % (task_num+1)))
      swarming_task.dimensions = dimensions
      swarming_task.priority = 90
      swarming_tasks.append(swarming_task)
    self.m.swarming.trigger(swarming_tasks)
    return swarming_tasks

  def collect_swarming_tasks(self, swarming_tasks):
    """Collects all swarming tasks triggered by this recipe.

    Args:
      swarming_tasks: list of swarming.SwarmingTask instances.
    """
    return self.m.swarming.collect(swarming_tasks)
