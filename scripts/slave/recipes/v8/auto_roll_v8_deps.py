
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import (
    DoesNotRun, DropExpectation, Filter, MustRun)
from recipe_engine.types import freeze

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gerrit',
  'depot_tools/git',
  'recipe_engine/context',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/service_account',
  'recipe_engine/step',
  'v8',
]

BASE_URL = 'https://chromium.googlesource.com'
V8_REPO = BASE_URL + '/v8/v8'
CR_REPO = BASE_URL + '/chromium/src'
LOG_TEMPLATE = 'Rolling v8/%s: %s/+log/%s..%s'

BOT_CONFIGS = {
  'Auto-roll - test262': {
    'subject': 'Update test262.',
    'whitelist': [
      # Only roll these dependencies (list without solution name prefix).
      'test/test262/data',
    ],
    'reviewers': [
      'adamk@chromium.org',
      'gsathya@chromium.org',
    ],
  },
  'Auto-roll - v8 deps': {
    'subject': 'Update V8 DEPS.',
    'blacklist': [
      # Skip these dependencies (list without solution name prefix).
      'test/mozilla/data',
      'test/simdjs/data',
      'test/test262/data',
      'test/wasm-js',
      'testing/gtest',
      'third_party/WebKit/Source/platform/inspector_protocol',
      'third_party/blink/renderer/platform/inspector_protocol',
    ],
    'reviewers': [
      'machenbach@chromium.org',
      'hablich@chromium.org',
      'sergiyb@chromium.org',
    ],
  },
}

def GetDEPS(api, name, repo):
  # Make a fake spec. Gclient is not nice to us when having two solutions
  # side by side. The latter checkout kills the former's gclient file.
  spec = ('solutions=[{'
      '\'managed\':False,'
      '\'name\':\'%s\','
      '\'url\':\'%s\','
      '\'deps_file\':\'DEPS\'}]' % (name, repo))

  # Read local deps information. Each deps has one line in the format:
  # path/to/deps: repo@revision
  with api.context(cwd=api.path['start_dir']):
    step_result = api.gclient(
        'get %s deps' % name,
        ['revinfo', '--deps', 'all', '--spec', spec],
        stdout=api.raw_io.output_text(),
    )

  # Transform into dict. Skip the solution prefix in keys (e.g. src/).
  deps = {}
  for line in step_result.stdout.strip().splitlines():
    key, value = line.strip().split(' ')

    # Remove trailing colon.
    key = key.split(':')[0]

    # Skip the deps entry to the solution itself.
    if not '/' in key:
      continue

    # Strip trailing solution name (e.g. src/).
    key = '/'.join(key.split('/')[1:])

    deps[key] = value

  # Log DEPS output.
  step_result.presentation.logs['deps'] = api.json.dumps(
      deps, indent=2).splitlines()
  return deps


