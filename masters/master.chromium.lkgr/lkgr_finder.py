#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
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

# The 2 following modules are not present on python 2.5
# pylint: disable=F0401
import datetime
import json
import multiprocessing
import optparse
import os
import re
import signal
import smtplib
import socket
import subprocess
import sys
import threading
import urllib
import urllib2


VERBOSE = True
EMAIL_ENABLED = False

REVISIONS_URL = 'https://chromium-status.appspot.com'
REVISIONS_PASSWORD_FILE = '.status_password'
MASTER_TO_BASE_URL = {
  'chromium': 'http://build.chromium.org/p/chromium',
  'chromium.chrome': 'http://build.chromium.org/p/chromium.chrome',
  'chromium.linux': 'http://build.chromium.org/p/chromium.linux',
  'chromium.mac': 'http://build.chromium.org/p/chromium.mac',
  'chromium.win': 'http://build.chromium.org/p/chromium.win',
}

# LKGR_STEPS controls which steps must pass for a revision to be marked
# as LKGR.
#-------------------------------------------------------------------------------

LKGR_STEPS = {
  'chromium.win': {
    'Win Builder (dbg)': [
      'compile',
    ],
    'Win7 Tests (dbg)(1)': [
      'base_unittests',
      'cacheinvalidation_unittests',
      'cc_unittests',
      'check_deps',
      'chromedriver2_unittests',
      'components_unittests',
      'content_unittests',
      'courgette_unittests',
      'crypto_unittests',
      'googleurl_unittests',
      'installer_util_unittests',
      'ipc_tests',
      'jingle_unittests',
      'media_unittests',
      'ppapi_unittests',
      'printing_unittests',
      'remoting_unittests',
      'sql_unittests',
      'sync_unit_tests',
      'ui_unittests',
      'unit_tests',
      'webkit_compositor_bindings_unittests',
    ],
    'Win7 Tests (dbg)(2)': [
      'net_unittests', 'browser_tests',
    ],
    'Win7 Tests (dbg)(3)': [
      'browser_tests',
    ],
    'Win7 Tests (dbg)(4)': [
      'browser_tests',
    ],
    'Win7 Tests (dbg)(5)': [
      'browser_tests',
    ],
    'Win7 Tests (dbg)(6)': [
      'browser_tests',
    ],
    'Chrome Frame Tests (ie8)': [
      'chrome_frame_tests',
      'chrome_frame_unittests',
    ],
    # 'Interactive Tests (dbg)': [
    #   'interactive_ui_tests',
    # ],
    'Win Aura Builder': [
      'compile',
    ],
    'Win Aura Tests (1)': [
      'ash_unittests',
      'aura_unittests',
      'browser_tests',
      'content_browsertests',
    ],
    'Win Aura Tests (2)': [
      'browser_tests',
      'compositor_unittests',
      'content_unittests',
      'unit_tests',
      'views_unittests',
    ],
    'Win Aura Tests (3)': [
      'browser_tests',
      'interactive_ui_tests',
    ],
  },  # chromium.win
  'chromium.mac': {
    'Mac Builder (dbg)': [
      'compile',
    ],
    'Mac 10.6 Tests (dbg)(1)': [
      'browser_tests',
      'cc_unittests',
      'chromedriver2_unittests',
      'googleurl_unittests',
      'ppapi_unittests',
      'printing_unittests',
      'remoting_unittests',
      'jingle_unittests',
      'webkit_compositor_bindings_unittests',
    ],
    'Mac 10.6 Tests (dbg)(2)': [
      'browser_tests',
      'check_deps',
      'media_unittests',
      'net_unittests',
    ],
    'Mac 10.6 Tests (dbg)(3)': [
      'base_unittests', 'browser_tests', 'interactive_ui_tests',
    ],
    'Mac 10.6 Tests (dbg)(4)': [
      'browser_tests',
      'components_unittests',
      'content_unittests',
      'ipc_tests',
      'sql_unittests',
      'sync_unit_tests',
      'ui_unittests',
      'unit_tests',
    ],
    'iOS Device': [
      'compile',
    ],
    'iOS Simulator (dbg)': [
      'compile',
      'base_unittests',
      'content_unittests',
      'crypto_unittests',
      'googleurl_unittests',
      'media_unittests',
      'net_unittests',
      'sql_unittests',
      'sync_unit_tests',
      'ui_unittests',
      'unit_tests',
    ],
  },  # chromium.mac
  'chromium.linux': {
    'Linux Builder (dbg)': [
      'compile',
    ],
    'Linux Builder (dbg)(32)': [
      'compile',
    ],
    'Linux Builder': [
      'check_deps',
    ],
    # TODO(phajdan.jr): Add 32-bit Linux Precise testers to LKGR.
    'Linux Tests (dbg)(1)': [
      'browser_tests',
      'net_unittests',
    ],
    'Linux Tests (dbg)(2)': [
      'base_unittests',
      'cacheinvalidation_unittests',
      'cc_unittests',
      'chromedriver2_unittests',
      'components_unittests',
      'content_unittests',
      'googleurl_unittests',
      'interactive_ui_tests',
      'ipc_tests',
      'jingle_unittests',
      'media_unittests',
      'nacl_integration',
      'ppapi_unittests',
      'printing_unittests',
      'remoting_unittests',
      'sql_unittests',
      'sync_unit_tests',
      'ui_unittests',
      'unit_tests',
      'webkit_compositor_bindings_unittests',
    ],
    'Linux Aura': [
      'aura_unittests',
      'base_unittests',
      'browser_tests',
      'cacheinvalidation_unittests',
      'compile',
      'compositor_unittests',
      'content_browsertests',
      'content_unittests',
      'crypto_unittests',
      'device_unittests',
      'googleurl_unittests',
      'gpu_unittests',
      'ipc_tests',
      'interactive_ui_tests',
      'jingle_unittests',
      'media_unittests',
      'net_unittests',
      'ppapi_unittests',
      'printing_unittests',
      'remoting_unittests',
      'sync_unit_tests',
      'ui_unittests',
      'unit_tests',
      'views_unittests',
    ],
    'Android Builder (dbg)': [
      'slave_steps',
    ],
    'Android Tests (dbg)': [
      'slave_steps',
    ],
    'Android Builder': [
      'slave_steps',
    ],
    'Android Tests': [
      'slave_steps',
    ],
    'Android Clang Builder (dbg)': [
      'slave_steps',
    ],
  },  # chromium.linux
  'chromium.chrome': {
    'Google Chrome Linux x64': [  # cycle time is ~14 mins as of 5/5/2012
      'compile',
    ],
  },  # chromium.chrome
}

