#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import signal
import sys
import time
import urllib2

from common import chromium_utils

PID_PATH = os.path.realpath(__file__) + '.pid'

# Trigger the buildbot when LKGR is updated.
def TriggerBot(revision):
  buildbot_runner = os.path.join(os.path.dirname(PID_PATH), 'buildbot')
  cmd = ['python', buildbot_runner, 'sendchange',
         '--master', 'localhost:8118',
         '--revision', revision,
         '--branch', 'src',
         '--username', 'lkgr',
         '--category', 'lkgr',
         'no file information']
  print cmd
  ret = chromium_utils.RunCommand(cmd)
  print "Returned %d" % ret

def main():
  # Make sure the master can kill us by writing a pid file.
  if os.path.exists(PID_PATH):
    print "Poller already running or you have a stale %s file" % PID_PATH
    sys.exit(1)

  pid_file = open(PID_PATH, 'w')
  pid_file.write(str(os.getpid()))
  pid_file.close()

  # Poll LKGR every 90 seconds. Trigger the buildbot when it changes.  
  revision = None
  while True:
    try:
      lkgr_file = urllib2.urlopen('http://chromium-status.appspot.com/lkgr')
      lkgr = lkgr_file.read()
      lkgr_file.close()
      if revision is None:
        # We don't know if we already triggered this build.
        # Skipping this revision.
        print "Set initial LKGR revision to " + lkgr
        revision = lkgr
      
      if lkgr != revision:
        # LKGR got updated. Triggering the bots.
        revision = lkgr
        TriggerBot(revision)

    except urllib2.HTTPError, e:
      print "Failed to read LKGR - HTTP error " + str(e.code)

    except urllib2.URLError, e:
      print "Failed to read LKGR - URL error " + e.reason
  
    time.sleep(90)

# We are going away. Delete the PID file.
def clean(*args):
  if os.path.exists(PID_PATH):
    os.remove(PID_PATH)
  sys.exit(0)

if '__main__' == __name__:
  for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, clean)
    
  main()
