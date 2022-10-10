# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from recipe_engine import recipe_api

from RECIPE_MODULES.build import chromium

# Regular expression to identify a Git hash.
GIT_COMMIT_HASH_RE = re.compile(r'[a-zA-Z0-9]{40}')

class CodesearchApi(recipe_api.RecipeApi):
  _PROJECT_BROWSER, _PROJECT_OS, _PROJECT_UNSUPPORTED = range(3)

  def get_config_defaults(self):
    return {
      'CHECKOUT_PATH': self.m.path['checkout'],
    }

  def cleanup_old_generated(self, age_days=7):
    """Clean up generated files older than the specified number of days.

    Args:
      age_days: Minimum age in days for files to delete (integer).
    """
    if self.c.PLATFORM.startswith('win'):
      # Flag explanations for the Windows command:
      # /p <path>  -- Search files in the given path
      # /s         -- Search recursively
      # /m *       -- Use the search mask *. This includes files without an
      #               extension (the default is *.*).
      # /d -<age>  -- Find files last modified before <age> days ago
      # /c <cmd>   -- Run <cmd> for each file. In our case we delete the file if
      #               it's not a directory.
      delete_command = ['forfiles', '/p', self.m.path['checkout'].join('out'),
                        '/s', '/m', '*', '/d', ('-%d' % age_days),
                        '/c', 'cmd /c if @isdir==FALSE del @path']
      try:
        self.m.step('delete old generated files', delete_command)
      except self.m.step.StepFailure as f:
        # On Windows, forfiles returns an error code if it found no files. We
        # don't want to fail if this happens, so convert it to a warning.
        self.m.step.active_result.presentation.step_text = f.reason_message()
        self.m.step.active_result.presentation.status = self.m.step.WARNING
    else:
      # Flag explanations for the Linux command:
      # find <path>    -- Find files recursively in the given path
      # -mtime +<age>  -- Find files last modified before <age> days ago
      # -type f        -- Find files only (not directories)
      # -delete        -- Delete the found files
      delete_command = ['find', self.m.path['checkout'].join('out'),
                        '-mtime', ('+%d' % age_days), '-type', 'f', '-delete']
      self.m.step('delete old generated files', delete_command)

  def generate_compilation_database(self,
                                    targets,
                                    builder_group,
                                    buildername,
                                    output_file=None,
                                    mb_config_path=None):
    self.m.chromium.mb_gen(
        chromium.BuilderId.create_for_group(builder_group, buildername),
        build_dir=self.c.out_path,
        name='generate build files',
        mb_config_path=mb_config_path)

    output_file = output_file or self.c.compile_commands_json_file

    try:
      step_result = self.m.step('generate compilation database', [
          'python3', '-u', self.m.path['checkout'].join(
              'tools', 'clang', 'scripts', 'generate_compdb.py'), '-p',
          self.c.out_path, '-o', output_file
      ] + list(targets))
    except self.m.step.StepFailure as e:
      raise e

    return step_result

  def generate_gn_compilation_database(self,
                                       targets,
                                       builder_group,
                                       buildername,
                                       mb_config_path=None):
    self.m.chromium.mb_gen(
        chromium.BuilderId.create_for_group(builder_group, buildername),
        build_dir=self.c.out_path,
        name='generate build files',
        mb_config_path=mb_config_path)

    with self.m.context(
        cwd=self.m.path['checkout'], env=self.m.chromium.get_env()):
      export_compile_cmd = '--export-compile-commands'
      if targets:
        export_compile_cmd += '=' + ','.join(targets)
      self.m.step(
          'generate gn compilation database', [
              'python3', '-u', self.m.depot_tools.gn_py_path, 'gen',
              export_compile_cmd, self.c.out_path
          ],
          stdout=self.m.raw_io.output_text()).stdout

  def generate_gn_target_list(self, targets=None, output_file=None):
    output_file = output_file or self.c.gn_targets_json_file
    with self.m.context(
        cwd=self.m.path['checkout'], env=self.m.chromium.get_env()):
      targets_cmd = '*'
      if targets:
        targets_cmd = ' '.join(targets)
      output = self.m.step(
          'generate gn target list', [
              'python3', '-u', self.m.depot_tools.gn_py_path, 'desc',
              self.c.out_path, targets_cmd, '--format=json'
          ],
          stdout=self.m.raw_io.output_text()).stdout
    self.m.file.write_raw('write gn target list', output_file, output)

  def add_kythe_metadata(self):
    """Adds inline Kythe metadata to Mojom generated files.

    This metadata is used to connect things in the generated file to the thing
    in the Mojom file which generated it. This is made possible by annotations
    added to the generated file by the Mojo compiler.
    """
    self.m.step('add kythe metadata', [
        'python3',
        self.resource('add_kythe_metadata.py'),
        '--corpus',
        self.c.CORPUS,
        self.c.out_path,
    ])

  def clone_clang_tools(self, clone_dir):
    """Clone chromium/src clang tools."""
    clang_dir = clone_dir.join('clang')
    with self.m.context(cwd=clone_dir):
      self.m.file.rmtree('remove previous instance of clang tools', clang_dir)
      self.m.git('clone',
                 'https://chromium.googlesource.com/chromium/src/tools/clang')
    return clang_dir

  def run_clang_tool(self, clang_dir=None, run_dirs=None):
    """Download and run the clang tool."""
    clang_dir = clang_dir or self.m.path['checkout'].join('tools', 'clang')

    # Download the clang tool.
    translation_unit_dir = self.m.path.mkdtemp()
    self.m.step(
        name='download translation_unit clang tool',
        cmd=[
            'python3', '-u',
            clang_dir.join('scripts',
                           'update.py'), '--package=translation_unit',
            '--output-dir=' + str(translation_unit_dir)
        ])

    # Run the clang tool
    args = [
        '--tool', 'translation_unit', '--tool-path',
        translation_unit_dir.join('bin'), '-p', self.c.out_path, '--all'
    ]
    if run_dirs is None:
      run_dirs = [self.m.context.cwd]
    for run_dir in run_dirs:
      try:
        with self.m.context(cwd=run_dir):
          self.m.step(
              'run translation_unit clang tool',
              ['python3', '-u',
               clang_dir.join('scripts', 'run_tool.py')] + args)

      except self.m.step.StepFailure as f:  # pragma: nocover
        # For some files, the clang tool produces errors. This is a known issue,
        # but since it only affects very few files (currently 9), we ignore
        # these errors for now. At least this means we can already have cross
        # reference support for the files where it works.
        # TODO(crbug/1284439): Investigate translation_unit failures for CrOS.
        self.m.step.active_result.presentation.step_text = f.reason_message()
        self.m.step.active_result.presentation.status = self.m.step.WARNING

  def _get_project_type(self):
    """Returns the type of the project.
    """
    if self.c.PROJECT in ('chromium', 'chrome'):
      return self._PROJECT_BROWSER
    elif self.c.PROJECT == 'chromiumos':
      return self._PROJECT_OS
    return self._PROJECT_UNSUPPORTED  # pragma: nocover

  def _get_commit_position(self):
    """Returns the commit position of the project.
    """
    got_revision_cp = self.m.chromium.build_properties.get('got_revision_cp')
    if not got_revision_cp:
      # For some downstream bots, the build properties 'got_revision_cp' are not
      # generated. To resolve this issue, use 'got_revision' property here
      # instead.
      return self._get_revision()
    _, rev = self.m.commit_position.parse(got_revision_cp)
    return rev

  def _get_revision(self):
    """Returns the git commit hash of the project.
    """
    commit = self.m.chromium.build_properties.get('got_revision')
    if commit and GIT_COMMIT_HASH_RE.match(commit):
      return commit

  def create_and_upload_kythe_index_pack(self, commit_hash, commit_timestamp):
    """Create the kythe index pack and upload it to google storage.

    Args:
      commit_hash: Hash of the commit at which we're creating the index pack,
        if None use got_revision.
      commit_timestamp: Timestamp of the commit at which we're creating the
        index pack, in integer seconds since the UNIX epoch.

    Returns:
      Path to the generated index pack.
    """
    commit_hash = commit_hash or self._get_revision()
    # TODO(jsca): Delete the second part of the below condition after LUCI
    # migration is complete.
    experimental_suffix = '_experimental' if (
        self.c.EXPERIMENTAL or self.m.runtime.is_experimental) else ''

    index_pack_kythe_base = '%s_%s' % (self.c.PROJECT, self.c.PLATFORM)
    index_pack_kythe_name_with_id = ''
    commit_position = ''
    project_type = self._get_project_type()
    if project_type == self._PROJECT_BROWSER:
      commit_position = self._get_commit_position()
      index_pack_kythe_name_with_id = '%s_%s_%s+%d%s.kzip' % (
          index_pack_kythe_base, commit_position, commit_hash, commit_timestamp,
          experimental_suffix)
    elif project_type == self._PROJECT_OS:
      index_pack_kythe_name_with_id = '%s_%s+%d%s.kzip' % (
          index_pack_kythe_base, commit_hash, commit_timestamp,
          experimental_suffix)
    else:  # pragma: no cover
      assert False, 'Unsupported codesearch project %s' % self.c.PROJECT

    index_pack_kythe_name = '%s.kzip' % index_pack_kythe_base
    index_pack_kythe_path = self.c.out_path.join(index_pack_kythe_name)
    self._create_kythe_index_pack(index_pack_kythe_path)

    if self.m.tryserver.is_tryserver:
      return index_pack_kythe_path

    assert self.c.bucket_name, (
        'Trying to upload Kythe index pack but no google storage bucket name')
    self._upload_kythe_index_pack(self.c.bucket_name, index_pack_kythe_path,
                                  index_pack_kythe_name_with_id)

    # Also upload compile_commands.json for debugging purposes.
    compdb_name_with_revision = 'compile_commands_%s_%s.json' % (
        self.c.PLATFORM, commit_position or commit_hash)
    self._upload_compile_commands_json(self.c.bucket_name,
                                       compdb_name_with_revision)

    return index_pack_kythe_path

  def _create_kythe_index_pack(self, index_pack_kythe_path):
    """Create the kythe index pack.

    Args:
      index_pack_kythe_path: Path to the Kythe index pack
    """
    exec_path = self.m.cipd.ensure_tool("infra/tools/package_index/${platform}",
                                        "latest")
    args = [
        '--checkout_dir',
        self.m.path['checkout'],
        '--path_to_compdb',
        self.c.compile_commands_json_file,
        '--path_to_gn_targets',
        self.c.gn_targets_json_file,
        '--path_to_archive_output',
        index_pack_kythe_path,
        '--corpus',
        self.c.CORPUS,
        '--project',
        self.c.PROJECT,
    ]

    if self.c.javac_extractor_output_dir:
      args.extend(['--path_to_java_kzips', self.c.javac_extractor_output_dir])

    # If out_path is /path/to/src/out/foo and
    # self.m.path['checkout'] is /path/to/src/,
    # then out_dir wants src/out/foo.
    args.extend([
        '--out_dir',
        self.m.path.relpath(
            self.c.out_path,
            self.m.path.dirname(self.m.path['checkout']),
        )
    ])

    if self.c.BUILD_CONFIG:
      args.extend(['--build_config', self.c.BUILD_CONFIG])
    self.m.step('create kythe index pack', [exec_path] + args)

  def _upload_kythe_index_pack(self, bucket_name, index_pack_kythe_path,
                               index_pack_kythe_name_with_id):
    """Upload the kythe index pack to google storage.

    Args:
      bucket_name: Name of the google storage bucket to upload to
      index_pack_kythe_path: Path of the Kythe index pack
      index_pack_kythe_name_with_revision: Name of the Kythe index pack
                                           with identifier
    """
    self.m.gsutil.upload(
        name='upload kythe index pack',
        source=index_pack_kythe_path,
        bucket=bucket_name,
        dest='prod/%s' % index_pack_kythe_name_with_id)

  def _upload_compile_commands_json(self, bucket_name,
                                    destination_filename):
    """Upload the compile_commands.json file to Google Storage.

    This is useful for debugging.

    Args:
      bucket_name: Name of the Google Storage bucket to upload to
      destination_filename: Name to use for the compile_commands file in
                            Google Storage
    """
    self.m.gsutil.upload(
        name='upload compile_commands.json',
        source=self.c.compile_commands_json_file,
        bucket=bucket_name,
        dest='debug/%s' % destination_filename
    )


  def checkout_generated_files_repo_and_sync(self,
                                             copy,
                                             kzip_path=None,
                                             revision=None):
    """Check out the generated files repo and sync the generated files
       into this checkout.

    Args:
      copy: A dict that describes how generated files should be synced. Keys are
        paths to local directories and values are where they are copied to in
        the generated files repo.

          {
              '/path/to/foo': 'foo',
              '/path/to/bar': 'baz/bar',
          }

        The above copy config would result in a generated files repo like:

          repo/
          repo/foo/
          repo/baz/bar/

      kzip_path: Path to kzip that will be used to prune uploded files.
      revision: A commit hash to be used in the commit message.
    """
    if not self.c.SYNC_GENERATED_FILES:
      return
    if self.m.tryserver.is_tryserver:
      return
    assert self.c.generated_repo, (
        'Trying to check out generated files repo,'
        ' but the repo is not indicated')

    # Check out the generated files repo. We use a named cache so that the
    # checkout stays around between builds (this saves ~15 mins of build time).
    generated_repo_dir = self.m.path['cache'].join('generated')

    # Windows is unable to checkout files with names longer than 260 chars.
    # This git setting works around this limitation.
    if self.c.PLATFORM.startswith('win'):
      try:
        with self.m.context(cwd=generated_repo_dir):
          self.m.git('config', 'core.longpaths', 'true',
                     name='set core.longpaths')
      except self.m.step.StepFailure as f: # pragma: nocover
        # If the bot runs with an empty cache, generated_repo_dir won't be a git
        # directory yet, causing git config to fail. In this case, we should
        # continue the run anyway. If the checkout fails on the next step due to
        # a long filename, this is no big deal as it should pass on the next
        # run.
        self.m.step.active_result.presentation.step_text = f.reason_message()
        self.m.step.active_result.presentation.status = self.m.step.WARNING

    env = {
        # Turn off the low speed limit, since checkout will be long.
        'GIT_HTTP_LOW_SPEED_LIMIT': '0',
        'GIT_HTTP_LOW_SPEED_TIME': '0',
    }
    with self.m.context(env=env):
      self.m.git.checkout(
          self.c.generated_repo,
          ref=self.c.GEN_REPO_BRANCH,
          dir_path=generated_repo_dir,
          submodules=False)
    with self.m.context(cwd=generated_repo_dir):
      self.m.git('config', 'user.email', self.c.generated_author_email)
      self.m.git('config', 'user.name', self.c.generated_author_name)

    # Sync the generated files into this checkout.
    cmd = ['vpython3', self.resource('sync_generated_files.py')]
    for src, dest in copy.items():
      cmd.extend(['--copy', '%s;%s' % (src, dest)])
    cmd.extend([
        '--message',
        'Generated files from "%s" build %d, revision %s' %
        (self.m.buildbucket.builder_name, self.m.buildbucket.build.id,
         revision or self._get_revision()),
        '--dest-branch',
        self.c.GEN_REPO_BRANCH,
        generated_repo_dir,
    ])
    if self.m.runtime.is_experimental:
      cmd.append('--dry-run')
    if kzip_path:
      cmd.extend(['--kzip-prune', kzip_path])
    if self._get_project_type() == self._PROJECT_BROWSER:
      cmd.append('--nokeycheck')

    self.m.step('sync generated files', cmd)
