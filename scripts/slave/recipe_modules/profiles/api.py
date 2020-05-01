# Copyright (c) 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from recipe_engine import recipe_api


class ProfilesApi(recipe_api.RecipeApi):

  def __init__(self, *args, **kwargs):
    super(ProfilesApi, self).__init__(*args, **kwargs)
    # Directory storing the merge scripts for profile generation
    self._merge_scripts_dir = None
    # Single temporary directory to contain all profile data for all targets
    self._root_profile_dir = None
    # Dictionary to map subdirectories
    self._profile_subdirs = {}

  @property
  def merge_scripts_dir(self):
    # TODO(crbug.com/1076055) - Refactor the code_coverage folder to a common
    # profiles folder
    if not self._merge_scripts_dir:  # pragma: no cover
      self._merge_scripts_dir = self.m.chromium_checkout.working_dir.join(
          'src', 'testing', 'merge_scripts', 'code_coverage')
    return self._merge_scripts_dir

  @property
  def merge_steps_script(self):
    return self.merge_scripts_dir.join('merge_steps.py')

  @property
  def merge_results_script(self):
    return self.merge_scripts_dir.join('merge_results.py')

  @property
  def profile_subdirs(self):
    return self._profile_subdirs

  @property
  def _llvm_base_path(self):
    return self.m.path['checkout'].join('third_party', 'llvm-build',
                                        'Release+Asserts', 'bin')

  def llvm_exec_path(self, name):
    name += '.exe' if self.m.platform.is_win else ''
    return self._llvm_base_path.join(name)

  @property
  def llvm_profdata_exec(self):
    return self.llvm_exec_path('llvm-profdata')

  @staticmethod
  def normalize(key):
    """Normalizes the input to be suitable for filename/path.

    Converts to lowercase, removes non-alpha characters,
    and converts spaces to underscores. Adapted from:
    https://stackoverflow.com/questions/295135/turn-a-string-into-a-valid-filename

    Args:
      key (str): the input to normalize.

    Returns:
      a normalized string
    """
    value = re.sub('[^\w\s]', '', key).strip().lower()
    value = re.sub('[-\s]+', '_', value)
    return value

  def profile_dir(self, identifier=None):
    """Ensures a directory exists for writing the merged profdata files.

    Args:
      identifier (str): (optional) a key to identify a profile dir. Usually the
                      name of a step for a target, such that the target's
                      profdata are all stored there. Defaults to None, which
                      will store profdata files in the parent directory.

    Returns:
      Path object to the dir
    """
    # Create the parent directory if not created yet
    if not self._root_profile_dir:
      self._root_profile_dir = self.m.path.mkdtemp()

    if not identifier:
      return self._root_profile_dir

    if not identifier in self._profile_subdirs:
      path = self.normalize(identifier)
      new_subdir = self._root_profile_dir.join(path)
      self.m.file.ensure_directory('ensure profile dir for %s' % identifier,
                                   new_subdir)

      self._profile_subdirs[identifier] = new_subdir

    return self._profile_subdirs[identifier]

  # TODO(crbug.com/1077304) - migrate this to sparse once the merge scripts
  # have migrated
  def merge_profdata(self,
                     output_artifact,
                     profdata_filename_pattern=None,
                     no_sparse=False):
    """Helper function to invoke 'merge_steps.py'.

    Args:
      output_artifact (str): filename of the output, ending in .profdata.
      profdata_filename_pattern (str): (optional) regex pattern to pass to
        'merge_steps.py' when searching for .profdata files.
      no_sparse (bool): (optional) flag to invoke the merge script without
        sparse. Defaults to False.
    """
    args = [
        '--input-dir',
        self.profile_dir(),
        '--output-file',
        output_artifact,
        '--llvm-profdata',
        self.llvm_profdata_exec,
    ]

    if profdata_filename_pattern:
      args += [
          '--profdata-filename-pattern',
          profdata_filename_pattern,
      ]

    if no_sparse:
      args += [
          '--no-sparse',
      ]

    self.m.python(
        'merge all profile files into a single .profdata',
        self.merge_steps_script,
        args=args)

  def upload(self, bucket, path, local_artifact, args=None, link_name=None):
    """Invokes gsutil recipe module to upload.

    Args:
      bucket (str): name of the gs bucket to upload to.
      path (str): gs bucket path to upload to.
      local_artifact (str): path to the local artifact to upload
      args (list): list of string arguments to pass to gsutil

    Example:
      gsutil cp {local_artifact} {args} gs://{bucket}/{path}

    Reference:
      https://cloud.google.com/storage/docs/quickstart-gsutil
    """
    upload_step = self.m.gsutil.upload(
        local_artifact,
        bucket,
        path,
        args=args,
        link_name=link_name,
        name='upload artifact to GS')

    return upload_step

  def surface_merge_errors(self):
    """Display any profiles that failed to merge to the LUCI console"""
    test_data = {
        "failed profiles": {
            "browser_tests": ["/tmp/1/default-123.profraw"]
        },
        "total": 1
    }
    step_result = self.m.python(
        'Finding profile merge errors',
        self.resource('load_merge_errors.py'),
        args=['--root-dir', self.profile_dir()],
        step_test_data=lambda: self.m.json.test_api.output_stream(test_data),
        stdout=self.m.json.output())

    if step_result.stdout:
      step_result.presentation.text = 'Found invalid profraw files'
      step_result.presentation.properties['bad_profiles'] = step_result.stdout
