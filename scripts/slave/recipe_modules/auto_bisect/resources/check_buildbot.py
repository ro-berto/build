#!/usr/bin/python
#
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Checks buildbot jobs by name."""

import json
import os
import subprocess
import sys
import time
import urllib2

BASE_URL = ('https://build.chromium.org/p/%(master)s/json/builders/%(builder)s/'
            'builds/_all?as_text=1&filter=0')
LINK_URL = ('https://build.chromium.org/p/%(master)s/builders/%(builder)s/'
            'builds/%(build_num)s')


def _get_build_name(job):
  for property_tuple in job['properties']:
    if property_tuple[0] == 'job_name':
      return property_tuple[1]


def main(argv):
  if len(argv) < 4:
    print 'Usage: %s <master> <builder> <job_name1> [<job_name2> [...]]'
    print '  e.g. %s tryserver.chromium.perf linux_perf_bisector a012bc66ef98bb'
    sys.exit(1)

  master, builder = argv[1:3]
  job_names = argv[3:]

  if 'TESTING_MASTER_HOST' in os.environ:
    url = ('http://%(host)s:8041/json/builders/%(builder)s/'
           'builds/_all?as_text=1&filter=0') % {
               'host': os.environ['TESTING_MASTER_HOST'],
               'builder': builder,
            }
  else:
    url = BASE_URL % {'master': master, 'builder': builder}
  print 'Verifying buildbot jobs status at: ', url
  builds_info = json.load(urllib2.urlopen(url))

  for build_num in builds_info.keys():
    build_name = _get_build_name(builds_info[build_num])
    if build_name in job_names:
      if builds_info[build_num]['results'] in [2, 4]:
        locator = 'bb:%s:%s:%s' % (master, builder, build_name)
        print 'Failed build url: %(url)s\nBuild failed: %(locator)s' % {
            'locator': locator,
            'url': LINK_URL % {
                'master': master,
                'builder': builder,
                'build_num': build_num,
              }
            }
        return 1
  print 'The specified jobs are not failed.'
  return 0



if __name__ == '__main__':
  sys.exit(main(sys.argv))
