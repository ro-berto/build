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

from recipe_engine.post_process import (
    DropExpectation, DoesNotRunRE, MustRun, StepFailure)
from recipe_engine.recipe_api import Property

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'builder_group',
    'depot_tools/gclient',
    'depot_tools/gerrit',
    'depot_tools/git',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/json',
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

RELEASE_BRANCH_REF_RE = re.compile(r'^refs/branch-heads/\d+\.\d+$')
MAX_COMMIT_WAIT_RETRIES = 5
MAX_NUMBER_OF_TRACKED_BRANCHES = 10
REMOTE_REPO_URL = 'https://chromium.googlesource.com/v8/v8.git'

# TODO(sergiyb): Replace with api.service_account.default().get_email() when
# https://crbug.com/846923 is resolved.
PUSH_ACCOUNT = (
    'v8-ci-autoroll-builder@chops-service-accounts.iam.gserviceaccount.com')

PROPERTIES = {
    'tracked_branches_count': Property(
            kind=int,
            help='Number of maximum branches that we want to track.',
            default=MAX_NUMBER_OF_TRACKED_BRANCHES)
}


def RunSteps(api, tracked_branches_count):
    api.gclient.set_config('v8')
    api.v8.checkout(with_branch_heads=True)

    with api.context(
            cwd=api.path['checkout'],
            env_prefixes={'PATH': [api.v8.depot_tools_path]}):
        branches = last_branches(api)
        assert len(branches) >= tracked_branches_count
        for branch_version in branches[:tracked_branches_count]:
            check_branch(api, branch_version)


def check_branch(api, branch_version):
    with api.step.nest('Checking branch %s.%s' % branch_version):
        branch_ref = 'branch-heads/%s.%s' % branch_version
        git_output(api, 'checkout', branch_ref)
        version_at_branch_head = api.v8.read_version_from_ref(
            "HEAD", branch_ref)
        proof_of_version_change = git_output(api,
            'show', 'HEAD:%s' % api.v8.VERSION_FILE,
            ok_ret='any',
            name='Proof of version change')
        if proof_of_version_change:
            verify_tag(api, version_at_branch_head)
            verify_lkgr(api, branch_version, version_at_branch_head)
        else:
            maybe_increment_version(api, branch_ref, version_at_branch_head)


def last_branches(api):
    branch_step = api.git(
        'branch',
        '-r',
        '--list',
        'branch-heads/*',
        stdout=api.raw_io.output_text(),
        name='last branches')
    output = branch_step.stdout
    branch_step.presentation.logs['stdout'] = output.splitlines()
    branch_pattern = re.compile(r"branch-heads/(\d+)\.(\d+)")
    versions = []
    for line in output.splitlines():
        m = branch_pattern.match(line.strip())
        if m:
            versions.append((int(m.group(1)), int(m.group(2))))
    versions.sort()
    versions.reverse()
    return versions


def verify_tag(api, version_at_branch_head):
    with api.step.nest('Verify tag'):
        commit_at_tag = git_output(api,
                'show', '--format=%H', '--no-patch',
                'refs/tags/%s' % version_at_branch_head,
                name='Commit at %s' % version_at_branch_head,
                ok_ret='any')
        commit_at_head = git_output(api,
                'show', '--format=%H', '--no-patch', 'HEAD',
                name='Commit at HEAD')
        assert commit_at_head
        if commit_at_head != commit_at_tag:
            # Tag latest version.
            if api.properties.get('dry_run') or api.runtime.is_experimental:
                api.step('Dry-run tag %s' % version_at_branch_head, cmd=None)
            else:
                api.git('tag', str(version_at_branch_head), 'HEAD')
                api.git('push', REMOTE_REPO_URL, str(version_at_branch_head))


def verify_lkgr(api, branch_version, version_at_branch_head):
    with api.step.nest('Verify LKGR'):
        lkgr_ref = 'refs/heads/%s.%s-lkgr' % branch_version
        current_lkgr = get_commit_for_ref(api, lkgr_ref)
        branch_head = get_commit_for_ref(api,
                'refs/tags/%s' % version_at_branch_head)
        api.step('LKGR commit %s' % current_lkgr, [])
        api.step('HEAD commit %s' % branch_head, [])
        if branch_head != current_lkgr:
            set_lkgr(api, branch_head, lkgr_ref)
        else:
            api.step('There is no new lkgr.', [])


