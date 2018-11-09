#!/usr/bin/python
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This script generates the json data of the code coverage using llvm-cov."""

import argparse
import collections
import json
import logging
import os
import psutil
import subprocess
import sys
import time
import zlib


def _extract_coverage_info(segments):
  """Returns the line and sub-line block coverage info based on the segments.

  Args:
    segments(list): refer to function `_to_file_record` below on the detail.

  Returns:
    A tuple (lines, uncovered_blocks).
    lines (dict): A mapping from line number to how many executions the line is.
    uncovered_blocks(dict(list)): A mapping from line number to a list of
        sub-line blocks where the code is not covered. A block is represented by
        two integers [start_column, end_column].
  """
  # Maps a line number to its hit count.
  line_data = {}
  # Maps a line number to its uncovered sub-line blocks.
  # line# --> list([start_column, end_column])
  block_data = collections.defaultdict(list)

  stack = []
  for segment in segments:
    if segment[4]:  # Start of a region.
      stack.append(segment)
      continue

    # End of a region.
    if len(stack) == 0:
      # TODO(crbug.com/902397): some region doesn't have a beginning segment.
      continue

    start = stack.pop()

    # Check whether it is an uncovered sub-line block.
    if start[0] == segment[0] and start[2] == 0:
      block_data[start[0]].append([start[1], segment[1]])

    # Set line counts for all lines in the region from start[0] to segment[0].
    i = start[0]
    while i <= segment[0]:
      if i not in line_data:
        if start[3]:
          line_data[i] = start[2]
        else:
          line_data[i] = -1
        line_data[i] = start[2]
      i += 1

  #assert len(stack) == 0, "Some regions still open!"
  return line_data, block_data,


def _to_flat_format(line_data, block_data):
  """Turns output of `_extract_coverage_info` to a flat format."""
  lines = []
  for line, count in line_data:
    info = {
        'line': line,
        'count': count,
        # Clang doesn't support if/else branches.
        # 'total_branches': -1,
        # 'covered_branches': -1,
    }
    uncovered_blocks = block_data.get(line)
    if uncovered_blocks:
      info['uncovered_blocks'] = uncovered_blocks
    lines.append(info)
  return lines


def _to_compressed_format(line_data, block_data):
  """Turns output of `_extract_coverage_info` to a compressed format."""
  lines = []
  # Aggregate contiguous blocks of lines with the exact same hit count.
  last_index = 0
  for i in xrange(1, len(line_data) + 1):
    if (i >= len(line_data) or
        line_data[i][1] != line_data[last_index][1]):
      lines.append({
          'first': line_data[last_index][0],
          'last': line_data[i - 1][0],
          'count': line_data[last_index][1],
      })
      last_index = i

  uncovered_blocks = []
  for line_number in sorted(block_data.keys()):
    ranges = []
    for start, end in block_data[line_number]:
      ranges.append({
          'first': start,
          'last': end,
      })
    uncovered_blocks.append({
        'line': line_number,
        'ranges': ranges,
    })

  return lines, uncovered_blocks


def _to_file_record(src_path, file_coverage_data, compressed_format):
  """Converts the given file coverage data to line-based coverage info.

  Args:
    src_path (str): The absolute path to the root directory of the checkout.
    file_coverage_data (dict): The file coverage data from clang with format
      {
        "segments": [[3, 26, 1, True, True], ...],
        "summary": {
          "lines": {
            "count": 55,
          }
        },
        "filename": "/absolute/path/to/source.cc",
      }
      Each segment is another list with five values in the following order:
        /// The line where this segment begins.
        unsigned Line;
        /// The column where this segment begins.
        unsigned Col;
        /// The execution count, or zero if no count was recorded.
        uint64_t Count;
        /// When false, the segment was uninstrumented or skipped.
        bool HasCount;
        /// Whether this enters a new region or returns to a previous count.
        bool IsRegionEntry;
    compressed_format (bool): indicate whether the compressed format is used.

  Returns:
    A json containing the coverage info for the given file.
  """
  segments = file_coverage_data['segments']
  if not segments:
    return None

  filename = file_coverage_data['filename']
  src_file = os.path.relpath(filename, src_path)
  # TODO(crbug.com/902397): some region doesn't have a beginning segment.
  # assert len(segments) % 2 == 0, "segments should be even"

  line_data, block_data = _extract_coverage_info(segments)

  # TODO(crbug.com/902404): for per-CL coverage, we need to map the line numbers
  # of a file in the bot to the line numbers of the same file on Gerrit, because
  # the base revisions are different.
  line_data = sorted(line_data.items(), key=lambda x: x[0])

  if not compressed_format:
    return {
        'path': src_file,
        'total_lines': file_coverage_data['summary']['lines']['count'],
        'lines': _to_flat_format(line_data, block_data),
    }
  else:
    lines, uncovered_blocks = _to_compressed_format(line_data, block_data)
    data = {
        'path': src_file,
        'total_lines': file_coverage_data['summary']['lines']['count'],
        'lines': lines,
    }
    if uncovered_blocks:
      data['uncovered_blocks'] = uncovered_blocks
    return data


def _compute_llvm_args(
    profdata_path, llvm_cov_path, binaries, sources, output_dir):
  args = [llvm_cov_path, 'export', '-instr-profile', profdata_path,
          binaries[0]]
  for b in binaries[1:]:
    args.append('-object')
    args.append(b)
  args.extend(sources or [])
  return args


def _get_coverage_data_in_json(
    profdata_path, llvm_cov_path, binaries, sources, output_dir):
  """Returns a json object of the coverage info."""
  coverage_json_file = os.path.join(output_dir, 'coverage.json')
  p = None
  try:
    with open(coverage_json_file, 'w') as f:
      args = _compute_llvm_args(
          profdata_path, llvm_cov_path, binaries, sources, output_dir)
      p = subprocess.Popen(args, stdout=f)
      proc = None
      try:
        proc = psutil.Process(p.pid)
      except psutil.Error:  # The process might already finish.
        pass

      min_duration_seconds = 5
      max_duration_seconds = 10 * 60  # 10 minutes
      duration_seconds = min_duration_seconds
      while p.poll() is None:
        if proc is not None:
          try:
            logging.info('Thread numbers: %d', proc.num_threads())

            # Dump the memory, cpu, and disk io usage of the process.
            p_mem = proc.memory_info()
            if p_mem.shared:
              shared_mem = '%.2fG' % (p_mem.shared*1.0/1024/1024/1024)
            else:
              shared_mem = 'N/A'
            logging.info('llvm-cov Memory: '
                         'RSS=%.2fG,  VMS=%.2fG, shared=%s',
                         p_mem.rss/1024./1024/1024,
                         p_mem.vms/1024./1024/1024,
                         shared_mem)

            p_cpu_times = proc.cpu_times()
            cpu_percent = proc.cpu_percent(interval=1)
            logging.info('llvm-cov CPU: '
                         'user=%.2f hours, sys=%.2f hours, percent=%.2f%%',
                         p_cpu_times.user/60./60,
                         p_cpu_times.system/60./60,
                         cpu_percent)

            os_disk_io = psutil.disk_io_counters()
            logging.info('OS-level disk io: write=%.2fG, read=%.2fG',
                         os_disk_io.write_bytes/1024./1024/1024,
                         os_disk_io.read_bytes/1024./1024/1024)
            p_disk_io = proc.io_counters()
            logging.info('llvm-cov disk io: write=%.2fG, read=%.2fG',
                         p_disk_io.write_bytes/1024./1024/1024,
                         p_disk_io.read_bytes/1024./1024/1024)
          except psutil.Error:  # The process might already finish.
            pass

        logging.info('waiting %d seconds...', duration_seconds)
        time.sleep(duration_seconds)
        duration_seconds = min(duration_seconds * 2, max_duration_seconds)

    if p.returncode == 0:
      with open(coverage_json_file, 'r') as f:
        return json.load(f)
  finally:
    # Delete the coverage.json, because it could be huge.
    # Keep it for now for testing/debug purpose.
    # os.remove(coverage_json_file)
    # Wait for llvm in case the above code ran into uncaught exceptions.
    if p is not None:
      if p.wait() != 0:
        sys.exit(p.returncode)


def _generate_metadata(src_path, output_dir, profdata_path, llvm_cov_path,
                       binaries, sources):
  sources = sources or []
  sources = [os.path.join(src_path, s) for s in sources]

  logging.info('Generating coverage.json ...')
  start_time = time.time()
  data = _get_coverage_data_in_json(
      profdata_path, llvm_cov_path, binaries, sources, output_dir)
  minutes = (time.time() - start_time) / 60
  logging.info('Generating & loading coverage.json with "llvm-cov export" '
               'took %.0f minutes',  minutes)

  logging.info('Processing coverage data ...')
  start_time = time.time()
  compressed_files = []
  flat_files = []
  for datum in data['data']:
    for file_data in datum['files']:
      compressed_files.append(
          _to_file_record(src_path, file_data, compressed_format=True))
      flat_files.append(
          _to_file_record(src_path, file_data, compressed_format=False))
  minutes = (time.time() - start_time) / 60
  logging.info('Processing coverage data took %.0f minutes', minutes)

  compressed_data = {
      'files': compressed_files,
  }
  flat_data = {
      'files': flat_files,
  }

  logging.info('Dumping aggregated data ...')
  start_time = time.time()
  with open(os.path.join(output_dir, 'compressed.json.gz'), 'w') as f:
    f.write(zlib.compress(json.dumps(compressed_data)))
  with open(os.path.join(output_dir, 'flat.json.gz'), 'w') as f:
    f.write(zlib.compress(json.dumps(flat_data)))
  minutes = (time.time() - start_time) / 60
  logging.info('Dumping aggregated data took %.0f minutes', minutes)


def _parse_args(args):
  parser = argparse.ArgumentParser(
      description='Generate the coverage data in metadata format')
  parser.add_argument(
      '--src-path', required=True, type=str,
      help='absolute path to the code checkout')
  parser.add_argument(
      '--output-dir', required=True, type=str,
      help='absolute path to the directory to store the metadata, must exist')
  parser.add_argument(
      '--profdata-path', required=True, type=str,
      help='absolute path to the merged profdata')
  parser.add_argument(
      '--llvm-cov', required=True, type=str,
      help='absolute path to llvm-cov executable')
  parser.add_argument(
      '--binaries', nargs='+', type=str,
      help='absolute path to binaries to generate the coverage for')
  parser.add_argument(
      '--sources', nargs='*', type=str,
      help='the source files to generate the coverage for, path should be '
           'relative to the root of the code checkout')
  return parser.parse_args(args=args)


def main():
  params = _parse_args(sys.argv[1:])

  # Validate parameters
  if not os.path.exists(params.output_dir):
    raise RuntimeError('Output directory %s must exist'
                       % params.output_dir)

  if not os.path.isfile(params.llvm_cov) or not os.access(
      params.llvm_cov, os.X_OK):
    raise RuntimeError('%s must exist and be executable' % params.llvm_cov)

  if not os.path.exists(params.profdata_path):
    raise RuntimeError('Input data %s missing' % params.profdata_path)

  _generate_metadata(params.src_path, params.output_dir, params.profdata_path,
                     params.llvm_cov, params.binaries, params.sources)


if __name__ == '__main__':
  logging.basicConfig(format='[%(asctime)s %(levelname)s] %(message)s',
                      level=logging.INFO)
  sys.exit(main())
