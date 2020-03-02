# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# [VPYTHON:BEGIN]
# wheel: <
#    name: "infra/python/wheels/pyyaml/${vpython_platform}"
#    version: "version:3.12"
# >
# [VPYTHON:END]

from __future__ import print_function

import collections
import io
import json
import logging
import sys
import unittest

import tricium_clang_tidy as tidy


def _to_stringio(contents):
  if sys.version_info[0] == 2 and isinstance(contents, str):
    contents = unicode(contents)
  return io.StringIO(contents)


def _parse_fixes_file_text(line_offsets,
                           contents_text,
                           tidy_invocation_dir='/tidy/dir'):
  return list(
      tidy._parse_tidy_fixes_file(
          read_line_offsets=lambda _file_path: line_offsets,
          stream=_to_stringio(contents_text),
          tidy_invocation_dir=tidy_invocation_dir))


def _convert_tidy_diags_to_yaml(tidy_diags):
  """Converts the given _TidyDiagnostics to their YAML form.

    Note that the file offset of each diagnostic == its index in tidy_diags.
  """
  diagnostics = [{
      'DiagnosticName': diag.diag_name,
      'DiagnosticMessage': {
          'Message': diag.message,
          'FilePath': diag.file_path,
          'FileOffset': i,
      },
  } for i, diag in enumerate(tidy_diags)]

  # YAML doesn't have a dumps() on my local machine; JSON's easiest.
  return json.dumps({
      'Diagnostics': diagnostics,
  })


class _SilencingFilter(object):

  def __init__(self):
    pass

  def filter(self, _record):
    return 0