#-------------------------------------------------------------------------------

def SendMail(sender, recipients, subject, message):
  if not EMAIL_ENABLED:
    return
  try:
    body = ['From: %s' % sender]
    body.append('To: %s' % recipients)
    body.append('Subject: %s' % subject)
    # Default to sending replies to the recipient list, not the account running
    # the script, since that's probably just a role account.
    body.append('Reply-To: %s' % recipients)
    body.append('')
    body.append(message)
    server = smtplib.SMTP('localhost')
    server.sendmail(sender, recipients.split(','), '\n'.join(body))
    server.quit()
  except Exception as e:
    # If smtp fails, just dump the output. If running under cron, that will
    # capture the output and send its own (ugly, but better than nothing) email.
    print message
    print ('\n--------- Exception in %s -----------\n' %
           os.path.basename(__file__))
    raise e

run_log = []

def FormatPrint(s):
  return '%s: %s' % (datetime.datetime.now(), s)

def Print(s):
  msg = FormatPrint(s)
  run_log.append(msg)
  print msg

def VerbosePrint(s):
  if VERBOSE:
    Print(s)
  else:
    run_log.append(FormatPrint(s))

def FetchBuildsMain(master, builder, builds):
  if master not in MASTER_TO_BASE_URL:
    raise Exception('ERROR: master %s not in MASTER_TO_BASE_URL' % master)
  master_url = MASTER_TO_BASE_URL[master]
  url = '%s/json/builders/%s/builds/_all' % (master_url, urllib2.quote(builder))
  try:
    # Requires python 2.6
    # pylint: disable=E1121
    url_fh = urllib2.urlopen(url, None, 600)
    builder_history = json.load(url_fh)
    url_fh.close()
    # check_deps was moved to Linux Builder x64 at build 39789.  Ignore
    # builds older than that.
    if builder == 'Linux Builder x64':
      for build in builder_history.keys():
        if int(build) < 39789:
          Print('removing build %s from Linux Build x64' % build)
          del builder_history[build]
    # Note that builds will be modified concurrently by multiple threads.
    # That's safe for simple modifications like this, but don't iterate builds.
    builds[builder] = builder_history
  except urllib2.URLError:
    VerbosePrint('URLException while fetching %s' % url)

