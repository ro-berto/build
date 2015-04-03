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
TIMEOUT_INTERVAL = 60 * 60
# Global gsutil path, expected to be set by main.
gsutil_path = ''


def _is_job_url(url):
  """Returns True if the URL looks like a Job and not like an image file.

  A file containing the Buildbot URL is expected to be named as a UUID with no
  extension, unlike an image (a build) which is expected to have an extension.
  """
  filename = url.split('/')[-1]
  if '.' not in filename and len(filename) == 32:
    try:
      _ = int(filename, 16)
      return True
    except ValueError:
      pass
  return False


def _is_gs_url(url):
  return url.lower().startswith('gs://')


def _run_gsutil(cmd):
  # Sleep for a short time between gsutil calls
  time.sleep(SHORT_INTERVAL)
  cmd = [gsutil_path] + cmd
  try:
    out = subprocess.check_output(cmd)
    return 0, out
  except subprocess.CalledProcessError as cpe:
    return cpe.returncode, cpe.output


def _check_buildbot_job(url):
  print "Checking buildbot url:", url
  time.sleep(SHORT_INTERVAL)
  try:
    doc = urllib2.urlopen(url).read()
    build_status_dict = json.loads(doc)
    if build_status_dict['currentStep'] is None:
      print url, " finished."
      return True
  except Exception:
    print "Could not retrieve or parse the buildbot url: ", url
  return False


def _gs_file_exists(url):
  """Checks that running 'gsutil ls' returns 0 to see if file at url exists."""
  return _run_gsutil(['ls', url])[0] == 0


def main(argv):
  if len(argv) < 3:
    usage = "Usage: %s <gsutil path> url1 [url2 [url3...]]"
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
      if _is_gs_url(url):
        if _gs_file_exists(url):
          if _is_job_url(url):
            new_url = _run_gsutil(['cat', url])[1]
            print "Buildbot URL found.", new_url
            urls.append(new_url)
            urls.remove(url)
            continue
          else:
            print 'Build finished: ', url
            return 0
      else:
        # Assuming url is buildbot JSON API
        finished = _check_buildbot_job(url)
        if finished:
          return 0

    if time.time() - start_time > TIMEOUT_INTERVAL:
      print "Timed out waiting for: ", urls
      return 1
    time.sleep(LONG_INTERVAL)
  print "No jobs to check."
  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv))
