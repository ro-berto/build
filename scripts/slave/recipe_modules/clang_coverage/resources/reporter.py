# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Functions for interacting with llvm-cov"""

import json
import logging
import os
import subprocess


def _call_cov_tool(cov_tool_path, profile_input_file_path,
                   report_output_dir_path, binaries, sources):
  """Calls the llvm-cov tool.

  Args:
    cov_tool_path (str): path to the llvm-cov executable
    profile_input_file_path (str): path to the merged profdata file.
    report_output_dir_path (str): path to the directory where the report files
        are to be written.
    binaries (list of str): list of paths to the instrumented executables to
        create a report for.
    sources (list of str): list of paths to the source files to include in the
        report, includes all if not specified.

  Raises:
    CalledProcessError: An error occurred generating the report.
  """
  logging.info('Generating report.')

  try:
    subprocess_cmd = [
        cov_tool_path, 'show', '-format=html',
        '-output-dir=' + report_output_dir_path,
        '-instr-profile=' + profile_input_file_path, '-Xdemangler', 'c++filt',
        '-Xdemangler', '-n', binaries[0]
    ]
    for binary in binaries[1:]:
      subprocess_cmd.extend(['-object', binary])
    if sources:
      subprocess_cmd.extend(sources)

    output = subprocess.check_output(subprocess_cmd)
    logging.debug('Report generation output: %s', output)
  except subprocess.CalledProcessError as error:
    logging.error('Failed to generate report.')
    raise error

  logging.info('Report created in: "%s".', report_output_dir_path)


def generate_report(llvm_cov, profdata_path, report_directory, binaries,
                    sources=None):
  """Generates an html report for profile data using llvm-cov.

  Args:
    llvm_cov (str): The path to the llvm-cov executable.
    profdata_path (str): The path to the merged input profile.
    report_directory (str): Where to write the report.
    binaries (list of str): The binaries to write a report for.
    sources (list of str): list of paths to the source files to include in the
        report, includes all if not specified.
  """
  _call_cov_tool(llvm_cov, profdata_path, report_directory, binaries, sources)
