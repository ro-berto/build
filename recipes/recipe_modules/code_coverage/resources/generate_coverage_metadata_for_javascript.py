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
import zlib

import aggregation_util
import repository_util


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
      """Adds uncovered code block to |uncovered_blocks|

      If the supplied coverage offsets extend before or after the supplied
      line offsets, only add a coverage block for the current line. If the
      line is already under consideration (i.e. multiple disjoint uncovered
      blocks exist on the same line) then append to the ranges array for
      the last line added to |uncovered_blocks|.

      Args:
        coverage_start_offset: The uncovered coverage block start
          character offset (inclusive)
        coverage_end_offset: The uncovered coverage block end character
          offset (exclusive)
        line_start_offset: The absolute character offset for the start
          off the current line. (inclusive)
        line_end_offset: The absolute character offset for the end
          off the current line. (inclusive)
      """
      uncovered_block_start = max(coverage_start_offset,
                                  line_start_offset) - line_start_offset
      uncovered_block_end = min(coverage_end_offset,
                                line_end_offset) - line_start_offset
      uncovered_block = None

      if uncovered_blocks and uncovered_blocks[-1]['line'] == line_num:
        uncovered_block = uncovered_blocks.pop()
      else:
        uncovered_block = {'line': line_num, 'ranges': []}

      uncovered_block['ranges'].append({
          'first': uncovered_block_start,
          'last': uncovered_block_end
      })
      uncovered_blocks.append(uncovered_block)

    def _append_or_extend_previous_line_range(line_num, coverage_count):
      """Extends the last added line range identified

      If the last line added to |lines| has the same coverage count
      as the supplied line, extend the last value on the final
      element in |lines|. Otherwise, append a new line.

      If the last line added to |lines| and the supplied |line_num|
      have a gap, append a line range of 0 count from last line + 1
      up until |line_num| - 1 to indicate instrumented but not
      invoked line range. This line range will match up with a
      corresponding uncovered_block.

      Args:
        line_num: The current line number
        coverage_count: Invocation count for |line_num|
      """
      if lines and line_num == lines[-1]['last'] + 1 \
          and lines[-1]['count'] == coverage_count:
        # Extend previous LineRange by one line.
        lines[-1]['last'] = line_num
      elif lines and line_num == lines[-1]['last'] \
          and lines[-1]['count'] < coverage_count:
        if lines[-1]['last'] > lines[-1]['first']:
          # LineRange extends across multiple lines
          # break it up instead of changing count.
          lines[-1]['last'] = line_num - 1
          lines.append({
              'first': line_num,
              'last': line_num,
              'count': coverage_count
          })
        else:
          # Larger coverage found on same line, use
          # higher count.
          lines[-1]['count'] = coverage_count
      elif lines and line_num == lines[-1]['last'] \
          and lines[-1]['count'] >= coverage_count:
        # Same or smaller count identified on same line, discard.
        return
      else:
        if lines and lines[-1]['last'] < line_num - 1:
          # Pad lines with 0 count LineRange up to the
          # current line.
          lines.append({
              'first': lines[-1]['last'] + 1,
              'last': line_num - 1,
              'count': 0
          })

        # Start new LineRange.
        lines.append({
            'first': line_num,
            'last': line_num,
            'count': coverage_count
        })

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
              'coverage block must match total characters in source file')

        coverage_block = coverage_data.pop(0)
        # Use the previous coverage block end offset to
        # start the next coverage block.
        coverage_start_offset = coverage_end_offset
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


def get_line_coverage_metric_summary(lines):
  """Get line coverage summary metric for supplied lines

  Args:
    lines: A list of LineRange's which are sourced from the
      |convert_coverage_to_line_column_format| method.
  
  Returns:
    A dictionary containing the summary of line coverage
    which is defined as:
    {
      name: Hardcoded to 'line'.
      total: Number of instrumented lines in the file
        which should always be the number of lines in
        JavaScript coverage.
      covered: Number of lines with invocation count >0.
    }
  """
  line_coverage_metric = {}
  line_coverage_metric['name'] = 'line'
  line_coverage_metric['total'] = 0
  line_coverage_metric['covered'] = 0

  for line_range in lines:
    # First and last are inclusive line numbers.
    lines_in_range = line_range['last'] - line_range['first'] + 1

    if line_range['count'] > 0:
      line_coverage_metric['covered'] += lines_in_range

    line_coverage_metric['total'] += lines_in_range

  return line_coverage_metric


