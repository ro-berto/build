# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of common operations/utilities for build archiving."""

import os


# Base name of the database of files to archive.
FILES_FILENAME = 'FILES.cfg'


class StagingError(Exception):
  pass


def ParseFilesList(files_file, buildtype, arch):
  """Determine the list of archive files for a given release.

  NOTE: A version of this handling is also in
  build-internal/scripts/slave-internal/branched/stage_build.py
  so be sure to update that if this is updated.
  """
  if not os.path.exists(files_file):
    raise StagingError('Files list does not exist (%s).' % files_file)
  exec_globals = {'__builtins__': None}

  files_list = None
  execfile(files_file, exec_globals)
  files_list = [
      fileobj['filename'] for fileobj in exec_globals['FILES']
      if (buildtype in fileobj['buildtype'] and arch in fileobj['arch'] and
          not fileobj.get('archive'))
  ]
  return files_list