def FetchLKGR():
  lkgr_url = '%s/lkgr' % REVISIONS_URL
  try:
    # pylint: disable=E1121
    url_fh = urllib2.urlopen(lkgr_url, None, 60)
  except urllib2.URLError:
    VerbosePrint('URLException while fetching %s' % lkgr_url)
    return
  try:
     # TODO: Fix for git: git revisions can't be converted to int.
    return int(url_fh.read())
  finally:
    url_fh.close()

def FetchBuildData():
  builds = dict((master, {}) for master in MASTER_TO_BASE_URL)
  fetch_threads = []
  for master, builders in LKGR_STEPS.iteritems():
    for builder in builders:
      th = threading.Thread(target=FetchBuildsMain,
                            name='Fetch %s' % builder,
                            args=(master, builder, builds[master]))
      th.start()
      fetch_threads.append(th)
  for th in fetch_threads:
    th.join()

  return builds

def ReadBuildData(fn):
  try:
    if fn == '-':
      fn = '<stdin>'
      return json.load(sys.stdin)
    else:
      with open(fn, 'r') as fh:
        return json.load(fh)
  except Exception, e:
    sys.stderr.write('Could not read build data from %s:\n%s\n' % (
        fn, repr(e)))
    raise

def CollateRevisionHistory(builds, lkgr_steps):
  """Organize builder data into:
  build_history = [ (revision, {master: {builder: True/False, ...}, ...}), ... ]
  ... and sort revisions chronologically, latest revision first
  """
  # revision_history[revision][builder] = True/False (success/failure)
  revision_history = {}
  for master in builds.keys():
    for (builder, builder_history) in builds[master].iteritems():
      VerbosePrint('%s/%s:' % (master, builder))
      for build_num in sorted(builder_history, key=int):
        build_data = builder_history[build_num]
        build_num = int(build_num)
        revision = build_data['sourceStamp']['revision']
        if not revision:
          continue
        build_steps = {}
        reasons = []
        for step in build_data['steps']:
          build_steps[step['name']] = step
        for lkgr_step in lkgr_steps[master][builder]:
          # This allows us to rename a step and tell lkgr_finder that it should
          # accept either name for step status.  We assume in the code that any
          # given build will have at most one of the two steps.
          if isinstance(lkgr_step, str):
            steps = (lkgr_step,)
          else:
            steps = lkgr_step
          matching_steps = [s for s in build_steps if s in steps]
          if not matching_steps:
            reasons.append('Step %s is not listed on the build.' % (lkgr_step,))
            continue
          elif len(matching_steps) > 1:
            reasons.append('Multiple step matches: %s' % matching_steps)
            continue
          step = matching_steps[0]
          if build_steps[step].get('isFinished') is not True:
            reasons.append('Step %s has not completed (isFinished: %s)' % (
                step, build_steps[step].get('isFinished')))
            continue
          if 'results' in build_steps[step]:
            result = build_steps[step]['results'][0]
            if type(result) == list:
              result = result[0]
            if result and str(result) not in ('0', '1'):
              reasons.append('Step %s failed' % step)
        revision_history.setdefault(revision, {})
        revision_history[revision].setdefault(master, {})
        if reasons:
          revision_history[revision][master][builder] = False
          VerbosePrint('  Build %s (rev %s) is bad or incomplete' % (
              build_num, revision))
          for reason in reasons:
            VerbosePrint('    %s' % reason)
        else:
          revision_history[revision][master][builder] = True

  # Need to fix the sort for git
  # pylint: disable=W0108
  sorted_keys = sorted(revision_history.keys(), None, lambda x: int(x), True)
  build_history = [(rev, revision_history[rev]) for rev in sorted_keys]

  return build_history

