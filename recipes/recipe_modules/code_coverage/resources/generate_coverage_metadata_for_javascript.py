# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Script to generate JavaScript coverage metadata file.

The code coverage data format is defined at:
https://chromium.googlesource.com/infra/infra/+/refs/heads/master/appengine/findit/model/proto/code_coverage.proto
"""

import argparse
import fnmatch
import json
import logging
import os
import sys


def get_json_coverage_files(json_dir):
  """Gets all JSON coverage files from directory.

  Args:
    dir: Directory in which to search for JSON files.

  Returns:
    A list of absolute paths to the JSON files that match.
  """
  files = []
  for filename in os.listdir(json_dir):
    if fnmatch.fnmatch(filename, '*.json'):
      files.append(os.path.join(json_dir, filename))

  return files


def get_coverage_data_and_paths(src_checkout, coverage_file_path):
  """Returns coverage data and make source paths absolute

  Args:
    src_checkout: The absolute path to the checkout of
      source files, used to make the return paths
      absolute.
    coverage_file_path: The absolute path to the code
      coverage JSON file. The file contains a JSON
      object with keys pertaining to file paths
      relative to the checkout src.

  Returns:
    A dictionary with keys being absolute paths to the
    source file and values being the coverage data.

  Raises:
    If one of the source paths in the |coverage_file_path|
    does not exist, raise an exception and fail immediately.
  """
  with open(coverage_file_path) as f:
    coverage_data = json.load(f)
    source_files_and_coverage_data = {}

    for file_path in coverage_data.keys():
      relative_file_path = file_path.replace('//', '')
      absolute_file_path = os.path.join(src_checkout, relative_file_path)

      if not os.path.exists(absolute_file_path):
        raise Exception('Identified source path %s does not exist' %
                        absolute_file_path)

      source_files_and_coverage_data[absolute_file_path] = coverage_data[
          file_path]

    return source_files_and_coverage_data


def convert_coverage_to_line_column_format(absolute_source_file_path,
                                           coverage_data):
  """Convert the v8 coverage to the code_coverage.proto format

  Coverage is merged by //testing/merge_scripts/code_coverage/merge_js_lib.py
  script and the result is contiguous blocks with invocation counts. The format
  described code_coverage.proto requires coverage in line with their invocation
  counts and uncovered blocks.

  This conversion does lose some information such as different invocation
  counts within the same line. For example:

    const isValid = (isTruthy) ? 'valid' : 'invalid';
    <------------- 4 ----------><--- 1 --><--- 4 --->

  The above coverage could be constructed by calling isValid(false) 4 times,
  followed by isValid(true) 1 time. However the code_coverage.proto format will
  simply show line invocation count of 4 or 1. The larger value has been
  arbitrarily chosen.

  Args:
    absolute_source_file_path: The absolute file path to the source that the
      coverage data is repoted on.
    coverage_data: The coverage data as a dictionary read from the merged
      output.

  Returns:
    lines: List of python dictionaries which define line ranges and their
      invocation counts contiguously as follows;
      {
        count: Invocation count for this line range
        first: First line that has this invocation
        last: Last line that has this invocation count
      }
    uncovered_blocks: A list of python dictionaries which define blocks of code
      that have not been invoked as follows:
      {
        line: The line number containing the uncovered block
        ranges: List of character offsets (inclusive) defining an uncovered
          block
      }

  Raises:
    If identified coverage blocks extend past the bounds of the source file
      offsets.
  """
  logging.info('Converting v8 coverage format for file: %s' %
               absolute_source_file_path)

  with open(absolute_source_file_path) as f:
    line_num = 0
    lines = []
    uncovered_blocks = []

    # Character offsets that define the absolute start
    # offset and absolute end offset for the current line
    # with the start of the file having offset 0.
    # This is worked out as the line_start_offset + the
    # current lines character count excluding the new line
    # characters.
    line_start_offset = 0
    line_end_offset = 0

    if not coverage_data:
      raise Exception('No coverage data supplied for file')

    # Character offsets that define the start and end of a
    # block of coverage data. These offsets are sourced after
    # the merge script here:
    #   //testing/merge_scripts/code_coverage/merge_js_lib.py
    # These offsets can cover multiple lines.
    coverage_block = coverage_data.pop(0)
    coverage_start_offset = 0
    coverage_end_offset = coverage_block['end']
    coverage_count = coverage_block['count']

    def _add_uncovered_block(coverage_start_offset, coverage_end_offset,
                             line_start_offset, line_end_offset):
      # TODO(benreich): Implement adding of an uncovered block of code
      pass

    def _append_or_extend_previous_line_range(line_num, coverage_count):
      # TODO(benreich): Implement extending a line range that has already
      #   been added to the list of lines.
      pass

    def _is_coverage_within_line_range(coverage_start_offset,
                                       coverage_end_offset, line_start_offset,
                                       line_end_offset):
      """Identifies if the coverage block is within the supplied line

      There are 4 possible scenarios where the coverage block offsets reside
      within the line offsets.

      1. Encapsulating.
         Coverage extends before and after line offsets.

           [--------------] <- coverage_{start,end}_offset
              [-------]     <-     line_{start,end}_offset

      2. Overlaps line start.
         Coverage beings before the line offset starts and finishes before the
         line offset ends.

           [----------]     <- coverage_{start,end}_offset
                  [-------] <-     line_{start,end}_offset

      3. Overlaps line end.
         Coverage begings after the line offsets starts and finishes after the
         line offset ends.

               [----------] <- coverage_{start,end}_offset
           [-------]        <-     line_{start,end}_offset

      4. Nested.
         Coverage starts and ends within the line start and end offsets.
               [------]     <- coverage_{start,end}_offset
           [--------------] <-     line_{start,end}_offset

      Args:
        coverage_start_offset: The absolute character offset that starts the
          coverage block (inclusive).
        coverage_end_offset: The absolute character offset that ends the
          coverage block (exclusive).
        line_start_offset: The absolute character offset that starts the
          current line (inclusive).
        line_end_offset: The absolute character offset that ends the
          current line (inclusive).

      Returns:
        Boolean: True if coverage block is within the bounds of the supplied
          line offsets, false otherwise.
      """
      # Encapsulating.
      if line_start_offset >= coverage_start_offset and \
          line_end_offset < coverage_end_offset:
        return True

      # Overlaps line start.
      if (line_start_offset >= coverage_start_offset and line_start_offset <
          coverage_end_offset) and line_end_offset >= coverage_end_offset:
        return True

      # Overlaps line end.
      if (coverage_start_offset >= line_start_offset and coverage_start_offset <
          line_end_offset) and coverage_end_offset >= line_end_offset:
        return True

      # Nested
      if coverage_start_offset >= line_start_offset and \
          coverage_end_offset < line_end_offset:
        return True

      return False

    for line in f:
      line_num += 1
      line_start_offset = line_end_offset
      line_end_offset = line_start_offset + len(line)

      # Multiple coverage blocks may exist for a single line of
      # code, keep popping the blocks until the coverage block
      # ends after the currently enumerated line.
      while coverage_end_offset < line_end_offset:
        if coverage_count == 0:
          _add_uncovered_block(coverage_start_offset, coverage_end_offset,
                               line_start_offset, line_end_offset)
        else:
          _append_or_extend_previous_line_range(line_num, coverage_count)

        if not coverage_data:
          raise Exception(
              'Source file still has characters without coverage data, final '
              'coverage block must match total characters in source file'
          )

        coverage_block = coverage_data.pop(0)
        # Use the previous coverage block end offset to
        # start the next coverage block.
        coverage_start_offset = 0 if not coverage_block else coverage_end_offset
        coverage_end_offset = coverage_block['end']
        coverage_count = coverage_block['count']

      if coverage_count == 0:
        _add_uncovered_block(coverage_start_offset, coverage_end_offset,
                             line_start_offset, line_end_offset)
      elif _is_coverage_within_line_range(coverage_start_offset,
                                          coverage_end_offset,
                                          line_start_offset, line_end_offset):
        _append_or_extend_previous_line_range(line_num, coverage_count)

    if coverage_end_offset != line_end_offset:
      # This may occur due to a difference between the source and the
      # bundled JavaScript. This may cause a mismatch in source line offsets
      # and the recorded coverage offsets. Please see crbug.com/1152612.
      raise Exception(
          'The coverage_end_offset (%s) does not match the line_end_offset (%s)'
          % (coverage_end_offset, line_end_offset))

    # Make sure last line coverage is used
    if coverage_count == 0:
      _add_uncovered_block(coverage_start_offset, coverage_end_offset,
                           line_start_offset, line_end_offset)
    else:
      _append_or_extend_previous_line_range(line_num, coverage_count)

    return lines, uncovered_blocks


def _parse_args(args):
  """Parses the arguments.

  Args:
    args: The passed arguments.

  Returns:
    The parsed arguments as parameters.
  """
  parser = argparse.ArgumentParser(
      description='Generate the JavaScript coverage metadata')
  parser.add_argument(
      '--src-path',
      required=True,
      type=str,
      help='absolute path to the code checkout')
  parser.add_argument(
      '--output-dir',
      required=True,
      type=str,
      help='absolute path to the directory to write the metadata, must exist')
  parser.add_argument(
      '--coverage-dir',
      required=True,
      type=str,
      help='absolute path to the directory that contains merged JavaScript '
      'coverage data')
  parser.add_argument(
      '--dir-metadata-path',
      type=str,
      help='absolute path to json file mapping dirs to metadata')
  params = parser.parse_args(args=args)

  if params.dir_metadata_path and not os.path.isfile(params.dir_metadata_path):
    parser.error('Dir metadata %s is missing' % params.dir_metadata_path)

  return params


def main():
  params = _parse_args(sys.argv[1:])

  component_mapping = None
  if params.dir_metadata_path:
    with open(params.dir_metadata_path) as f:
      component_mapping = {
          d: md['monorail']['component']
          for d, md in json.load(f)['dirs'].iteritems()
          if 'monorail' in md and 'component' in md['monorail']
      }

  assert component_mapping, (
      'component_mapping (for full-repo coverage) must be specified')

  coverage_files = get_json_coverage_files(params.coverage_dir)
  if not coverage_files:
    raise Exception('No coverage file found under %s' % params.coverage_dir)
  logging.info('Found coverage files: %s', str(coverage_files))

  coverage_by_absolute_path = {}
  for file_path in coverage_files:
    source_files_and_coverage_data = get_coverage_data_and_paths(
        params.src_path, file_path)

    for absolute_source_path, coverage in source_files_and_coverage_data.items(
    ):
      if absolute_source_path in coverage_by_absolute_path:
        raise Exception(
            'Duplicate source file %s found, merging during this step '
            'not supported' % absolute_source_path)

      covered_lines, uncovered_blocks = convert_coverage_to_line_column_format(
          absolute_source_path, coverage)
      coverage_by_absolute_path[absolute_source_path] = {
          'lines': covered_lines,
          'uncovered_blocks': uncovered_blocks,
      }

  if not coverage_by_absolute_path:
    raise Exception('No source files found')
  logging.info('Found source files: %s', str(coverage_by_absolute_path.keys()))

  # TODO(benreich): Finish off the extra information required for the format.
  #   - Add directory level summaries.
  #   - Add component level summaries.


if __name__ == '__main__':
  logging.basicConfig(
      format='[%(asctime)s %(levelname)s] %(message)s', level=logging.INFO)
  sys.exit(main())
