# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import (
    DoesNotRun, DropExpectation, Filter, MustRun)
from recipe_engine.recipe_api import Property
from recipe_engine.config import ConfigGroup, Dict, Single, List
from recipe_engine.engine_types import freeze

PYTHON_VERSION_COMPATIBILITY = "PY3"

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
  'recipe_engine/raw_io',
  'recipe_engine/service_account',
  'recipe_engine/step',
  'recipe_engine/url',
  'v8',
]

PROPERTIES = {
    # Configuration of the auto-roller
    'autoroller_config':
        Property(
            kind=ConfigGroup(
                # Subject of the rolling CL
                subject=Single(str),
                # Configuration parameters of the project where dependencies
                # will be rolled in. The source is always Chromium project.
                target_config=ConfigGroup(
                    # Solution name to be used for project checkout
                    solution_name=Single(str, required=True),
                    # Project name. Together with the 'base_url' it will form
                    # the location for the project
                    project_name=Single(str, required=True),
                    # The name of the account used to create the roll CL
                    account=Single(str),
                    # Template for the commit message used with regular
                    # dependencies
                    log_template=Single(str),
                    # Template for the commit message used with cipd
                    # dependencies
                    cipd_log_template=Single(str),
                    # Gerrit URL to be used for rolling CL review
                    gerrit_base_url=Single(
                        str,
                        required=True,
                        empty_val='https://chromium-review.googlesource.com'),
                    # Repo base URL together with 'project_name' to locate the
                    # repo where the rolling CL will be landed
                    base_url=Single(
                        str,
                        required=True,
                        empty_val='https://chromium.googlesource.com/'),
                ),
                # List of (target side) dependencies to be expcluded from
                # rolling with the current config
                excludes=Single(list, empty_val=None),
                # List of (target side) dependencies to be included when rolling
                # with the current config
                includes=Single(list, empty_val=None),
                # Mapping between the dependency name in the target project and
                # the name in the source project
                deps_key_mapping=Dict(value_type=str),
                # List of reviewers of the roll CL
                reviewers=List(str),
                # Add extra log entries to the commit message.
                show_commit_log=Single(bool),
                # Flag for rolling the binary chromium pin in target project
                roll_chromium_pin=Single(bool, empty_val=False),
                # Bugs included in roll CL description
                # TODO(liviurau): Remove obsolete feature from configs and
                # remove the parameters here afterwards
                bugs=Single(str),
            )),
}

GERRIT_BASE_URL = 'https://chromium-review.googlesource.com'
BASE_URL = 'https://chromium.googlesource.com/'
CR_PROJECT_NAME = 'chromium/src'
MAX_COMMIT_LOG_ENTRIES = 8
CIPD_DEP_URL_PREFIX = 'https://chrome-infra-packages.appspot.com/'


# DEPS configuration of pinned Devtools-Frontend Chromium versions.
STORAGE_URL = ('https://commondatastorage.googleapis.com/'
               'chromium-browser-snapshots/%s/LAST_CHANGE')
CHROMIUM_PINS = {
  'chromium_linux': STORAGE_URL % 'Linux_x64',
  'chromium_win': STORAGE_URL % 'Win_x64',
  'chromium_mac': STORAGE_URL % 'Mac',
}


def GetDEPS(api, name, project_name, base_url):
  # Make a fake spec. Gclient is not nice to us when having two solutions
  # side by side. The latter checkout kills the former's gclient file.
  spec = ('solutions=[{'
          '\'managed\':False,'
          '\'name\':\'%s\','
          '\'url\':\'%s\','
          '\'deps_file\':\'DEPS\'}]' % (name, base_url + project_name))

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
    tokens = line.strip().split(' ')
    if len(tokens) != 2:
      raise Exception("malformatted DEPS entry '%s'" % tokens)

    key, value = tokens

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


