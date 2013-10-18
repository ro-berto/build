# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class ArchiveApi(recipe_api.RecipeApi):
  def tar(self, step_name, tar_file, components, **kwargs):
    assert isinstance(components, list)
    assert len(components)
    return self.m.python.inline(
        step_name,
        """
          import sys
          import tarfile

          tar = tarfile.open(sys.argv[1], 'w')
          for arg in sys.argv[2:]:
            tar.add(arg)
          tar.close()
        """,
        args=[tar_file] + components,
        **kwargs)
      
  def untar(self, step_name, tar_file, dest=None, **kwargs):
    args = [tar_file]
    if dest:
      args.append(dest)
    return self.m.python.inline(
        step_name,
        """
          import sys
          import tarfile

          tar = tarfile.open(sys.argv[1], 'r')
          dest = '.'
          if len(sys.argv) == 3:
            dest = sys.argv[2]
          tar.extractall(dest)
          tar.close()
        """,
        args=args,
        **kwargs)
