# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api


class FileApi(recipe_api.RecipeApi):
  """FileApi contains helper functions for reading and writing files."""

  def __init__(self, **kwargs):
    super(FileApi, self).__init__(**kwargs)

  def read(self, name, path, test_data=None):
    """Read a file and return its contents."""
    kwargs = {}
    if test_data is not None:
      kwargs['step_test_data'] = (
          lambda: self.m.raw_io.test_api.output(test_data)
      )

    return self.m.python.inline(
        name,
        """
        import shutil
        import sys
        shutil.copy(sys.argv[1], sys.argv[2])
        """,
        args=[path, self.m.raw_io.output()],
        add_python_log=False,
        **kwargs
    ).raw_io.output

  def write(self, name, path, data, **kwargs):
    """Write the given data to a file."""
    return self.m.python.inline(
        name,
        """
        import shutil
        import sys
        shutil.copy(sys.argv[1], sys.argv[2])
        """,
        args=[self.m.raw_io.input(data), path],
        **kwargs
    )

