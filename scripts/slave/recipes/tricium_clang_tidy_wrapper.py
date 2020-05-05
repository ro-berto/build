# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import json

from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_checkout',
    'goma',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'depot_tools/gerrit',
    'depot_tools/tryserver',
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

_chromium_tidy_path = ('third_party', 'llvm-build', 'Release+Asserts', 'bin',
                       'clang-tidy')


def _is_clang_diagnostic(check_name):
  """Returns if `check_name` is a clang diagnostic instead of a tidy nit."""
  return check_name.startswith('clang-diagnostic-')


_TidyDiagnosticID = collections.namedtuple(
    '_TidyDiagnosticID', ['message', 'line_number', 'check_name'])


class _SourceFileComments(object):

  def __init__(self):
    self._source_comments = []
    # _source_comments which have notes that map them back to macros. We have
    # to group these, since a single CL might have multiple diagnostics that
    # ultimately point to this same macro.
    self._macro_comments = collections.defaultdict(set)
    self._build_failed = False
    self._tidy_failed = False
    self._tidy_timed_out = False

  def note_tidy_timed_out(self):
    self._tidy_timed_out = True

  def note_build_failed(self):
    self._build_failed = True

  def note_tidy_failed(self):
    self._tidy_failed = True

  def add_macro_expanded_tidy_diagnostic(self, message, line_number, check_name,
                                         suggestions, file_of_expansion,
                                         line_of_expansion):
    key = _TidyDiagnosticID(message, line_number, check_name)
    # FIXME(gbiv): Macro suggestions may be tricky. Don't mind them for now.
    _ = suggestions
    self._macro_comments[key].add((file_of_expansion, line_of_expansion))

  def add_tidy_diagnostic(self, message, line_number, check_name, suggestions):
    # Clang diagnostics should be reported through presubmits, rather than
    # Tricium. One diagnostic can cause a cascade of others, and that's a bad
    # UX.
    assert not _is_clang_diagnostic(check_name), check_name
    self._source_comments.append((_TidyDiagnosticID(message, line_number,
                                                    check_name), suggestions))

  def __iter__(self):
    """Yields comments as (category, message, line_num, suggestions) tuples."""
    category = 'ClangTidy'

    if self._tidy_timed_out:
      message = ('warning: clang-tidy timed out on this file; issuing '
                 'diagnostics is impossible.')
      yield category, message, 0, ()

    def fix_message(message, check_name):
      return (message + ' (https://clang.llvm.org/extra/clang-tidy/checks/'
              '%s.html)' % check_name)

    if self._build_failed:
      failure_suffix = ('\n\n(Note: building this file or its dependencies '
                        'failed; this diagnostic might be incorrect as a '
                        'result.)')
    elif self._tidy_failed:
      failure_suffix = ('\n\n(Note: running clang-tidy on this file failed; '
                        'this diagnostic might be incorrect as a result.)')
    else:
      failure_suffix = ''

    for (message, line_number,
         check_name), suggestions in self._source_comments:
      subcategory = '/'.join([category, check_name])
      message = fix_message(message, check_name) + failure_suffix
      yield subcategory, message, line_number, suggestions

    macro_comments = sorted(self._macro_comments.items())
    for (message, line_number, check_name), expansions in macro_comments:
      assert len(expansions) > 0, message

      message = fix_message(message, check_name)
      expansions = sorted(expansions)
      expansion_file, expansion_line = expansions[0]
      suffix = '\n\nExpanded from %s:%d' % (expansion_file, expansion_line)

      # Listing one expansion location should be enough for now.
      if len(expansions) == 1:
        suffix += '.'
      elif len(expansions) == 2:
        suffix += ', and 1 other place.'
      else:
        suffix += ', and %d other places.' % (len(expansions) - 1)

      subcategory = '/'.join([category, check_name])
      yield subcategory, message + suffix + failure_suffix, line_number, ()


