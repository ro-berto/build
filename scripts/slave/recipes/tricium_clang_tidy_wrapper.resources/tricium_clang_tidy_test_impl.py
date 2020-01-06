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

import io
import json
import logging
import sys
import unittest

import tricium_clang_tidy as tidy


def _parse_fixes_file_text(line_offsets,
                           contents_text,
                           tidy_invocation_dir='/tidy/dir'):
  if sys.version_info[0] == 2 and isinstance(contents_text, str):
    contents_text = unicode(contents_text)
  return list(
      tidy._parse_tidy_fixes_file(
          line_offsets,
          io.StringIO(contents_text),
          tidy_invocation_dir=tidy_invocation_dir))


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
            replacements=()),
        tidy._TidyDiagnostic(
            file_path='/foo2',
            line_number=1,
            diag_name='-Wfoo2',
            message='foo2',
            replacements=()),
        tidy._TidyDiagnostic(
            file_path='foo3',
            line_number=2,
            diag_name='-Wfoo3',
            message='foo3',
            replacements=()),
    ]

    diagnostics = [{
        'DiagnosticName': diag.diag_name,
        'DiagnosticMessage': {
            'Message': diag.message,
            'FilePath': diag.file_path,
            'FileOffset': i,
        },
    } for i, diag in enumerate(tidy_diags)]

    inputs = {
        'Diagnostics': diagnostics,
    }

    tidy_diags[-1] = tidy_diags[-1]._replace(file_path='/tidy/foo3')
    # YAML doesn't have a dumps() on my local machine; JSON's easiest.
    self.assertEqual(
        _parse_fixes_file_text(input_file, json.dumps(inputs),
                               tidy_invocation_dir), tidy_diags)

  def test_generate_tidy_actions_actually_builds_everything(self):
    chunk_size = 2
    has_built = set()

    def builder(what_to_build):
      what_to_build = set(what_to_build)
      self.assertLessEqual(len(what_to_build), chunk_size)
      self.assertEqual(what_to_build & has_built, set())
      has_built.update(what_to_build)
      return []

    what_to_build = ['foo.cc', 'bar.cc', 'baz.cc']
    objects_to_build = [name + '.o' for name in what_to_build]
    compile_commands = [
        tidy._CompileCommand(
            target_name=obj,
            file_abspath='/%s' % name,
            file=name,
            directory='/in',
            command=['whee'],
        ) for name, obj in zip(what_to_build, objects_to_build)
    ]

    actions, failed = tidy._generate_tidy_actions(
        '/out', ['/%s' % x for x in what_to_build], builder, compile_commands,
        chunk_size)
    self.assertEqual(failed, [])
    self.assertEqual(set(objects_to_build), has_built)
    self.assertEqual(actions, [
        tidy._TidyAction(
            cc_file=cmd.file_abspath,
            target=cmd.target_name,
            in_dir=cmd.directory,
            flags=cmd.command) for cmd in compile_commands
    ])

  def test_generate_tidy_actions_doesnt_crash_on_nonexistent_files(self):
    self._silence_logs()

    builder_called_with = set()

    def builder(what_to_build):
      builder_called_with.update(set(what_to_build))
      return []

    compile_commands = [
        tidy._CompileCommand(
            target_name='foo.cc.o',
            file_abspath='/foo.cc',
            file='foo.cc',
            directory='/in',
            command=['whee'],
        )
    ]

    actions, failed = tidy._generate_tidy_actions(
        '/out', ['/foo.cc', '/bar.cc'], builder, compile_commands)
    self.assertEqual(failed, [])
    self.assertEqual(actions, [
        tidy._TidyAction(
            cc_file='/foo.cc', target='foo.cc.o', in_dir='/in', flags=['whee'])
    ])
    self.assertEqual(builder_called_with, set(x.target for x in actions))

  def test_generate_tidy_actions_functions_with_no_filter(self):
    builder_called_with = set()

    def builder(what_to_build):
      builder_called_with.update(set(what_to_build))
      return []

    compile_commands = [
        tidy._CompileCommand(
            target_name='foo.cc.o',
            file_abspath='/foo.cc',
            file='foo.cc',
            directory='/in',
            command=['whee'],
        )
    ]

    actions, failed = tidy._generate_tidy_actions('/out', None, builder,
                                                  compile_commands)
    self.assertEqual(failed, [])
    self.assertEqual(actions, [
        tidy._TidyAction(
            cc_file='/foo.cc', target='foo.cc.o', in_dir='/in', flags=['whee'])
    ])
    self.assertEqual(builder_called_with, set(x.target for x in actions))

  def test_generate_tidy_actions_reports_failures(self):
    self._silence_logs()

    builder_called_with = set()

    def builder(what_to_build):
      builder_called_with.update(set(what_to_build))
      return list(what_to_build)

    compile_commands = [
        tidy._CompileCommand(
            target_name='foo.cc.o',
            file_abspath='/foo.cc',
            file='foo.cc',
            directory='/in',
            command=['whee'],
        )
    ]

    actions, failed = tidy._generate_tidy_actions('/out', None, builder,
                                                  compile_commands)
    self.assertEqual(failed, ['/foo.cc'])
    self.assertEqual(actions, [
        tidy._TidyAction(
            cc_file='/foo.cc', target='foo.cc.o', in_dir='/in', flags=['whee'])
    ])
    self.assertEqual(builder_called_with, set(x.target for x in actions))

  def test_run_all_tidy_actions_reports_everything(self):
    self._silence_logs()

    binary = object()
    actions = [
        tidy._TidyAction(
            cc_file='timeout', target='timeout.o', in_dir='in/', flags=[]),
        tidy._TidyAction(
            cc_file='fail', target='fail.o', in_dir='in/', flags=[]),
        tidy._TidyAction(
            cc_file='success', target='success.o', in_dir='in/', flags=[]),
    ]

    good_diag = tidy._TidyDiagnostic(
        file_path='whee',
        line_number=1,
        diag_name='-Whee',
        message='whee',
        replacements=())
    bad_diag = tidy._TidyDiagnostic(
        file_path='oh_no',
        line_number=1,
        diag_name='-Whee',
        message='oh no',
        replacements=())

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

    self.assertEqual(failed_cc_files, {'fail'})
    self.assertEqual(timed_out_cc_files, {'timeout'})
    self.assertEqual(findings, {good_diag, bad_diag})

  def testLineOffsetMapHandlesNoTextGracefully(self):
    no_text = tidy._LineOffsetMap.for_text('')
    self.assertEqual(no_text.get_line_number(0), 1)
    self.assertEqual(no_text.get_line_offset(0), 0)
    self.assertEqual(no_text.get_line_number(1), 1)
    self.assertEqual(no_text.get_line_offset(1), 1)

  def testLineOffsetMapIsNextLineAfterEOLCharacter(self):
    newline_start = tidy._LineOffsetMap.for_text('\n')
    self.assertEqual(newline_start.get_line_number(0), 1)
    self.assertEqual(newline_start.get_line_offset(0), 0)
    self.assertEqual(newline_start.get_line_number(1), 2)
    self.assertEqual(newline_start.get_line_offset(1), 0)
    self.assertEqual(newline_start.get_line_number(2), 2)
    self.assertEqual(newline_start.get_line_offset(2), 1)

  def testLineOffsetMapOnRandomInput(self):
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

  def testFilterInvalidFindingsFiltersAllTheBadThings(self):
    self._silence_logs()

    good = [
        tidy._TidyDiagnostic(
            file_path='foo.c',
            line_number=1,
            diag_name='bar',
            message='baz',
            replacements=())
    ]

    bad = [
        tidy._TidyDiagnostic(
            file_path='',
            line_number=1,
            diag_name='bar',
            message='baz',
            replacements=())
    ]

    self.assertEqual(tidy._filter_invalid_findings(good + bad), good)

  def testPathNormalizationFunctionsAtAll(self):
    self.assertEqual(tidy._normalize_path_to_base('/foo', base=None), '/foo')
    self.assertEqual(tidy._normalize_path_to_base('/foo', base='/'), 'foo')
    self.assertEqual(tidy._normalize_path_to_base('/foo', base='/foo'), '.')
    self.assertIsNone(tidy._normalize_path_to_base('/foo', base='/foo/bar'))
    self.assertIsNone(tidy._normalize_path_to_base('/bar', base='/foo'))
    self.assertIsNone(tidy._normalize_path_to_base('/bar', base='/ba'))

  def testPathNormalizationMappersDiscardNones(self):
    base = '/foo'
    input_list = [
        '/foo/bar',
        '/bar',
        '/',
        '/bar/foo',
    ]
    self.assertListEqual(
        list(tidy._normalize_paths_to_base(input_list, base)), [
            'bar',
            None,
            None,
            None,
        ])

    input_list = [
        tidy._TidyDiagnostic(
            file_path='/foo/bar.cc',
            line_number=1,
            diag_name='foo',
            message='aaaaa',
            replacements=()),
        tidy._TidyDiagnostic(
            file_path='/bar/baz.cc',
            line_number=2,
            diag_name='bar',
            message='bbbbb',
            replacements=()),
    ]
    self.assertListEqual(
        list(tidy._normalize_diags_to_base(input_list, base)), [
            tidy._TidyDiagnostic(
                file_path='bar.cc',
                line_number=1,
                diag_name='foo',
                message='aaaaa',
                replacements=()),
            None,
        ])


if __name__ == '__main__':
  if '--using_hacky_test_runner' not in sys.argv:
    print('You seem to be running this directly. Please consider using '
          'tricium_clang_tidy_test.py instead, since that tries to test under '
          'both py2 and py3.',
          file=sys.stderr)

  unittest.main(argv=[s for s in sys.argv if s != '--using_hacky_test_runner'])
