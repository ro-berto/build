#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Synchronized Standard IO Linebuffer/Muxer implemented with cStringIO.

Derived from src/tools/sharding_supervisor/stdio_buffer.py.
"""

import os
import sys
import threading
import time
import Queue


class BufferMuxer(object):
  """Multiplex and line-buffer multiple character streams.

  Note: this class requires streams to be opened in 'universal newline'
  mode! Make sure streams and pipes are opened (or re-opened) with 'rU'.

  Usage:

  muxer = BufferMuxer()
  muxer.add_pipe(sys.stdout, my_stdout)
  muxer.add_pipe(sys.stderr, my_stderr)
  muxer.add_pipe('my_file', open('myfile', 'rU'))
  (ts, id, line) = muxer.readline()
  if not line: [exit]

  """
  def __init__(self):
    self.queue = Queue.Queue()
    self.completed = 0
    self.added = 0

  def _pipe_handler(self, pipe_id, pipe):
    """Helper method for collecting streaming output.

    Output is collected until a newline is seen, at which point an event is
    triggered and the line is pushed to a buffer as a (timestamp, id, line)
    tuple.
    """
    for line in pipe:
      self.queue.put((time.time(), pipe_id, line))
    self.queue.put((time.time(), pipe_id, None))

  def add_pipe(self, pipe_id, pipe):
    self.added += 1
    t = threading.Thread(target=self._pipe_handler, args=[pipe_id, pipe])
    t.daemon = True  # if main thread is ctrl-C'd, kill this thread too
    t.start()
    return t

  def readline(self):
    """Emits a tuple of (timestamp, sys.stderr, line),
                        (timestamp, sys.stdout, line),
    or (None, None, None) if the process has finished.
    This is a blocking call.
    """
    while True:  # if a pipe is closed with None, keep going
      if self.completed >= self.added:
        return (None, None, None)
      (ts, pipe, line) = self.queue.get(True)
      if line:
        return (ts, pipe, line)
      self.completed += 1


class StreamJoin(object):
  """Merges multiple streams while preserving lines.

  Make sure streams have been opened with 'universal newlines.'
  """

  def __init__(self, streams, flush_on_line=False):
    self.flush_on_line = flush_on_line
    self.buffer = BufferMuxer()
    for stream in streams:
      self.buffer.add_pipe(None, stream)

    (r, w) = os.pipe()
    self.rpipe = os.fdopen(r, 'r')
    self.wpipe = os.fdopen(w, 'w')

    self.t = threading.Thread(target=self._readlines)
    self.t.daemon = True
    self.t.start()

  def getPipe(self):
    return self.rpipe

  def _readlines(self):
    (_, _, line) = self.buffer.readline()
    while line:
      self.wpipe.write(line)
      if self.flush_on_line:
        self.wpipe.flush()
      (_, _, line) = self.buffer.readline()
    self.wpipe.close()

  def __iter__(self):
    return self

  def close(self):
    return self.rpipe.close()

  def fileno(self):
    return self.rpipe.fileno()

  def isatty(self):
    return self.rpipe.isatty()

  def next(self):
    return self.rpipe.next()

  def read(self, *args):
    return self.rpipe.read(*args)

  def readline(self, *args):
    return self.rpipe.readline(*args)

  def readlines(self, *args):
    return self.rpipe.readlines(*args)

  def seek(self, *args):
    return self.rpipe.seek(*args)

  def tell(self):
    return self.rpipe.tell()

  def write(self, *args):
    return self.rpipe.write(*args)

  def writelines(self, *args):
    return self.rpipe.write(*args)


def main(argv):
  streams = []
  if len(argv) > 1:
    for arg in argv[1:]:
      if arg == '-':
        streams.append(sys.stdin)
      else:
        streams.append(open(arg, 'rU'))
  else:
    streams.append(sys.stdin)

  join = StreamJoin(streams)
  for line in join:
    print line,

  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv))