def _generate_clang_tidy_comments(api, file_paths):
  clang_tidy_location = api.context.cwd.join(*_chromium_tidy_path)
  per_file_comments = collections.defaultdict(_SourceFileComments)

  # CLs based before Chromium's src@a55e6bed3d40262fad227ae7fb68ee1fea0e32af
  # won't sync clang-tidy, and so will show up as red if we try to run
  # tricium_clang_tidy on them. Avoid that.
  #
  # FIXME(crbug.com/1035217): Remove this once M80 is a distant memory.
  if not api.path.exists(clang_tidy_location):
    api.step.active_result.presentation.status = 'WARNING'
    api.step.active_result.presentation.logs['skipped'] = [
        'No clang-tidy binary found; skipping linting (crbug.com/1035217)'
    ]
    return per_file_comments

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

  ninja_path = {'PATH': [api.path.dirname(api.depot_tools.ninja_path)]}
  with api.context(env_suffixes=ninja_path):
    api.python(
        name='tricium_clang_tidy.py',
        script=api.resource('tricium_clang_tidy.py'),
        args=tricium_clang_tidy_args)

  # Please see tricium_clang_tidy.py for full docs on what this contains.
  clang_tidy_output = api.file.read_json('read tidy output', warnings_file)

  if clang_tidy_output.get('failed_src_files') or clang_tidy_output.get(
      'failed_tidy_files') or clang_tidy_output.get('timed_out_src_files'):
    api.step.active_result.presentation.status = 'WARNING'

  for file_path in clang_tidy_output.get('failed_src_files', []):
    per_file_comments[file_path].note_build_failed()

  for file_path in clang_tidy_output.get('failed_tidy_files', []):
    per_file_comments[file_path].note_tidy_failed()

  for file_path in clang_tidy_output.get('timed_out_src_files', []):
    per_file_comments[file_path].note_tidy_timed_out()

  for diagnostic in clang_tidy_output.get('diagnostics', []):
    file_path = diagnostic['file_path']
    assert file_path, ("Empty paths should've been filtered "
                       "by tricium_clang_tidy: %s" % diagnostic)

    diag_name = diagnostic['diag_name']
    if _is_clang_diagnostic(diag_name):
      continue

    tidy_replacements = diagnostic['replacements']
    if tidy_replacements:
      suggestions = [{
          'replacements': [{
              'path': file_path,
              'replacement': x['new_text'],
              'start_line': x['start_line'],
              'end_line': x['end_line'],
              'start_char': x['start_char'],
              'end_char': x['end_char'],
          } for x in tidy_replacements],
      }]
    else:
      suggestions = ()

    message = diagnostic['message']
    report_line = diagnostic['line_number']
    report_file = file_path

    expansions = diagnostic['expansion_locs']
    if expansions:
      # Expansions are emitted by clang-tidy (thus tricium_clang_tidy) such
      # that item [i] "invokes" the expansion of [i+1]. So the last item in
      # this list should tell us where the original macro definition is.
      e = expansions[-1]
      per_file_comments[e['file_path']].add_macro_expanded_tidy_diagnostic(
          message, e['line_number'], diag_name, suggestions, report_file,
          report_line)
    else:
      per_file_comments[report_file].add_tidy_diagnostic(
          message, report_line, diag_name, suggestions)

  return per_file_comments


def _should_skip_linting(api):
  revision_info = api.gerrit.get_revision_info(
      'https://%s' % api.tryserver.gerrit_change.host,
      api.tryserver.gerrit_change.change, api.tryserver.gerrit_change.patchset)

  commit_message = revision_info['commit']['message']
  return commit_message.startswith('Revert')