def RunSteps(api):
  # Configure this particular instance of the auto-roller.
  bot_config = BOT_CONFIGS[api.properties.get('buildername')]

  # Bail out on existing roll. Needs to be manually closed.
  # TODO(machenbach): Add auto-abandon on stale roll.
  push_account = (
      # TODO(sergiyb): Replace with api.service_account.default().get_email()
      # when https://crbug.com/846923 is resolved.
      'v8-ci-autoroll-builder@chops-service-accounts.iam.gserviceaccount.com'
      if api.runtime.is_luci else 'v8-autoroll@chromium.org')
  commits = api.gerrit.get_changes(
      'https://chromium-review.googlesource.com',
      query_params=[
          ('project', 'v8/v8'),
          ('owner', push_account),
          ('status', 'open'),
      ],
      limit=20,
      step_test_data=api.gerrit.test_api.get_empty_changes_response_data,
  )
  for commit in commits:
    # The auto-roller might have a CL open for a particular roll config.
    if commit['subject'] == bot_config['subject']:
      api.step('Existing rolls found.', cmd=None)
      return

  api.gclient.set_config('v8')
  api.gclient.apply_config('chromium')

  # Chromium and V8 side-by-side makes the got_revision mapping ambiguous.
  api.gclient.c.got_revision_mapping.pop('src', None)
  api.gclient.c.got_revision_reverse_mapping['got_revision'] = 'v8'

  # Allow rolling all v8 os deps.
  api.gclient.c.target_os.add('android')
  api.gclient.c.target_os.add('win')

  # Skip large repos.
  s = api.gclient.c.solutions[1]
  s.custom_deps.update({
    'src/chrome/test/data/pdf_private': None,
    'src/native_client': None,
    'src/third_party/blink': None,
    'src/third_party/skia': None,
    'src/third_party/webrtc': None,
    'src/third_party/WebKit': None,
    'src/tools/valgrind': None,
    'src/v8': None,
  })
  api.bot_update.ensure_checkout(no_shallow=True)

  # Enforce a clean state.
  dt_path = api.path['checkout'].join('third_party', 'depot_tools')
  with api.context(cwd=api.path['checkout'], env_prefixes={'PATH': [dt_path]}):
    api.git('checkout', '-f', 'origin/master')
    api.git('branch', '-D', 'roll', ok_ret='any')
    api.git('clean', '-ffd')
    api.git('new-branch', 'roll')

  # Get chromium's and v8's deps information.
  cr_deps = GetDEPS(
      api, 'src', CR_REPO)
  v8_deps = GetDEPS(
      api, 'v8', V8_REPO)

  commit_message = []

  # White/blacklist certain deps keys.
  blacklist = bot_config.get('blacklist', [])
  whitelist = bot_config.get('whitelist', [])

  # Iterate over all v8 deps.
  for name in sorted(v8_deps.keys()):
    if blacklist and name in blacklist:
      continue
    if whitelist and name not in whitelist:
      continue
    def SplitValue(solution_name, value):
      assert '@' in value, (
          'Found %s value %s without pinned revision.' % (solution_name, name))
      return value.split('@')

    v8_repo, v8_rev = SplitValue('v8', v8_deps[name])
    cr_value = cr_deps.get(name)
    if cr_value:
      # Use the given revision from chromium's DEPS file.
      cr_repo, new_rev = SplitValue('src', cr_value)
      assert v8_repo == cr_repo, 'Found v8 %s for src %s.' % (v8_repo, cr_repo)
    else:
      # Use the HEAD of the deps repo.
      step_result = api.git(
        'ls-remote', v8_repo, 'HEAD',
        name='look up %s' % name.replace('/', '_'),
        stdout=api.raw_io.output_text(),
      )
      new_rev = step_result.stdout.strip().split('\t')[0]
      step_result.presentation.step_text = new_rev

    # Check if an update is necessary.
    if v8_rev != new_rev:
      with api.context(cwd=api.path['checkout']):
        step_result = api.gclient(
            'setdep %s' % name.replace('/', '_'),
            ['setdep', '-r', 'v8/%s@%s' % (name, new_rev)],
            ok_ret='any',
        )
      if step_result.retcode == 0:
        repo = v8_repo[:-len('.git')] if v8_repo.endswith('.git') else v8_repo
        commit_message.append(LOG_TEMPLATE % (
            name, repo, v8_rev[:7], new_rev[:7]))
      else:
        step_result.presentation.status = api.step.WARNING

  # Check for a difference. If no deps changed, the diff is empty.
  with api.context(cwd=api.path['checkout']):
    step_result = api.git('diff', stdout=api.raw_io.output_text())
  diff = step_result.stdout.strip()
  step_result.presentation.logs['diff'] = diff.splitlines()

  # Commit deps change and send to CQ.
  if diff:
    if api.runtime.is_experimental:
      api.step('fake commit and send to CQ', cmd=None)
    else:
      args = ['commit', '-a', '-m', bot_config['subject']]
      for message in commit_message:
        args.extend(['-m', message])
      args.extend(['-m', 'TBR=%s' % ','.join(bot_config['reviewers'])])
      kwargs = {'stdout': api.raw_io.output_text()}
      with api.context(
          cwd=api.path['checkout'], env_prefixes={'PATH': [dt_path]}):
        api.git(*args, **kwargs)
        api.git(
            'cl', 'upload', '-f', '--use-commit-queue', '--bypass-hooks',
            '--email', push_account, '--gerrit', '--send-mail',
        )


