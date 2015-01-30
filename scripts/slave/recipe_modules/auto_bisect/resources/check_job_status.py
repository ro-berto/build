#!/usr/bin/python
#
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Retrieves the status of a buildbot job and prints its completion status.

The url to the job (via buildbot's json API) is expected as the only CLI
parameter.

For example:
http://build.chromium.org/p/tryserver.chromium.perf/json/builders/mac_perf_bisect_builder/builds/2287
"""

import sys
import urllib2
import json


def main(argv):
  url = sys.argv[1]
  doc = urllib2.urlopen(url).read()
  build_status_dict = json.loads(doc)
  if build_status_dict['currentStep'] is None:
  # TODO(robertocn): Output structured data instead of hardcoded strings
    print 'Complete'
  else:
    print 'In Progress'
  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv))
