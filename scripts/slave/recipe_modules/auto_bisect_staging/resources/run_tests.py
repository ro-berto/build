#!/usr/bin/env vpython
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Runs all tests in all unit test modules in this directory."""

import os
import sys
import unittest
import logging


def _fix_path():  # pragma: no cover
  _add_to_sys_path(os.path.join(os.path.dirname(__file__), os.path.pardir))


def _add_to_sys_path(path):
  if path not in sys.path:
    sys.path.insert(0, path)


def main():  # pragma: no cover
  _fix_path()
  suite = unittest.TestSuite()
  suite.addTests(unittest.TestLoader().discover(
      start_dir=os.path.dirname(__file__), pattern='*_test.py'))
  result = unittest.TextTestRunner(verbosity=1).run(suite)
  return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
  sys.exit(main())  # pragma: no cover
