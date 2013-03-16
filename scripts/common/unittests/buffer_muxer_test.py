#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for buffer_muxer.py."""

import cStringIO
import collections
import threading
import unittest

import test_env  # pylint: disable=W0611

from common import buffer_muxer


# TODO(xusydoc): replace with os.pipe()
class FifoPipe(object):
  """Threadsafe blocking readable/writable pipe."""

  def __init__(self, string=''):
    self.event = threading.Event()  # signals that the deque is empty
    self.event.clear()
    self.deq = collections.deque()
    self.lock = threading.Lock()
    self.write(string)
    self.done = False

  def read(self, length):
    """Blocking read."""
    if length > 1:
      raise NotImplementedError()

    self.event.wait()  # block until the deque has data
    data = self.deq.popleft()
    with self.lock:
      if len(self.deq) > 0:
        self.event.set()
      else:
        self.event.clear()
    return data

  def __iter__(self):
    return self

  def next(self):
    """Simulates a File next(), which operates on lines.."""
    if self.done:
      raise StopIteration()
    data = self.read(1)
    if not data:
      self.done = True
      raise StopIteration()
    buf = cStringIO.StringIO()
    while data:
      buf.write(data)
      if data == '\n':
        break
      data = self.read(1)
    line = buf.getvalue()
    buf.close()
    return line

  def write(self, string):
    self.deq.extend(string)
    with self.lock:
      self.event.set()

  def close(self):
    self.deq.append('')
    with self.lock:
      self.event.set()


class BufferMuxerTest(unittest.TestCase):
  """Holds tests for BufferMuxer."""
  def setUp(self):
    super(BufferMuxerTest, self).setUp()

    self.buffer = buffer_muxer.BufferMuxer()

    self.lines = ['this is stream one',
                  'this is stream two\nstill stream two',
                  'this is stream three',
                  'this is stream four']

    self.streams = [FifoPipe(line) for line in self.lines]

  def _AddNewline(self, index, nl='\n'):
    stream = self.streams[index]
    stream.write(nl)
    stream.close()


  def _AddNewlines(self, nl='\n'):
    for idx in range(len(self.streams)):
      self._AddNewline(idx)

  def _AddStream(self, index):
    self.buffer.add_pipe(index, self.streams[index])
    return self.streams[index]

  def _AssertLineIsNone(self):
    (_, _, line) = self.buffer.readline()
    self.assertTrue(line is None)

  def _AssertLineEquals(self, expected_line, add_nl='\n'):
    (_, _, line) = self.buffer.readline()
    self.assertEqual(line, expected_line + add_nl)

  def testSingleLine(self):
    self._AddNewlines()
    self._AddStream(0)

    self._AssertLineEquals(self.lines[0])
    self._AssertLineIsNone()

  def testMuxing(self):
    self._AddStream(0)
    self._AddStream(1)
    self._AssertLineEquals(self.lines[1].split('\n')[0])
    self._AddNewlines()
    self._AssertLineEquals(self.lines[0])
    self._AssertLineEquals(self.lines[1].split('\n')[1])
    self._AssertLineIsNone()

  def testOutOfSeq(self):
    self._AddStream(0)
    self._AddStream(3)
    self._AddStream(2)
    self._AddNewline(2)
    self._AssertLineEquals(self.lines[2])
    self._AddNewline(0)
    self._AssertLineEquals(self.lines[0])
    self._AddNewline(3)
    self._AssertLineEquals(self.lines[3])
    self._AssertLineIsNone()


class StreamJoinTest(unittest.TestCase):
  """Holds tests for StreamJoin."""

  def setUp(self):
    super(StreamJoinTest, self).setUp()

    self.lines = ['this is stream one',
                  'this is stream two\nstill stream two',
                  'this is stream three',
                  'this is stream four']

    self.streams = [FifoPipe(line) for line in self.lines]

    self.joiner = buffer_muxer.StreamJoin(self.streams, flush_on_line=True)

  def tearDown(self):
    self.joiner.close()

  def _AddNewline(self, index, nl='\n'):
    stream = self.streams[index]
    stream.write(nl)
    stream.close()

  def _AssertLineEquals(self, expected_line, add_nl='\n'):
    line = self.joiner.readline()
    self.assertEqual(line, expected_line + add_nl)

  def testOutOfSeq(self):
    self._AssertLineEquals(self.lines[1].split('\n')[0])
    self._AddNewline(2)
    self._AssertLineEquals(self.lines[2])
    self._AddNewline(0)
    self._AssertLineEquals(self.lines[0])
    self._AddNewline(3)
    self._AssertLineEquals(self.lines[3])
    self._AddNewline(1)
    self._AssertLineEquals(self.lines[1].split('\n')[1])


if __name__ == '__main__':
  unittest.main()
