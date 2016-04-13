# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import sys
import tempfile

# Install Infra build environment.
BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
                             os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BUILD_ROOT, 'scripts'))

from common import chromium_utils


LOGGER = logging.getLogger('robust_tempdir')


def _ensure_directory(*path):
  path = os.path.join(*path)
  if not os.path.isdir(path):
    os.makedirs(path)
  return path


class RobustTempdir(object):
  """RobustTempdir is a ContextManager that tracks generated files and cleans
  them up at exit.
  """

  def __init__(self, prefix, leak=False):
    """Creates a RobustTempdir.

    Args:
      prefix (str): prefix to use for the temporary directories
      leak (bool): if True, do not remove temporary directories
                   on exit
    """

    self._tempdirs = []
    self._prefix = prefix
    self._leak = leak

  def cleanup(self, path):
    self._tempdirs.append(path)

  def tempdir(self, base=None):
    """Creates a temporary working directory and yields it.

    This creates two levels of directory:
      <base>/<prefix>
      <base>/<prefix>/tmpFOO

    On termination, the entire "<base>/<prefix>" directory is deleted,
    removing the subdirectory created by this instance as well as cleaning up
    any other temporary subdirectories leaked by previous executions.

    Args:
      base (str/None): The directory under which the tempdir should be created.
          If None, the default temporary directory root will be used.
    """
    base = base or tempfile.gettempdir()
    # TODO(phajdan.jr): Clean up leaked directories at the beginning.
    # Doing so should automatically prevent more out-of-disk-space scenarios.
    basedir = _ensure_directory(base, self._prefix)
    self.cleanup(basedir)
    tdir = tempfile.mkdtemp(dir=basedir)
    return tdir

  def __enter__(self):
    return self

  def __exit__(self, _et, _ev, _tb):
    self.close()

  def close(self):
    if self._leak:
      LOGGER.warning('Leaking temporary paths: %s', self._tempdirs)
    else:
      for path in reversed(self._tempdirs):
        try:
          if os.path.isdir(path):
            LOGGER.debug('Cleaning up temporary directory [%s].', path)
            chromium_utils.RemoveDirectory(path)
        except BaseException:
          LOGGER.exception('Failed to clean up temporary directory [%s].',
                           path)
    del(self._tempdirs[:])
