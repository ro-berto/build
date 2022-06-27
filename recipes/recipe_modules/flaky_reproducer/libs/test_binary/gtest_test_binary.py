# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import tempfile

from .base_test_binary import (BaseTestBinary, strip_command_switches,
                               strip_env_vars)
from ..result_summary.gtest_result_summary import GTestTestResultSummary


class GTestTestBinary(BaseTestBinary):

  def strip_for_bots(self):
    ret = super().strip_for_bots()

    gtest_strip_switches = {
        key: 1
        for key in ('test-launcher-summary-output', 'test-launcher-retry-limit',
                    'isolated-script-test-repeat', 'test-launcher-filter-file',
                    'isolated-script-test-filter', 'gtest_filter')
    }
    ret.command = strip_command_switches(ret.command, gtest_strip_switches)

    gtest_env_keys = ('GTEST_SHARD_INDEX', 'GTEST_TOTAL_SHARDS')
    ret.env_vars = strip_env_vars(ret.env_vars, gtest_env_keys)

    return ret

  def run_tests(self, tests, repeat=1):
    tmp_files = []
    try:
      cmd = self.command[:]
      cmd.append('--test-launcher-retry-limit=0')  # Disable retry.
      cmd.append("--isolated-script-test-repeat={0}".format(repeat))

      if len(tests) >= 10:
        filter_file = tempfile.NamedTemporaryFile(delete=False)
        tmp_files.append(filter_file)
        filter_file.writelines(tests)
        filter_file.close()
        cmd.append("--test-launcher-filter-file={0.name}".format(filter_file))
      else:
        cmd.append("--isolated-script-test-filter={0}".format(':'.join(tests)))

      output_json = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
      tmp_files.append(output_json)
      output_json.close()
      cmd.append("--test-launcher-summary-output={0.name}".format(output_json))

      ret_code = self.run_cmd(cmd)
      if ret_code != 0:
        raise ChildProcessError(
            "Run command failed with code {0}.".format(ret_code))

      return GTestTestResultSummary.from_output_json(
          json.load(open(output_json.name)))
    finally:
      for f in tmp_files:
        os.unlink(f.name)