def GenTests(api):
  v8_deps_info = """v8: https://chromium.googlesource.com/v8/v8.git
v8/base/trace_event/common: https://chromium.googlesource.com/chromium/src/base/trace_event/common.git@08b7b94e88aecc99d435af7f29fda86bd695c4bd
v8/build: https://chromium.googlesource.com/chromium/src/build.git@d3f34f8dfaecc23202a6ef66957e83462d6c826d
v8/buildtools: https://chromium.googlesource.com/chromium/buildtools.git@5fd66957f08bb752dca714a591c84587c9d70762
v8/test/test262/data: https://chromium.googlesource.com/external/github.com/tc39/test262.git@29c23844494a7cc2fbebc6948d2cb0bcaddb24e7
v8/tools/gyp: https://chromium.googlesource.com/external/gyp.git@702ac58e477214c635d9b541932e75a95d349352
v8/tools/swarming_client: https://chromium.googlesource.com/external/swarming.client.git@380e32662312eb107f06fcba6409b0409f8fe000"""
  cr_deps_info = """src: https://chromium.googlesource.com/chromium/src.git
src/buildtools: https://chromium.googlesource.com/chromium/buildtools.git@5fd66957f08bb752dca714a591c84587c9d70762
src/third_party/snappy/src: https://chromium.googlesource.com/external/snappy.git@762bb32f0c9d2f31ba4958c7c0933d22e80c20bf
src/tools/gyp: https://chromium.googlesource.com/external/gyp.git@e7079f0e0e14108ab0dba58728ff219637458563
v8/tools/swarming_client: https://chromium.googlesource.com/external/swarming.client.git@380e32662312eb107f06fcba6409b0409f8fe001"""

  def template(testname, buildername):
    return (
        api.test(testname) +
        api.properties.generic(mastername='client.v8.fyi',
                               buildername=buildername) +
        api.override_step_data(
            'gclient get v8 deps',
            api.raw_io.stream_output(v8_deps_info, stream='stdout'),
        ) +
        api.override_step_data(
            'gclient get src deps',
            api.raw_io.stream_output(cr_deps_info, stream='stdout'),
        ) +
        api.override_step_data(
            'git diff',
            api.raw_io.stream_output('some difference', stream='stdout'),
        )
    )

  yield (
      template('roll', 'Auto-roll - v8 deps') +
      api.override_step_data(
          'gclient setdep base_trace_event_common',
          retcode=1,
      ) +
      api.override_step_data(
          'look up build',
          api.raw_io.stream_output('deadbeef\tHEAD', stream='stdout'),
      ) +
      api.override_step_data(
          'look up base_trace_event_common',
          api.raw_io.stream_output('deadbeef\tHEAD', stream='stdout'),
      )
  )
  yield (
      template('test262', 'Auto-roll - test262') +
      api.override_step_data(
          'look up test_test262_data',
          api.raw_io.stream_output('deadbeef\tHEAD', stream='stdout'),
      ) +
      api.post_process(Filter('git commit', 'git cl'))
  )

  yield (
      api.test('stale_roll') +
      api.properties.generic(mastername='client.v8.fyi',
                             buildername='Auto-roll - v8 deps') +
      api.override_step_data(
          'gerrit changes', api.json.output(
              [{'_number': '123', 'subject': 'Update V8 DEPS.'}])) +
      api.post_process(MustRun, 'Existing rolls found.') +
      api.post_process(DoesNotRun, 'look up build') +
      api.post_process(DropExpectation)
  )

  yield (
      template('experimental_roll_v8_deps', 'Auto-roll - v8 deps') +
      api.runtime(is_luci=True, is_experimental=True)
  )
