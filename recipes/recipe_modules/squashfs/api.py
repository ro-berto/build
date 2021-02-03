# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class SquashfsApi(recipe_api.RecipeApi):

  def mksquashfs(self, folder_path, output_file_path):
    """Archive a folder to a file using squashfs format.

    Args:
      folder_path: String representing the folder to compress.
      output_file_path: String representing the output image.

    Example: mksquashfs('/abs/path/', '/abs/another/path/image.sqsh')
    Meaning call:
    mksquashfs /abs/path/ /abs/another/path/image.sqsh
    See more at:
    https://github.com/plougher/squashfs-tools/blob/master/USAGE
    """
    if not self.m.platform.is_linux:
      self.m.python.failing_step('Mksquashfs only supports linux',
                                 'Only use this for linux builds.')

    binary_path = self.repo_resource('third_party', 'squashfs',
                                     'squashfs-tools', 'mksquashfs')
    if not self.m.path.exists(binary_path):
      self.m.python.failing_step('Mksquashfs is not found',
                                 'Binary not found at %s.' % binary_path)
    self.m.build.python('mksquashfs', self.resource('squashfs_invoke.py'), [
        '--binary-path',
        self.m.path.abspath(binary_path),
        '--folder',
        folder_path,
        '--output-file',
        output_file_path,
    ])
