# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from recipe_engine import recipe_api


_BUCKET_NAME = 'cr-coverage-profile-data'


class ClangCoverageApi(recipe_api.RecipeApi):
  """This module contains apis to interact with llvm-cov and llvm-profdata."""

  def __init__(self, *args, **kwargs):
    super(ClangCoverageApi, self).__init__(*args, **kwargs)
    # A single temporary directory to contain the profile data for all targets
    # in the build.
    self._base_profdata_dir = None
    # Maps step names to subdirectories of the above.
    self._profdata_dirs = {}

  @staticmethod
  def _dir_name_for_step(step_name):
    """Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to underscores.

    Adapted from:
    https://stackoverflow.com/questions/295135/turn-a-string-into-a-valid-filename

    Args:
      step_name (str): the name of the step to use.
    """
    value = re.sub('[^\w\s]', '', step_name).strip().lower()
    value = re.sub('[-\s]+', '_', value)
    return value

  @property
  def raw_profile_merge_script(self):
    """Returns the location of a script that merges raw profiles from shards.

    This is intended to be passed to the swarming recipe module to be called
    upon completion of the shards.
    """
    return self.resource('merge_profiles.py')

  @property
  def profdata_executable(self):
    """Returns the path to the llvm-profdata deployed by gclient hooks."""
    return self.m.path['checkout'].join('third_party', 'llvm-build',
                                        'Release+Asserts', 'bin',
                                        'llvm-profdata')

  def profdata_dir(self, step_name=None):
    """Ensures a directory exists for writing the step-level merged profdata.

    Args:
      step_name (str): The name of the step for the target whose profile we'll
          save in in this dir. None for getting the parent directory to contain
          the dirs for all steps.
    """
    # Create the parent directory when first needed.
    if not self._base_profdata_dir:
      self._base_profdata_dir = self.m.path.mkdtemp()

    if not step_name:
      return self._base_profdata_dir

    if step_name in self._profdata_dirs:
      return self._profdata_dirs[step_name]

    new_dir = self._base_profdata_dir.join(self._dir_name_for_step(step_name))
    self.m.file.ensure_directory('ensure profdata dir for %s' % step_name,
                                 new_dir)
    self._profdata_dirs[step_name] = new_dir
    return new_dir

  @property
  def using_coverage(self):
    """Checks if the current build is running coverage-instrumented targets."""
    # TODO(crbug.com/896751): Implement a cleaner way to determine if the recipe
    # is using code coverage instrumentation.
    return (self.m.gclient.c
            and self.m.gclient.c.solutions
            and 'checkout_clang_coverage_tools'
                in self.m.gclient.c.solutions[0].custom_vars)

  def create_report(self):
    """Placeholder for report generation.

    At the moment, this only merges the profile data of all the steps in the
    build into a single profdata file, and uploads to google storage.
    """
    if len(self._profdata_dirs):
      out_file = self.profdata_dir().join('merged.profdata')
      self.m.python(
          'merge profile data for %d targets' % len(self._profdata_dirs),
          self.resource('merge_steps.py'),
          args=[
              '--input-dir', self.profdata_dir(),
              '--output-file', out_file,
              '--llvm-profdata', self.profdata_executable,
          ])
      self.m.gsutil.upload(
          out_file, _BUCKET_NAME, '%s/%s/merged.profdata' % (
          self.m.properties['buildername'], self.m.properties['buildnumber']),
          name='upload merged profile data')

  def shard_merge(self, step_name):
    """Returns a merge object understood by the swarming module.

    See the docstring for the `merge` parameter of api.swarming.task.
    """
    return {
        'script': self.raw_profile_merge_script,
        'args': [
            '--profdata-dir', self.profdata_dir(step_name),
            '--llvm-profdata', self.profdata_executable,
        ],
    }