def roll_chromium_pin(api):
  """Updates the values of gclient variables chromium_(win|mac|linux) with the
  latest prebuilt versions.
  """
  with api.context(cwd=api.path['checkout']):
    for var_name, url in sorted(CHROMIUM_PINS.items()):
      step_result = api.gclient(
          'get %s deps' % var_name,
          ['getdep', '--var=%s' % var_name],
          stdout=api.raw_io.output_text())
      # The first line contains the commit position number. Strip the rest.
      current_number = int(step_result.stdout.strip().splitlines()[0].strip())
      new_number = int(api.url.get_text(
          url,
          step_name='check latest %s' % var_name,
          default_test_data='123').output)
      if new_number > current_number:
        api.gclient(
            'set %s deps' % var_name,
            ['setdep', '--var=%s=%d' % (var_name, new_number)])


def create_gclient_config(api, target_config, base_url):
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = target_config['solution_name']
  soln.url = base_url + target_config['project_name']
  soln.revision = 'HEAD'
  return src_cfg


def get_tot_revision(api, name, target_loc):
  def ls_remote(branch, name_suffix=''):
    step_result = api.git(
        'ls-remote', target_loc, 'refs/heads/%s' % branch,
        name='look up %s%s' % (name.replace('/', '_'), name_suffix),
        stdout=api.raw_io.output_text(),
    )
    return step_result.stdout.strip()

  output = ls_remote('main')
  if output:
    return output.split('\t')[0]

  # TODO(crbug.com/1222015): Fallback code for refs/heads/main
  # needed until all repositories use a main branch.
  output = ls_remote('main', ' (fallback)')
  api.step.active_result.presentation.status = api.step.WARNING
  api.step.active_result.presentation.step_text += (
      '%s lacks a main branch\n' % name)
  return output.split('\t')[0]


def get_key_mapper(autoroller_config):
  custom_mapping = autoroller_config.get('deps_key_mapping', {})
  if custom_mapping:
    # Mapper that looks-up the key in the dictionary
    # or return the key as the default value
    return lambda key: custom_mapping.get(key, key)
  else:
    # Identity mapper (no mapping)
    return lambda key: key


def get_recent_instance_id(api, package_name):
  """Returns the latest uploaded instance id for a package.

  If a ref named `latest` is used, prefer this instance. Otherwise select the
  most recently uploaded instance.
  """
  instances = api.cipd.instances(package_name, 0)

  for instance in instances:
    if instance.refs and 'latest' in instance.refs:
      return instance.pin.instance_id

  return instances[0].pin.instance_id


