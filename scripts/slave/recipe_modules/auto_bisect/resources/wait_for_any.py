#!/usr/bin/python
#
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Waits for any one job out of a list to complete or a default timeout."""

import json
import subprocess
import sys
import time
import urllib2


# The following intervals are specified in seconds, are expected to be sent as
# arguments to time.sleep()
# All URLs are checked in sequence separated by 'short' interval seconds, to
# prevent possibly getting throttled by whatever endpoint gsutil or urllib are
# hitting.
SHORT_INTERVAL = 0.4
# If none of the URLs is determined to be ready, we sleep for a 'long'
# interval.
LONG_INTERVAL = 60
# If the 'timeout' interval elapses without any URL becoming ready, we fail.
timeout_interval = 60 * 60
# Global gsutil path, expected to be set by main.
gsutil_path = ''


def _run_gsutil(cmd):
  # Sleep for a short time between gsutil calls
  time.sleep(SHORT_INTERVAL)
  cmd = [gsutil_path] + cmd
  try:
    out = subprocess.check_output(cmd)
    return 0, out
  except subprocess.CalledProcessError as cpe:
    return cpe.returncode, cpe.output


def _gs_file_exists(url):
  """Checks that running 'gsutil ls' returns 0 to see if file at url exists."""
  return _run_gsutil(['ls', url])[0] == 0


def main(argv):
  global timeout_interval
  if argv[-1].startswith('--timeout='):
    timeout_interval = int(argv[-1].split('=')[1])
    argv = argv[:-1]

  if len(argv) < 3:
    usage = "Usage: %s <gsutil path> url1 [url2 [url3...]] [--timeout=<seconds>]"
    print usage % argv[0]
    return 1

  list_of_urls = ', '.join(['<%s>' % url for url in argv[2:]])
  print 'Waiting for the following urls: ' + list_of_urls
  global gsutil_path
  start_time  = time.time()
  gsutil_path = argv[1]
  urls = argv[2:]
  while urls:
    for url in urls:
      if _gs_file_exists(url):
          print 'Build finished: ', url
          return 0
    if time.time() - start_time > timeout_interval:
      print "Timed out waiting for: ", urls
      return 1
    time.sleep(LONG_INTERVAL)
  print "No jobs to check."
  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv))
