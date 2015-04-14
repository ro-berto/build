# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api


class FileApi(recipe_api.RecipeApi):
  """FileApi contains helper functions for reading and writing files."""

  def __init__(self, **kwargs):
    super(FileApi, self).__init__(**kwargs)

  def copy(self, name, source, dest, step_test_data=None):
    """Copy a file."""
    return self.m.python.inline(
        name,
        """
        import shutil
        import sys
        shutil.copy(sys.argv[1], sys.argv[2])
        """,
        args=[source, dest],
        add_python_log=False,
        step_test_data=step_test_data
    )

  def copytree(self, name, source, dest, **kwargs):
    """Run shutil.copytree in a step."""
    return self.m.python.inline(
        name,
        """
        import shutil
        import sys
        shutil.copytree(sys.argv[1], sys.argv[2])
        """,
        args=[source, dest],
        add_python_log=False,
        **kwargs
    )

  def read(self, name, path, test_data=None):
    """Read a file and return its contents."""
    step_test_data = None
    if test_data is not None:
      step_test_data = lambda: self.m.raw_io.test_api.output(test_data)
    return self.copy(name, path, self.m.raw_io.output(),
                     step_test_data=step_test_data).raw_io.output

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
        add_python_log=False,
        **kwargs
    )

  def glob(self, name, pattern, test_data=None, **kwargs):
    """Performs glob search on a directory.

    Returns list of files found.
    """
    step_test_data = None
    if test_data is not None:
      step_test_data = (
          lambda: self.m.raw_io.test_api.output('\n'.join(map(str, test_data))))
    step_result = self.m.python.inline(
        name,
        r"""
        import glob
        import sys
        with open(sys.argv[1], 'w') as f:
          f.write('\n'.join(glob.glob(sys.argv[2])))
        """,
        args=[self.m.raw_io.output(), pattern],
        step_test_data=step_test_data,
        add_python_log=False,
        **kwargs
    )
    return step_result.raw_io.output.splitlines()

  def remove(self, name, path, **kwargs):
    """Remove the given file."""
    return self.m.python.inline(
        name,
        """
        import os
        import sys
        os.remove(sys.argv[1])
        """,
        args=[path],
        **kwargs
    )

