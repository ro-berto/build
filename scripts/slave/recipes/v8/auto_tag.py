# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This recipe checks if a version update on branch <B> is necessary, where
'version' refers to the contents of the v8 version file (part of the v8
sources).

The recipe will:
- Commit a v8 version change to <B> with an incremented patch level if the
  latest two commits point to the same version.
- Make sure that the actual HEAD of <B> is tagged with its v8 version (as
  specified in the v8 version file at HEAD).
- Update a ref called <B>-lkgr to point to the latest commit that has a unique,
  incremented version and that is tagged with that version.
"""

import re

from recipe_engine.post_process import DropExpectation, MustRun

DEPS = [
  'depot_tools/gclient',
  'depot_tools/git',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/service_account',
  'recipe_engine/step',
  'v8',
]

REPO = 'https://chromium.googlesource.com/v8/v8'
RELEASE_BRANCH_REF_RE = re.compile(r'^refs/branch-heads/\d+\.\d+$')
MAX_COMMIT_WAIT_RETRIES = 5

# TODO(sergiyb): Replace with api.service_account.default().get_email() when
# https://crbug.com/846923 is resolved.
PUSH_ACCOUNT = (
    'v8-ci-autoroll-builder@chops-service-accounts.iam.gserviceaccount.com')


def InitClean(api):
  """Ensures a clean state of the git checkout."""
  with api.context(cwd=api.path['checkout']):
    api.git('checkout', '-f', 'FETCH_HEAD')
    api.git('branch', '-D', 'work', ok_ret='any')
    api.git('clean', '-ffd')


def Git(api, *args, **kwargs):
  """Convenience wrapper."""
  with api.context(cwd=api.path['checkout']):
    return api.git(
        *args,
        stdout=api.raw_io.output_text(),
        **kwargs
    ).stdout


def GetCommitForRef(api, repo, ref):
  result = Git(
      api, 'ls-remote', repo, ref,
      # Need str() to turn unicode into ascii in production.
      name=str('git ls-remote %s' % ref.replace('/', '_')),
  ).strip()
  if result:
    # Extract hash if available. Otherwise keep empty string.
    result = result.split()[0]
  api.step.active_result.presentation.logs['ref'] = [result]
  return result


def PushRef(api, repo, ref, hsh):
  with api.context(cwd=api.path['checkout']):
    api.git('push', repo, '+%s:%s' % (hsh, ref))


def LogStep(api, text):
  api.step('log', ['echo', text])


def IncrementVersion(api, ref, latest_version, latest_version_file):
  """Increment the version on branch 'ref' to the next patch level and wait
  for the committed ref to be gnumbd-ed or time out.

  Args:
    api: The recipe api.
    ref: Ref name where to change the version, e.g.
         refs/remotes/branch-heads/1.2.
    latest_version: The currently latest version to be incremented.
    latest_version_file: The content of the current version file.
  """

  # Create a fresh work branch.
  with api.context(
      cwd=api.path['checkout'],
      env_prefixes={'PATH': [api.v8.depot_tools_path]}):
    api.git('new-branch', 'work', '--upstream', ref)
    api.git(
        'config', 'user.name', 'V8 Autoroll', name='git config user.name',
    )
    api.git(
        'config', 'user.email', PUSH_ACCOUNT, name='git config user.email',
    )

  # Increment patch level and update file content.
  latest_version = latest_version.with_incremented_patch()
  latest_version_file = latest_version.update_version_file_blob(
      latest_version_file)

  # Write file to disk.
  api.file.write_text(
      'Increment version',
      api.path['checkout'].join(api.v8.VERSION_FILE),
      latest_version_file,
  )

  # Commit and push changes.
  with api.context(cwd=api.path['checkout']):
    api.git('commit', '-am', 'Version %s' % latest_version)

  if api.properties.get('dry_run') or api.runtime.is_experimental:
    api.step('Dry-run commit', cmd=None)
    return

  with api.context(
      cwd=api.path['checkout'],
      env_prefixes={'PATH': [api.v8.depot_tools_path]}):
    api.git('cl', 'upload', '-f', '--bypass-hooks', '--send-mail',
            '--no-autocc', '--tbrs', PUSH_ACCOUNT)
    api.git('cl', 'land', '-f', '--bypass-hooks', name='git cl land')

  # Function to check if commit has landed.
  def has_landed():
    with api.context(cwd=api.path['checkout']):
      api.git('fetch', REPO, 'refs/branch-heads/*:refs/remotes/branch-heads/*')
    real_latest_version = api.v8.read_version_from_ref(ref, 'committed')
    return real_latest_version == latest_version

  # Wait for commit to land (i.e. wait for gnumbd).
  count = 1
  while not has_landed():
    if count == MAX_COMMIT_WAIT_RETRIES:
      # This is racy. Someone other than this script might
      # commit another version change right before the fetch (rarely).
      # In this case, we time out and leave this commit untagged.
      step_result = api.step(
          'Waiting for commit timed out', cmd=None)
      step_result.presentation.status = api.step.FAILURE
      break
    api.python.inline(
        'Wait for commit',
        'import time; time.sleep(%d)' % (5 * count),
    )
    count += 1


def RunSteps(api):
  # Ensure a proper branch is specified.
  ref = api.buildbucket.gitiles_commit.ref
  if not ref or not RELEASE_BRANCH_REF_RE.match(ref):
    raise api.step.InfraFailure('A ref for release branch must be specified.')
  branch = ref[len('refs/branch-heads/'):]
  repo = api.properties.get('repo', REPO)

  local_branch_ref = 'refs/remotes/branch-heads/%s' % branch

  api.gclient.set_config('v8')
  with api.context(cwd=api.path['builder_cache']):
    api.gclient.checkout()

  # Enforce a clean state.
  InitClean(api)

  # Check the last two versions.
  latest_version_file = api.v8.read_version_file(local_branch_ref, 'latest')
  latest_version = api.v8.version_from_file(latest_version_file)

  previous_version = api.v8.read_version_from_ref(
      local_branch_ref + '~1', 'previous')

  # If the last two commits have the same version, we need to create a version
  # increment.
  if latest_version == previous_version:
    IncrementVersion(
        api, local_branch_ref, latest_version, latest_version_file)
  elif not latest_version == previous_version.with_incremented_patch():
    step_result = api.step(
        'Incorrect patch levels between %s and %s' % (
              previous_version, latest_version),
        cmd=None,
    )
    step_result.presentation.status = api.step.WARNING

  # Read again the current HEAD's version and check if it is tagged with it.
  # If fetching the version change from above has timed out, we don't want
  # to set the wrong tag.
  head = Git(api, 'log', '-n1', '--format=%H', local_branch_ref).strip()
  head_version = api.v8.read_version_from_ref(head, 'head')
  tag = Git(api, 'describe', '--tags', head).strip()

  if tag != str(head_version):
    # Tag latest version.
    if api.properties.get('dry_run') or api.runtime.is_experimental:
      api.step('Dry-run tag %s' % head_version, cmd=None)
    else:
      with api.context(cwd=api.path['checkout']):
        api.git('tag', str(head_version), head)
        api.git('push', repo, str(head_version))

  # Update lkgr ref.
  # TODO(machenbach): Add updating refs/heads/release/%s instead.
  UpdateRef(api, repo, head, 'refs/heads/%s-lkgr' % branch)


def UpdateRef(api, repo, head, lkgr_ref):
  # Get the branch's current lkgr ref and update to HEAD.
  current_lkgr = GetCommitForRef(api, repo, lkgr_ref)
  # If the lkgr_ref doesn't exist, it's an empty string. In this case the push
  # ref command will create it.
  if head != current_lkgr:
    if api.properties.get('dry_run') or api.runtime.is_experimental:
      api.step('Dry-run lkgr update %s' % head, cmd=None)
    else:
      PushRef(api, repo, lkgr_ref, head)
  else:
    LogStep(api, 'There is no new lkgr.')


def GenTests(api):
  hsh_old = '74882b7a8e55268d1658f83efefa1c2585cee723'
  hsh_new = 'c1a7fd0c98a80c52fcf6763850d2ee1c41cfe8d6'

  def stdout(step_name, text):
    return api.override_step_data(
        step_name, api.raw_io.stream_output(text, stream='stdout'))

  def test(name, patch_level_previous, patch_level_latest,
           patch_level_after_commit, current_lkgr, head, head_tag,
           wait_count=0, commit_found_count=0, dry_run=False,
           commit_loop_test_data=True):
    test_data = (
        api.test(name) +
        api.properties.generic(mastername='client.v8.branches',
                               path_config='kitchen') +
        api.buildbucket.ci_build(
          project='v8',
          git_repo='https://chromium.googlesource.com/v8/v8',
          builder='Auto-tag',
          git_ref='refs/branch-heads/3.4',
        ) +
        api.v8.version_file(patch_level_latest, 'latest') +
        api.v8.version_file(patch_level_previous, 'previous') +
        api.v8.version_file(patch_level_after_commit, 'head') +
        stdout('git log', head) +
        stdout('git describe', head_tag) +
        stdout(
            'git ls-remote refs_heads_3.4-lkgr',
            current_lkgr + '\trefs/heads/3.4-lkgr',
        )
    )
    if dry_run:
      test_data += api.properties(dry_run=True)
    elif commit_loop_test_data:
      # Test data for the loop waiting for the version-increment commit.
      for count in range(1, wait_count + 1):
        test_data += api.v8.version_file(
            patch_level_latest + bool(count == commit_found_count),
            'committed',
            count,
        )
    return test_data

  # Test where version, the tag at HEAD and the lkgr are up-to-date.
  yield test(
      'same_lkgr',
      patch_level_previous=2,
      patch_level_latest=3,
      patch_level_after_commit=3,
      current_lkgr=hsh_old,
      head=hsh_old,
      head_tag='3.4.3.3',
  )
  # Requires a version update, sets a tag and updates the lkgr. After the
  # version-increment commit has been found, 'git describe' doesn't find
  # an accurate version tag.
  yield test(
      'update',
      patch_level_previous=2,
      patch_level_latest=2,
      patch_level_after_commit=3,
      current_lkgr=hsh_old,
      head=hsh_new,
      head_tag='3.4.3.2-sometext',
      wait_count=2,
      commit_found_count=2,
  )
  # Requires a version update, but times out waiting for gnumbd. After the
  # timeout, HEAD still points to the last commit which has a consistent
  # version tag.
  yield test(
      'update_timeout',
      patch_level_previous=2,
      patch_level_latest=2,
      patch_level_after_commit=2,
      current_lkgr=hsh_old,
      head=hsh_old,
      head_tag='3.4.3.2',
      wait_count=MAX_COMMIT_WAIT_RETRIES,
      commit_found_count=MAX_COMMIT_WAIT_RETRIES + 1,
  )
  # No updates required, but lkgr ref is missing, i.e. was never set. Also warn
  # about an inconsistency in the patch levels.
  yield test(
      'missing',
      patch_level_previous=1,
      patch_level_latest=3,
      patch_level_after_commit=3,
      current_lkgr='',
      head=hsh_new,
      head_tag='3.4.3.3',
  )
  # Everything out-of-date, but dry run.
  yield test(
      'dry_run',
      patch_level_previous=2,
      patch_level_latest=2,
      patch_level_after_commit=2,
      current_lkgr='hsh_old',
      head=hsh_new,
      head_tag='3.4.3.1-sometext',
      dry_run=True
  )
  # The bot was triggered without specifying a branch.
  yield (
      api.test('missing_branch') +
      api.properties.generic(mastername='client.v8.branches',
                             path_config='kitchen') +
      api.buildbucket.ci_build(
        project='v8',
        git_repo='https://chromium.googlesource.com/v8/v8',
        builder='Auto-tag',
      )
  )
  # Experimental mode.
  yield (
      test(
        'experimental',
        patch_level_previous=2,
        patch_level_latest=2,
        patch_level_after_commit=3,
        current_lkgr=hsh_old,
        head=hsh_new,
        head_tag='3.4.3.2-sometext',
        wait_count=2,
        commit_found_count=2,
        commit_loop_test_data=False
      ) +
      api.runtime(is_luci=True, is_experimental=True) +
      api.post_process(
        MustRun,
        'Dry-run commit',
        'Dry-run tag 3.4.3.3',
        'Dry-run lkgr update c1a7fd0c98a80c52fcf6763850d2ee1c41cfe8d6') +
      api.post_process(DropExpectation)
  )
