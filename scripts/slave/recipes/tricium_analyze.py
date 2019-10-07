# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_checkout',
    'goma',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'depot_tools/gerrit',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
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


def _add_clang_tidy_comments(api, file_paths):
  ninja_path = {'PATH': [api.path.dirname(api.depot_tools.ninja_path)]}
  with api.context(env_suffixes=ninja_path):
    # FIXME(gbiv): We probably should stop building clang-tidy on every run
    # before we ship this for real.
    api.python(
        name='build clang-tidy',
        script=api.context.cwd.join('tools', 'clang', 'scripts',
                                    'build_clang_tools_extra.py'),
        args=[
            '--fetch',
            '%s' % api.context.cwd,
            'clang-tidy',
        ])

  clang_tidy_location = api.context.cwd.join(
      'tools', 'clang', 'third_party', 'llvm', 'build', 'bin', 'clang-tidy')

  def add_comment(message, file_path, line):
    api.tricium.add_comment(
        'Lint/clang-tidy',
        message,
        file_path,
        # Clang-tidy only gives us one file offset, so we use line comments.
        start_line=line,
    )

  def add_file_warning(file_path, message):
    api.step.active_result.presentation.status = 'WARNING'
    add_comment('warning: ' + message, file_path, line=0)

  with api.step.nest('generate-warnings'):
    warnings_file = api.path['cleanup'].join('clang_tidy_complaints.yaml')

    tricium_clang_tidy_args = [
        '--out_dir=%s' % api.chromium.output_dir,
        '--findings_file=%s' % warnings_file,
        '--clang_tidy_binary=%s' % clang_tidy_location,
        '--base_path=%s' % api.context.cwd,
        '--ninja_jobs=%s' % api.goma.recommended_goma_jobs,
        '--verbose',
        '--',
    ]
    tricium_clang_tidy_args += file_paths

    with api.context(env_suffixes=ninja_path):
      api.python(
          name='tricium_clang_tidy.py',
          script=api.resource('tricium_clang_tidy.py'),
          args=tricium_clang_tidy_args)

    # Please see tricium_clang_tidy.py for full docs on what this contains.
    clang_tidy_output = api.file.read_json('read tidy output', warnings_file)

    for failed in clang_tidy_output.get('failed_cc_files', []):
      add_file_warning(
          failed, 'building this file or its dependencies failed; '
          'clang-tidy comments may be incorrect or incomplete.')

    for timed_out in clang_tidy_output.get('timed_out_cc_files', []):
      add_file_warning(
          timed_out, 'clang-tidy timed out on this file; issuing'
          'diagnostics is impossible.')

  for diagnostic in clang_tidy_output.get('diagnostics', []):
    assert diagnostic['file_path'], ("Empty paths should've been filtered "
                                     "by tricium_clang_tidy: %s" % diagnostic)
    add_comment(diagnostic['message'], diagnostic['file_path'],
                diagnostic['line_number'])


def _should_skip_linting(api):
  revision_info = api.gerrit.get_revision_info(
      'https://%s' % api.tryserver.gerrit_change.host,
      api.tryserver.gerrit_change.change, api.tryserver.gerrit_change.patchset)

  commit_message = revision_info['commit']['message']
  if commit_message.startswith('Revert'):
    return True

  # FIXME(gbiv): remove this once testing is done
  author = revision_info['commit']['author']['email']
  is_gbiv = author in ('gbiv@google.com', 'gbiv@chromium.org')
  return not (is_gbiv and 'TriciumTest' in commit_message)


def RunSteps(api):
  assert api.tryserver.is_tryserver

  if _should_skip_linting(api):
    return

  with api.chromium.chromium_layout():
    api.gclient.set_config('chromium')
    api.chromium.set_config('chromium')
    api.chromium.apply_config('mb')

    mastername = api.properties['mastername']
    buildername = api.buildbucket.builder_name
    bot_config = {}
    checkout_dir = api.chromium_checkout.get_checkout_dir(bot_config)
    with api.context(cwd=checkout_dir):
      api.chromium_checkout.ensure_checkout(bot_config)

    api.chromium.runhooks(name='runhooks (with patch)')

    src_dir = checkout_dir.join('src')
    with api.context(cwd=src_dir):
      # If files were removed by the CL, they'll be listed by
      # get_files_affected_by_patch. We probably don't want to try to lint
      # them. :)
      affected = [
          f for f in api.chromium_checkout.get_files_affected_by_patch()
          if api.path.exists(src_dir.join(f))
      ]

      # FIXME(gbiv): Header support would be nice, but would likely require
      # tighter gn integration.
      cc_file_suffixes = {'.cc', '.cpp', '.cxx', '.c'}
      tidyable_paths = [
          p for p in affected if api.path.splitext(p)[1] in cc_file_suffixes
      ]

      if tidyable_paths:
        api.chromium.ensure_goma()
        api.goma.start()
        api.chromium.mb_gen(mastername, buildername)

        with api.step.nest('clang-tidy'):
          _add_clang_tidy_comments(api, affected)

      api.tricium.write_comments()