def RunSteps(api):
  assert api.tryserver.is_tryserver

  if _should_skip_linting(api):
    return

  with api.chromium.chromium_layout():
    api.gclient.set_config('chromium')
    api.gclient.apply_config('use_clang_tidy')

    api.chromium.set_config('chromium')
    api.chromium.apply_config('mb')

    # Do not rebase the patch, so that the Tricium analyzer observes the correct
    # line numbers. Otherwise, line numbers would be relative to origin/master,
    # which may be synced to include changes subsequent to the actual patch.
    api.chromium_checkout.ensure_checkout(gerrit_no_rebase_patch_ref=True)

    api.chromium.runhooks(name='runhooks (with patch)')

    src_dir = api.chromium_checkout.checkout_dir.join('src')
    with api.context(cwd=src_dir):
      # If files were removed by the CL, they'll be listed by
      # get_files_affected_by_patch. We probably don't want to try to lint
      # them. :)
      #
      # Similarly, linting non-source files is out of scope.
      src_file_suffixes = {'.cc', '.cpp', '.cxx', '.c', '.h', '.hpp'}
      affected = [
          f for f in api.chromium_checkout.get_files_affected_by_patch()
          if api.path.exists(src_dir.join(f)) and
          api.path.splitext(f)[1] in src_file_suffixes
      ]

      if affected:
        api.chromium.ensure_goma()
        api.goma.start()

        # `gn gen` can take up to a minute, and the script we call out to
        # already does that for us, so set up a minimal build dir.
        gn_args = api.chromium.mb_lookup(api.chromium.get_builder_id())
        api.file.ensure_directory('ensure out dir', api.chromium.output_dir)
        api.file.write_text('write args.gn',
                            api.chromium.output_dir.join('args.gn'), gn_args)

        with api.step.nest('clang-tidy'):
          with api.step.nest('generate-warnings'):
            per_file_comments = _generate_clang_tidy_comments(api, affected)

          for file_path, comments in per_file_comments.items():
            for category, message, line_number, suggestions in comments:
              # Clang-tidy only gives us one file offset, so we use line
              # comments.
              api.tricium.add_comment(
                  category,
                  message,
                  file_path,
                  start_line=line_number,
                  suggestions=suggestions)

      api.tricium.write_comments()


def _get_tricium_comments(steps):
  write_results = steps['write results']
  tricium_json = write_results.output_properties['tricium']
  return json.loads(tricium_json).get('comments')


def tricium_has_no_messages(check, steps):
  comments = _get_tricium_comments(steps)
  check(not comments)


def tricium_has_message(check, steps, message):
  comments = _get_tricium_comments(steps)
  check(comments)
  if comments:
    check(message in [x['message'] for x in comments])


def tricium_has_replacements(check, steps, *expected_replacements):
  replacement_messages = set()
  for comment in _get_tricium_comments(steps):
    for suggestion in comment.get('suggestions', ()):
      for replacement in suggestion['replacements']:
        replacement_messages.add(replacement['replacement'])

  check(set(expected_replacements) == replacement_messages)


def tricium_outputs_json(check, steps, json_obj):
  comments = _get_tricium_comments(steps)
  check(comments == json_obj)