def RunSteps(api, autoroller_config):
  target_config = autoroller_config['target_config']

  # Look for overrides for the default base and gerrit locations
  target_gerrit_base_url = target_config.get('gerrit_base_url', GERRIT_BASE_URL)
  target_base_url = target_config.get('base_url', BASE_URL)

  # Bail out on existing roll. Needs to be manually closed.
  commits = api.gerrit.get_changes(
      target_gerrit_base_url,
      query_params=[
          ('project', target_config['project_name']),
          # TODO(sergiyb): Use api.service_account.default().get_email() when
          # https://crbug.com/846923 is resolved.
          ('owner', target_config['account']),
          ('status', 'open'),
      ],
      limit=20,
      step_test_data=api.gerrit.test_api.get_empty_changes_response_data,
  )
  for commit in commits:
    # The auto-roller might have a CL open for a particular roll config.
    if commit['subject'] == autoroller_config['subject']:
      api.gerrit.abandon_change(target_gerrit_base_url, commit['_number'],
                                'stale roll')
      step_result = api.step('Previous roll failed', cmd=None)
      step_result.presentation.step_text = 'Notify sheriffs!'
      step_result.presentation.status = 'FAILURE'

  api.gclient.c = create_gclient_config(api, target_config, target_base_url)
  api.gclient.apply_config('chromium')

  # Allow rolling all os deps.
  api.gclient.c.target_os.add('android')
  api.gclient.c.target_os.add('win')

  api.v8.checkout(ignore_input_commit=True, set_output_commit=False)

  # Enforce a clean state.
  with api.context(
      cwd=api.path['checkout'],
      env_prefixes={'PATH': [api.v8.depot_tools_path]}):
    api.git('checkout', '-f', 'origin/main')
    api.git('branch', '-D', 'roll', ok_ret='any')
    api.git('clean', '-ffd')
    api.git('new-branch', 'roll')

  # Get chromium's and the target repo's deps information.
  cr_deps = GetDEPS(api, 'src', CR_PROJECT_NAME, BASE_URL)
  target_deps = GetDEPS(api, target_config['solution_name'],
                        target_config['project_name'], target_base_url)

  commit_message = []

  # Include/exclude certain deps keys.
  excludes = autoroller_config.get('excludes')
  includes = autoroller_config.get('includes')

  # Map deps keys between destination and source
  key_mapper = get_key_mapper(autoroller_config)

  # Iterate over all target deps.
  failed_deps = []
  for name in sorted(target_deps.keys()):
    if excludes is not None and name in excludes:
      continue
    if includes is not None and name not in includes:
      continue
    def SplitValue(solution_name, value):
      assert '@' in value, (
          'Found %s value %s without pinned revision.' % (solution_name, name))
      return value.split('@')

    target_loc, target_ver = SplitValue(
        target_config['solution_name'], target_deps[name])
    cr_value = cr_deps.get(key_mapper(name))
    is_cipd_dep = target_loc.startswith(CIPD_DEP_URL_PREFIX)
    if cr_value:
      # Use the given revision from chromium's DEPS file.
      cr_repo, new_ver = SplitValue('src', cr_value)
      if target_loc != cr_repo:
        # The gclient tool does not have commands that allow overriding the
        # repo, hence we'll need to make changes like this manually. However,
        # this should not block updating other DEPS and creating roll CL, hence
        # just create a failing step and continue.
        step_result = api.step(
            'dep %s has changed repo from %s to %s' % (
                name, target_loc, cr_repo),
            cmd=None)
        step_result.presentation.status = api.step.FAILURE
        failed_deps.append(name)
        continue
    else:
      if is_cipd_dep:
        new_ver = get_recent_instance_id(api,
                                         target_loc[len(CIPD_DEP_URL_PREFIX):])
      else:
        # Use the ToT of the deps repo.
        new_ver = get_tot_revision(api, name, target_loc)
      api.step.active_result.presentation.step_text += new_ver

    # Check if an update is necessary.
    if target_ver != new_ver:
      with api.context(cwd=api.path['checkout']):
        step_result = api.gclient(
            'setdep %s' % name.replace('/', '_'),
            ['setdep', '-r', '%s@%s' %
             (name, new_ver)],
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
          commit_message.append(
              target_config['cipd_log_template'] % (path, target_ver, new_ver))
        else:
          repo = target_loc
          if repo.endswith('.git'):
            repo = repo[:-len('.git')]
          commit_message.append(target_config['log_template'] % (
              name, repo, target_ver[:7], new_ver[:7]))
          if autoroller_config['show_commit_log']:
            commit_message.extend(commit_messages_log_entries(
                api, repo, target_ver, new_ver))
      else:
        step_result.presentation.status = api.step.WARNING

  # Roll pinned Chromium binaries.
  if autoroller_config.get('roll_chromium_pin', False):
    roll_chromium_pin(api)

  # Check for a difference. If no deps changed, the diff is empty.
  with api.context(cwd=api.path['checkout']):
    step_result = api.git('diff', stdout=api.raw_io.output_text())
  diff = step_result.stdout.strip()
  step_result.presentation.logs['diff'] = diff.splitlines()

  # Commit deps change and send to CQ.
  if diff:
    args = ['commit', '-a', '-m', autoroller_config['subject']]
    for message in commit_message:
      args.extend(['-m', message])
    args.extend(['-m', 'R=%s' % ','.join(autoroller_config['reviewers'])])
    kwargs = {'stdout': api.raw_io.output_text()}
    with api.context(
        cwd=api.path['checkout'],
        env_prefixes={'PATH': [api.v8.depot_tools_path]}):
      api.git(*args, **kwargs)
      api.git('show')
      upload_args = [
          'cl', 'upload', '-f', '--use-commit-queue', '--bypass-hooks',
          '--set-bot-commit', '--send-mail',
      ]
      if 'bugs' in autoroller_config:
        upload_args += ['-b', autoroller_config['bugs']]
      api.git(*upload_args)

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
mock/package-without-latest-ref:mock/package-without-latest-ref: https://chrome-infra-packages.appspot.com/mock/package-without-latest-ref@7fd66957f08bb752dca714a591c84587c9d70764
mock/package-latest:mock/package-latest: https://chrome-infra-packages.appspot.com/mock/package-latest@6fd66957f08bb752dca714a591c84587c9d70763"""
  cr_deps_info = """src: https://chromium.googlesource.com/chromium/src.git
src/buildtools: https://chromium.googlesource.com/chromium/buildtools.git@5fd66957f08bb752dca714a591c84587c9d70762
src/foo/bar: https://github.com/foo/bar.git@29c23844494a7cc2fbebc6948d2cb0bcaddb24e7
src/third_party/snappy/src: https://chromium.googlesource.com/external/snappy.git@762bb32f0c9d2f31ba4958c7c0933d22e80c20bf
src/tools/gyp: https://chromium.googlesource.com/external/gyp.git@e7079f0e0e14108ab0dba58728ff219637458563
src/tools/luci-go:infra/tools/luci/isolate/${platform}: https://chrome-infra-packages.appspot.com/infra/tools/luci/isolate/${platform}@git_revision:3d8f881462b1a93c7525499381fafc8a08691be7"""
  bad_cr_deps_info = """src: https://chromium.googlesource.com/chromium/src.git
src/buildtools:  https://chromium.googlesource.com/chromium/buildtools.git@5fd66957f08bb752dca714a591c84587c9d70762"""
  target_config_v8 = {
    'solution_name': 'v8',
    'project_name': 'v8/v8',
    'account': 'v8-ci-autoroll-builder@'
              'chops-service-accounts.iam.gserviceaccount.com',
    'log_template': 'Rolling v8/%s: %s/+log/%s..%s',
    'cipd_log_template': 'Rolling v8/%s: %s..%s',
  }
  v8_deps_config = {
        'target_config': target_config_v8,
        'subject': 'Update V8 DEPS.',
        'excludes': [
            'third_party/protobuf',
            'test/test262/data',
        ],
        'reviewers': [
            'anybody@chromium.org',
            'ciciobello@chromium.org',
        ],
        'show_commit_log': False,
    }

  def template(testname, buildername, solution_name='v8'):
    return api.test(
        testname,
        api.buildbucket.ci_build(
            project='v8',
            git_repo='https://chromium.googlesource.com/v8/v8',
            builder=buildername,
            revision='',
        ),
        api.override_step_data(
            'gclient get %s deps' % solution_name,
            api.raw_io.stream_output_text(v8_deps_info, stream='stdout'),
        ),
        api.override_step_data(
            'gclient get src deps',
            api.raw_io.stream_output_text(cr_deps_info, stream='stdout'),
        ),
        api.override_step_data(
            'git diff',
            api.raw_io.stream_output_text('some difference', stream='stdout'),
        ),
    )

  yield (
      template('roll', 'Auto-roll - v8 deps') +
      api.properties(autoroller_config=v8_deps_config) + api.override_step_data(
          'gclient setdep base_trace_event_common',
          retcode=1,
      ) + api.override_step_data(
          'look up build',
          api.raw_io.stream_output_text(
              'deadbeef\trefs/heads/main', stream='stdout'),
      ) + api.override_step_data(
          'look up base_trace_event_common',
          api.raw_io.stream_output_text('', stream='stdout'),
      ) +
      # TODO(crbug.com/1222015): Temporary test data for fallback case. Once
      # all repos have a main branch, add back output for the call above.
      api.override_step_data(
          'look up base_trace_event_common (fallback)',
          api.raw_io.stream_output_text(
              'deadbeef\trefs/heads/main', stream='stdout'),
      ) + api.override_step_data(
          'cipd instances mock/package-without-latest-ref',
          api.cipd._resultify({
              'instances': [{
                  'pin': {
                      'package':
                          'mock/package-without-latest-ref',
                      'instance_id':
                          api.cipd.make_resolved_version('no-latest'),
                  },
                  'registered_by': 'user:doe@developer.gserviceaccount.com',
                  'registered_ts': 1987654321,
                  'refs': None,
              }]
          })))

  yield api.test(
      'bad-cr-roll',
      api.buildbucket.ci_build(
          project='v8',
          git_repo='https://chromium.googlesource.com/v8/v8',
          builder='Auto-roll - v8 deps',
          revision='',
      ) +
      api.properties(autoroller_config=v8_deps_config),
      api.override_step_data(
          'gclient get src deps',
          api.raw_io.stream_output_text(bad_cr_deps_info, stream='stdout'),
      ),
      api.expect_exception("Exception"),
  )

  yield (
      template('commit log', 'Roll with commit log') +
      api.properties(autoroller_config={
          'target_config': target_config_v8,
          'subject': 'Update Test262.',
          'includes': [
              # Only roll these dependencies (list without solution name prefix).
              'test/test262/data',
          ],
          'reviewers': [
              'anybody@chromium.org',
          ],
          'show_commit_log': True,
      }) +
      api.override_step_data(
          'look up test_test262_data',
          api.raw_io.stream_output_text(
              'deadbeef\trefs/heads/main', stream='stdout'),
      ) +
      api.post_process(Filter('git commit', 'git cl'))
  )

  yield (template('p1-roller', 'New roller', 'p1') + api.post_process(
      Filter('git commit', 'git cl')
  ) + api.properties(
      autoroller_config={
          "target_config": {
              "solution_name":
                  "p1",
              "project_name":
                  "p1/p1",
              "account":
                  "p1-autoroll@chops-service-accounts.iam.gserviceaccount.com",
              "log_template":
                  "Rolling %s: %s/+log/%s..%s",
              "cipd_log_template":
                  "Rolling %s: %s..%s",
              "gerrit_base_url":
                  "https://other-review.com",
              "base_url":
                  "https://other-source.com/",
          },
          "subject": "Update DevTools New DEPS.",
          "reviewers": ["liviurau@chromium.org"],
          "deps_key_mapping": {
              "dep1": "third_party/dep1/src"
          },
          "show_commit_log": False,
          "bugs": "none",
      }))

  # Test updating chromium pins. The test data for checking the latest number
  # returns 123 by default. Hence only linux should be updated here.
  important_steps = Filter().include_re(
      r'.*(?:chromium_linux|chromium_win|chromium_mac).*')
  yield (
      template('roll chromium linux pin',
               'Auto-roll - chromium somewhere', 'somewhere') +
      api.override_step_data(
          'gclient get chromium_linux deps',
          api.raw_io.stream_output_text('122', stream='stdout'),
      ) +
      api.override_step_data(
          'gclient get chromium_win deps',
          api.raw_io.stream_output_text('123', stream='stdout'),
      ) +
      api.properties(autoroller_config={
          'target_config': {
            'solution_name': 'somewhere',
            'project_name': 'home/somewhere',
            'account': 'somebot@chops-service-accounts.iam.gserviceaccount.com',
            'log_template': 'Rolling %s: %s/+log/%s..%s',
            'cipd_log_template': 'Rolling %s: %s..%s',
          },
          'subject': 'Update Somewhere Chromium DEPS.',
          # Don't roll any of the other dependencies.
          'includes': [],
          'reviewers': [
              'neicanimeni@chromium.org',
          ],
          'show_commit_log': False,
          'roll_chromium_pin': True,
      }) +
      api.override_step_data(
          'gclient get chromium_mac deps',
          api.raw_io.stream_output_text('124', stream='stdout'),
      ) +
      api.post_process(important_steps) +
      api.post_process(MustRun, 'gclient set chromium_linux deps') +
      api.post_process(DoesNotRun, 'gclient set chromium_win deps') +
      api.post_process(DoesNotRun, 'gclient set chromium_mac deps')
  )

  yield api.test(
      'stale_roll',
      api.buildbucket.ci_build(
          project='v8',
          git_repo='https://chromium.googlesource.com/v8/v8',
          builder='Auto-roll - v8 deps'
          ) +
      api.properties(autoroller_config=v8_deps_config),
      api.override_step_data(
          'gerrit changes',
          api.json.output([{
              '_number': '123',
              'subject': 'Update V8 DEPS.'
          }])),
      api.post_process(MustRun, 'gerrit abandon'),
      api.post_process(MustRun, 'Previous roll failed'),
      api.post_process(DropExpectation),
  )
