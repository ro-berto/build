# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Recipe for the Skia AutoRoll Bot."""


import re
from common.skia import global_constants


DEPS = [
  'file',
  'gclient',
  'gsutil',
  'json',
  'path',
  'properties',
  'python',
  'raw_io',
  'step',
]


APPENGINE_IS_STOPPED_URL = 'http://skia-tree-status.appspot.com/arb_is_stopped'
APPENGINE_SET_STATUS_URL = (
    'https://skia-tree-status.appspot.com/set_arb_status')
DEPS_ROLL_AUTHOR = 'skia-deps-roller@chromium.org'
DEPS_ROLL_NAME = 'Skia DEPS Roller'
HTML_CONTENT = '''
<html>
<head>
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="-1">
<meta http-equiv="refresh" content="0; url=%s" />
</head>
</html>
'''
RIETVELD_URL = 'https://codereview.chromium.org'
ISSUE_URL_TEMPLATE = RIETVELD_URL + '/%(issue)s/'
# TODO(borenet): Find a way to share these filenames (or their full GS URL) with
# the webstatus which links to them.
FILENAME_CURRENT_ATTEMPT = 'depsroll.html'
FILENAME_ROLL_STATUS = 'arb_status.html'

METATADATA_STATUS_PASSWORD_URL = ('http://metadata/computeMetadata/v1/project/'
                                  'attributes/skia_tree_status')

REGEXP_ISSUE_CREATED = (
    r'Issue created. URL: %s/(?P<issue>\d+)' % RIETVELD_URL)
REGEXP_ROLL_ACTIVE = (
    r'%s/(?P<issue>\d+)/ is still active' % RIETVELD_URL)
REGEXP_ROLL_STOPPED = (
    r'%s/(?P<issue>\d+)/: Rollbot was stopped by' % RIETVELD_URL)
# This occurs when the ARB has "caught up" and has nothing new to roll, or when
# a different roll (typically a manual roll) has already rolled past it.
REGEXP_ROLL_TOO_OLD = r'Already at .+ refusing to roll backwards to .+'
ROLL_STATUS_IN_PROGRESS = 'In progress'
ROLL_STATUS_IN_PROGRESS_URL = (
    'In progress - <a href="{0}" target="_blank">{0}</a>'.format(
        ISSUE_URL_TEMPLATE)
)
ROLL_STATUS_STOPPED = 'Stopped'
ROLL_STATUS_STOPPED_URL = (
    'Stopped - <a href="{0}" target="_blank">{0}</a>'.format(
        ISSUE_URL_TEMPLATE)
)
ROLL_STATUS_IDLE = 'Idle'
ROLL_STATUSES = (
  (REGEXP_ISSUE_CREATED, ROLL_STATUS_IN_PROGRESS, ROLL_STATUS_IN_PROGRESS_URL),
  (REGEXP_ROLL_ACTIVE,   ROLL_STATUS_IN_PROGRESS, ROLL_STATUS_IN_PROGRESS_URL),
  (REGEXP_ROLL_STOPPED,  ROLL_STATUS_STOPPED,     ROLL_STATUS_STOPPED_URL),
  (REGEXP_ROLL_TOO_OLD,  ROLL_STATUS_IDLE,        ROLL_STATUS_IDLE),
)


