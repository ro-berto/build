#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import optparse
import StringIO
import sys
import urllib2
import zipfile


def main():
  parser = optparse.OptionParser(usage='%prog [swarm_server_url]')
  (_, args) = parser.parse_args()

  if len(args) != 1:
    parser.error('Expected 1 argument, got %d.' % len(args))

  swarm_get_code_url = args[0].rstrip('/') + '/get_slave_code'
  try:
    response = urllib2.urlopen(swarm_get_code_url)
  except urllib2.URLError as e:
    logging.error('Unable to download swarm slave code.\n%s', e)
    return 1

  # The response doesn't act exactly like a file so we can't pass it directly
  # to the zipfile reader.
  zipped_contents = StringIO.StringIO(response.read())
  with zipfile.ZipFile(zipped_contents, 'r') as z:
    z.extractall()

  return 0


if __name__ == '__main__':
  sys.exit(main())
