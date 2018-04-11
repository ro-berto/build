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
    """Clean up old generated files.

    Args:
      age_days: Ages in days on the form +days, e.g., '+30'.
    """
    self.m.step('delete old generated files',
                ['find', self.m.path['checkout'].join('out'),
                 '-mtime', ('+%d' % age_days), '-type', 'f', '-delete'])

  def generate_compilation_database(self, targets, platform, mb_config_path=None):
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

    command = ['ninja', '-C', self.c.debug_path] + list(targets)
    # Add the parameters for creating the compilation database.
    command += ['-t', 'compdb', 'cc', 'cxx', 'objc', 'objcxx']

    command += ['-j', self.m.goma.recommended_goma_jobs]

    # TODO(tikuta): Support returning step result in api.m.goma.build_with_goma
    self.m.goma.start()

    build_exit_status = 1
    try:
      step_result = self.m.step('generate compilation database for %s' % platform,
                                command, stdout=self.m.raw_io.output_text())
      build_exit_status = step_result.retcode
    except self.m.step.StepFailure as e:
      build_exit_status = e.retcode
      raise e
    finally:
      self.m.goma.stop(ninja_log_outdir=self.c.debug_path,
                       ninja_log_command=command,
                       ninja_log_compiler='goma',
                       build_exit_status=build_exit_status)

    return step_result

  def copy_compilation_output(self, result):
    """Copy the created output to the correct directory.

    Args:
      result: Result output of the generated compilation database.
    """
    self.m.step('copy compilation database',
                ['cp', self.m.raw_io.input_text(data=result.stdout),
                 self.c.compile_commands_json_file])

  def filter_compilation(self, result):
    """Filter out duplicate compilation units.

    Args:
      result: Result output of the generated compilation database.
    """
    compile_file = self.c.compile_commands_json_file
    self.m.build.python('Filter out duplicate compilation units',
                        self.package_repo_resource('scripts', 'slave', 'chromium',
                                                   'filter_compilations.py'),
                        ['--compdb-input', compile_file,
                         '--compdb-filter', self.m.raw_io.input_text(data=result.stdout),
                         '--compdb-output', compile_file])

  def run_clang_tool(self):
    """Download and run the clang tool.
    """
    # Download the clang tool.
    script_path = self.m.path.sep.join(['build', 'download_translation_unit_tool.py'])
    with self.m.context(cwd=self.m.path['checkout']):
      self.m.step('download translation_unit clang tool', [script_path])

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
    index_pack_kythe_name = 'index_pack_%s_kythe.zip' % self.c.PLATFORM
    index_pack_kythe_name_with_revision = 'index_pack_%s_kythe_%s.zip' % (
        self.c.PLATFORM, commit_position)
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
            '--index-pack-format', 'kythe',
            '--corpus', self.c.CORPUS,
            '--revision', self._get_revision()]
    if self.c.ROOT:
      args.extend(['--root', self.c.ROOT])
    self.m.build.python('create kythe index pack',
                        self.package_repo_resource('scripts', 'slave', 'chromium',
                                                   'package_index.py'),
                        args)

  def _upload_kythe_index_pack(self, bucket_name, index_pack_kythe_name,
                              index_pack_kythe_name_with_revision):
    """Upload the kythe index pack to goole storage.

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
    self.m.build.python('sync generated files',
                        self.package_repo_resource('scripts','slave',
                                                   'sync_generated_files_codesearch.py'),
                        ['--message',
                         'Generated files from "%s" build %s, revision %s' % (
                             self.m.properties['buildername'],
                             self.m.properties['buildnumber'],
                             self._get_revision()),
                         '--dest-branch',
                         self.c.GEN_REPO_BRANCH,
                         'src/out',
                         generated_repo_dir])
