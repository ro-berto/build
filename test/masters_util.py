# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Buildbot master utility functions.
"""

from __future__ import with_statement
import logging
import os
import time
import urllib

import find_depot_tools  # pylint: disable=W0611
import subprocess2
from rietveld import json


def start_master(master, path):
  try:
    subprocess2.check_call(
        ['make', 'start'], timeout=60, cwd=path,
        stderr=subprocess2.STDOUT)
  except subprocess2.CalledProcessError:
    logging.error('Error: cannot start %s' % master)
    return False
  return True


def stop_master(master, path):
  if not os.path.isfile(os.path.join(path, 'twistd.pid')):
    return True
  try:
    subprocess2.check_output(
        ['make', 'stop'], timeout=60, cwd=path,
        stderr=subprocess2.STDOUT)
    for _ in range(100):
      if not os.path.isfile(os.path.join(path, 'twistd.pid')):
        return True
      time.sleep(0.1)
    return False
  except subprocess2.CalledProcessError, e:
    if 'No such process' in e.stdout:
      logging.warning('Flushed ghost twistd.pid for %s' % master)
      os.remove(os.path.join(path, 'twistd.pid'))
      return True
    return False


def search_for_exceptions(path):
  """Looks in twistd.log for an exception.

  Returns True if an exception is found.
  """
  twistd_log = os.path.join(path, 'twistd.log')
  with open(twistd_log) as f:
    lines = f.readlines()
    stripped_lines = [l.strip() for l in lines]
    try:
      i = stripped_lines.index('--- <exception caught here> ---')
      # Found an exception at line 'i'!  Now find line 'j', the number
      # of lines from 'i' where there's a blank line.  If we cannot find
      # a blank line, then we will show up to 10 lines from i.
      try:
        j = stripped_lines[i:-1].index('')
      except ValueError:
        j = 10
      # Print from either 15 lines back from i or the start of the log
      # text to j lines after i.
      print ''.join(lines[max(i-15, 0):i+j])
      return True
    except ValueError:
      pass
  return False


def wait_for_start(master, name, path):
  """Waits for ~10s for the masters to open its web server."""
  ports = range(8000, 8080) + range(8200, 8240) + range(9000, 9080)
  for _ in range(100):
    for p in ports:
      try:
        data = json.load(
            urllib.urlopen('http://localhost:%d/json/project' % p)) or {}
        if not data or (not 'projectName' in data and not 'title' in data):
          logging.debug('Didn\'t get valid data from %s' % master)
          continue
        got_name = data.get('projectName', data.get('title'))
        if got_name != name:
          logging.error(
              'Wrong %s name, expected %s, got %s' %
              (master, name, got_name))
          return False
        # The server is now answering /json requests. Check that the log file
        # doesn't have any other exceptions just in case there was some other
        # unexpected error.
        return not search_for_exceptions(path)
      except ValueError:
        logging.warning('Didn\'t get valid data from %s' % master)
      except IOError:
        logging.debug('Didn\'t get data from %s' % master)
      if search_for_exceptions(path):
        return False
    time.sleep(0.1)
  logging.error('Didn\'t find open port for %s' % master)
  return False
