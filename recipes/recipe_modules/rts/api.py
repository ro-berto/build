# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Interface for the performing regression test selection

See https://source.chromium.org/chromium/chromium/src/+/master:docs/testing/regr
ession-test-selection.md for more information
"""

from recipe_engine import recipe_api


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
        self.m.cipd.EnsureFile().add_package('chromium/rts/model', 'latest'))

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
                           changed_files,
                           skip_test_files_path,
                           target_change_recall=None,
                           step_name='select tests to skip (rts)',
                           rts_chromium_version='latest',
                           model_version='latest'):
    """Selects tests to skip.

    RTS looks at the changed_files and desired change recall and writes the
    tests to skip to skip_test_files_path.

    Args:
      changed_files (list[str]): A list of files changed in the CL. Paths must
      skip_test_files_path (str): A path to the file where RTS will put what
          should be skipped. Each line of the file will be a filename with
          the "//" prefix.
      target_change_recall (float): Must be between 0 and 1.
          A target change recall (safety).
          Higher values result in fewer tests skipped.
      step_name (str): The name of the step. If None, generate a name.
      rts_chromium_version (str): The version of the binary to download and use.
      model_version (str): The version of the model to download and use.
    """
    with self.m.step.nest(step_name):
      assert target_change_recall is None or 0 < target_change_recall < 1, \
         'target_change_recall must be a number between 0 and 1 or None.'

      rts_exec = self._ensure_exec(rts_chromium_version)
      model_dir = self._ensure_model(model_version)

      # Write changed_files
      changed_files_path = self.m.path.mkstemp()
      self.m.file.write_text('write changed_files', changed_files_path,
                             '\n'.join(changed_files))

      args = [
          rts_exec,
          'select',
          '-model-dir', model_dir, \
          '-changed-files', str(changed_files_path), \
          '-skip-test-files', str(skip_test_files_path),
      ]
      if target_change_recall is not None:
        args += ['-target-change-recall', str(target_change_recall)]

      # Run it
      self.m.step('rts-chromium select', args)
