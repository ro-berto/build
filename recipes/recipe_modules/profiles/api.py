# Copyright (c) 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from recipe_engine import recipe_api


class ProfilesApi(recipe_api.RecipeApi):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    # Directory storing the merge scripts for profile generation
    self._merge_scripts_dir = None
    # Single temporary directory to contain all profile data for all targets
    self._root_profile_dir = None
    # Path to llvm binaries
    self._llvm_base_path = None
    # Dictionary to map subdirectories
    self._profile_subdirs = {}
    # Path to checkout
    self._src_dir = None

  @property
  def src_dir(self):
    assert self._src_dir, 'src_dir must be set for this recipe_module'
    return self._src_dir

  @src_dir.setter
  def src_dir(self, value):
    self._src_dir = value

  @property
  def merge_scripts_dir(self):
    # TODO(crbug.com/1076055) - Refactor the code_coverage folder to a common
    # profiles folder
    if not self._merge_scripts_dir:  # pragma: no cover
      self._merge_scripts_dir = self.src_dir.join('testing', 'merge_scripts',
                                                  'code_coverage')
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

  def llvm_exec_path(self, name):
    if not self._llvm_base_path:
      self._llvm_base_path = self.src_dir.join('third_party', 'llvm-build',
                                               'Release+Asserts', 'bin')
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

  def merge_profdata(self,
                     output_artifact,
                     profdata_filename_pattern=None,
                     sparse=False):
    """Helper function to invoke 'merge_steps.py'.

    Args:
      output_artifact (str): filename of the output, ending in .profdata.
      profdata_filename_pattern (str): (optional) regex pattern to pass to
        'merge_steps.py' when searching for .profdata files.
      sparse (bool): (optional) flag to invoke the merge script with sparse.
        Defaults to False.
    """
    cmd = [
        'python3',
        self.merge_steps_script,
        '--input-dir',
        self.profile_dir(),
        '--output-file',
        output_artifact,
        '--llvm-profdata',
        self.llvm_profdata_exec,
    ]

    if profdata_filename_pattern:
      cmd += [
          '--profdata-filename-pattern',
          profdata_filename_pattern,
      ]

    if sparse:
      cmd += [
          '--sparse',
      ]

    self.m.step('merge all profile files into a single .profdata', cmd)

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

  def find_merge_errors(self):
    """Search for any profiles that failed to merge"""
    step_result = self.m.step(
        'Finding profile merge errors', [
            'python3',
            self.resource('load_merge_errors.py'),
            '--root-dir',
            self.profile_dir(),
        ],
        stdout=self.m.json.output())

    return step_result