def GenSteps(api):
  # Check out Chrome.
  gclient_cfg = api.gclient.make_config()
  s = gclient_cfg.solutions.add()
  s.name = 'src'
  s.url = 'https://chromium.googlesource.com/chromium/src.git'
  gclient_cfg.got_revision_mapping['src/third_party/skia'] = 'got_revision'

  api.gclient.checkout(gclient_config=gclient_cfg)

  src_dir = api.path['checkout']
  api.step('git config user.name',
           ['git', 'config', '--local', 'user.name', DEPS_ROLL_NAME],
           cwd=src_dir)
  api.step('git config user.email',
           ['git', 'config', '--local', 'user.email', DEPS_ROLL_AUTHOR],
           cwd=src_dir)

  res = api.python.inline(
      'is_stopped',
      '''
      import urllib2
      import sys
      with open(sys.argv[2], 'w') as f:
        f.write(urllib2.urlopen(sys.argv[1]).read())
      ''',
      args=[APPENGINE_IS_STOPPED_URL, api.json.output()],
      step_test_data=lambda: api.json.test_api.output({
        'is_stopped': api.properties['test_arb_is_stopped'],
       }))
  is_stopped = res.json.output['is_stopped']

  output = ''
  error = None
  issue = None
  if is_stopped:
    # Find any active roll and stop it.
    issue = api.python.inline(
      'stop_roll',
      '''
      import json
      import re
      import sys
      import urllib2

      sys.path.insert(0, sys.argv[4])
      import rietveld

      # Find the active roll, if it exists.
      res = json.load(urllib2.urlopen(
          '%s/search?closed=3&owner=%s&format=json' % (sys.argv[1], sys.argv[2])
      ))['results']
      issue = None
      for i in res:
        if re.search('Roll src/third_party/skia .*:.*', i['subject']):
          issue = i
          break

      # Report back the issue number.
      with open(sys.argv[3], 'w') as f:
        json.dump({'issue': issue['issue'] if issue else None}, f)

      # Uncheck the 'commit' box.
      if issue and issue['commit']:
        r = rietveld.Rietveld(sys.argv[1], sys.argv[2], None, None)
        r.set_flag(issue['issue'], issue['patchsets'][-1], 'commit', False)
      ''',
      args=[RIETVELD_URL, DEPS_ROLL_AUTHOR, api.json.output(),
            api.path['depot_tools']],
      step_test_data=lambda: api.json.test_api.output({'issue': 1234})
    ).json.output['issue']
  else:
    auto_roll = api.path['build'].join('scripts', 'tools', 'blink_roller',
                                       'auto_roll.py')
    try:
      output = api.step(
          'do auto_roll',
          ['python', auto_roll, 'skia', DEPS_ROLL_AUTHOR, src_dir],
          cwd=src_dir,
          stdout=api.raw_io.output()).stdout
    except api.step.StepFailure as f:
      output = f.result.stdout
      # Suppress failure for "refusing to roll backwards."
      if not re.search(REGEXP_ROLL_TOO_OLD, output):
        error = f

    match = (re.search(REGEXP_ISSUE_CREATED, output) or
             re.search(REGEXP_ROLL_ACTIVE, output) or
             re.search(REGEXP_ROLL_STOPPED, output))
    if match:
      issue = match.group('issue')
      # Upload the issue URL to a file in GS.
      file_contents = HTML_CONTENT % (ISSUE_URL_TEMPLATE % {'issue': issue})
      api.file.write('write %s' % FILENAME_CURRENT_ATTEMPT,
                     FILENAME_CURRENT_ATTEMPT,
                     file_contents)
      api.gsutil.upload(FILENAME_CURRENT_ATTEMPT,
                        global_constants.GS_GM_BUCKET,
                        FILENAME_CURRENT_ATTEMPT,
                        args=['-a', 'public-read'])

  if is_stopped:
    roll_status = ROLL_STATUS_STOPPED
    roll_status_detail = ROLL_STATUS_STOPPED
  else:
    roll_status = None
    roll_status_detail = None
    for regexp, status_msg, status_detail_msg in ROLL_STATUSES:
      match = re.search(regexp, output)
      if match:
        roll_status = status_msg
        roll_status_detail = status_detail_msg % match.groupdict()
        break

  if roll_status:
    # Upload status the old way.
    api.file.write('write %s' % FILENAME_ROLL_STATUS,
                   FILENAME_ROLL_STATUS,
                   roll_status_detail)
    api.gsutil.upload(FILENAME_ROLL_STATUS,
                      global_constants.GS_GM_BUCKET,
                      FILENAME_ROLL_STATUS,
                      args=['-a', 'public-read'])

    # POST status to appengine.
    api.python.inline(
      'update_status',
      '''
      import json
      import shlex
      import subprocess
      import sys
      import urllib
      import urllib2

      def full_hash(short):
        return subprocess.check_output(['git', 'rev-parse', short]).rstrip()

      password = urllib2.urlopen(urllib2.Request(
          sys.argv[2],
          headers={'Metadata-Flavor': 'Google'})).read()
      params = {'status': sys.argv[1],
                'password': password}
      if sys.argv[3] != '':
        params['deps_roll_link'] = sys.argv[3]
        split = sys.argv[3].split('/')
        split.insert(-2, 'api')
        api_url = '/'.join(split)
        issue_details = json.load(urllib2.urlopen(api_url))
        old, new = shlex.split(issue_details['subject'])[-1].split(':')
        params['last_roll_rev'] = full_hash(old)
        params['curr_roll_rev'] = full_hash(new)

      urllib2.urlopen(urllib2.Request(
          sys.argv[4],
          urllib.urlencode(params)))
      ''',
      args=[roll_status,
            METATADATA_STATUS_PASSWORD_URL,
            ISSUE_URL_TEMPLATE % {'issue': issue} if issue else '',
            APPENGINE_SET_STATUS_URL],
      cwd=src_dir.join('third_party/skia'))

  if error:
    # Pylint complains about raising NoneType, but that's exactly what we're
    # NOT doing here...
    # pylint: disable=E0702
    raise error


def GenTests(api):
  yield (
    api.test('AutoRoll_upload') +
    api.properties(test_arb_is_stopped=False) +
    api.step_data('do auto_roll', retcode=0, stdout=api.raw_io.output(
        'Issue created. URL: %s/1234' % RIETVELD_URL))
  )
  yield (
    api.test('AutoRoll_failed') +
    api.properties(test_arb_is_stopped=False) +
    api.step_data('do auto_roll', retcode=1, stdout=api.raw_io.output('fail'))
  )
  yield (
    api.test('AutoRoll_stopped') +
    api.properties(test_arb_is_stopped=True)
  )