def get_files_coverage_data(src_path, coverage_files):
  """Extract and convert coverage data to required format.

  Takes in a coverage file which contains the merged v8 coverage
  format and return back a list of files which conform to the
  File message type.

  Args:
    src_path: The absolute path to the source files checkout.
    coverage_files: A list of files containing merged coverage.

  Returns:
    List of File dictionaries defined as:
    {
      lines: List of lines and their invocation counts.
      uncovered_blocks: Blocks of code uncovered by coverage.
      path: Path to source file relative to src checkout.
      summaries: Summary of metric data for the file.
    }

  Raises:
    Exception: If 2+ coverage files contain the same source file
      which may happen if tests for source files are sharded
      over different builders.
  """
  files_coverage_data = []
  files_seen = set()

  for file_path in coverage_files:
    source_files_and_coverage_data = get_coverage_data_and_paths(
        src_path, file_path)

    for absolute_source_path, coverage in source_files_and_coverage_data.items(
    ):
      if absolute_source_path in files_seen:
        # TODO(benreich): Allow for merging of duplicate coverage data.
        #   This may occur when tests are sharded and 2 tests covering
        #   the same file is on 2 different shards.
        raise Exception(
            'Duplicate source file %s found, merging during this step '
            'not supported' % absolute_source_path)

      files_seen.add(absolute_source_path)
      covered_lines, uncovered_blocks = convert_coverage_to_line_column_format(
          absolute_source_path, coverage)
      files_coverage_data.append({
          'lines': covered_lines,
          'uncovered_blocks': uncovered_blocks,
          'path': '//' + os.path.relpath(absolute_source_path, src_path),
          'summaries': [get_line_coverage_metric_summary(covered_lines)],
      })

  return files_coverage_data


def generate_json_coverage_metadata(coverage_dir, src_path, component_mapping):
  """Generate a JSON output representing JavaScript code coverage.

  JSON format conforms to the proto:
  //infra/appengine/findit/model/proto/code_coverage.proto

  Args:
    coverage_dir: Absolute path that contains merged v8 coverage reports.
    src_path: The absolute path to the source files checkout.
    component_mapping: Mapping of monorail component to directory.

  Returns:
    JSON format coverage metadata.
  """
  coverage_files = get_json_coverage_files(coverage_dir)
  if not coverage_files:
    raise Exception('No coverage file found under %s' % coverage_dir)
  logging.info('Found coverage files: %s', str(coverage_files))

  data = {}
  data['files'] = get_files_coverage_data(src_path, coverage_files)

  if not data['files']:
    raise Exception('No coverage data associated with source files found.')

  # Add git revision and timestamp per source file.
  repository_util.AddGitRevisionsToCoverageFilesMetadata(
      data['files'], src_path, 'DEPS')

  logging.info('Adding directories and components coverage data ...')

  per_directory_coverage_data, per_component_coverage_data = (
      aggregation_util.get_aggregated_coverage_data_from_files(
          data['files'], component_mapping))

  data['components'] = None
  data['dirs'] = None
  if per_component_coverage_data:
    data['components'] = per_component_coverage_data.values()
  if per_directory_coverage_data:
    data['dirs'] = per_directory_coverage_data.values()
    data['summaries'] = per_directory_coverage_data['//']['summaries']

  return data


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

  data = generate_json_coverage_metadata(params.coverage_dir, params.src_path,
                                         component_mapping)

  logging.info('Writing fulfilled JavaScript coverage metadata to %s',
               params.output_dir)
  with open(os.path.join(params.output_dir, 'all.json.gz'), 'w') as f:
    f.write(zlib.compress(json.dumps(data)))


if __name__ == '__main__':
  logging.basicConfig(
      format='[%(asctime)s %(levelname)s] %(message)s', level=logging.INFO)
  sys.exit(main())