def set_lkgr(api, branch_head, lkgr_ref):
    if api.properties.get('dry_run') or api.runtime.is_experimental:
        api.step('Dry-run lkgr update %s' % branch_head, cmd=None)
    else:
        push_ref(api, REMOTE_REPO_URL, lkgr_ref, branch_head)


def git_output(api, *args, **kwargs):
    """Convenience wrapper."""
    step_result = api.git(*args, stdout=api.raw_io.output_text(), **kwargs)
    result = step_result.stdout
    step_result.presentation.logs['stdout'] = result.splitlines()
    return result.strip()


def get_commit_for_ref(api, ref):
    result = git_output(
        api,
        'ls-remote',
        REMOTE_REPO_URL,
        ref,
        # Need str() to turn unicode into ascii in production.
        name=str('git ls-remote %s' % ref.replace('/', '_')),
    )
    if result:
        # Extract hash if available. Otherwise keep empty string.
        result = result.split()[0]
    return result


def push_ref(api, repo, ref, hsh):
    api.git('push', repo, '+%s:%s' % (hsh, ref))


def maybe_increment_version(api, ref, latest_version):
    with api.step.nest('Increment version from %s' % latest_version):
        commits = api.gerrit.get_changes(
            'chromium-review.googlesource.com',
            query_params=[
                ('project', 'v8/v8'),
                ('owner', PUSH_ACCOUNT),
                ('status', 'open'),
            ],
            limit=20,
            step_test_data=api.gerrit.test_api.get_empty_changes_response_data,
        )
        if [c for c in commits if c['subject'] == subject(latest_version)]:
            step_result = api.step('Stale version change CL found!', cmd=None)
            step_result.presentation.status = 'FAILURE'
        else:
            increment_version(api, ref, latest_version)


def subject(latest_version):
    return 'Version %s' % latest_version

def increment_version(api, ref, latest_version):
    """Increment the version on branch 'ref' to the next patch level.

    Args:
      api: The recipe api.
      ref: Ref name where to change the version, e.g.
           refs/remotes/branch-heads/1.2.
      latest_version: The currently latest version to be incremented.
    """
    api.git('branch', '-D', 'work', ok_ret='any')
    api.git('clean', '-ffd')

    # Create a fresh work branch.
    api.git('new-branch', 'work', '--upstream', ref)
    api.git(
        'config',
        'user.name',
        'V8 Autoroll',
        name='git config user.name',
    )
    api.git(
        'config',
        'user.email',
        PUSH_ACCOUNT,
        name='git config user.email',
    )

    # Increment patch level and update file content.
    latest_version_file = api.v8.read_version_file(ref, 'latest')
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
    api.git('commit', '-am', 'Version %s' % latest_version)

    if api.properties.get('dry_run') or api.runtime.is_experimental:
        api.step('Dry-run commit', cmd=None)
        return

    api.git('cl', 'upload', '-f', '--bypass-hooks', '--send-mail',
            '--no-autocc', '--set-bot-commit')
    api.git('cl', 'land', '-f', '--bypass-hooks')

