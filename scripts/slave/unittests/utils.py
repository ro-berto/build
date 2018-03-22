# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A collection of utils used by slave unittests."""

import contextlib
import coverage
import os
import shutil
import tempfile
import unittest


@contextlib.contextmanager
def print_coverage(include=None):
  cov = coverage.coverage(include=include)
  cov.start()
  try:
    yield
  finally:
    cov.stop()
    cov.report()


class FakeBuildRootTestCase(unittest.TestCase):
  """Sets up a fake build root (e.g., "<TEMP>/b/build/slave/buildername/build".

  NOTE: This is *expensive*, as it does an actual fetch of "build"!
  """

  @classmethod
  def setUpClass(cls):
    # Create a simulated buildslave root.
    cls._tmp_root = tempfile.mkdtemp(suffix='build_test')
    b_dir = os.path.join(cls._tmp_root, 'b')
    cls._build_dir = os.path.join(b_dir, 'build')
    os.makedirs(cls._build_dir)

    # Create a ".gclient" file. This will be populated by "update_scripts".
    with open(os.path.join(b_dir, '.gclient'), 'w') as fd:
      solution = {
          'url': 'https://chromium.googlesource.com/chromium/tools/build.git',
          'managed': False,
          'name': 'build',
      }
      fd.write('solutions = %s' % (repr([solution]),))

    # Get a fake BuildBot builder directory.
    cls._builder_dir = os.path.join(
        cls._build_dir, 'slave', 'buildername', 'build')
    os.makedirs(cls._builder_dir)


  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls._tmp_root)

  @property
  def fake_build_root(self):
    return self._builder_dir

  def get_test_env(self, **kwargs):
    env = os.environ.copy()
    # Force "update_scripts" to update our fake build directory.
    env['RUN_SLAVE_UPDATED_SCRIPTS_TEST_BUILD_DIR'] = self._build_dir
    env.pop('RUN_SLAVE_UPDATED_SCRIPTS', None)
    env.update(kwargs)
    return env