def GenTests(api):

  def test_with_patch(name,
                      affected_files,
                      is_revert=False,
                      include_diff=True,
                      auto_exist_files=True,
                      author='gbiv@google.com'):
    commit_message = 'Revert foo' if is_revert else 'foo'
    commit_message += '\nTriciumTest'
    test = (
        api.test(name) + api.properties.tryserver(
            build_config='Release',
            mastername='tryserver.chromium.linux',
            buildername='linux_chromium_compile_rel_ng',
            buildnumber='1234',
            patch_set=1) + api.platform('linux', 64) + api.override_step_data(
                'gerrit changes',
                api.json.output([{
                    'revisions': {
                        'a' * 40: {
                            '_number': 1,
                            'commit': {
                                'author': {
                                    'email': author,
                                },
                                'message': commit_message,
                            }
                        }
                    }
                }])))

    # If this would otherwise be skipped, we'll never analyze the patch.
    if include_diff:
      test += api.step_data('git diff to analyze patch',
                            api.raw_io.stream_output('\n'.join(affected_files)))

    if auto_exist_files:
      test += api.path.exists(*[
          api.path['cache'].join('builder', 'src', x) for x in affected_files
      ])

    return test

  yield (test_with_patch('no_files', affected_files=[]) + api.post_process(
      post_process.DoesNotRun, 'clang-tidy') + api.post_process(
          post_process.StatusSuccess) + api.post_process(
              post_process.DropExpectation))

  yield (test_with_patch(
      'no_analysis_non_cpp', affected_files=['some/cc/file.txt']) +
         api.post_process(post_process.DoesNotRun, 'clang-tidy') +
         api.post_process(post_process.StatusSuccess) + api.post_process(
             post_process.DropExpectation))

  yield (test_with_patch(
      'removed_file',
      affected_files=['path/to/some/cc/file.cpp'],
      auto_exist_files=False) + api.post_process(
          post_process.DoesNotRun, 'clang-tidy') + api.post_process(
              post_process.StatusSuccess) + api.post_process(
                  post_process.DropExpectation))

  yield (test_with_patch(
      'analyze_cpp_timed_out_files',
      affected_files=['path/to/some/cc/file.cpp']) + api.step_data(
          'clang-tidy.generate-warnings.read tidy output',
          api.file.read_json({
              'timed_out_cc_files': ['oh/no.cpp']
          })) + api.post_process(post_process.StepWarning,
                                 'clang-tidy.generate-warnings') +
         api.post_process(post_process.StatusSuccess) + api.post_process(
             post_process.DropExpectation))

  yield (test_with_patch(
      'analyze_cpp_failed_files',
      affected_files=['path/to/some/cc/file.cpp']) + api.step_data(
          'clang-tidy.generate-warnings.read tidy output',
          api.file.read_json({
              'failed_cc_files': ['path/to/some/cc/file.cpp']
          })) + api.post_process(post_process.StepWarning,
                                 'clang-tidy.generate-warnings') +
         api.post_process(post_process.StatusSuccess) + api.post_process(
             post_process.DropExpectation))

  yield (test_with_patch(
      'analyze_cpp',
      affected_files=['path/to/some/cc/file.cpp']) + api.step_data(
          'clang-tidy.generate-warnings.read tidy output',
          api.file.read_json({
              'diagnostics': [
                  {
                      'file_path': 'path/to/some/cc/file.cpp',
                      'line_number': 2,
                      'message': 'hello, world',
                  },
                  {
                      'file_path': 'path/to/some/cc/file.cpp',
                      'line_number': 50,
                      'message': 'hello, world'
                  },
              ]
          })) + api.post_process(post_process.StepSuccess,
                                 'clang-tidy.generate-warnings') +
         api.post_process(post_process.StatusSuccess) + api.post_process(
             post_process.DropExpectation))

  yield (test_with_patch(
      'skip_reverted_cl',
      affected_files=['path/to/some/cc/file.cpp'],
      is_revert=True,
      include_diff=False) + api.post_process(
          post_process.DoesNotRun, 'bot_update') + api.post_process(
              post_process.StatusSuccess) + api.post_process(
                  post_process.DropExpectation))

  yield (test_with_patch(
      'skip_not_gbiv',
      affected_files=['path/to/some/cc/file.cpp'],
      author='woof@doge.goog',
      include_diff=False) + api.post_process(
          post_process.DoesNotRun, 'bot_update') + api.post_process(
              post_process.StatusSuccess) + api.post_process(
                  post_process.DropExpectation))