def GenTests(api):

  def test_with_patch(name,
                      affected_files,
                      is_revert=False,
                      include_diff=True,
                      auto_exist_files=True,
                      clang_tidy_exists=True,
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

    existing_files = []
    if auto_exist_files:
      existing_files += [
          api.path['cache'].join('builder', 'src', x) for x in affected_files
      ]

    if clang_tidy_exists:
      existing_files.append(api.path['cache'].join('builder', 'src',
                                                   *_chromium_tidy_path))

    if existing_files:
      test += api.path.exists(*existing_files)

    return test

  yield (test_with_patch('no_files', affected_files=[]) +
         api.post_process(post_process.DoesNotRun, 'clang-tidy') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'no_analysis_non_cpp', affected_files=['some/cc/file.txt']) +
         api.post_process(post_process.DoesNotRun, 'clang-tidy') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'removed_file',
      affected_files=['path/to/some/cc/file.cpp'],
      auto_exist_files=False) +
         api.post_process(post_process.DoesNotRun, 'clang-tidy') +
         api.post_process(tricium_has_no_messages) +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'analyze_cpp_timed_out_files',
      affected_files=['path/to/some/cc/file.cpp']) + api.step_data(
          'clang-tidy.generate-warnings.read tidy output',
          api.file.read_json({'timed_out_src_files': ['oh/no.cpp']})) +
         api.post_process(post_process.StepWarning,
                          'clang-tidy.generate-warnings') +
         api.post_process(
             tricium_has_message, 'warning: clang-tidy timed out on this '
             'file; issuing diagnostics is impossible.') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'analyze_cpp_failed_files', affected_files=['path/to/some/cc/file.cpp']) +
         api.step_data(
             'clang-tidy.generate-warnings.read tidy output',
             api.file.read_json(
                 {'failed_src_files': ['path/to/some/cc/file.cpp']})) +
         api.post_process(post_process.StepWarning,
                          'clang-tidy.generate-warnings') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'analyze_cpp_failed_tidy_files',
      affected_files=['path/to/some/cc/file.cpp']) + api.step_data(
          'clang-tidy.generate-warnings.read tidy output',
          api.file.read_json(
              {'failed_tidy_files': ['path/to/some/cc/file.cpp']})) +
         api.post_process(post_process.StepWarning,
                          'clang-tidy.generate-warnings') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'analyze_cpp', affected_files=['path/to/some/cc/file.cpp']) +
         api.step_data(
             'clang-tidy.generate-warnings.read tidy output',
             api.file.read_json({
                 'diagnostics': [
                     {
                         'file_path': 'path/to/some/cc/file.cpp',
                         'line_number': 2,
                         'diag_name': 'super-cool-diag',
                         'message': 'hello, world 1',
                         'replacements': [],
                         'expansion_locs': [],
                     },
                     {
                         'file_path': 'path/to/some/cc/file.cpp',
                         'line_number': 50,
                         'diag_name': 'moderately-cool-diag',
                         'message': 'hello, world',
                         'replacements': [],
                         'expansion_locs': [],
                     },
                 ]
             })) + api.post_process(post_process.StepSuccess,
                                    'clang-tidy.generate-warnings') +
         api.post_process(post_process.StatusSuccess) + api.post_process(
             tricium_has_message, 'hello, world 1 (https://clang.llvm.org/'
             'extra/clang-tidy/checks/super-cool-diag.html)') +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'only_warnings_and_errors_are_silenced',
      affected_files=['path/to/some/cc/file.cpp']) + api.step_data(
          'clang-tidy.generate-warnings.read tidy output',
          api.file.read_json({
              'failed_src_files': ['path/to/some/cc/file.cpp'],
              'diagnostics': [
                  {
                      'file_path': 'path/to/some/cc/file.cpp',
                      'line_number': 2,
                      'diag_name': 'clang-diagnostic-warning',
                      'message': 'hello, world',
                      'replacements': [],
                      'expansion_locs': [],
                  },
                  {
                      'file_path': 'path/to/some/cc/file.cpp',
                      'line_number': 2,
                      'diag_name': 'clang-diagnostic-error',
                      'message': 'hello, world',
                      'replacements': [],
                      'expansion_locs': [],
                  },
              ],
          })) + api.post_process(post_process.StepWarning,
                                 'clang-tidy.generate-warnings') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(tricium_has_no_messages) +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'append_complaint_on_failure',
      affected_files=['path/to/some/cc/file.cpp']) + api.step_data(
          'clang-tidy.generate-warnings.read tidy output',
          api.file.read_json({
              'failed_src_files': ['path/to/some/cc/file.cpp'],
              'diagnostics': [{
                  'file_path': 'path/to/some/cc/file.cpp',
                  'line_number': 2,
                  'diag_name': 'b',
                  'message': 'a',
                  'replacements': [],
                  'expansion_locs': [],
              },],
          })) + api.post_process(post_process.StepWarning,
                                 'clang-tidy.generate-warnings') +
         api.post_process(post_process.StatusSuccess) + api.post_process(
             tricium_has_message,
             'a (https://clang.llvm.org/extra/clang-tidy/checks/b.html)\n\n'
             '(Note: building this file or its dependencies failed; this '
             'diagnostic might be incorrect as a result.)') +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'prefer_complaints_about_build_failures_over_tidy_ones',
      affected_files=['path/to/some/cc/file.cpp']) + api.step_data(
          'clang-tidy.generate-warnings.read tidy output',
          api.file.read_json({
              'failed_tidy_files': ['path/to/some/cc/file.cpp'],
              'failed_src_files': ['path/to/some/cc/file.cpp'],
              'diagnostics': [{
                  'file_path': 'path/to/some/cc/file.cpp',
                  'line_number': 2,
                  'diag_name': 'b',
                  'message': 'a',
                  'replacements': [],
                  'expansion_locs': [],
              },],
          })) + api.post_process(post_process.StepWarning,
                                 'clang-tidy.generate-warnings') +
         api.post_process(post_process.StatusSuccess) + api.post_process(
             tricium_has_message,
             'a (https://clang.llvm.org/extra/clang-tidy/checks/b.html)\n\n'
             '(Note: building this file or its dependencies failed; this '
             'diagnostic might be incorrect as a result.)') +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'append_complaint_on_tidy_failure',
      affected_files=['path/to/some/cc/file.cpp']) + api.step_data(
          'clang-tidy.generate-warnings.read tidy output',
          api.file.read_json({
              'failed_tidy_files': ['path/to/some/cc/file.cpp'],
              'diagnostics': [{
                  'file_path': 'path/to/some/cc/file.cpp',
                  'line_number': 2,
                  'diag_name': 'b',
                  'message': 'a',
                  'replacements': [],
                  'expansion_locs': [],
              },],
          })) + api.post_process(post_process.StepWarning,
                                 'clang-tidy.generate-warnings') +
         api.post_process(post_process.StatusSuccess) + api.post_process(
             tricium_has_message,
             'a (https://clang.llvm.org/extra/clang-tidy/checks/b.html)\n\n'
             '(Note: running clang-tidy on this file failed; this '
             'diagnostic might be incorrect as a result.)') +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'diagnostic_suggestions', affected_files=['path/to/some/cc/file.cpp']) +
         api.step_data(
             'clang-tidy.generate-warnings.read tidy output',
             api.file.read_json({
                 'diagnostics': [{
                     'file_path': 'path/to/some/cc/file.cpp',
                     'line_number': 2,
                     'diag_name': 'tidy-is-angry',
                     'message': 'hello, world',
                     'replacements': [
                         {
                             'new_text': 'foo',
                             'start_line': 1,
                             'end_line': 2,
                             'start_char': 0,
                             'end_char': 1,
                         },
                         {
                             'new_text': 'bar',
                             'start_line': 3,
                             'end_line': 4,
                             'start_char': 5,
                             'end_char': 5,
                         },
                     ],
                     'expansion_locs': [],
                 },]
             })) + api.post_process(post_process.StepSuccess,
                                    'clang-tidy.generate-warnings') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(tricium_has_replacements, 'foo', 'bar') +
         api.post_process(post_process.DropExpectation))

  expansions_tests = [
      (1, 1, '.'),
      (2, 1, ', and 1 other place.'),
      (3, 1, ', and 2 other places.'),
      (4, 2, ', and 3 other places.'),
  ]

  for num_expansions, expansion_duplication, suffix in expansions_tests:
    diags = []
    for i in range(num_expansions):
      for _ in range(expansion_duplication):
        diags.append({
            'file_path':
                'path/to/some/cc/file%d.cpp' % i,
            'line_number':
                2,
            'diag_name':
                'tidy-is-angry',
            'message':
                'grrr',
            'replacements': [],
            'expansion_locs': [
                {
                    'file_path': 'path/to/some/cc/file%d.cpp' % i,
                    'line_number': 1,
                },
                {
                    'file_path': 'path/to/some/cc/file.h',
                    'line_number': 3,
                },
            ],
        })

    yield (
        test_with_patch(
            'expansion_%d' % num_expansions,
            affected_files=['path/to/some/cc/file.cpp']) +
        api.step_data('clang-tidy.generate-warnings.read tidy output',
                      api.file.read_json({'diagnostics': diags})) +
        api.post_process(post_process.StepSuccess,
                         'clang-tidy.generate-warnings') +
        api.post_process(post_process.StatusSuccess) +
        api.post_process(tricium_outputs_json, [{
            'category': 'ClangTidy/tidy-is-angry',
            'path': 'path/to/some/cc/file.h',
            'message':
                'grrr '
                '(https://clang.llvm.org/extra/clang-tidy/checks/tidy-is-angry'
                '.html)'
                '\n\nExpanded from path/to/some/cc/file0.cpp:2' + suffix,
            'startLine': 3,
        }]) + api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'skip_if_no_clang_tidy',
      affected_files=['path/to/some/cc/file.cpp'],
      clang_tidy_exists=False,
  ) + api.post_process(post_process.StepWarning, 'clang-tidy') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.DropExpectation))

  yield (test_with_patch(
      'skip_reverted_cl',
      affected_files=['path/to/some/cc/file.cpp'],
      is_revert=True,
      include_diff=False) +
         api.post_process(post_process.DoesNotRun, 'bot_update') +
         api.post_process(post_process.StatusSuccess) +
         api.post_process(post_process.DropExpectation))
