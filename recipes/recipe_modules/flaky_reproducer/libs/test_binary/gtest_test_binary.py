# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import tempfile

from . import utils
from .base_test_binary import (BaseTestBinary, TestBinaryWithBatchMixin,
                               TestBinaryWithParallelMixin)
from ..result_summary.gtest_result_summary import GTestTestResultSummary


class GTestTestBinary(TestBinaryWithBatchMixin, TestBinaryWithParallelMixin,
                      BaseTestBinary):

  def strip_for_bots(self):
    ret = super().strip_for_bots()

    gtest_strip_switches = {
        key: 1
        for key in ('test-launcher-summary-output', 'test-launcher-retry-limit',
                    'isolated-script-test-repeat', 'test-launcher-batch-limit',
                    'test-launcher-jobs', 'test-launcher-filter-file',
                    'isolated-script-test-filter', 'gtest_filter')
    }
    ret.command = utils.strip_command_switches(ret.command,
                                               gtest_strip_switches)
    # Should strip all wrappers
    is_local = len(ret.command) >= 1 and ret.command[0].startswith('.')
    is_test_env_py = len(ret.command) >= 2 and ret.command[1].strip('./\\') in (
        'testing/test_env.py', 'testing/xvfb.py')
    if not (is_local or is_test_env_py):
      raise ValueError('Command line contains unknown wrapper: {0}'.format(
          ret.command))

    gtest_env_keys = ('GTEST_SHARD_INDEX', 'GTEST_TOTAL_SHARDS')
    ret.env_vars = utils.strip_env_vars(ret.env_vars, gtest_env_keys)

    return ret

  def _get_command(self, filter_file=None, output_json=None):
    """Get the command line with switches applied."""
    cmd = self.command[:]
    cmd.append('--test-launcher-retry-limit=0')  # Disable retry.
    if filter_file:
      cmd.append("--test-launcher-filter-file={0}".format(filter_file))
    elif self.tests:
      cmd.append("--isolated-script-test-filter={0}".format(':'.join(
          self.tests)))
    if self.repeat:
      cmd.append("--isolated-script-test-repeat={0}".format(self.repeat))
    if self.single_batch:
      cmd.append("--test-launcher-batch-limit=0")
    if self.parallel_jobs:
      cmd.append("--test-launcher-jobs={0}".format(self.parallel_jobs))
    if output_json:
      cmd.append("--test-launcher-summary-output={0}".format(output_json))
    return cmd

  def run(self):
    tmp_files = []
    filter_file = None
    output_json = None
    try:
      if self.tests and len(self.tests) >= 10:
        fp = tempfile.NamedTemporaryFile(suffix='.filter', delete=False)
        tmp_files.append(fp.name)
        fp.writelines(self.tests)
        fp.close()
        filter_file = fp.name

      fp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
      tmp_files.append(fp.name)
      fp.close()
      output_json = fp.name

      cmd = self._get_command(filter_file, output_json)
      utils.run_cmd(cmd, cwd=self.cwd)

      return GTestTestResultSummary.from_output_json(
          json.load(open(output_json)))
    finally:
      for f in tmp_files:
        os.unlink(f)

  def readable_command(self):
    filter_message = ''
    filter_file = None
    if self.tests and len(self.tests) >= 10:
      filter_file = 'tests.filter'
      filter_message = "cat <<EOF > {0}\n{1}\nEOF\n".format(
          filter_file, '\n'.join(self.tests))
    cmd = self._get_command(filter_file)
    return filter_message + ' '.join(cmd)
