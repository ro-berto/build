#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Copy a directory and ignore some paths.

This copies directories and files without access stats.
"""

import os
import shutil
import sys


# This is python's implementation of shutil.copytree with some modifications
# and simplifications. Under PSF license:
# https://docs.python.org/2/library/shutil.html#copytree-example
# Changes: Removed symlink option, don't call copystat on directories and use
# copy instead of copy2 to not copy file stats.
def copytree(src, dst, ignore):
  names = os.listdir(src)
  ignored_names = ignore(src, names)

  os.makedirs(dst)
  errors = []
  for name in names:
    if name in ignored_names:
      continue
    srcname = os.path.join(src, name)
    dstname = os.path.join(dst, name)
    try:
      if os.path.isdir(srcname):
        copytree(srcname, dstname, ignore)
      else:
        shutil.copy(srcname, dstname)
    except (IOError, os.error) as why:
      errors.append((srcname, dstname, str(why)))
    except shutil.Error as err:
      errors.extend(err.args[0])
  if errors:
    raise shutil.Error(errors)


def ignore(p, files):
  return [
    f for path in sys.argv[3:]
      for f in files
        if (os.path.abspath(os.path.join(p, f)) == path or
            f == path)]


copytree(sys.argv[1], sys.argv[2], ignore)