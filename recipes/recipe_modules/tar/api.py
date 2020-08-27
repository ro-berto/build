# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class TarApi(recipe_api.RecipeApi):
  """Provides steps to tar and untar files."""

  def make_package(self, root, output, compression=None):
    """Returns TarPackage object that can be used to compress a set of files.

    Usage:
      pkg = api.tar.make_package(root, output, 'bz2')
      pkg.add_file(root.join('file'))
      pkg.add_directory(root.join('directory'))
      yield pkg.tar('taring step')

    Args:
      root: a directory that would become root of a package, all files added to
          an archive will have archive paths relative to this directory.
      output: path to a tar file to create.

    Returns:
      TarPackage object.
    """
    return TarPackage(self, root, output, compression)

  def directory(self, step_name, directory, output):
    """Step to compress a single directory.

    Args:
      step_name: display name of the step.
      directory: path to a directory to compress, it would become the root of
          an archive, i.e. |directory|/file.txt would be named 'file.txt' in
          the archive.
      output: path to a tar file to create.
    """
    pkg = self.make_package(directory, output)
    pkg.add_directory(directory)
    pkg.tar(step_name)

  def untar(self, step_name, tar_file, output, quiet=False):
    """Step to uncompress |tar_file| into |output| directory.

    Tar package will be unpacked to |output| so that root of an archive is in
    |output|, i.e. archive.tar/file.txt will become |output|/file.txt.

    Step will FAIL if |output| already exists.

    Args:
      step_name: display name of a step.
      tar_file: path to a tar file to uncompress, should exist.
      output: path to a directory to unpack to, it should NOT exist.
      quiet (bool): If True, print terse output instead of the name
          of each untared file.
    """
    script_input = {
      'output': str(output),
      'tar_file': str(tar_file),
      'quiet': quiet,
    }
    self.m.python(
        name=step_name,
        script=self.resource('untar.py'),
        stdin=self.m.json.input(script_input))


class TarPackage(object):
  """Used to gather a list of files to tar."""

  def __init__(self, module, root, output, compression):
    self._module = module
    self._root = root
    self._output = output
    self._compression = compression
    self._entries = []

  @property
  def root(self):
    return self._root

  @property
  def output(self):
    return self._output

  def add_file(self, path, archive_name=None):
    """Stages single file to be added to the package.

    Args:
      path: absolute path to a file, should be in |root| subdirectory.
      archive_name: name of the file in the archive, if non-None
    """
    assert self._root.is_parent_of(path), path
    self._entries.append({
      'type': 'file',
      'path': str(path),
      'archive_name': archive_name
    })

  def add_directory(self, path):
    """Stages a directory with all its content to be added to the package.

    Args:
      path: absolute path to a directory, should be in |root| subdirectory.
    """
    # TODO(phosek): Implement 'exclude' filter.
    assert self._root.is_parent_of(path) or path == self._root, path
    self._entries.append({
      'type': 'dir',
      'path': str(path),
    })

  def tar(self, step_name):
    """Step to tar all staged files."""
    script_input = {
      'entries': self._entries,
      'output': str(self._output),
      'compression': str(self._compression),
      'root': str(self._root),
    }
    step_result = self._module.m.python(
        name=step_name,
        script=self._module.resource('tar.py'),
        stdin=self._module.m.json.input(script_input))
    self._module.m.path.mock_add_paths(self._output)
    return step_result
