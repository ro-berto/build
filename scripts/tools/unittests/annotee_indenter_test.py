#!/usr/bin/env vpython
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import test_env

import os
import sys
import unittest
import Queue
import StringIO

from tools import annotee_indenter


class AnnoteeNesterTest(unittest.TestCase):
  def _indent_test(self, data_in, data_out_expected, base_level=2):
    # left-strip from provided lines so test code is easier to read.
    input_lines = [x.lstrip() for x in data_in.splitlines(True)]
    output_lines_expected = [x.lstrip() for x in
                             data_out_expected.splitlines(True)]

    output_stream = StringIO.StringIO()
    annotee_indenter.indent(base_level, input_lines, output_stream)
    output_lines = output_stream.getvalue().splitlines(True)
    self.assertListEqual(output_lines, output_lines_expected)

  def test_basic(self):
    self._indent_test("""@@@STEP_STARTED@@@
                         @@@STEP_CLOSED@@@""",
                      """@@@STEP_STARTED@@@
                         @@@STEP_NEST_LEVEL@2@@@
                         @@@STEP_CLOSED@@@""",
                      base_level=2)

  def test_already_indented(self):
    self._indent_test("""@@@STEP_STARTED@@@
                         @@@STEP_NEST_LEVEL@1@@@
                         @@@STEP_CLOSED@@@""",
                      """@@@STEP_STARTED@@@
                         @@@STEP_NEST_LEVEL@2@@@
                         @@@STEP_NEST_LEVEL@3@@@
                         @@@STEP_CLOSED@@@""",
                      base_level=2)

  def test_kind_of_nested(self):
    self._indent_test("""@@@STEP_STARTED@@@
                         @@@STEP_STARTED@@@
                         @@@STEP_CLOSED@@@
                         @@@STEP_CLOSED@@@""",
                      """@@@STEP_STARTED@@@
                         @@@STEP_NEST_LEVEL@2@@@
                         @@@STEP_STARTED@@@
                         @@@STEP_NEST_LEVEL@2@@@
                         @@@STEP_CLOSED@@@
                         @@@STEP_CLOSED@@@""",
                      base_level=2)

  def test_line_generator_basic(self):
    q = Queue.Queue()
    for chunk in ['1st\n', '2nd\n3', 'r', 'd', '\n4t', 'h', '\n', '5', 'th']:
      q.put(('stdout', chunk))
      q.put(('stderr', chunk))
    q.put(annotee_indenter.QUEUE_TERMINATE_ITEM)
    stderr_stream = StringIO.StringIO()
    res = list(annotee_indenter.line_generator(q, stderr_stream))
    expected = ['1st\n', '2nd\n', '3rd\n', '4th\n', '5th']
    self.assertEqual(res, expected)
    self.assertEqual(stderr_stream.getvalue().splitlines(True), expected)

  def _communicate(self, args, cwd):
    """Return [stdout lines as list, stderr as string, return_code]"""
    res = []
    def target(q, base_level):
      stderr_stream = StringIO.StringIO()
      res.append(list(annotee_indenter.line_generator(q, stderr_stream)))
      res.append(stderr_stream.getvalue())

    ret_code = annotee_indenter.run(args, cwd, base_level=1, target=target)
    self.assertEqual(len(res), 2)
    out_list, err = res  # pylint: disable=W0632
    return out_list, err, ret_code

  def _communicate_test(self, name, ret_code):
    # Run ./output_generator.py with given name and ret_code.
    return self._communicate(
        [sys.executable, 'output_generator.py', name, str(ret_code)],
        cwd=os.path.dirname(__file__))

  def test_run_stdout(self):
    out, err, ret = self._communicate_test('simple_out', 0)
    self.assertEqual(err, '')
    self.assertEqual(out, ['simple' + os.linesep])
    self.assertEqual(ret, 0)

  def test_run_stderr(self):
    out, err, ret = self._communicate_test('simple_err', 2)
    self.assertEqual(out, [])
    self.assertEqual(err, 'simple' + os.linesep)
    self.assertEqual(ret, 2)

  def test_run_both(self):
    out, err, ret = self._communicate_test('simple_both', 0)
    self.assertEqual(out, ['simple' + os.linesep])
    self.assertEqual(err, 'simple' + os.linesep)
    self.assertEqual(ret, 0)

  def test_run_both_x_100000(self):
    out, err, ret = self._communicate_test('both_x_100000', 0)
    self.assertEqual(out, ['simple' + os.linesep] * 100000)
    self.assertEqual(err, ('simple' + os.linesep) * 100000)
    self.assertEqual(ret, 0)

  def test_run_overload_buffers(self):
    self.maxDiff = 1000000
    out, err, ret = self._communicate_test('overload_buffers', 0)
    s = 'x' * 99 + os.linesep
    self.assertEqual(out, [s] * (10 * 1000))
    self.assertEqual(err, s * (10 * 1000))
    self.assertEqual(ret, 0)

if __name__ == '__main__':
  unittest.main()
