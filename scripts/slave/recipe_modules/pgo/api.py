# Copyright (c) 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib
import json
from recipe_engine import recipe_api


class PgoApi(recipe_api.RecipeApi):

  GS_BUCKET = 'chromium-optimization-profiles'
  GS_BUCKET_PATH = 'pgo_profiles'
  TEMP_PROFDATA_FILENAME = 'pgo_final_aggregate.profdata'

  def __init__(self, properties, *args, **kwargs):
    super(PgoApi, self).__init__(*args, **kwargs)
    self._use_pgo = properties.use_pgo

  @property
  def using_pgo(self):
    """Indicates this run uses PGO, set in bot's *.star configuration files.

    Used by chromium_tests.run_tests() to process profile data when True.
    """
    return self._use_pgo

  @property
  def branch(self):
    """Parse the branch name from ref."""
    ref = self.m.buildbucket.gitiles_commit.ref
    # Release ref: refs/branch-heads/4103
    # Master ref: refs/heads/master
    # If ref is undefined, default it to master
    return ref.split('/', 3)[2] if ref else 'master'

  def _profdata_artifact_name(self, sha1):
    """Generate profdata artifact name.

    Args:
      sha1 - (string) sha1 hash of the profdata content.

    Template:
    chrome-{platform}-{branch number}-{timestamp}-{profile_hash}.profdata
    * {platform} refers to the platform, which is one of [win32, win64 and mac].
    * {branch number} refers to the branch number, such as 4103.
    * {timestamp} refers to the timestamp of the commit at HEAD.
    * {profile_hash} refers to the sha1 hash of the profdata content.

    Return:
        (string) filename of the resulting .profdata.
    """
    # TODO(crbug.com/1077004) - Prefix should be chromium for profiles generated
    # without internal sources. Update this prefix when support is introduced.
    profdata_template = 'chrome-%s-%s-%s-%s.profdata'

    # platform from recipe_engine/platform recipe_module
    # if is_win, should append bits [32,64]
    platform = self.m.platform.name

    if self.m.platform.is_win:
      platform += str(self.m.chromium.c.TARGET_BITS)

    # timestamp from git commit HEAD. under the hood invokes
    # `git show --format=%at -s`, where %at=author date, UNIX timestamp
    with self.m.context(cwd=self.m.path['checkout']):
      timestamp = str(self.m.git.get_timestamp(test_data='1587876258'))

    return profdata_template % (platform, self.branch, timestamp, sha1)

  def ensure_profdata_files(self, tests):
    """Ensure there is a profdata file generated for each test.

    Each test run should have a subfolder path in profiles.profile_subdirs
    with a profdata file. Fails the current run if the number of tests don't
    match the number of profdata files in the subdir

    Args:
      tests: list of step.Test objects.
    """
    with self.m.step.nest('Ensure .profdata for each test'):
      missing_files = {}

      files = set(
          self.m.file.listdir(
              'searching for profdata files',
              self.m.profiles.profile_dir(),
              recursive=True))

      for test in tests:
        # Key in profile_subdirs is set as test.step_name with suffix
        subdir_identifier = test.step_name('')
        path = self.m.profiles.profile_subdirs.get(subdir_identifier)
        profdata_filename = test.target_name + '.profdata'
        profdata_path = path.join(profdata_filename)
        # In this path, there should be a profdata file named after the test
        if profdata_path not in files:
          missing_files[profdata_filename] = subdir_identifier

      if missing_files:
        output = {
            'missing_profdata': [{
                'profdata_filename': k,
                'step_name': v,
            } for k, v in missing_files.iteritems()],
            'all_files': str(files)
        }
        self.m.python.failing_step('Expected .profdata files are missing',
                                   json.dumps(output, indent=2))

  def process_pgo_data(self, tests):
    """Processes the pgo profraw files generated by benchmark tests.

    The implementation is similar to self.m.code_coverage.process_coverage_data,
    but leaves out the cruft and focuses only on merging and uploading.

    Args:
      tests: (list) of step.Test objects
    """
    # Ensure a profdata was generated per test, before even starting to process
    self.ensure_profdata_files(tests)
    with self.m.step.nest('Processing PGO .profraw data'):
      # Invoke the merge script
      profdata_artifact = self.m.profiles.profile_dir().join(
          self.TEMP_PROFDATA_FILENAME)
      # We want to run llvm-profdata without the --sparse argument.
      # https://llvm.org/docs/CommandGuide/llvm-profdata.html#profdata-merge
      self.m.profiles.merge_profdata(profdata_artifact)

      if not self.m.path.exists(profdata_artifact):
        self.m.python.failing_step(
            'No profdata was generated.', 'Verify that the Swarming tasks have '
            'completed successfully, and have output .profraw files')

      # Check for any merge errors
      merge_errors = self.m.profiles.find_merge_errors()
      if merge_errors.stdout:
        result = self.m.step.active_result
        result.presentation.text = 'Found invalid profraw files'
        result.presentation.properties['merge errors'] = merge_errors.stdout
        self.m.python.failing_step(
            'Failing due to merge errors found alongside'
            ' invalid profile data.', 'Please see logs '
            'of failed step for details.')

      # TODO(crbug.com/1076999) - Look into replacing this hash for the sha1
      # of the git commit of src associated w/ build.
      # SHA1 hash content of the profdata is required as part of the naming
      # make it content-addressed.
      contents = self.m.file.read_raw(
          'Read profdata content',
          profdata_artifact,
          test_data='some_profdata_content')
      sha1 = hashlib.sha1(contents).hexdigest()

      # The final profdata artifact name requires the sha1 hash of the contents,
      # so the profdata file is generated first, and then renamed.
      new_filename = self._profdata_artifact_name(sha1)
      new_filepath = self.m.profiles.profile_dir().join(new_filename)
      self.m.file.move('Rename the profdata artifact', profdata_artifact,
                       new_filepath)

      # Reset profdata_artifact to the updated naming
      self.m.profiles.upload(
          self.GS_BUCKET,
          '%s/%s' % (self.GS_BUCKET_PATH, new_filename),
          new_filepath,
          args=[
              '-Z',
          ],
          link_name=new_filename)
