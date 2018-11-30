#!/usr/bin/python
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Put source files and their html-version coverage report side by side.

Assumptions:
* The html report by llvm-cov has the same files as the json export.
* For a source file /path/to/source.cc, the html report file is in the format of
  $HTML_REPORT_DIR/coverage/path/to/source.cc.html
                    ^^^^^^^^^                 ^^^^^
  In particular, the "coverage/" directory, and ".html" suffix.
* The index file $HTML_REPORT_DIR/index.html list all the html files.
* In each html file, paths are relative to $HTML_REPORT_DIR.
"""

import argparse
import logging
import os
import time
import shutil
import sys


_HTML_SUFFIX = '.html'

# Use symbolic links if possible to avoid the unneeded overhead of file
# content copy.
_SOFT_COPY_FUNC = os.symlink or shutil.copy2


def _CopySourceAndHtmlFile(html_file_dir, html_file_name,
                         html_report_dir, html_report_src_dir,
                         output_dir, output_dir_coverage, src_path):
  """Copies the source file and copies & updates the html report file.

  Args:
    html_report_dir (str): the root directory of the entire html report.
       e.g. /path/to/llvm_html_report/
    html_report_src_dir (str): the path to the src/ directory in the html report
       e.g. /path/to/llvm_html_report/b/tmp/build/cache/src/
    html_file_dir (str): the immediate directory of the html file to process.
       e.g. /path/to/llvm_html_report/b/tmp/build/cache/src/base/
    html_file_name (str): the name of the html file to process.
       e.g. at_exit.cc.html (corresponding to base/at_exit.cc in src/)
    output_dir (str): the path to the root directory to hold the htmls and
       source files.
    output_dir_coverage (str): the path to the coverage/ in the output
       directory, e.g. /path/to/source_and_html_report/coverage/
    src_path (str): the path to the source code checkout src/, e.g.
       /b/tmp/build/cache/src/

  Returns:
    The relative path of the html file if it is copied; otherwise None.
  """
  html_absolute_path = os.path.join(html_file_dir, html_file_name)
  if not html_file_name.endswith(_HTML_SUFFIX):
    logging.warning('Not an html file: %s', html_absolute_path)
    return

  # The path relative to the src/. Here they are:
  #   /path/to/llvm_html_report/b/tmp/build/cache/src/base/at_exit.cc.html
  #   /path/to/llvm_html_report/b/tmp/build/cache/src/
  # So it is base/at_exit.cc.html
  html_relative_path = os.path.relpath(html_absolute_path, html_report_src_dir)

  # The path for the html file in the output directory. Here they are:
  #   /path/to/source_and_html_report/coverage/
  #   base/at_exit.cc.html
  # So it is /path/to/source_and_html_report/coverage/base/at_exit.cc.html
  html_destination_path = os.path.join(output_dir_coverage, html_relative_path)

  # How many levels up the html file is relative to the root of the html report.
  # Here they are:
  #   /path/to/llvm_html_report/
  #   /path/to/llvm_html_report/b/tmp/build/cache/src/base/
  # So it is six levels ../../../../../../
  original_html_relative_path = os.path.relpath(html_report_dir, html_file_dir)

  # How many levels up the html file is relative to the root of the output
  # directory. Here they are:
  #   /path/to/source_and_html_report/coverage/
  #   /path/to/source_and_html_report/coverage/base/at_exit.cc.html
  # So it is two levels ../../
  new_html_relative_path = os.path.relpath(
      output_dir_coverage, html_destination_path)
  #new_html_relative_path = os.path.relpath(
  #    output_dir, os.path.dirname(html_destination_path))

  # Update and then copy the html file.
  # TODO(crbug.com/910410): update in place and do a soft copy instead.
  with open(html_absolute_path, 'r') as f:
    html_content = f.read()
  new_html_content = html_content.replace(
      original_html_relative_path, new_html_relative_path
      ).replace(src_path, '/')
  with open(html_destination_path, 'w') as f:
    f.write(new_html_content)
  # _SOFT_COPY_FUNC(html_absolute_path, html_destination_path)

  # base/at_exit.cc.html  -->  base/at_exit.cc
  source_relative_path = html_relative_path[:-len(_HTML_SUFFIX)]
  # base/at_exit.cc  -->  /b/tmp/build/cache/src/base/at_exit.cc
  source_absolute_path = os.path.join(src_path, source_relative_path)
  if os.path.isfile(source_absolute_path):
    # base/at_exit.cc  -->
    # /path/to/source_and_html_report/coverage/base/at_exit.cc
    source_destination_path = os.path.join(
        output_dir_coverage, source_relative_path)
    _SOFT_COPY_FUNC(source_absolute_path, source_destination_path)
  else:
    logging.error('Source file not found: %s', source_relative_path)

  return html_relative_path


def _CopySourceAndHtmlReport(src_path, html_report_dir, output_dir):
  """Copies each source file and its html report to the given directory."""
  assert not os.listdir(output_dir), 'Output directory is not empty.'

  start_time = time.time()

  # Joining 'coverage' and '/path' becomes '/path' instead of 'coverage/path'.
  # TODO: For windows, this might not work, since src_path could be 'C://path'.
  html_report_src_dir = os.path.join(html_report_dir, 'coverage', src_path[1:])

  logging.info('Processing html report in %s', html_report_src_dir)

  dir_count = 0
  file_count = 0
  html_files = []
  output_dir_coverage = os.path.join(output_dir, 'coverage')
  for root, dirs, files in os.walk(html_report_src_dir):
    # Create directories.
    for d in dirs:
      dir_count += 1

      dir_relative_path = os.path.relpath(
          os.path.join(root, d), html_report_src_dir)
      os.makedirs(os.path.join(output_dir_coverage, dir_relative_path))

    # Copy files.
    for f in files:
      html_relative_path = _CopySourceAndHtmlFile(
          root, f, html_report_dir, html_report_src_dir,
          output_dir, output_dir_coverage, src_path)
      if not html_relative_path:
        continue

      html_files.append(html_relative_path)
      file_count += 1
      if file_count % 100 == 0:
        logging.info('Processed %d directories and %d files',
                     dir_count, file_count)
  logging.info('Processed %d directories and %d files', dir_count, file_count)

  # Copy other files other than the code coverage report html files, including
  # index.html, style.css, etc.
  index_html_name = 'index.html'
  for name in os.listdir(html_report_dir):
    path = os.path.join(html_report_dir, name)
    if os.path.isfile(path):
      if name != index_html_name:
        _SOFT_COPY_FUNC(path, os.path.join(output_dir, name))
      else:
        # We make a hard copy for the index file for updating as below.
        shutil.copy2(path, os.path.join(output_dir, name))

  # Update the path in the index.html file.
  index_html = os.path.join(output_dir, index_html_name)
  if not os.path.isfile(index_html):
    logging.error('No index.html detected')
    return 1

  with open(index_html, 'r') as f:
    index_content = f.read()
  new_index_content = index_content.replace(
      src_path, '').replace(src_path[1:], '/')
  with open(index_html, 'w') as f:
    f.write(new_index_content)

  minutes = (time.time() - start_time) / 60
  logging.info('Done in %.0f minutes', minutes)
  return 0


def _parse_args(args):
  parser = argparse.ArgumentParser(
      description='Copy (symbolic links on Linux) of source files and '
                  'their html-version coverage reports to the given directory')
  parser.add_argument(
      '--src-path',
      required=True,
      type=str,
      help='absolute path to the code checkout')
  parser.add_argument(
      '--html-report-dir',
      required=True,
      type=str,
      help='absolute path to the html report directory')
  parser.add_argument(
      '--output-dir',
      required=True,
      type=str,
      help='absolute path to the directory to host the source files and '
           'their html-version coverage reports')
  return parser.parse_args(args=args)


def main():
  params = _parse_args(sys.argv[1:])

  # Validate parameters
  if not os.path.isdir(params.src_path):
    raise RuntimeError(
        'Source code directory %s must exist' % params.src_path)

  if not os.path.isdir(params.html_report_dir):
    raise RuntimeError(
        'Html report directory %s must exist' % params.html_report_dir)

  if not os.path.isdir(params.output_dir):
    raise RuntimeError(
        'Output directory %s must exist' % params.output_dir)

  return _CopySourceAndHtmlReport(
      params.src_path, params.html_report_dir, params.output_dir)


if __name__ == '__main__':
  logging.basicConfig(
      format='[%(asctime)s %(levelname)s] %(message)s', level=logging.INFO)
  sys.exit(main())
