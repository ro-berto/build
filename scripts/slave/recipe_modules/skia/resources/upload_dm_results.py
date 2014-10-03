#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Upload DM output PNG files and JSON summary to Google Storage."""

import datetime
import os
import shutil
import sys
import tempfile

from slave.skia import gs_utils

def main(dm_dir, git_hash, builder_name, build_number, try_issue):
  """Upload DM output PNG files and JSON summary to Google Storage.

    dm_dir:        path to PNG files and JSON summary    (str)
    git_hash:      this build's Git hash                 (str)
    builder_name:  name of this builder                  (str)
    build_number:  nth build on this builder             (str or int)
    try_issue:     Rietveld issue if this is a try job   (str, int, or None)
  """
  # Private, but Google-readable.
  ACL = gs_utils.GSUtils.PredefinedACL.PRIVATE
  FINE_ACLS = [(
    gs_utils.GSUtils.IdType.GROUP_BY_DOMAIN,
    'google.com',
    gs_utils.GSUtils.Permission.READ
  )]

  # Move dm.json to its own directory to make uploading it easier.
  tmp = tempfile.mkdtemp()
  shutil.move(os.path.join(dm_dir, 'dm.json'),
              os.path.join(tmp,    'dm.json'))

  # /dm-json-v1/year/month/day/hour/git-hash/builder/build-number/dm.json
  now = datetime.datetime.now()
  summary_dest_dir = '/'.join(['dm-json-v1',
                               str(now.year ).zfill(4),
                               str(now.month).zfill(2),
                               str(now.day  ).zfill(2),
                               str(now.hour ).zfill(2),
                               git_hash,
                               builder_name,
                               str(build_number)])

  # Trybot results are further siloed by CL.
  if try_issue:
    summary_dest_dir = '/'.join(['trybot', summary_dest_dir, str(try_issue)])

  # Upload the JSON summary.
  gs = gs_utils.GSUtils()
  gs.upload_dir_contents(tmp,
                         'chromium-skia-gm',
                         summary_dest_dir,
                         predefined_acl = ACL,
                         fine_grained_acl_list = FINE_ACLS)

  # Only images are left in dm_dir.  Upload any new ones.
  gs.upload_dir_contents(dm_dir,
                         'chromium-skia-gm',
                         'dm-images-v1',
                         upload_if = gs.UploadIf.IF_NEW,
                         predefined_acl = ACL,
                         fine_grained_acl_list = FINE_ACLS)

  # Just for hygiene, put dm.json back.
  shutil.move(os.path.join(tmp,    'dm.json'),
              os.path.join(dm_dir, 'dm.json'))
  os.rmdir(tmp)


if '__main__' == __name__:
  main(*sys.argv[1:])