def FindLKGRCandidate(build_history, lkgr_steps):
  """Given a build_history of builds, run the algorithm for finding an LKGR
  candidate (refer to the algorithm description at the top of this script).
  green1 and green2 record the sequence of two successful builds that are
  required for LKGR.
  """
  candidate = -1
  green1 = {}
  green2 = {}
  num_builders = 0
  for master in lkgr_steps.keys():
    num_builders += len(lkgr_steps[master])

  for entry in build_history:
    if len(green2) == num_builders:
      break
    revision = entry[0]
    history = entry[1]
    if candidate == -1:
      master_loop_must_break = False
      for master in history.keys():
        if master_loop_must_break:
          break
        for (builder, status) in history[master].iteritems():
          if not status:
            candidate = -1
            green1.clear()
            master_loop_must_break = True
            break
          green1[master + '/' + builder] = revision
      if len(green1) == num_builders:
        candidate = revision
        for master in history.keys():
          for builder in history[master].keys():
            green2[master + '/' + builder] = revision
      continue
    master_loop_must_break = False
    for master in history.keys():
      if master_loop_must_break:
        break
      for (builder, status) in history[master].iteritems():
        if not status:
          candidate = -1
          green1.clear()
          green2.clear()
          master_loop_must_break = True
          break
        green2[master + '/' + builder] = revision

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
    Print('Could not read password file %s' % password_file)
    Print('Aborting upload')
    return
  params = {
    'revision': lkgr,
    'success': 1,
    'password': password
  }
  params = urllib.urlencode(params)
  Print(params)
  if not dry:
    # Requires python 2.6
    # pylint: disable=E1121
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
        '--who', 'lkgr',
        '--category', 'lkgr',
        'no file information']
    if dry:
      return
    import buildbot.scripts.runner
    buildbot.scripts.runner.run()

  p = multiprocessing.Process(None, _NotifyMain, 'notify-%s' % master)
  p.start()
  p.join(5)
  if p.is_alive():
    Print('Timeout while notifying %s' % master)
    # p.terminate() can hang; just obliterate the sucker.
    os.kill(p.pid, signal.SIGKILL)

def CheckLKGRLag(lag_age, rev_gap, allowed_lag_hrs, allowed_rev_gap):
  """Determine if the LKGR lag is acceptable for current commit activity.

    Returns True if the lag is within acceptable thresholds.
  """
  # Lag isn't an absolute threshold because when things are slow, e.g. nights
  # and weekends, there could be bad revisions that don't get noticed and
  # fixed right away, so LKGR could go a long time without updating, but it
  # wouldn't be a big concern, so we want to back off the 'ideal' threshold.
  # When the tree is active, we don't want to back off much, or at all, to keep
  # the lag under control.
  # This causes the allowed_lag to back off proportionally to how far LKGR is
  # below the gap threshold, which is used as a rough measure of activity.

  # Equation arbitrarily chosen to fit the range of 2 to 12 hours when using the
  # default allowed_lag and allowed_gap. Might need tweaking.
  max_lag_hrs = (1 + max(0, allowed_rev_gap - rev_gap) / 30) * allowed_lag_hrs

  lag_hrs = (lag_age.days * 24) + (lag_age.seconds / 3600)
  VerbosePrint('LKGR is %s hours old (threshold: %s hours)' %
               (lag_hrs, max_lag_hrs))

  return lag_age < datetime.timedelta(hours=max_lag_hrs)