class Tests(unittest.TestCase):

  def _silence_logs(self):
    root = logging.getLogger()
    filt = _SilencingFilter()
    root.addFilter(filt)
    self.addCleanup(root.removeFilter, filt)

  def test_parse_compile_commands_raises_on_no_object(self):
    input_json = json.dumps([
        {
            'command': '/path/to/not an object file.o',
            'directory': '/dir/ect/ory',
            'file': 'foo.cc',
        },
    ])

    with self.assertRaises(ValueError) as ex:
      list(tidy._parse_compile_commands(_to_stringio(input_json)))

    self.assertIn('lacks an output file', str(ex.exception))

  def test_parse_compile_commands_skips_pnacl(self):

    def compile_command(command):
      return {
          'command': command,
          'directory': '/dir/ect/ory',
          'file': 'foo.cc',
      }

    input_json = json.dumps([
        compile_command('/path/to/clang++ foo -o foo.o'),
        compile_command('/path/to/pnacl-clang foo -o foo-1.o'),
        compile_command('/path/to/pnacl-clang++ foo -o foo-2.o'),
        compile_command('/path/to/gomacc /path/to/pnacl-clang foo -o foo-3.o'),
        compile_command(
            '/path/to/gomacc /path/to/pnacl-clang++ foo -o foo-4.o'),
        compile_command('/some/clang /path/to/pnacl-helpers.c -o foo-5.o'),
        compile_command(
            '/path/to/gomacc /some/clang /path/to/pnacl-helpers.c -o foo-6.o'),
    ])

    results = list(tidy._parse_compile_commands(_to_stringio(input_json)))
    self.assertEqual(results, [
        tidy._CompileCommand(
            target_name='foo.o',
            file_abspath='/dir/ect/ory/foo.cc',
            file='foo.cc',
            directory='/dir/ect/ory',
            command='/path/to/clang++ foo -o foo.o',
        ),
        tidy._CompileCommand(
            target_name='foo-5.o',
            file_abspath='/dir/ect/ory/foo.cc',
            file='foo.cc',
            directory='/dir/ect/ory',
            command='/some/clang /path/to/pnacl-helpers.c -o foo-5.o',
        ),
        tidy._CompileCommand(
            target_name='foo-6.o',
            file_abspath='/dir/ect/ory/foo.cc',
            file='foo.cc',
            directory='/dir/ect/ory',
            command='/path/to/gomacc /some/clang /path/to/pnacl-helpers.c -o '
            'foo-6.o',
        ),
    ])

  def test_broken_yaml_is_parse_error(self):
    no_offsets = tidy._LineOffsetMap.for_text('')
    with self.assertRaises(tidy._ParseError) as err:
      _parse_fixes_file_text(no_offsets, '{')
    self.assertIn('Broken yaml', str(err.exception))

    with self.assertRaises(tidy._ParseError) as err:
      # Missing keys
      _parse_fixes_file_text(no_offsets, '{"Diagnostics": [{}]}')
    self.assertIn('missing key', str(err.exception))

  def test_successful_tidy_file_parses(self):
    no_offsets = tidy._LineOffsetMap.for_text('')
    self.assertEqual(_parse_fixes_file_text(no_offsets, ''), [])

    tidy_invocation_dir = '/tidy'
    input_file = tidy._LineOffsetMap.for_text('a\nb')
    tidy_diags = [
        tidy._TidyDiagnostic(
            file_path='/foo1',
            line_number=1,
            diag_name='-Wfoo1',
            message='foo1',
            replacements=(),
            expansion_locs=()),
        tidy._TidyDiagnostic(
            file_path='/foo2',
            line_number=1,
            diag_name='-Wfoo2',
            message='foo2',
            replacements=(),
            expansion_locs=()),
        tidy._TidyDiagnostic(
            file_path='foo3',
            line_number=2,
            diag_name='-Wfoo3',
            message='foo3',
            replacements=(),
            expansion_locs=()),
    ]

    diag_yaml = _convert_tidy_diags_to_yaml(tidy_diags)
    tidy_diags[-1] = tidy_diags[-1]._replace(file_path='/tidy/foo3')
    # YAML doesn't have a dumps() on my local machine; JSON's easiest.
    self.assertEqual(
        _parse_fixes_file_text(input_file, diag_yaml, tidy_invocation_dir),
        tidy_diags)

  def test_expansion_locs_are_parsed_from_notes(self):
    yaml = '\n'.join([
        'MainSourceFile:  "/tmp/x.c"',
        'Diagnostics:',
        ' - DiagnosticName:  google-explicit-constructor',
        '   DiagnosticMessage:',
        '     Message:         foo',
        '     FilePath:        "/tmp/x.c"',
        '     FileOffset:      3',
        '     Replacements:    []',
        '   Notes:',
        '     - Message:         "expanded from macro \'\'a\'\'"',
        '       FilePath:        "/tmp/x.h"',
        '       FileOffset:      2',
        '     - Message:         "expanded from macro \'\'b\'\'"',
        '       FilePath:        "/tmp/x.h"',
        '       FileOffset:      1',
        '',
    ])

    def read_line_offsets(file_path):
      if file_path == '/tmp/x.c':
        return tidy._LineOffsetMap([0, 1])
      if file_path == '/tmp/x.h':
        return tidy._LineOffsetMap([1])
      self.fail('Unknown parsed file path: %r' % file_path)

    diags = list(
        tidy._parse_tidy_fixes_file(
            read_line_offsets=read_line_offsets,
            stream=_to_stringio(yaml),
            tidy_invocation_dir='/tidy'))

    self.assertEqual(diags, [
        tidy._TidyDiagnostic(
            file_path='/tmp/x.c',
            line_number=3,
            diag_name='google-explicit-constructor',
            message='foo',
            replacements=(),
            expansion_locs=(
                tidy._ExpandedFrom(file_path='/tmp/x.h', line_number=2),
                tidy._ExpandedFrom(file_path='/tmp/x.h', line_number=1),
            ),
        )
    ])

  def test_fix_parsing_handles_multiple_files_gracefully(self):
    tidy_diags = [
        tidy._TidyDiagnostic(
            file_path='/foo1',
            line_number=1,
            diag_name='-Wfoo1',
            message='foo1',
            replacements=(),
            expansion_locs=()),
        tidy._TidyDiagnostic(
            file_path='/foo1',
            line_number=1,
            diag_name='-Wfoo1',
            message='foo1',
            replacements=(),
            expansion_locs=()),
        tidy._TidyDiagnostic(
            file_path='/foo1',
            line_number=2,
            diag_name='-Wfoo1',
            message='foo1',
            replacements=(),
            expansion_locs=()),
        tidy._TidyDiagnostic(
            file_path='/foo2',
            line_number=1,
            diag_name='-Wfoo2',
            message='foo2',
            replacements=(),
            expansion_locs=()),
    ]
    diag_yaml = _convert_tidy_diags_to_yaml(tidy_diags)

    def read_file_offsets(file_path):
      if file_path == '/foo1':
        return tidy._LineOffsetMap.for_text('_\n')
      if file_path == '/foo2':
        return tidy._LineOffsetMap.for_text('')
      self.fail('Unknown file path %s' % file_path)

    fixes = list(
        tidy._parse_tidy_fixes_file(
            read_file_offsets,
            _to_stringio(diag_yaml),
            tidy_invocation_dir='/tidy'))
    self.assertEqual(fixes, tidy_diags)

  def test_fix_parsing_doesnt_read_the_same_offsets_twice(self):
    tidy_diags = [
        tidy._TidyDiagnostic(
            file_path='/foo1',
            line_number=1,
            diag_name='-Wfoo1',
            message='foo1',
            replacements=(),
            expansion_locs=()),
        tidy._TidyDiagnostic(
            file_path='/foo1',
            line_number=1,
            diag_name='-Wfoo1',
            message='foo1',
            replacements=(),
            expansion_locs=()),
        tidy._TidyDiagnostic(
            file_path='/foo2',
            line_number=2,
            diag_name='-Wfoo2',
            message='foo2',
            replacements=(),
            expansion_locs=()),
    ]
    diag_yaml = _convert_tidy_diags_to_yaml(tidy_diags)
    retrievals = collections.defaultdict(int)

    def read_file_offsets(file_path):
      retrievals[file_path] += 1
      return tidy._LineOffsetMap.for_text('')

    list(
        tidy._parse_tidy_fixes_file(
            read_file_offsets,
            _to_stringio(diag_yaml),
            tidy_invocation_dir='/tidy'))
    self.assertEqual(retrievals, {'/foo1': 1, '/foo2': 1})

  def test_fix_parsing_handles_empty_file_paths_gracefully(self):
    tidy_diags = [
        tidy._TidyDiagnostic(
            file_path='',
            line_number=1,
            diag_name='-Wfoo1',
            message='foo1',
            replacements=(),
            expansion_locs=()),
    ]
    self.assertEqual(
        _parse_fixes_file_text(
            line_offsets=None,
            contents_text=_convert_tidy_diags_to_yaml(tidy_diags),
            tidy_invocation_dir='/tidy'), tidy_diags)

  def test_generate_tidy_actions_only_generates_up_to_n_actions_per_src(self):

    def parse_ninja_deps(_):
      return [
          ('foo.o', ['/foo.h', '/foo.cc']),
          ('bar.o', ['/foo.h', '/bar.cc']),
      ]

    # Each test case is a tuple of `(max_tidy_actions_per_file,
    # expected_tidy_actions)`.
    test_cases = [
        (1, {
            tidy._TidyAction(
                cc_file='/foo.cc', target='foo.o', in_dir='/in',
                flags='whee'): ['/foo.h'],
        }),
        (2, {
            tidy._TidyAction(
                cc_file='/foo.cc', target='foo.o', in_dir='/in',
                flags='whee'): ['/foo.h'],
            tidy._TidyAction(
                cc_file='/bar.cc', target='bar.o', in_dir='/in',
                flags='whee'): ['/foo.h'],
        }),
    ]

    for max_actions, expected_actions in test_cases:
      actions, _ = tidy._generate_tidy_actions(
          out_dir='/out',
          only_src_files=['/foo.h'],
          run_ninja=lambda out_dir, phony_targets, object_targets: (),
          gn_desc=tidy._GnDesc({
              '//rule': ['/foo.h', '/foo.cc', '/bar.cc'],
          }),
          parse_ninja_deps=parse_ninja_deps,
          compile_commands=[
              tidy._CompileCommand(
                  target_name='foo.o',
                  file_abspath='/foo.cc',
                  file='foo.cc',
                  directory='/in',
                  command='whee',
              ),
              tidy._CompileCommand(
                  target_name='bar.o',
                  file_abspath='/bar.cc',
                  file='bar.cc',
                  directory='/in',
                  command='whee',
              ),
          ],
          max_tidy_actions_per_file=max_actions)

      self.assertEqual(actions, expected_actions)

  def test_generate_tidy_actions_works_with_cc_files(self):

    def run_ninja(out_dir, phony_targets, object_targets):
      self.assertEqual(out_dir, '/out')
      self.assertEqual(phony_targets, [])
      self.assertEqual(object_targets, ['bar.o', 'foo.o'])
      return ()

    compile_commands = [
        tidy._CompileCommand(
            target_name='foo.o',
            file_abspath='/foo.cc',
            file='foo.cc',
            directory='/in',
            command='whee',
        ),
        tidy._CompileCommand(
            target_name='bar.o',
            file_abspath='/bar.cc',
            file='bar.cc',
            directory='/in',
            command='whee',
        ),
    ]

    actions, failed = tidy._generate_tidy_actions(
        out_dir='/out',
        only_src_files=['/foo.cc', '/bar.cc'],
        run_ninja=run_ninja,
        gn_desc=tidy._GnDesc({}),
        parse_ninja_deps=lambda _: (),
        compile_commands=compile_commands)
    self.assertEqual(failed, [])
    self.assertEqual(
        actions, {
            tidy._TidyAction(
                cc_file='/foo.cc', target='foo.o', in_dir='/in',
                flags='whee'): ['/foo.cc'],
            tidy._TidyAction(
                cc_file='/bar.cc', target='bar.o', in_dir='/in',
                flags='whee'): ['/bar.cc'],
        })

  def test_generate_tidy_actions_includes_headers_in_output(self):

    def run_ninja(out_dir, phony_targets, object_targets):
      self.assertEqual(out_dir, '/out')
      self.assertEqual(phony_targets, ['my/awesome:target'])
      self.assertEqual(object_targets, ['bar.o', 'foo.o'])
      return ()

    compile_commands = [
        tidy._CompileCommand(
            target_name='foo.o',
            file_abspath='/foo.cc',
            file='foo.cc',
            directory='/in',
            command='whee',
        ),
        tidy._CompileCommand(
            target_name='bar.o',
            file_abspath='/bar.cc',
            file='bar.cc',
            directory='/in',
            command='whee',
        ),
    ]

    def parse_ninja_deps(_):
      return [
          ('foo.o', ['/foo.h', '/foo.cc']),
          ('bar.o', ['/bar.cc']),
      ]

    actions, failed = tidy._generate_tidy_actions(
        out_dir='/out',
        only_src_files=['/foo.cc', '/foo.h', '/bar.cc'],
        run_ninja=run_ninja,
        gn_desc=tidy._GnDesc({
            '//my/awesome:target': ['/foo.cc', '/bar.cc', '/baz.cc'],
        }),
        parse_ninja_deps=parse_ninja_deps,
        compile_commands=compile_commands)
    self.assertEqual(failed, [])
    self.assertEqual(
        actions, {
            tidy._TidyAction(
                cc_file='/foo.cc', target='foo.o', in_dir='/in',
                flags='whee'): ['/foo.cc', '/foo.h'],
            tidy._TidyAction(
                cc_file='/bar.cc', target='bar.o', in_dir='/in',
                flags='whee'): ['/bar.cc'],
        })

  def test_generate_tidy_actions_ignores_nonexistent_files(self):
    self._silence_logs()

    def run_ninja(out_dir, phony_targets, object_targets):
      if phony_targets != ['all']:
        self.assertEqual(object_targets, ['foo.cc.o'])
      return ()

    actions, failed = tidy._generate_tidy_actions(
        out_dir='/out',
        only_src_files=['/foo.cc', '/bar.cc'],
        run_ninja=run_ninja,
        gn_desc=tidy._GnDesc({}),
        parse_ninja_deps=lambda _: (),
        compile_commands=[
            tidy._CompileCommand(
                target_name='foo.cc.o',
                file_abspath='/foo.cc',
                file='foo.cc',
                directory='/in',
                command='whee',
            )
        ])
    self.assertEqual(failed, [])
    self.assertEqual(
        actions, {
            tidy._TidyAction(
                cc_file='/foo.cc',
                target='foo.cc.o',
                in_dir='/in',
                flags='whee'): ['/foo.cc'],
        })

  def test_generate_tidy_actions_functions_with_no_src_file_filter(self):

    def run_ninja(out_dir, phony_targets, object_targets):
      self.assertEqual(out_dir, '/out')
      self.assertEqual(phony_targets, [])
      self.assertEqual(object_targets, ['foo.cc.o'])
      return ()

    actions, failed = tidy._generate_tidy_actions(
        out_dir='/out',
        only_src_files=None,
        run_ninja=run_ninja,
        parse_ninja_deps=lambda _: (),
        gn_desc=tidy._GnDesc({}),
        compile_commands=[
            tidy._CompileCommand(
                target_name='foo.cc.o',
                file_abspath='/foo.cc',
                file='foo.cc',
                directory='/in',
                command='whee',
            )
        ])

    self.assertEqual(failed, [])
    self.assertEqual(
        actions, {
            tidy._TidyAction(
                cc_file='/foo.cc',
                target='foo.cc.o',
                in_dir='/in',
                flags='whee'): ['/foo.cc'],
        })

  def test_generate_tidy_actions_reports_failures(self):
    self._silence_logs()

    def run_ninja(out_dir, phony_targets, object_targets):
      return list(object_targets)

    actions, failed = tidy._generate_tidy_actions(
        out_dir='/out',
        only_src_files=None,
        run_ninja=run_ninja,
        parse_ninja_deps=lambda _: (),
        gn_desc=tidy._GnDesc({}),
        compile_commands={
            tidy._CompileCommand(
                target_name='foo.cc.o',
                file_abspath='/foo.cc',
                file='foo.cc',
                directory='/in',
                command='whee',
            )
        })
    expected_action = tidy._TidyAction(
        cc_file='/foo.cc', target='foo.cc.o', in_dir='/in', flags='whee')
    self.assertEqual(failed, [expected_action])
    self.assertEqual(actions, {expected_action: ['/foo.cc']})

  def test_run_all_tidy_actions_reports_everything(self):
    self._silence_logs()

    binary = object()
    timeout_action = tidy._TidyAction(
        cc_file='timeout', target='timeout.o', in_dir='in/', flags='')
    fail_action = tidy._TidyAction(
        cc_file='fail', target='fail.o', in_dir='in/', flags='')
    good_action = tidy._TidyAction(
        cc_file='success', target='success.o', in_dir='in/', flags='')
    actions = [timeout_action, fail_action, good_action]

    good_diag = tidy._TidyDiagnostic(
        file_path='whee',
        line_number=1,
        diag_name='-Whee',
        message='whee',
        replacements=(),
        expansion_locs=())
    bad_diag = tidy._TidyDiagnostic(
        file_path='oh_no',
        line_number=1,
        diag_name='-Whee',
        message='oh no',
        replacements=(),
        expansion_locs=())

    def runner(arg_binary, action):
      self.assertIs(arg_binary, binary)
      if action.cc_file == 'timeout':
        return None, '', []
      if action.cc_file == 'fail':
        return 1, '', [bad_diag]
      self.assertEqual(action.cc_file, 'success')
      return 0, '', [good_diag]

    failed_cc_files, timed_out_cc_files, findings = tidy._run_all_tidy_actions(
        actions,
        runner,
        tidy_jobs=len(actions),
        clang_tidy_binary=binary,
        use_threads=True)

    self.assertEqual(failed_cc_files, {fail_action})
    self.assertEqual(timed_out_cc_files, {timeout_action})
    self.assertEqual(findings, {good_diag, bad_diag})

  def test_line_offset_map_handles_no_text_gracefully(self):
    no_text = tidy._LineOffsetMap.for_text('')
    self.assertEqual(no_text.get_line_number(0), 1)
    self.assertEqual(no_text.get_line_offset(0), 0)
    self.assertEqual(no_text.get_line_number(1), 1)
    self.assertEqual(no_text.get_line_offset(1), 1)

  def test_line_offset_map_is_next_line_after_eol_character(self):
    newline_start = tidy._LineOffsetMap.for_text('\n')
    self.assertEqual(newline_start.get_line_number(0), 1)
    self.assertEqual(newline_start.get_line_offset(0), 0)
    self.assertEqual(newline_start.get_line_number(1), 2)
    self.assertEqual(newline_start.get_line_offset(1), 0)
    self.assertEqual(newline_start.get_line_number(2), 2)
    self.assertEqual(newline_start.get_line_offset(2), 1)

  def test_line_offset_map_on_random_input(self):
    line_offset_pairs = [
        ('a', 1, 0),
        ('b', 1, 1),
        ('\n', 1, 2),
        ('c', 2, 0),
        ('\n', 2, 1),
        ('\n', 3, 0),
        ('d', 4, 0),
        ('', 4, 1),
        ('', 4, 2),
    ]
    text = tidy._LineOffsetMap.for_text(''.join(
        x for x, _, _ in line_offset_pairs))
    for offset, (_, line_number, line_offset) in enumerate(line_offset_pairs):
      self.assertEqual(text.get_line_number(offset), line_number)
      self.assertEqual(text.get_line_offset(offset), line_offset)

  def test_path_normalization_functions_at_all(self):
    self.assertEqual(tidy._normalize_path_to_base('/foo', base=None), '/foo')
    self.assertEqual(tidy._normalize_path_to_base('/foo', base='/'), 'foo')
    self.assertEqual(tidy._normalize_path_to_base('/foo', base='/foo'), '.')
    self.assertIsNone(tidy._normalize_path_to_base('/foo', base='/foo/bar'))
    self.assertIsNone(tidy._normalize_path_to_base('/bar', base='/foo'))
    self.assertIsNone(tidy._normalize_path_to_base('/bar', base='/ba'))

  def test_output_conversion_drops_paths_outside_of_the_base(self):
    self._silence_logs()

    # I don't _expect_ for paths like these to exist. That said, logging and
    # dropping sounds better than crashing, or producing nonsensical output.
    main_action = tidy._TidyAction(
        cc_file='/foo/bar.cc', target='bar.o', in_dir='in/', flags='')

    result = tidy._convert_tidy_output_json_obj(
        base_path='/foo',
        tidy_actions={main_action: ['/not_in_base/bar.cc']},
        failed_actions=[main_action],
        failed_tidy_actions=[],
        timed_out_actions=[main_action],
        findings=[
            tidy._TidyDiagnostic(
                file_path='',
                line_number=1,
                diag_name='bar',
                message='baz',
                replacements=(),
                expansion_locs=()),
            tidy._TidyDiagnostic(
                file_path='/not_in_base/bar.cc',
                line_number=1,
                diag_name='bar',
                message='baz',
                replacements=(),
                expansion_locs=())
        ],
        only_src_files=None,
    )

    self.assertEqual(result, {
        'diagnostics': [],
        'failed_src_files': [],
        'timed_out_src_files': [],
    })

  def test_output_conversion_converts_non_diagnostic_paths_to_src_files(self):
    self._silence_logs()

    main_action = tidy._TidyAction(
        cc_file='/foo/cc_file.cc', target='bar.o', in_dir='in/', flags='')
    secondary_action = tidy._TidyAction(
        cc_file='/foo/secondary_file.cc',
        target='baz.o',
        in_dir='in/',
        flags='')
    result = tidy._convert_tidy_output_json_obj(
        base_path='/foo',
        tidy_actions={
            main_action: ['/foo/src_file.cc', '/foo/src_file.h'],
            secondary_action: ['/foo/secondary_file.cc', '/foo/src_file.h'],
        },
        failed_actions=[main_action],
        failed_tidy_actions=[],
        timed_out_actions=[secondary_action],
        findings=[
            tidy._TidyDiagnostic(
                file_path='/foo/not_src.h',
                line_number=1,
                diag_name='bar',
                message='baz',
                replacements=(),
                expansion_locs=()),
            tidy._TidyDiagnostic(
                file_path='/foo/src_file.cc',
                line_number=1,
                diag_name='bar',
                message='baz',
                replacements=(),
                expansion_locs=()),
        ],
        only_src_files=None,
    )

    self.assertEqual(
        result, {
            'diagnostics': [
                tidy._TidyDiagnostic(
                    file_path='not_src.h',
                    line_number=1,
                    diag_name='bar',
                    message='baz',
                    replacements=(),
                    expansion_locs=()).to_dict(),
                tidy._TidyDiagnostic(
                    file_path='src_file.cc',
                    line_number=1,
                    diag_name='bar',
                    message='baz',
                    replacements=(),
                    expansion_locs=()).to_dict(),
            ],
            'failed_src_files': ['src_file.cc', 'src_file.h'],
            'timed_out_src_files': ['secondary_file.cc', 'src_file.h'],
        })

  def test_output_conversion_doesnt_outputs_paths_only_once(self):
    self._silence_logs()

    main_action = tidy._TidyAction(
        cc_file='/foo/cc_file.cc', target='bar.o', in_dir='in/', flags='')
    secondary_action = tidy._TidyAction(
        cc_file='/foo/secondary_file.cc',
        target='baz.o',
        in_dir='in/',
        flags='')
    result = tidy._convert_tidy_output_json_obj(
        base_path='/foo',
        tidy_actions={
            main_action: ['/foo/src_file.cc'],
            secondary_action: ['/foo/bar/../src_file.cc'],
        },
        failed_actions=[main_action, secondary_action],
        failed_tidy_actions=[],
        timed_out_actions=[main_action, secondary_action],
        findings=[],
        only_src_files=None,
    )

    self.assertEqual(
        result, {
            'diagnostics': [],
            'failed_src_files': ['src_file.cc'],
            'timed_out_src_files': ['src_file.cc'],
        })

  def test_output_conversion_respects_src_file_filters(self):
    self._silence_logs()

    main_action = tidy._TidyAction(
        cc_file='/foo/src_file.cc', target='bar.o', in_dir='in/', flags='')
    result = tidy._convert_tidy_output_json_obj(
        base_path='/foo',
        tidy_actions={
            main_action: ['/foo/src_file.cc', '/foo/src_file.h'],
        },
        failed_actions=[],
        failed_tidy_actions=[],
        timed_out_actions=[],
        findings=[
            tidy._TidyDiagnostic(
                file_path='/foo/src_file.h',
                line_number=1,
                diag_name='bar',
                message='baz',
                replacements=(),
                expansion_locs=()),
            tidy._TidyDiagnostic(
                file_path='/foo/src_file.cc',
                line_number=1,
                diag_name='bar',
                message='baz',
                replacements=(),
                expansion_locs=()),
        ],
        only_src_files=['/foo/src_file.cc'],
    )

    self.assertEqual(
        result, {
            'diagnostics': [
                tidy._TidyDiagnostic(
                    file_path='src_file.cc',
                    line_number=1,
                    diag_name='bar',
                    message='baz',
                    replacements=(),
                    expansion_locs=()).to_dict(),
            ],
            'failed_src_files': [],
            'timed_out_src_files': [],
        })

  def test_ninja_deps_parsing_filters_stale_entries(self):
    test_input = '\n'.join([
        'obj/foo.o: #deps 43, deps mtime 1579507293554707398 (STALE)',
        '    ../../tools/cfi/blacklist.txt',
        '    ../../base/foo_unittest.cc',
        'obj/bar.o: #deps 43, deps mtime 1579507293554707399 (VALID)',
        '    ../../tools/cfi/blacklist.txt',
        '    ../../base/bar_unittest.cc',
    ])

    output = list(
        tidy._parse_ninja_deps_output(_to_stringio(test_input), u'/in/dir'))
    self.assertEqual(output, [
        ('obj/bar.o', [
            '/in/dir/../../tools/cfi/blacklist.txt',
            '/in/dir/../../base/bar_unittest.cc'
        ]),
    ])

  def test_gn_desc_parsing_makes_only_file_paths_relative_to_root(self):
    gn_desc = {
        '//my_awesome:target': {
            'sources': ['//awesome.cpp'],
        },
    }

    results = tidy._parse_gn_desc_output(gn_desc, '/root')
    self.assertEqual(results.targets_containing('//awesome.cpp'), ())
    self.assertEqual(
        results.targets_containing('/root/awesome.cpp'),
        ['//my_awesome:target'])
    self.assertEqual(
        results.source_files_for_target('//my_awesome:target'),
        ['/root/awesome.cpp'])
    self.assertEqual(
        results.source_files_for_target('//my_awesome:target_v2'), ())

  def test_gn_desc_parsing_gracefully_handles_unknown_paths(self):
    gn_desc = {
        '//my_awesome:target': {
            'sources': ['//awesome.cpp'],
        },
    }

    results = tidy._parse_gn_desc_output(gn_desc, '/root')
    self.assertEqual(results.targets_containing('/doesnt/exist'), ())
    self.assertEqual(results.source_files_for_target('//doesnt/exist'), ())

  def test_buildable_src_files_returns_identity_if_file_is_buildable(self):
    cc_to_target_map = {
        '/foo.gen': ['foo.gen.o'],
        '/foo.cc': ['foo.cc.o'],
        '/foo.h': ['foo.h.o'],
    }

    no_desc = tidy._GnDesc({})
    for target in cc_to_target_map:
      self.assertEqual(
          tidy._buildable_src_files_for(target, cc_to_target_map, no_desc),
          [target])

  def test_buildable_src_files_returns_nothing_if_nonbuildable_nonheader(self):
    cc_to_target_map = {
        '/foo.cc': ['foo.o'],
    }

    no_desc = tidy._GnDesc({})
    self.assertEqual(
        tidy._buildable_src_files_for('/foo.inc', cc_to_target_map, no_desc),
        [])

  def test_buildable_src_files_returns_naive_rename_for_headers(self):
    cc_to_target_map = {
        '/foo.cc': ['foo.o'],
    }

    no_desc = tidy._GnDesc({})
    self.assertEqual(
        tidy._buildable_src_files_for('/foo.h', cc_to_target_map, no_desc),
        ['/foo.cc'])

  def test_perform_build_builds_all_src_phony_and_object_targets(self):
    self._silence_logs()

    cc_to_target_map = {
        '/foo.cc': ['foo.o'],
        '/bar.cc': ['bar.o'],
    }

    def run_ninja(out_dir, phony_targets, object_targets):
      self.assertEqual(phony_targets, ['path/to/my:targ'])
      self.assertEqual(sorted(object_targets), ['bar.o', 'foo.o'])
      return ()

    tidy._perform_build(
        out_dir='/out',
        run_ninja=run_ninja,
        parse_ninja_deps=lambda _: [('foo.o', ['/foo.cc', '/foo.h'])],
        cc_to_target_map=cc_to_target_map,
        gn_desc=tidy._GnDesc(per_target_srcs={
            '//path/to/my:targ': ['/foo.cc', '/bar.cc', '/foo.h']
        }),
        potential_src_cc_file_deps={
            '/foo.h': ['/foo.cc', '/bar.cc'],
        })

  def test_perform_build_falls_back_to_all_if_deps_werent_found(self):
    self._silence_logs()

    cc_to_target_map = {
        '/foo.cc': ['foo.o'],
        '/bar.cc': ['bar.o'],
        '/baz.cc': ['baz.o'],
    }

    built_objects = []
    built_targets = []

    def run_ninja(out_dir, phony_targets, object_targets):
      built_targets.append(phony_targets)
      built_objects.append(object_targets)
      return ()

    tidy._perform_build(
        out_dir='/out',
        run_ninja=run_ninja,
        parse_ninja_deps=lambda _: [('foo.o', ['/foo.cc'])],
        cc_to_target_map=cc_to_target_map,
        gn_desc=tidy._GnDesc(per_target_srcs={
            '//path/to/my:targ': ['/foo.cc', '/foo.h'],
        }),
        potential_src_cc_file_deps={
            '/foo.h': ['/foo.cc'],
        })

    self.assertEqual(built_objects, [['foo.o'], []])
    self.assertEqual(built_targets, [['path/to/my:targ'], ['all']])

  def test_perform_build_doesnt_fall_back_if_only_cc_files_werent_found(self):
    self._silence_logs()

    built_objects = []
    built_targets = []

    def run_ninja(out_dir, phony_targets, object_targets):
      built_targets.append(phony_targets)
      built_objects.append(object_targets)
      return ()

    tidy._perform_build(
        out_dir='/out',
        run_ninja=run_ninja,
        parse_ninja_deps=lambda _: [],
        cc_to_target_map={
            '/foo.cc': ['foo.o'],
        },
        gn_desc=tidy._GnDesc(per_target_srcs={
            '//path/to/my:targ': ['/foo.cc', '/foo.h'],
        }),
        potential_src_cc_file_deps={
            '/foo.cc': ['/foo.cc'],
        })

    self.assertEqual(built_objects, [['foo.o']])
    self.assertEqual(built_targets, [['path/to/my:targ']])

  def test_perform_build_reported_dependency_information_is_correct(self):
    self._silence_logs()

    cc_to_target_map = {
        '/foo.cc': ['foo.o'],
        '/bar.cc': ['bar.o'],
        '/baz.cc': ['baz.o'],
    }

    src_file_to_target_map, _ = tidy._perform_build(
        out_dir='/out',
        run_ninja=lambda out_dir, phony_targets, object_targets: (),
        parse_ninja_deps=lambda _: [
            ('foo.o', ['/foo.cc', '/foo.h']),
            ('bar.o', ['/bar.cc', '/foo.h']),
            ('baz.o', ['/baz.cc']),],
        cc_to_target_map=cc_to_target_map,
        gn_desc=tidy._GnDesc(per_target_srcs={
            '//path/to/my:targ': ['/foo.cc', '/foo.h', '/bar.cc', '/baz.cc'],
        }),
        potential_src_cc_file_deps={
            '/foo.h': ['/foo.cc', '/bar.cc', '/baz.cc'],
        })

    self.assertEqual(src_file_to_target_map, {
        '/foo.h': {'foo.o', 'bar.o'},
    })

  def test_perform_build_includes_dep_info_from_build_of_all(self):
    self._silence_logs()

    cc_to_target_map = {
        '/foo.cc': ['foo.o'],
        '/bar.cc': ['bar.o'],
        '/baz.cc': ['baz.o'],
    }

    built_objects = set()
    built_targets = set()

    def run_ninja(out_dir, phony_targets, object_targets):
      built_targets.update(phony_targets)
      built_objects.update(object_targets)
      return ()

    def parse_ninja_deps(out_dir):
      self.assertEqual(out_dir, '/out')
      if 'all' in built_targets:
        return [('foo.o', ['/foo.cc', '/foo.h'])]
      return ()

    src_file_to_target_map, _ = tidy._perform_build(
        out_dir='/out',
        run_ninja=run_ninja,
        parse_ninja_deps=parse_ninja_deps,
        cc_to_target_map=cc_to_target_map,
        gn_desc=tidy._GnDesc({}),
        potential_src_cc_file_deps={
            '/foo.h': [],
        })

    self.assertIn('all', built_targets)
    self.assertEqual(src_file_to_target_map, {
        '/foo.h': {'foo.o'},
    })


if __name__ == '__main__':
  if '--using_hacky_test_runner' not in sys.argv:
    print('You seem to be running this directly. Please consider using '
          'tricium_clang_tidy_test.py instead, since that tries to test under '
          'both py2 and py3.',
          file=sys.stderr)

  unittest.main(argv=[s for s in sys.argv if s != '--using_hacky_test_runner'])
