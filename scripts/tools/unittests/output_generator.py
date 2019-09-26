# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys

out = lambda x: (sys.stdout.write(x), sys.stdout.flush())
err = lambda x: (sys.stderr.write(x), sys.stderr.flush())
eol = os.linesep


def simple_out():
  out('simple' + eol)

def simple_err():
  err('simple' + eol)

def simple_both():
  simple_out()
  simple_err()

def both_x_100000():
  for _ in xrange(100000):
    simple_out()
    simple_err()


def overload_buffers():
  s = 'x' * 99 + eol
  for _ in xrange(10):
    for _ in xrange(1000):
      out(s)
    for _ in xrange(1000):
      err(s)


if __name__ == '__main__':
  assert len(sys.argv) == 3, '(name of func) (return code) required.'
  name, ret_code = sys.argv[1:3]
  locals()[name]()
  sys.exit(int(ret_code))