def GetLKGRAge(lkgr, repo='svn://svn.chromium.org/chrome'):
  """Parse the LKGR revision timestamp from the svn log."""
  lkgr_age = datetime.timedelta(0)
  cmd = ['svn', 'log', '--non-interactive', '--xml', '-r', str(lkgr), repo]
  process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
  stdout = process.communicate()[0]
  if not process.returncode:
    match = re.search('<date>(?P<dt>.*)</date>', stdout)
    if match:
      lkgr_dt = datetime.datetime.strptime(match.group('dt'),
                                           '%Y-%m-%dT%H:%M:%S.%fZ')
      lkgr_age = datetime.datetime.utcnow() - lkgr_dt
  return lkgr_age


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
  opt_parser.add_option('--manual', help='Set LKGR manually')
  opt_parser.add_option('--build-data', metavar='FILE', dest='build_data',
                        help='Rather than querying the build master, read the '
                        'build data from this file.  Passing "-" as the '
                        'argument will read from stdin.')
  opt_parser.add_option('--dump-build-data', metavar='FILE', dest='dump_file',
                        help='For debugging, dump the raw json build data.')
  opt_parser.add_option('--email-errors', action='store_true', default=False,
                        help='Send e-mail to LKGR admins on errors (for cron).')
  opt_parser.add_option('--allowed-gap', type='int', default=150,
                        help='How many revisions to allow between head and '
                        'LKGR before it\'s considered out-of-date.')
  opt_parser.add_option('--allowed-lag', type='int', default=2,
                        help='How long (in hours) since an LKGR update before'
                        'it\'s considered out-of-date. This is a minimum and '
                        'will be increased when commit activity slows.')
  options, args = opt_parser.parse_args()

  # Error notification setup.
  fqdn = socket.getfqdn()
  sender = '%s@%s' % (os.environ.get('LOGNAME', 'unknown'), fqdn)
  recipients = 'chrome-troopers+alerts@google.com'
  subject_base = os.path.basename(__file__) + ': '

  global EMAIL_ENABLED
  EMAIL_ENABLED = options.email_errors

  if args:
    opt_parser.print_usage()
    SendMail(sender, recipients, subject_base + 'Usage error',
             ' '.join(sys.argv) + '\n' + opt_parser.get_usage())
    return 1

  global VERBOSE
  VERBOSE = not options.quiet

  if options.manual:
    PostLKGR(options.manual, options.pwfile, options.dry)
    for master in options.notify:
      NotifyMaster(master, options.manual, options.dry)
    return 0

  lkgr = FetchLKGR()
  if lkgr is None:
    SendMail(sender, recipients, subject_base + 'Failed to fetch LKGR',
             '\n'.join(run_log))
    return 1

  if options.build_data:
    builds = ReadBuildData(options.build_data)
  else:
    builds = FetchBuildData()

  if options.dump_file:
    try:
      with open(options.dump_file, 'w') as fh:
        json.dump(builds, fh, indent=2)
    except IOError, e:
      sys.stderr.write('Could not dump to %s:\n%s\n' % (
          options.dump_file, repr(e)))

  build_history = CollateRevisionHistory(builds, LKGR_STEPS)
  latest_rev = int(build_history[0][0])
  candidate = FindLKGRCandidate(build_history, LKGR_STEPS)

  VerbosePrint('-' * 80)
  VerbosePrint('LKGR=%d' % lkgr)
  VerbosePrint('-' * 80)
  # Fix for git
  if candidate != -1 and int(candidate) > lkgr:
    VerbosePrint('Revision %s is new LKGR' % candidate)
    for master in LKGR_STEPS.keys():
      formdata = ['builder=%s' % urllib2.quote(x)
                  for x in LKGR_STEPS[master].keys()]
      formdata = '&'.join(formdata)
      waterfall = '%s?%s' % (MASTER_TO_BASE_URL[master] + '/console', formdata)
      VerbosePrint('%s Waterfall URL:' % master)
      VerbosePrint(waterfall)
    if options.post:
      PostLKGR(candidate, options.pwfile, options.dry)
    for master in options.notify:
      NotifyMaster(master, candidate, options.dry)
  else:
    VerbosePrint('No newer LKGR found than current %s' % lkgr)

    rev_behind = latest_rev - lkgr
    VerbosePrint('LKGR is behind by %s revisions' % rev_behind)
    if rev_behind > options.allowed_gap:
      SendMail(sender, recipients,
               '%sLKGR (%s) > %s revisions behind' %
               (subject_base, lkgr, options.allowed_gap),
               '\n'.join(run_log))
      return 1

    if not CheckLKGRLag(GetLKGRAge(lkgr), rev_behind, options.allowed_lag,
                        options.allowed_gap):
      SendMail(sender, recipients, '%sLKGR (%s) exceeds lag threshold' %
               (subject_base, lkgr), '\n'.join(run_log))
      return 1

  VerbosePrint('-' * 80)

  return 0

if __name__ == '__main__':
  sys.exit(main())
