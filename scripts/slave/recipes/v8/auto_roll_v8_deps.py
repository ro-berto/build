
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
  'depot_tools/gitiles',
  'recipe_engine/buildbucket',
  'recipe_engine/cipd',
  'recipe_engine/context',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/service_account',
  'recipe_engine/step',
  'recipe_engine/url',
  'v8',
]

GERRIT_BASE_URL = 'https://chromium-review.googlesource.com'
BASE_URL = 'https://chromium.googlesource.com'
V8_REPO = BASE_URL + '/v8/v8'
CR_REPO = BASE_URL + '/chromium/src'
LOG_TEMPLATE = 'Rolling v8/%s: %s/+log/%s..%s'
CIPD_LOG_TEMPLATE = 'Rolling v8/%s: %s..%s'
MAX_COMMIT_LOG_ENTRIES = 8
CIPD_DEP_URL_PREFIX = 'https://chrome-infra-packages.appspot.com/'

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
    'show_commit_log': True,
  },
  'Auto-roll - v8 deps': {
    'subject': 'Update V8 DEPS.',
    'blacklist': [
      # https://crrev.com/c/1547863
      'third_party/perfetto',
      'third_party/protobuf',
      # Skip these dependencies (list without solution name prefix).
      'test/mozilla/data',
      'test/simdjs/data',
      'test/test262/data',
      'test/wasm-js/data',
      'testing/gtest',
      'third_party/WebKit/Source/platform/inspector_protocol',
      'third_party/blink/renderer/platform/inspector_protocol',
    ],
    'reviewers': [
      'machenbach@chromium.org',
      'tmrts@chromium.org',
    ],
    'show_commit_log': False,
  },
  'Auto-roll - wasm-spec': {
    'subject': 'Update wasm-spec.',
    'whitelist': [
      # Only roll these dependencies (list without solution name prefix).
      'test/wasm-js/data',
    ],
    'reviewers': [
      'ahaas@chromium.org',
      'clemensh@chromium.org',
    ],
    'show_commit_log': True,
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
  with api.context(cwd=api.v8.checkout_root):
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
    key = key.rstrip(':')

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


def commit_messages_log_entries(api, repo, from_commit, to_commit):
  """Returns list of log entries to be added to commit message.

  Args:
    api: Recipes api.
    repo: Gitiles url to rolled repository.
    from_commit: Parent of first rolled commit.
    to_commit: Newest rolled commit.
  """
  step_test_data = lambda: api.json.test_api.output({
    'log': [
      {
        'commit': 'deadbeef',
        'author': {'name': 'Tex'},
        'message': 'Commit 1\n\nsecond line',
      },
      {
        'commit': 'beefdead',
        'author': {'name': 'Mex'},
        'message': 'Commit 0\n\nsecond line',
      },
    ],
  })
  commits, _ = api.gitiles.log(
      url=repo,
      ref='%s..%s' % (from_commit, to_commit),
      step_test_data=step_test_data,
  )
  # Format commit log as:
  # <first line of commit message> (<author name>)
  # <url with short hash>
  commit_log = lambda commit: '%s (%s)\n%s' % (
      commit['message'].splitlines()[0],
      commit['author']['name'],
      api.url.join(repo, '+/%s' % commit['commit'][:7]))
  ellipse = [] if len(commits) < MAX_COMMIT_LOG_ENTRIES else ['...']
  return [commit_log(c) for c in commits[:MAX_COMMIT_LOG_ENTRIES]] + ellipse


def RunSteps(api):
  # Configure this particular instance of the auto-roller.
  bot_config = BOT_CONFIGS[api.buildbucket.builder_name]

  # Bail out on existing roll. Needs to be manually closed.
  commits = api.gerrit.get_changes(
      GERRIT_BASE_URL,
      query_params=[
          ('project', 'v8/v8'),
          # TODO(sergiyb): Use api.service_account.default().get_email() when
          # https://crbug.com/846923 is resolved.
          ('owner', 'v8-ci-autoroll-builder@'
                    'chops-service-accounts.iam.gserviceaccount.com'),
          ('status', 'open'),
      ],
      limit=20,
      step_test_data=api.gerrit.test_api.get_empty_changes_response_data,
  )
  for commit in commits:
    # The auto-roller might have a CL open for a particular roll config.
    if commit['subject'] == bot_config['subject']:
      api.gerrit.abandon_change(
          GERRIT_BASE_URL, commit['_number'], 'stale roll')

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
  api.v8.checkout(ignore_input_commit=True)

  # Enforce a clean state.
  with api.context(
      cwd=api.path['checkout'],
      env_prefixes={'PATH': [api.v8.depot_tools_path]}):
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
  failed_deps = []
  for name in sorted(v8_deps.keys()):
    if blacklist and name in blacklist:
      continue
    if whitelist and name not in whitelist:
      continue
    def SplitValue(solution_name, value):
      assert '@' in value, (
          'Found %s value %s without pinned revision.' % (solution_name, name))
      return value.split('@')

    v8_loc, v8_ver = SplitValue('v8', v8_deps[name])
    cr_value = cr_deps.get(name)
    is_cipd_dep = v8_loc.startswith(CIPD_DEP_URL_PREFIX)
    if cr_value:
      # Use the given revision from chromium's DEPS file.
      cr_repo, new_ver = SplitValue('src', cr_value)
      if v8_loc != cr_repo:
        # The gclient tool does not have commands that allow overriding the
        # repo, hence we'll need to make changes like this manually. However,
        # this should not block updating other DEPS and creating roll CL, hence
        # just create a failing step and continue.
        step_result = api.step(
            'dep %s has changed repo from %s to %s' % (name, v8_loc, cr_repo),
            cmd=None)
        step_result.presentation.status = api.step.FAILURE
        failed_deps.append(name)
        continue
    else:
      if is_cipd_dep:
        # Use the 'latest' ref for CIPD package.
        new_ver = api.cipd.describe(
            v8_loc[len(CIPD_DEP_URL_PREFIX):], 'latest').pin.instance_id
      else:
        # Use the HEAD of the deps repo.
        step_result = api.git(
          'ls-remote', v8_loc, 'HEAD',
          name='look up %s' % name.replace('/', '_'),
          stdout=api.raw_io.output_text(),
        )
        new_ver = step_result.stdout.strip().split('\t')[0]
      api.step.active_result.presentation.step_text = new_ver

    # Check if an update is necessary.
    if v8_ver != new_ver:
      with api.context(cwd=api.path['checkout']):
        step_result = api.gclient(
            'setdep %s' % name.replace('/', '_'),
            ['setdep', '-r', 'v8/%s@%s' % (name, new_ver)],
            ok_ret='any',
        )
      if step_result.retcode == 0:
        if is_cipd_dep:
          # Unfortunately CIPD does not provide a way to generate a link that
          # lists all versions from v8_rev to new_ver. Even just creating a link
          # to a list of versions of a DEP is complicated as package name can
          # contain ${platform}, which can usually be resolved to multiple
          # distinct packages.
          path, _ = name.split(':')
          commit_message.append(CIPD_LOG_TEMPLATE % (path, v8_ver, new_ver))
        else:
          repo = v8_loc[:-len('.git')] if v8_loc.endswith('.git') else v8_loc
          commit_message.append(LOG_TEMPLATE % (
              name, repo, v8_ver[:7], new_ver[:7]))
          if bot_config['show_commit_log']:
            commit_message.extend(commit_messages_log_entries(
                api, repo, v8_ver, new_ver))
      else:
        step_result.presentation.status = api.step.WARNING

  # Check for a difference. If no deps changed, the diff is empty.
  with api.context(cwd=api.path['checkout']):
    step_result = api.git('diff', stdout=api.raw_io.output_text())
  diff = step_result.stdout.strip()
  step_result.presentation.logs['diff'] = diff.splitlines()

  # Commit deps change and send to CQ.
  if diff:
    args = ['commit', '-a', '-m', bot_config['subject']]
    for message in commit_message:
      args.extend(['-m', message])
    args.extend(['-m', 'TBR=%s' % ','.join(bot_config['reviewers'])])
    kwargs = {'stdout': api.raw_io.output_text()}
    with api.context(
        cwd=api.path['checkout'],
        env_prefixes={'PATH': [api.v8.depot_tools_path]}):
      api.git(*args, **kwargs)
      api.git(
          'cl', 'upload', '-f', '--use-commit-queue', '--bypass-hooks',
          '--gerrit', '--send-mail',
      )

  if failed_deps:
    raise api.step.StepFailure(
        'Failed to update deps: %s' % ', '.join(failed_deps))

def GenTests(api):
  # pylint: disable=line-too-long
  v8_deps_info = """v8: https://chromium.googlesource.com/v8/v8.git
v8/base/trace_event/common: https://chromium.googlesource.com/chromium/src/base/trace_event/common.git@08b7b94e88aecc99d435af7f29fda86bd695c4bd
v8/build: https://chromium.googlesource.com/chromium/src/build.git@d3f34f8dfaecc23202a6ef66957e83462d6c826d
v8/buildtools: https://chromium.googlesource.com/chromium/buildtools.git@5fd66957f08bb752dca714a591c84587c9d70762
v8/test/test262/data: https://chromium.googlesource.com/external/github.com/tc39/test262.git@29c23844494a7cc2fbebc6948d2cb0bcaddb24e7
src/foo/bar: https://chromium.googlesource.com/external/github.com/foo/bar@29c23844494a7cc2fbebc6948d2cb0bcaddb24e7
v8/tools/gyp: https://chromium.googlesource.com/external/gyp.git@702ac58e477214c635d9b541932e75a95d349352
src/tools/luci-go:infra/tools/luci/isolate/${platform}: https://chrome-infra-packages.appspot.com/infra/tools/luci/isolate/${platform}@git_revision:8b15ba47cbaf07a56f93326e39f0c8e5069c19e9
v8/tools/clang/dsymutil:chromium/llvm-build-tools/dsymutil: https://chrome-infra-packages.appspot.com/chromium/llvm-build-tools/dsymutil@OWlhXkmj18li3yhJk59Kmjbc5KdgLh56TwCd1qBdzlIC
v8/tools/swarming_client: https://chromium.googlesource.com/external/swarming.client.git@380e32662312eb107f06fcba6409b0409f8fe000"""
  cr_deps_info = """src: https://chromium.googlesource.com/chromium/src.git
src/buildtools: https://chromium.googlesource.com/chromium/buildtools.git@5fd66957f08bb752dca714a591c84587c9d70762
src/foo/bar: https://github.com/foo/bar.git@29c23844494a7cc2fbebc6948d2cb0bcaddb24e7
src/third_party/snappy/src: https://chromium.googlesource.com/external/snappy.git@762bb32f0c9d2f31ba4958c7c0933d22e80c20bf
src/tools/gyp: https://chromium.googlesource.com/external/gyp.git@e7079f0e0e14108ab0dba58728ff219637458563
src/tools/luci-go:infra/tools/luci/isolate/${platform}: https://chrome-infra-packages.appspot.com/infra/tools/luci/isolate/${platform}@git_revision:3d8f881462b1a93c7525499381fafc8a08691be7
v8/tools/swarming_client: https://chromium.googlesource.com/external/swarming.client.git@380e32662312eb107f06fcba6409b0409f8fe001"""

  def template(testname, buildername):
    return (
        api.test(testname) +
        api.properties.generic(path_config='kitchen') +
        api.buildbucket.ci_build(
            project='v8',
            git_repo='https://chromium.googlesource.com/v8/v8',
            builder=buildername,
            revision='',
        ) +
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
        ) +
        api.runtime(is_luci=True, is_experimental=False)
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
      api.properties.generic(path_config='kitchen') +
      api.buildbucket.ci_build(
        project='v8',
        git_repo='https://chromium.googlesource.com/v8/v8',
        builder='Auto-roll - v8 deps'
      ) +
      api.override_step_data(
          'gerrit changes', api.json.output(
              [{'_number': '123', 'subject': 'Update V8 DEPS.'}])) +
      api.runtime(is_luci=True, is_experimental=False) +
      api.post_process(MustRun, 'gerrit abandon') +
      api.post_process(DropExpectation)
  )
