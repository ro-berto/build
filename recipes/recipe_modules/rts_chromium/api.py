# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Interface for the performing regression test selection

See https://source.chromium.org/chromium/chromium/src/+/master:docs/testing/
regression-test-selection.md
for more information
"""

from recipe_engine import recipe_api
from .rts_spec import RTSSpec


class RtsApi(recipe_api.RecipeApi):
  """Provides methods to perform regression test selection"""

  def _ensure_model(self, model_version='latest'):
    """Ensures the RTS model is installed from CIPD.

    Args:
      model_version (str): The version of the RTS model to install.

    Returns:
      The path to the RTS model.
    """
    # Jumping through some hoops to get the model dir instead of a binary path
    # from the cipd recipe_module
    model_dest_dir = self.m.path['cleanup'].join('rts-chromium-model',
                                                 model_version)
    self.m.cipd.ensure(
        model_dest_dir,
        self.m.cipd.EnsureFile().add_package('chromium/rts/model', 'latest'),
        name='ensure model installed')

    return model_dest_dir

  def _ensure_exec(self, rts_chromium_version='latest'):
    """Ensures the RTS binary is installed from CIPD.

    Args:
      rts_chromium_version (str): The version of rts-chromium to install.

    Returns:
      The path to the rts-chromium binary
    """
    exec_path = self.m.cipd.ensure_tool(
        'chromium/rts/rts-chromium/${platform}',
        rts_chromium_version,
        executable_path='rts-chromium')

    return exec_path

  def select_tests_to_skip(self,
                           spec,
                           changed_files,
                           step_name='select tests to skip (rts)'):
    """Selects tests to skip.

    RTS looks at the spec's changed_files and desired change recall and writes
    the tests to skip to skip_test_files_path.

    spec (RTSSpec): The RTS spec.
    changed_files (list[str]): A list of files changed in the CL. Paths must
      start with "//"
    step_name (str): The name of the step. If None, generate a name.
    """
    with self.m.step.nest(step_name):
      assert 0 < spec.target_change_recall < 1, \
         'target_change_recall must be a number between 0 and 1.'

      rts_exec = self._ensure_exec(spec.rts_chromium_version)
      model_dir = self._ensure_model(spec.model_version)

      # Write changed_files
      changed_files_path = self.m.path.mkstemp()
      self.m.file.write_text('write changed_files', changed_files_path,
                             '\n'.join(changed_files))

      skip_test_file_full_path = str(self.m.path['checkout'].join(
          spec.skip_test_files_path))
      args = [
          rts_exec,
          'select',
          '-model-dir', model_dir, \
          '-changed-files', str(changed_files_path), \
          '-skip-test-files', skip_test_file_full_path, \
          '-target-change-recall', str(spec.target_change_recall),
      ]

      # Run it
      self.m.step('rts-chromium select', args)

      # Present skippable files
      self.m.file.read_text(
          'read skip_test_files_path contents',
          skip_test_file_full_path,
          include_log=True)
