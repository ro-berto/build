#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Fetch the latest results for a pre-selected set of builders we care about.
If we find a 'good' revision -- based on criteria explained below -- we
mark the revision as LKGR, and POST it to the LKGR server:

http://chromium-status.appspot.com/lkgr

We're looking for a sequence in the revision history that looks something
like this:

  Revision        Builder1        Builder2        Builder3
 -----------------------------------------------------------
     12357         green

     12355                                         green

     12352                         green

     12349                                         green

     12345         green


Given this revision history, we mark 12352 as LKGR.  Why?

  - We know 12352 is good for Builder2.
  - Since Builder1 had two green builds in a row, we can be reasonably
    confident that all revisions between the two builds (12346 - 12356,
    including 12352), are also green for Builder1.
  - Same reasoning for Builder3.

To find a revision that meets these criteria, we can walk backward through
the revision history until we get a green build for every builder.  When
that happens, we mark a revision as *possibly* LKGR.  We then continue
backward looking for a second green build on all builders (and no failures).
For all builders that are green on the LKGR candidate itself (12352 in the
example), that revision counts as BOTH the first and second green builds.
Hence, in the example above, we don't look for an actual second green build
of Builder2.

Note that this arrangement is symmetrical; we could also walk forward through
the revisions and run the same algorithm.  Since we are only interested in the
*latest* good revision, we start with the most recent revision and walk
backward.
"""

import json
import multiprocessing
import optparse
import os
import signal
import sys
import threading
import urllib
import urllib2

import buildbot.scripts.runner

VERBOSE = True

BUILDER_URL = 'http://build.chromium.org/p/chromium/json'
REVISIONS_URL = 'https://chromium-status.appspot.com'
WATERFALL_URL = 'http://build.chromium.org/p/chromium/console'
REVISIONS_PASSWORD_FILE = '.status_password'

# LKGR_STEPS controls which steps must pass for a revision to be marked
# as LKGR.
#-------------------------------------------------------------------------------

LKGR_STEPS = {
  'Win Builder (dbg)': [
    'compile',
  ],
  'Vista Tests (dbg)(1)': [
    'check_deps',
    'base_unittests',
    'cacheinvalidation_unittests',
    'courgette_unittests',
    'googleurl_unittests',
    'jingle_unittests',
    'media_unittests',
    'printing_unittests',
    'remoting_unittests',
    'ipc_tests',
    'sql_unittests',
    'sync_unit_tests',
    'unit_tests',
    'installer_util_unittests',
    'gfx_unittests',
    'crypto_unittests',
  ],
  'Vista Tests (dbg)(2)': [
    'net_unittests', 'ui_tests', 'browser_tests',
  ],
  'Vista Tests (dbg)(3)': [
    'ui_tests', 'browser_tests',
  ],
  'Vista Tests (dbg)(4)': [
    'ui_tests', 'browser_tests',
  ],
  'Vista Tests (dbg)(5)': [
    'ui_tests', 'browser_tests',
  ],
  'Vista Tests (dbg)(6)': [
    'ui_tests', 'browser_tests',
  ],
  'Chrome Frame Tests (ie8)': [
    'chrome_frame_net_tests', 'chrome_frame_unittests',
  ],
  'Interactive Tests (dbg)': [
    'interactive_ui_tests',
  ],
  'Mac Builder (dbg)': [
    'compile',
  ],
  'Mac 10.5 Tests (dbg)(1)': [
    'browser_tests',
    'check_deps',
    'googleurl_unittests',
    'media_unittests',
    'printing_unittests',
    'remoting_unittests',
    'interactive_ui_tests',
    'ui_tests',
    'jingle_unittests',
  ],
  'Mac 10.5 Tests (dbg)(2)': [
    'browser_tests', 'net_unittests', 'ui_tests',
  ],
  'Mac 10.5 Tests (dbg)(3)': [
    'base_unittests', 'browser_tests', 'ui_tests',
  ],
  'Mac 10.5 Tests (dbg)(4)': [
    'browser_tests',
    'gfx_unittests',
    'ipc_tests',
    'sql_unittests',
    'sync_unit_tests',
    'ui_tests',
    'unit_tests',
  ],
  'Linux Builder (dbg)': [
    'compile',
  ],
  'Linux Tests (dbg)(1)': [
    'check_deps',  'browser_tests', 'net_unittests',
  ],
  'Linux Tests (dbg)(2)': [
    'ui_tests',
    'ipc_tests',
    'sync_unit_tests',
    'unit_tests',
    'sql_unittests',
    'interactive_ui_tests',
    'base_unittests',
    'googleurl_unittests',
    'media_unittests',
    'printing_unittests',
    'remoting_unittests',
    'gfx_unittests',
    'nacl_integration',
    'nacl_ui_tests',
    'nacl_sandbox_tests',
    'cacheinvalidation_unittests',
    'jingle_unittests',
  ],
  'Linux Builder (ChromiumOS)': [
    'compile',
    'base_unittests',
    'googleurl_unittests',
    'media_unittests',
    'net_unittests',
    'printing_unittests',
    'remoting_unittests',
    'ipc_tests',
    'sync_unit_tests',
    'unit_tests',
    'sql_unittests',
    'gfx_unittests',
    'jingle_unittests',
  ]
}

#-------------------------------------------------------------------------------

def VerbosePrint(s):
  if VERBOSE:
    print s

def FetchBuildsMain(builder, builds):
  url = '%s/builders/%s/builds/_all' % (BUILDER_URL, urllib2.quote(builder))
  try:
    url_fh = urllib2.urlopen(url, None, 60)
    builder_history = json.load(url_fh)
    url_fh.close()
    builds[builder] = builder_history
  except urllib2.URLError:
    VerbosePrint('URLException while fetching %s' % url)

def CollateRevisionHistory(builds):
  """Organize builder data into:
  build_history = [ (revision, {builder: True/False, ...}), ... ]
  ... and sort revisions chronologically, latest revision first
  """
  # revision_history[revision][builder] = True/False (success/failure)
  revision_history = {}
  for (builder, builder_history) in builds.iteritems():
    VerbosePrint('%s:' % builder)
    for (build_num, build_data) in builder_history.iteritems():
      build_num = int(build_num)
      revision = build_data['sourceStamp']['revision']
      if not revision:
        continue
      steps = {}
      reasons = []
      for step in build_data['steps']:
        steps[step['name']] = step
      for step in LKGR_STEPS[builder]:
        assert step in steps
        if ('isFinished' not in steps[step] or
           steps[step]['isFinished'] is not True):
          reasons.append('Step %s has not completed (%s)' % (
              step, steps[step]['isFinished']))
          continue
        if 'results' in steps[step]:
          result = steps[step]['results'][0]
          if type(result) == list:
            result = result[0]
          if result and str(result) != '0':
            reasons.append('Step %s failed' % step)
      revision_history.setdefault(revision, {})
      if reasons:
        revision_history[revision][builder] = False
        VerbosePrint('  Build %s (rev %s) is bad or incomplete' % (
            build_num, revision))
        for reason in reasons:
          VerbosePrint('    %s' % reason)
      else:
        revision_history[revision][builder] = True

  # Need to fix the sort for git
  # pylint: disable=W0108
  sorted_keys = sorted(revision_history.keys(), None, lambda x: int(x), True)
  build_history = [(rev, revision_history[rev]) for rev in sorted_keys]

  return build_history

def FindLKGRCandidate(build_history):
  """Given a build_history of builds, run the algorithm for finding an LKGR
  candidate (refer to the algorithm description at the top of this script).
  green1 and green2 record the sequence of two successful builds that are
  required for LKGR.
  """
  candidate = -1
  green1 = {}
  green2 = {}
  num_builders = len(LKGR_STEPS)

  for entry in build_history:
    if len(green2) == num_builders:
      break
    revision = entry[0]
    history = entry[1]
    if candidate == -1:
      for (builder, status) in history.iteritems():
        if not status:
          candidate = -1
          green1.clear()
          break
        green1[builder] = revision
      if len(green1) == num_builders:
        candidate = revision
        for builder in history.keys():
          green2[builder] = revision
      continue
    for (builder, status) in history.iteritems():
      if not status:
        candidate = -1
        green1.clear()
        green2.clear()
        break
      green2[builder] = revision

  if candidate != -1 and len(green2) == num_builders:
    VerbosePrint('-' * 80)
    VerbosePrint('Revision %s is good based on:' % candidate)
    revlist = list(green2.iteritems())
    revlist.sort(None, lambda x: x[1])
    for (builder, revision) in revlist:
      VerbosePrint('  Revision %s is green for builder %s' %
                   (revision, builder))
    VerbosePrint('-' * 80)
    revlist = list(green1.iteritems())
    revlist.sort(None, lambda x: x[1])
    for (builder, revision) in revlist:
      VerbosePrint('  Revision %s is green for builder %s' %
                   (revision, builder))
    return candidate

  return -1

def PostLKGR(lkgr, password_file, dry):
  url = '%s/revisions' % REVISIONS_URL
  VerbosePrint('Posting to %s...' % url)
  try:
    password_fh = open(password_file, 'r')
    password = password_fh.read().strip()
    password_fh.close()
  except IOError:
    print >> sys.stdout, 'Could not read password file %s' % password_file
    print >> sys.stdout, 'Aborting upload'
    return
  params = {
    'revision': lkgr,
    'success': 1,
    'password': password
  }
  params = urllib.urlencode(params)
  print params
  if not dry:
    request = urllib2.urlopen(url, params)
    request.close()
  VerbosePrint('Done!')

def NotifyMaster(master, lkgr, dry=False):
  def _NotifyMain():
    sys.argv = [
        'buildbot', 'sendchange',
        '--master', master,
        '--revision', lkgr,
        '--branch', 'src',
        '--user', 'lkgr',
        '--category', 'lkgr',
        'no file information']
    if dry:
      return
    buildbot.scripts.runner.run()

  p = multiprocessing.Process(None, _NotifyMain, 'notify-%s' % master)
  p.start()
  p.join(5)
  if p.is_alive():
    print >> sys.stdout, 'Timeout while notifying %s' % master
    # p.terminate() can hang; just obliterate the sucker.
    os.kill(p.pid, signal.SIGKILL)

def main():
  opt_parser = optparse.OptionParser()
  opt_parser.add_option('-q', '--quiet', default=False,
                        dest='quiet', action='store_true',
                        help='Suppress verbose output to stdout')
  opt_parser.add_option('-n', '--dry-run', default=False,
                        dest='dry', action='store_true',
                        help="Don't actually upload new LKGR")
  opt_parser.add_option('--post', default=False,
                        dest='post', action='store_true',
                        help='Upload new LKGR to chromium-status app')
  opt_parser.add_option('--password-file', default=REVISIONS_PASSWORD_FILE,
                        dest='pwfile', metavar='FILE',
                        help='File containing password for chromium-status app')
  opt_parser.add_option('--notify', default=[],
                        action='append', metavar='HOST:PORT',
                        help='Notify this master when a new LKGR is found')
  options, args = opt_parser.parse_args()

  if args:
    opt_parser.print_usage()
    sys.exit(1)

  global VERBOSE
  VERBOSE = not options.quiet

  builds = {}
  fetch_threads = []
  lkgr = -1

  for builder in LKGR_STEPS.keys():
    th = threading.Thread(target=FetchBuildsMain,
                          name='Fetch %s' % builder,
                          args=(builder, builds))
    th.start()
    fetch_threads.append(th)

  lkgr_url = '%s/lkgr' % REVISIONS_URL
  try:
    url_fh = urllib2.urlopen(lkgr_url, None, 60)
    # Fix for git
    lkgr = int(url_fh.read())
    url_fh.close()
  except urllib2.URLError:
    VerbosePrint('URLException while fetching %s' % lkgr_url)
    return 1

  for th in fetch_threads:
    th.join()

  build_history = CollateRevisionHistory(builds)
  candidate = FindLKGRCandidate(build_history)

  VerbosePrint('-' * 80)
  VerbosePrint('LKGR=%d' % lkgr)
  VerbosePrint('-' * 80)
  # Fix for git
  if candidate != -1 and int(candidate) > lkgr:
    VerbosePrint('Revision %s is new LKGR' % candidate)
    formdata = ['builder=%s' % urllib2.quote(x) for x in LKGR_STEPS.keys()]
    formdata = '&'.join(formdata)
    waterfall = '%s?%s' % (WATERFALL_URL, formdata)
    VerbosePrint('Waterfall URL:')
    VerbosePrint(waterfall)
    if options.post:
      PostLKGR(candidate, options.pwfile, options.dry)
    for master in options.notify:
      NotifyMaster(master, candidate, options.dry)
  else:
    VerbosePrint('No newer LKGR found than current %s' % lkgr)
  VerbosePrint('-' * 80)

  return 0

if __name__ == '__main__':
  sys.exit(main())
