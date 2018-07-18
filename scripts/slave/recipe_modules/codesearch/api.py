# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from recipe_engine import recipe_api

# Regular expression to identify a Git hash.
GIT_COMMIT_HASH_RE = re.compile(r'[a-zA-Z0-9]{40}')

class CodesearchApi(recipe_api.RecipeApi):
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

  def generate_compilation_database(self, targets, platform, output_file=None,
                                    mb_config_path=None):
    mastername = self.m.properties['mastername']
    buildername = self.m.properties['buildername']
    mb_config_path = mb_config_path or self.c.CHECKOUT_PATH.join('tools', 'mb',
                                                                 'mb_config.pyl')
    self.m.chromium.run_mb(mastername,
                           buildername,
                           build_dir=self.c.debug_path,
                           phase=platform,
                           name='generate build files for %s' % platform,
                           mb_config_path=mb_config_path)

    output_file = output_file or self.c.compile_commands_json_file
    args = ['-p', self.c.debug_path, '-o', output_file] + list(targets)

    build_exit_status = 1
    try:
      step_result = self.m.python(
          'generate compilation database',
          self.m.path['checkout'].join(
              'tools', 'clang', 'scripts', 'generate_compdb.py'),
          args)
      build_exit_status = step_result.retcode
    except self.m.step.StepFailure as e:
      build_exit_status = e.retcode
      raise e

    return step_result

  def run_clang_tool(self):
    """Download and run the clang tool."""
    # Download the clang tool.
    self.m.python(
        'download translation_unit clang tool',
        self.m.path['checkout'].join('build',
                                     'download_translation_unit_tool.py'))

    # Run the clang tool
    args = ['--tool', self.m.path['checkout'].join('third_party', 'llvm-build',
                                                   'Release+Asserts', 'bin',
                                                   'translation_unit'),
            '-p', self.c.debug_path, '--all']
    try:
      self.m.python(
          'run translation_unit clang tool',
          self.m.path['checkout'].join('tools', 'clang', 'scripts', 'run_tool.py'),
          args)
    except self.m.step.StepFailure as f:
      # For some files, the clang tool produces errors. This is a known issue,
      # but since it only affects very few files (currently 9), we ignore these
      # errors for now. At least this means we can already have cross references
      # support for the files where it works.
      self.m.step.active_result.presentation.step_text = f.reason_message()
      self.m.step.active_result.presentation.status = self.m.step.WARNING

  def _get_commit_position(self):
    """Returns the commit position of the project.
    """
    got_revision_cp = self.m.chromium.build_properties.get('got_revision_cp')
    if not got_revision_cp:
      # For some downstream bots, the build properties 'got_revision_cp' are not
      # generated. To resolve this issue, use 'got_revision' property here instead.
      return self._get_revision()
    return self.m.commit_position.parse_revision(got_revision_cp)

  def _get_revision(self):
    """Returns the git commit hash of the project.
    """
    commit = self.m.chromium.build_properties.get('got_revision')
    if commit and GIT_COMMIT_HASH_RE.match(commit):
      return commit

  def create_and_upload_kythe_index_pack(self):
    """Create the kythe index pack and upload it to google storage.
    """
    commit_position = self._get_commit_position()
    index_pack_kythe_name = 'chromium_%s.kzip' % self.c.PLATFORM
    # TODO(hinoka): Delete these two lines after migrated to LUCI.
    if self.m.runtime.is_experimental:
      index_pack_kythe_name_with_revision = (
          'chromium_%s_%s_%s_experimental.kzip' % (
              self.c.PLATFORM, commit_position, self._get_revision()))
    else:
      index_pack_kythe_name_with_revision = 'chromium_%s_%s_%s.kzip' % (
          self.c.PLATFORM, commit_position, self._get_revision())
    self._create_kythe_index_pack(index_pack_kythe_name)

    assert self.c.bucket_name, (
        'Trying to upload Kythe index pack but no google storage bucket name')
    self._upload_kythe_index_pack(self.c.bucket_name, index_pack_kythe_name,
                                  index_pack_kythe_name_with_revision)

  def _create_kythe_index_pack(self, index_pack_kythe_name):
    """Create the kythe index pack.

    Args:
      index_pack_kythe_name: Name of the Kythe index pack
    """
    args = ['--path-to-compdb', self.c.compile_commands_json_file,
            '--path-to-archive-output',
            self.c.debug_path.join(index_pack_kythe_name),
            '--corpus', self.c.CORPUS]
    if self.c.ROOT:
      args.extend(['--root', self.c.ROOT])
    if self.c.GEN_REPO_OUT_DIR:
      args.extend(['--out_dir', 'src/out/%s' % self.c.GEN_REPO_OUT_DIR])
    self.m.build.python('create kythe index pack',
                        self.resource('package_index.py'),
                        args)

  def _upload_kythe_index_pack(self, bucket_name, index_pack_kythe_name,
                              index_pack_kythe_name_with_revision):
    """Upload the kythe index pack to google storage.

    Args:
      bucket_name: Name of the google storage bucket to upload to
      index_pack_kythe_name: Name of the Kythe index pack
      index_pack_kythe_name_with_revision: Name of the Kythe index pack
                                           with git commit revision
    """
    self.m.gsutil.upload(
        name='upload kythe index pack',
        source=self.c.debug_path.join(index_pack_kythe_name),
        bucket=bucket_name,
        dest='prod/%s' % index_pack_kythe_name_with_revision
    )

  def checkout_generated_files_repo_and_sync(self):
    """Check out the generated files repo and sync the generated files
       into this checkout.
    """
    if not self.c.SYNC_GENERATED_FILES:
      return
    assert self.c.generated_repo, (
        'Trying to check out generated files repo, but the repo is not indicated')

    # Check out the generated files repo.
    generated_repo_dir = self.m.path['start_dir'].join('generated')
    self.m.git.checkout(
        self.c.generated_repo,
        ref=self.c.GEN_REPO_BRANCH,
        dir_path=generated_repo_dir,
        submodules=False)
    with self.m.context(cwd=generated_repo_dir):
      self.m.git('config', 'user.email', self.c.generated_author_email)
      self.m.git('config', 'user.name', self.c.generated_author_name)

    # Sync the generated files into this checkout.
    args = ['--message',
            'Generated files from "%s" build %s, revision %s' % (
                self.m.properties['buildername'],
                self.m.properties['buildnumber'],
                self._get_revision()),
            '--dest-branch',
            self.c.GEN_REPO_BRANCH,
            'src/out',
            generated_repo_dir]
    if self.c.GEN_REPO_OUT_DIR:
      args = ['--debug-dir', self.c.GEN_REPO_OUT_DIR] + args
    if self.m.runtime.is_experimental:
      args.append('--dry-run')
    self.m.build.python('sync generated files',
                        self.resource('sync_generated_files.py'),
                        args)