def GenTests(api):

    def stdout(step_name, text):
        return api.override_step_data(
            step_name, api.raw_io.stream_output(text, stream='stdout'))
    def test(name, branches=1):
        return api.test(name) + api.properties(tracked_branches_count=branches)

    yield (
        test('branches-to-update-version-for', 2) +
        stdout('last branches', 'branch-heads/9.1\nbranch-heads/9.2') +
        api.v8.version_file(3, 'branch-heads/9.2',
                prefix="Checking branch 9.2.") +
        api.v8.version_file(4, 'latest',
                prefix="Checking branch 9.2.Increment version from 3.4.3.3.") +
        api.v8.version_file(2, 'branch-heads/9.1',
                prefix="Checking branch 9.1.") +
        api.v8.version_file(3, 'latest',
                prefix="Checking branch 9.1.Increment version from 3.4.3.2.")
    )

    yield (
        test('dry-run-branches-to-update-version-for', 2) +
        api.runtime(is_experimental=True) +
        stdout('last branches', 'branch-heads/9.1\nbranch-heads/9.2') +

        api.v8.version_file(3, 'branch-heads/9.2',
                prefix="Checking branch 9.2.") +
        api.v8.version_file(4, 'latest',
                prefix="Checking branch 9.2.Increment version from 3.4.3.3.") +
        api.v8.version_file(2, 'branch-heads/9.1',
                prefix="Checking branch 9.1.") +
        api.v8.version_file(3, 'latest',
                 prefix="Checking branch 9.1.Increment version from 3.4.3.2.")
    )

    yield (
        test('branche-with-stale-version-update') +
        stdout('last branches', 'branch-heads/9.2') +

        api.v8.version_file(3, 'branch-heads/9.2',
                prefix="Checking branch 9.2.") +
        api.override_step_data('Checking branch 9.2.'
                'Increment version from 3.4.3.3.gerrit changes',
                api.json.output([{
                        '_number': '123',
                        'subject': 'Version 3.4.3.3'}])) +
        api.post_process(StepFailure, 'Checking branch 9.2.'
                'Increment version from 3.4.3.3.'
                'Stale version change CL found!')
    )


    yield (
        test('branch-with-updated-version-but-no-tag') +
        stdout('last branches', 'branch-heads/9.3') +
        api.v8.version_file(3, 'branch-heads/9.3',
                            prefix="Checking branch 9.3.") +
        stdout('Checking branch 9.3.Proof of version change',
            'dummy proof of version change') +
        stdout('Checking branch 9.3.Verify tag.Commit at HEAD', '123') +
        api.post_process(MustRun, 'Checking branch 9.3.Verify tag.git push') +
        api.post_process(DropExpectation)
    )

    yield (
        test('branch-with-correct-tags') +
        stdout('last branches', 'branch-heads/9.3') +
        api.v8.version_file(3, 'branch-heads/9.3',
                            prefix="Checking branch 9.3.") +
        stdout('Checking branch 9.3.Proof of version change',
                'dummy proof of version change') +
        stdout('Checking branch 9.3.Verify tag.Commit at 3.4.3.3', '123') +
        stdout('Checking branch 9.3.Verify tag.Commit at HEAD', '123') +
        stdout('Checking branch 9.3.Verify LKGR.'
                'git ls-remote refs_heads_9.3-lkgr', '112233') +
        stdout('Checking branch 9.3.Verify LKGR.'
            'git ls-remote refs_tags_3.4.3.3', '112233') +
        api.post_process(DoesNotRunRE, 'Checking branch 9.3.'
                'Verify tag.git tag') +
        api.post_process(MustRun, 'Checking branch 9.3.Verify LKGR.'
                'There is no new lkgr.')
    )

    yield (
        test('lkgr-branch') +
        stdout('last branches', 'branch-heads/9.3') +
        api.v8.version_file(3, 'branch-heads/9.3',
                            prefix="Checking branch 9.3.") +
        stdout('Checking branch 9.3.Proof of version change',
                'dummy proof of version change') +
        stdout('Checking branch 9.3.Verify tag.Commit at 3.4.3.3', '123') +
        stdout('Checking branch 9.3.Verify tag.Commit at HEAD', '123') +
        stdout('Checking branch 9.3.Verify LKGR.'
                'git ls-remote refs_heads_9.3-lkgr', 'faceb00c') +
        stdout('Checking branch 9.3.Verify LKGR.'
                'git ls-remote refs_tags_3.4.3.3', '404') +
        api.post_process(MustRun, 'Checking branch 9.3.Verify LKGR.git push') +
        api.post_process(DropExpectation)
    )

    yield (
        test('dry-run-branch-no-tag-no-lkgr') +
        api.runtime(is_experimental=True) +
        stdout('last branches', 'branch-heads/9.3') +
        stdout('Checking branch 9.3.Proof of version change',
                'dummy proof of version change') +
        stdout('Checking branch 9.3.Verify tag.Commit at HEAD', '123') +
        api.v8.version_file(3, 'branch-heads/9.3',
                            prefix="Checking branch 9.3.") +
        stdout('Checking branch 9.3.Verify LKGR.'
                'git ls-remote refs_heads_9.3-lkgr', '3e1a') +
        stdout('Checking branch 9.3.Verify LKGR.'
                'git ls-remote refs_tags_3.4.3.3', '404') +
        api.post_process(MustRun, 'Checking branch 9.3.Verify LKGR.'
                'Dry-run lkgr update 404')
    )