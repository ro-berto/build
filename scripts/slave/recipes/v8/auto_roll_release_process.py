# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'file',
  'gclient',
  'git',
  'path',
  'properties',
  'python',
  'raw_io',
  'step',
  'time',
]

REPO = 'https://chromium.googlesource.com/v8/v8'
CANDIDATE_REF = 'refs/heads/candidate'
STATUS_URL = 'https://v8-status.appspot.com'
SEC_TO_HOURS = 60 * 60
TIME_LIMIT_HOURS = 8
TIME_LIMIT_SEC = TIME_LIMIT_HOURS * SEC_TO_HOURS


def GetRef(api, repo, ref):
  # Fetch ref from remote.
  api.git(
      'fetch', repo, '+%s:%s' % (ref, ref),
      cwd=api.path['checkout'],
  )
  # Read ref locally.
  step_result = api.git(
      'show-ref', '-s', ref,
      cwd=api.path['checkout'],
      stdout=api.raw_io.output(),
  )
  result = step_result.stdout.strip()
  step_result.presentation.logs['ref'] = [result]
  return result


def PushRef(api, repo, ref, hsh):
  api.git(
      'update-ref', ref, hsh,
      cwd=api.path['checkout'],
  )
  api.git(
      'push', repo, '%s:%s' % (ref, ref),
      cwd=api.path['checkout'],
  )


def ReadTimeStamp(api, name):
  return int(float(
      api.file.read(
          name,
          api.path['slave_build'].join('timestamp.txt'),
      ).strip()))


def WriteTimeStamp(api, name, timestamp):
  api.file.write(
      name,
      api.path['slave_build'].join('timestamp.txt'),
      str(timestamp),
  )


def AgeLimitBailout(api, new_date, old_date):
  age = (new_date - old_date) / SEC_TO_HOURS
  api.step('log', ['echo',
    'Current candidate is %dh old (limit: %dh).' % (age, TIME_LIMIT_HOURS),
  ])
  return age < TIME_LIMIT_HOURS


def GetLKGR(api, new_date):
  step_result = api.python(
      'get new lkgr',
      api.path['build'].join('scripts', 'tools', 'runit.py'),
      [api.path['build'].join('scripts', 'tools', 'pycurl.py'),
       '%s/lkgr' % STATUS_URL],
      stdout=api.raw_io.output(),
  )
  lkgr = step_result.stdout.strip()
  step_result.presentation.logs['logs'] = [
    'New candidate: %s (%s)' % (lkgr, str(new_date)),
  ]
  return step_result, lkgr

def GenSteps(api):
  repo = api.properties.get('repo', REPO)
  fail_on_exit = None

  api.gclient.set_config('v8')
  api.bot_update.ensure_checkout(force=True, no_shallow=True)

  # Get current candidate. Needs to be set manually once.
  current_candidate = GetRef(api, repo, CANDIDATE_REF)

  try:
    current_date = ReadTimeStamp(api, 'check timestamp')
  except Exception:
    # If anything goes wrong, the process restarts with a fresh timestamp.
    current_date = api.time.time()
    WriteTimeStamp(api, 'init timestamp', current_date)
    fail_on_exit = 'Timestamp file was missing. Starting new candidate cycle.'

  new_date = api.time.time()
  if AgeLimitBailout(api, new_date, current_date):
    if fail_on_exit:
      raise api.step.StepFailure(fail_on_exit)
    else:
      return

  # Get new lkgr.
  step_result, new_candidate = GetLKGR(api, new_date)

  if current_candidate != new_candidate:
    PushRef(api, repo, CANDIDATE_REF, new_candidate)
    WriteTimeStamp(api, 'update timestamp', api.time.time())
  else:
    step_result.presentation.step_text = 'There is no new lkgr candidate.'


def GenTests(api):
  hsh_old = '74882b7a8e55268d1658f83efefa1c2585cee723'
  hsh_recent = '0df953c9e12c1e3b0e37f2d4ef1ef8c319e095cb'
  hsh_new = 'c1a7fd0c98a80c52fcf6763850d2ee1c41cfe8d6'
  date_old = str(100.0 * SEC_TO_HOURS + 0.5)
  date_recent = str(105.0 * SEC_TO_HOURS + 0.5)
  date_new = str(110.0 * SEC_TO_HOURS + 0.5)

  def Test(name, current_lkgr, current_date, new_lkgr, new_date):
    test = (
        api.test(name) +
        api.properties.generic(mastername='client.v8',
                               buildername='Auto-roll - release process') +
        api.override_step_data(
            'git show-ref',
            api.raw_io.stream_output(current_lkgr, stream='stdout'),
        ) +
        api.override_step_data(
            'check timestamp',
            api.raw_io.output(current_date),
        ) +
        api.time.seed(int(float(new_date))) +
        api.time.step(2)
      )
    if int(float(current_date)) + TIME_LIMIT_SEC < int(float(new_date)):
      test += api.override_step_data(
          'get new lkgr',
          api.raw_io.stream_output(new_lkgr, stream='stdout'),
      )
    return test

  yield Test(
      'same_lkgr',
      hsh_old,
      date_old,
      hsh_old,
      date_new,
  )
  yield Test(
      'recent_lkgr',
      hsh_recent,
      date_recent,
      hsh_new,
      date_new,
  )
  yield Test(
      'update',
      hsh_old,
      date_old,
      hsh_new,
      date_new,
  )
  yield Test(
      'new_lkgr_failed_timestamp',
      hsh_recent,
      date_recent,
      hsh_new,
      date_new,
  ) + api.override_step_data('check timestamp', retcode=1)
