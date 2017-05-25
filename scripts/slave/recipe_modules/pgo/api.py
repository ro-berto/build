# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class PGOApi(recipe_api.RecipeApi):
  """
  PGOApi encapsulate the various step involved in a PGO build.
  """

  def __init__(self, **kwargs):
    super(PGOApi, self).__init__(**kwargs)

  def _compile_instrumented_image(self, bot_config, mb_config_path=None):
    """
    Generates the instrumented version of the binaries.
    """
    self.m.chromium.set_config(bot_config['chromium_config_instrument'],
                               **bot_config.get('chromium_config_kwargs'))
    self.m.chromium.runhooks(name='Runhooks: Instrumentation phase.')
    self.m.chromium.run_mb(
        self.m.properties['mastername'],
        self.m.properties['buildername'],
        mb_config_path=mb_config_path,
        use_goma=False,
        phase=1)
    # Remove the profile files from the previous builds.
    self.m.file.rmwildcard('*.pg[cd]', str(self.m.chromium.output_dir))
    self.m.chromium.compile(name='Compile: Instrumentation phase.')

  def _run_pgo_benchmarks(self):
    """
    Run a suite of telemetry benchmarks to generate some profiling data.
    """
    target_arch = self.m.chromium.c.gyp_env.GYP_DEFINES['target_arch']
    target_cpu = {'ia32': 'x86'}.get(target_arch) or target_arch
    args = [
        '--browser-type', self.m.chromium.c.build_config_fs.lower(),
        '--target-cpu', target_cpu,
        '--build-dir', self.m.chromium.output_dir,
    ]
    self.m.python(
        'Profiling benchmarks.',
        self.m.path['checkout'].join('build', 'win',
                                     'run_pgo_profiling_benchmarks.py'),
        args)

  def _compile_optimized_image(self, bot_config, mb_config_path=None):
    """
    Generates the optimized version of the binaries.
    """
    self.m.chromium.set_config(bot_config['chromium_config_optimize'],
                               **bot_config.get('chromium_config_kwargs'))
    self.m.chromium.runhooks(name='Runhooks: Optimization phase.')
    self.m.chromium.run_mb(
        self.m.properties['mastername'],
        self.m.properties['buildername'],
        mb_config_path=mb_config_path,
        use_goma=False,
        phase=2)
    self.m.chromium.compile(name='Compile: Optimization phase.')

  def _merge_pgc_files(self):
    """
    Calls the script responsible of merging the PGC files.

    If this script is missing then this will be done automatically by the
    compiler during the final compile step.
    """
    merge_script = self.m.path['checkout'].join('build', 'win',
                                                'merge_pgc_files.py')
    if not self.m.path.exists(merge_script):
      return

    target_arch = self.m.chromium.c.gyp_env.GYP_DEFINES['target_arch']
    target_cpu = {'ia32': 'x86'}.get(target_arch) or target_arch
    base_args = [
        '--checkout-dir', self.m.path['checkout'],
        '--target-cpu', target_cpu,
        '--build-dir', self.m.chromium.output_dir,
    ]

    for f in self.m.file.glob('list PGD files',
                              self.m.chromium.output_dir.join('*.pgd'),
                              test_data=[
                                  self.m.chromium.output_dir.join('test1.pgd'),
                                  self.m.chromium.output_dir.join('test2.pgd'),
                              ]):
      binary_name = self.m.path.splitext(self.m.path.basename(f))[0]
      args = base_args + ['--binary-name', binary_name]
      self.m.python('Merge the pgc files for %s.' % binary_name,
                    merge_script, args)
      self.m.file.rmwildcard('%s!*.pgc' % binary_name,
                             str(self.m.chromium.output_dir))

  def compile_pgo(self, bot_config):
    """
    Do a PGO build. This takes care of building an instrumented image, profiling
    it and then compiling the optimized version of it.
    """
    self.m.gclient.set_config(bot_config['gclient_config'])

    # Augment the DEPS path if needed.
    if '%s' in self.m.gclient.c.solutions[0].deps_file:  # pragma: no cover
      self.m.gclient.c.solutions[0].deps_file = (
          self.m.gclient.c.solutions[0].deps_file % bot_config['bucket'])

    if self.m.properties.get('bot_id') != 'fake_slave':
      self.m.chromium.taskkill()

    update_step = self.m.bot_update.ensure_checkout()
    if bot_config.get('patch_root'):
      self.m.path['checkout'] = self.m.path['start_dir'].join(
          bot_config.get('patch_root'))

    # First step: compilation of the instrumented build.
    self._compile_instrumented_image(bot_config)

    # Second step: profiling of the instrumented build.
    self._run_pgo_benchmarks()

    # Merge the pgc files.
    self._merge_pgc_files()

    if bot_config.get('archive_pgd', False):
      self.archive_profile_database(
          update_step.presentation.properties['got_revision'])
      step_result = self.m.step.active_result
      step_result.presentation.status = self.m.step.WARNING

    # Third step: Compilation of the optimized build, this will use the
    #     profile data files produced by the previous step.
    self._compile_optimized_image(bot_config)

  def archive_profile_database(self, revision):
    """
    Archive the profile database into a cloud bucket and use 'git notes' to
    annotate the current commit with the URL to this file.
    """
    # Temporarily turn any failure during this step into a warning until the
    # permissions issues have been fixed.
    # TODO(sebmarchand): Remove the try/except once it works.
    try:
      with self.m.step.nest("archive profile database"):
        assert self.m.platform.is_win
        self.m.cipd.set_service_account_credentials(
            "C:\\creds\\service_accounts\\service-account-pgo-bot.json")
        target_arch = {
            'ia32': '386',
            'x64': 'amd64',
        }[self.m.chromium.c.gyp_env.GYP_DEFINES['target_arch']]
        package_name = "chromium/pgo/profiles/profile_database/windows-%s" % (
            target_arch)
        pkg = self.m.cipd.PackageDefinition(package_name,
                                            self.m.chromium.output_dir,
                                            'copy')

        # Copy the pgd files in a temp directory so cipd can pick them up.
        for f in self.m.file.glob('list PGD files',
                                  self.m.chromium.output_dir.join('*.pgd'),
                                  test_data=[
                                      self.m.chromium.output_dir.join(
                                          'test.pgd')
                                  ]):
          pkg.add_file(f)

        pkg_json = self.m.cipd.create_from_pkg(pkg)
        instance_id = pkg_json['instance_id']

        # Add the git notes for this profile database.
        git_notes_ref = ('refs/notes/pgo/profile_database/windows-%s' %
            target_arch)
        self.m.git('notes', '--ref', git_notes_ref,
                   'add', '-m', instance_id, revision)
        self.m.git('push', 'origin', git_notes_ref)
    except self.m.step.StepFailure:
      step_result = self.m.step.active_result
      step_result.presentation.status = self.m.step.WARNING

