# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'chromium',
    'chromium_checkout',
    'depot_tools/gclient',
    'depot_tools/gerrit',
    'depot_tools/git',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/cipd',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/tricium',
]


class _ChangeDetails(object):

  def __init__(self, api):
    changes = api.gerrit.get_changes(
        'https://%s' % api.tryserver.gerrit_change.host,
        query_params=[('change', str(api.tryserver.gerrit_change.change))],
        o_params=[
            'CURRENT_REVISION', 'ALL_COMMITS', 'DETAILED_LABELS',
            'DETAILED_ACCOUNTS'
        ],
        limit=1)

    if not changes:
      raise api.step.InfraFailure(
          'Error querying for CL details: host:%r change:%r; patchset:%r' %
          (api.tryserver.gerrit_change.host, api.tryserver.gerrit_change.change,
           api.tryserver.gerrit_change.patchset))

    change = changes[0]

    # Skip reverted CLs
    self.should_skip_linting = change['subject'].startswith('Revert')

    self.cc = []
    if 'reviewers' in change:
      if 'REVIEWER' in change['reviewers']:
        for reviewer in change['reviewers']['REVIEWER']:
          # Check 'email' here since some account does not have an email address
          if 'email' in reviewer:
            self.cc.append(reviewer['email'])
      if 'CC' in change['reviewers']:
        for reviewer in change['reviewers']['CC']:
          # Check 'email' here since some account does not have an email address
          if 'email' in reviewer:
            self.cc.append(reviewer['email'])


def _RunUntracedMemberAnalyzer(api, src_dir, affected):
  with api.step.nest('untraced_member'):
    target = 'UntracedMember'
    for path in affected:
      contents = api.file.read_text('read_file', path).splitlines()
      for line, text in enumerate(contents):
        pos = text.find(target)
        if not pos == -1:
          with api.step.nest('generate_tricium_comment'):
            category = 'Oilpan'
            oilpan_email = 'oilpan-reviews@chromium.org'
            message = 'Please CC {0} if you are adding new UntracedMember.' \
                      .format(oilpan_email)
            src_dir = api.chromium_checkout.checkout_dir.join('src')
            relpath = api.path.relpath(path, start=src_dir)
            api.tricium.add_comment(
                category,
                message,
                relpath,
                start_line=(line + 1),
                end_line=(line + 1),
                start_char=pos,
                end_char=(pos + len(target)))
          # Providing just one comment is enough to get author's attention.
          return


def RunSteps(api):
  assert api.tryserver.is_tryserver

  change = _ChangeDetails(api)
  if change.should_skip_linting:
    return

  oilpan_email = 'oilpan-reviews@chromium.org'
  if oilpan_email in change.cc:
    api.python.succeeding_step('already_in_cc',
                               '{oilpan_email} is already CCed')
    return

  with api.chromium.chromium_layout():
    api.gclient.set_config('chromium')
    api.chromium.set_config('chromium')

    # Do not rebase the patch, so that the Tricium analyzer observes the correct
    # line numbers. Otherwise, line numbers would be relative to origin/main,
    # which may be synced to include changes subsequent to the actual patch.
    api.chromium_checkout.ensure_checkout(gerrit_no_rebase_patch_ref=True)

    src_dir = api.chromium_checkout.checkout_dir.join('src')
    with api.context(cwd=src_dir):
      src_file_suffixes = {'.cc', '.cpp', '.cxx', '.c', '.h', '.hpp'}
      affected = [
          src_dir.join(f)
          for f in api.chromium_checkout.get_files_affected_by_patch()
          if api.path.exists(src_dir.join(f)) and
          api.path.splitext(f)[1] in src_file_suffixes
      ]
      if not affected:
        api.python.succeeding_step('no_cc_files_changed',
                                   'No C/C++ files changed')
        return

      with api.step.nest('oilpan_analyzer'):
        _RunUntracedMemberAnalyzer(api, src_dir, affected)

      api.tricium.write_comments()


def GenTests(api):

  def test_with_patch(name,
                      affected_files,
                      cc,
                      fake_file_content='',
                      is_revert=False):
    subject = 'Revert foo' if is_revert else 'foo'
    subject += '\nTriciumTest'
    test = (api.test(name) + api.properties.tryserver(
        build_config='Release',
        mastername='tryserver.chromium.linux',
        buildername='linux_chromium_compile_rel_ng',
        buildnumber='1234',
        patch_set=1) + api.platform('linux', 64)) + api.override_step_data(
            'gerrit changes',
            api.json.output([{
                'subject': subject,
                'reviewers': {
                    'REVIEWER': [{
                        "_account_id": 1227909,
                        'name': 'Yuki Yamada',
                        'email': 'yukiy@chromium.org'
                    }],
                    'CC': cc
                }
            }]))

    if affected_files:
      test += api.path.exists(*[
          api.path['cache'].join('builder', 'src', x) for x in affected_files
      ])
      test += api.step_data('git diff to analyze patch',
                            api.raw_io.stream_output('\n'.join(affected_files)))

    if fake_file_content:
      test += api.step_data('oilpan_analyzer.untraced_member.read_file',
                            api.file.read_text(fake_file_content))

    return test

  yield (test_with_patch('infra_failure', affected_files=[], cc=[]) +
         api.override_step_data('gerrit changes', api.json.output([])) +
         api.post_process(post_process.DoesNotRun,
                          'oilpan_analyzer.untraced_member') +
         api.post_check(post_process.StatusException) +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'skip_reverted_cl', affected_files=[], cc=[], is_revert=True) +
         api.post_process(post_process.DoesNotRun,
                          'oilpan_analyzer.untraced_member') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'already_in_cc',
      affected_files=[],
      cc=[{
          'email': 'oilpan-reviews@chromium.org'
      }]) + api.post_process(post_process.DoesNotRun,
                             'oilpan_analyzer.untraced_member') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.StepSuccess, 'already_in_cc') +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch('no_files', affected_files=[], cc=[]) +
         api.post_process(post_process.DoesNotRun,
                          'oilpan_analyzer.untraced_member') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.StepSuccess, 'no_cc_files_changed') +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'no_cc_files', affected_files=['path/to/some/file.txt'], cc=[]) +
         api.post_process(post_process.DoesNotRun,
                          'oilpan_analyzer.untraced_member') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.StepSuccess, 'no_cc_files_changed') +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'not_adding_untraced_member',
      affected_files=['path/to/some/file.cc'],
      cc=[],
      fake_file_content='aaa\nbbb') + api.post_process(
          post_process.MustRun, 'oilpan_analyzer.untraced_member') +
         api.post_process(
             post_process.DoesNotRun,
             'oilpan_analyzer.untraced_member.generate_tricium_comment') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'adding_untraced_member_without_oilpan_reviews',
      affected_files=['add_untraced_member.cc'],
      cc=[],
      fake_file_content='aaa\nbbb\nUntracedMember') + api.post_process(
          post_process.MustRun,
          'oilpan_analyzer.untraced_member.generate_tricium_comment') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.DropExpectation))
