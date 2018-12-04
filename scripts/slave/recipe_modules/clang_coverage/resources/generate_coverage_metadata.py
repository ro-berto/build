#!/usr/bin/python
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This script generates the json data of the code coverage using llvm-cov."""

import argparse
import collections
import copy
import json
import logging
import os
import psutil
import stat
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
      # If the line already exists, it means that an inner region includes the
      # line, and coverage info of inner region should be the true coverage for
      # the line.
      if i not in line_data:
        # If the line is uncoverable or uninstrumented, or skipped (a function
        # in a header file that is not used in all source files), we record it
        # as negative value -1; otherwise, we record the actual execution count
        # (either 0 or a positive value).
        if start[3]:
          line_data[i] = start[2]
        else:
          line_data[i] = -1
      i += 1

  #assert len(stack) == 0, "Some regions still open!"
  return line_data, block_data,


def _to_compressed_format(line_data, block_data):
  """Turns output of `_extract_coverage_info` to a compressed format."""
  lines = []
  # Aggregate contiguous blocks of lines with the exact same hit count.
  last_index = 0
  for i in xrange(1, len(line_data) + 1):
    if (i >= len(line_data) or line_data[i][1] != line_data[last_index][1]):
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


def _rebase_line_and_block_data(line_data, block_data, line_mapping):
  """Rebases the line numbers of the data according to the diff mapping.

  If the file is not in the mapping, then this function is non-op.

  Args:
    line_data: A list of tuples consists of line number and and how many
               executions the line is.
    block_data: A mapping from line number to a list of sub-line blocks where
                the code is not covered. A block is represented by two integers
                [start_column, end_column].
    line_mapping: A map that maps from local diff's line number to Gerrit diff's
                  line number as well as the line itself.

  Returns:
    A tuple of line_data and block with line numbers being rebased.
  """
  rebased_line_data = []
  for line_num, count in line_data:

    if str(line_num) not in line_mapping:
      continue

    rebased_line_num = line_mapping[str(line_num)][0]
    rebased_line_data.append((rebased_line_num, count))

  rebased_block_data = {}
  for line_num, subline_blocks in block_data.iteritems():
    if str(line_num) not in line_mapping:
      continue

    rebased_line_num = line_mapping[str(line_num)][0]
    rebased_block_data[rebased_line_num] = subline_blocks

  return rebased_line_data, rebased_block_data


def _to_compressed_file_record(src_path, file_coverage_data, diff_mapping=None):
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
    diff_mapping: A map whose key is a file name that is relative to the source
                  root, and the corresponding value is another map that maps
                  from local diff's line number to Gerrit diff's line number as
                  well as the line itself.

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
  line_data = sorted(line_data.items(), key=lambda x: x[0])
  if diff_mapping and src_file in diff_mapping:
    line_mapping = diff_mapping[src_file]
    line_data, block_data = _rebase_line_and_block_data(line_data, block_data,
                                                        line_mapping)

  lines, uncovered_blocks = _to_compressed_format(line_data, block_data)
  data = {
      'path': src_file,
      'total_lines': file_coverage_data['summary']['lines']['count'],
      'lines': lines,
  }
  if uncovered_blocks:
    data['uncovered_blocks'] = uncovered_blocks
  return data


def _compute_llvm_args(profdata_path, llvm_cov_path, binaries, sources,
                       output_dir, cpu_count, no_sharded_output):
  args = [
      llvm_cov_path,
      'export',
  ]

  shard_file_dir = None
  if not no_sharded_output:
    shard_file_dir = os.path.join(output_dir, 'shards')
    args.extend([
        '-output-dir',
        shard_file_dir,
        '-num-threads',
        str(cpu_count),
    ])

  args.extend(['-instr-profile', profdata_path, binaries[0]])
  for b in binaries[1:]:
    args.append('-object')
    args.append(b)
  args.extend(sources or [])

  return args, shard_file_dir


def _show_system_resource_usage(proc):
  if proc is None:
    return

  def bytes_to_gb(num):
    if num is None:
      return 'N/A'
    else:
      return '%.2fG' % (num / 1024.0 / 1024 / 1024)

  # Dump the memory, cpu, and disk io usage of the process.
  try:
    logging.info('Thread numbers: %d', proc.num_threads())

    p_mem = proc.memory_info()
    logging.info('llvm-cov Memory: '
                 'RSS=%s,  VMS=%s, shared=%s', bytes_to_gb(p_mem.rss),
                 bytes_to_gb(p_mem.vms), bytes_to_gb(p_mem.shared))

    os_vm = psutil.virtual_memory()
    logging.info(
        'OS virtual Memory: '
        'available=%s, used=%s, free=%s, cached=%s, shared=%s',
        bytes_to_gb(os_vm.available), bytes_to_gb(os_vm.used),
        bytes_to_gb(os_vm.free), bytes_to_gb(os_vm.cached),
        bytes_to_gb(os_vm.shared))

    os_sm = psutil.swap_memory()
    logging.info('OS swap: '
                 'used=%s, free=%s', bytes_to_gb(os_sm.used),
                 bytes_to_gb(os_sm.free))

    p_cpu_times = proc.cpu_times()
    cpu_percent = proc.cpu_percent(interval=1)
    logging.info(
        'llvm-cov CPU: '
        'user=%.2f hours, sys=%.2f hours, percent=%.2f%%',
        p_cpu_times.user / 60. / 60, p_cpu_times.system / 60. / 60, cpu_percent)

    os_disk_io = psutil.disk_io_counters()
    logging.info('OS-level disk io: write=%s, read=%s',
                 bytes_to_gb(os_disk_io.write_bytes),
                 bytes_to_gb(os_disk_io.read_bytes))
    p_disk_io = proc.io_counters()
    logging.info('llvm-cov disk io: write=%s, read=%s',
                 bytes_to_gb(p_disk_io.write_bytes),
                 bytes_to_gb(p_disk_io.read_bytes))
  except psutil.Error:  # The process might already finish.
    pass


def _get_coverage_data_in_json(profdata_path, llvm_cov_path, binaries, sources,
                               output_dir, no_sharded_output):
  """Returns a json object of the coverage info."""
  coverage_json_file = os.path.join(output_dir, 'coverage.json')
  error_out_file = os.path.join(output_dir, 'llvm_cov.stderr.log')
  p = None
  try:
    # Use as many cpu cores as possible for parallel processing of huge data.
    # Leave 5 cpu cores out for other processes in the bot.
    cpu_count = max(10, psutil.cpu_count() - 5)

    with open(coverage_json_file, 'w') as f_out, open(error_out_file,
                                                      'w') as f_error:
      args, shard_file_dir = _compute_llvm_args(profdata_path, llvm_cov_path,
                                                binaries, sources, output_dir,
                                                cpu_count, no_sharded_output)
      p = subprocess.Popen(args, stdout=f_out, stderr=f_error)
      llvm_cov_proc = None
      try:
        llvm_cov_proc = psutil.Process(p.pid)
      except psutil.Error:  # The process might already finish.
        pass

      min_duration_seconds = 5
      max_duration_seconds = 5 * 60  # 5 minutes
      duration_seconds = min_duration_seconds

      while p.poll() is None:
        _show_system_resource_usage(llvm_cov_proc)
        logging.info('-----------------waiting %d seconds...', duration_seconds)
        time.sleep(duration_seconds)
        duration_seconds = min(duration_seconds * 2, max_duration_seconds)

  finally:
    # Delete the coverage.json, because it could be huge.
    # Keep it for now for testing/debug purpose.
    # os.remove(coverage_json_file)
    # Wait for llvm in case the above code ran into uncaught exceptions.
    if p is not None:
      if p.wait() != 0:
        sys.exit(p.returncode)

  logging.info('---------------------Processing metadata--------------------')
  this_proc = psutil.Process(os.getpid())
  if p and p.returncode == 0:
    with open(coverage_json_file, 'r') as f:
      data = json.load(f)
      for real_data in data['data']:
        if 'file_shards' in real_data and shard_file_dir:
          files = []
          for file_shard in real_data['file_shards']:
            logging.info('------------Processing %s', file_shard)
            with open(os.path.join(shard_file_dir, file_shard), 'r') as shard:
              files.extend(json.load(shard))
            _show_system_resource_usage(this_proc)
          real_data['files'] = files
      return data


def _merge_summary(a, b):
  """Merges to 'summaries' fields in metadata format.

  This adds the 'total' and 'covered' field of each feature in the second
  parameter to the corresponding field in the first parameter.

  Returns a reference the updated first parameter.

  Each parameter is expected to be in the following format:
  [{'name': 'line', 'total': 10, 'covered': 9},
   {'name': 'region', 'total': 10, 'covered': 9},
   {'name': 'function', 'total': 10, 'covered': 9}]
  """

  def make_dict(summary_list):
    return {item['name']: item for item in summary_list}

  a_dict = make_dict(a)
  b_dict = make_dict(b)
  for feature in a_dict:
    for field in ('total', 'covered'):
      a_dict[feature][field] += b_dict[feature][field]
  return a


def _convert_file_summary(file_summary):
  """Convert llvm-cov summay to metadata format"""
  # llvm-cov uses 'lines', 'regions', 'functions', whereas metadata uses
  # 'line', 'region', 'function'.
  return [{
      'name': k[:-1],
      'covered': v['covered'],
      'total': v['count']
  } for k, v in file_summary.iteritems()]


def _merge_into_dir(directory, file_summary):
  _merge_summary(directory['summaries'], _convert_file_summary(file_summary))
  return directory


def _new_summaries():
  return [{
      'name': 'region',
      'covered': 0,
      'total': 0
  }, {
      'name': 'function',
      'covered': 0,
      'total': 0
  }, {
      'name': 'line',
      'covered': 0,
      'total': 0
  }]


def _add_file_to_directory_summary(directory_summaries, src_path, file_data):
  """Summarize for each directory, the summary information of its files.

  By incrementing the summary for each of its ancestors by the values in the
  coverage summary of the file.

  This is expected to be called with the data for each instrumented file.
  """

  def new_dir(path):
    return {
        'dirs': [],
        'files': [],
        'path': path,
        'summaries': _new_summaries(),
    }

  full_filename = file_data['filename']
  src_file = '//' + os.path.relpath(full_filename, src_path)
  parent = directory = os.path.dirname(src_file)
  filename = os.path.basename(src_file)
  summary = file_data['summary']
  while parent != '//':
    if parent + '/' not in directory_summaries:
      directory_summaries[parent + '/'] = new_dir(parent + '/')
    directory_summaries[parent + '/'] = _merge_into_dir(
        directory_summaries[parent + '/'], summary)
    parent = os.path.dirname(parent)

  if '//' not in directory_summaries:
    directory_summaries['//'] = new_dir('//')
  directory_summaries['//'] = _merge_into_dir(directory_summaries['//'],
                                              summary)

  # Directories need a trailing slash as per the metadata format.
  if directory != '//':
    directory += '/'

  directory_summaries[directory]['files'].append({
      'name': filename,
      'summaries': _convert_file_summary(summary),
  })


def _aggregate_dirs_and_components(directory_summaries, component_mapping):
  """Adds every directory's summary to:

     - Its parent's "dirs" field,
     - To its component, if one is defined for it and its immediate parent
       doesn't already count it.
  Args:
    directory_summaries (dict): Maps directory paths to its summary in metadata
        format.

  Returns:
    A dict mapping components to component coverage summaries.
  """
  component_summaries = {}  # Result.
  dirs_to_component = {}
  # sort lexicographically, parents should come before the children.
  for directory in sorted(directory_summaries.keys()):
    if not directory or directory == '//':
      # Root dir has no parent.
      continue
    while directory.endswith('/'):
      directory = directory[:-1]
    parent, dirname = os.path.split(directory)

    if parent != '//':
      parent += '/'
    # this summary is used in both the parent dir, and the component entry.
    inner_dir_summary = {
        'name': dirname + '/',
        'path': directory + '/',
        'summaries': directory_summaries[directory + '/']['summaries'],
    }
    directory_summaries[parent]['dirs'].append(inner_dir_summary)
    component = None
    if directory != '//':
      component = component_mapping.get(directory[len('//'):])
    # Do not add to summary if immediate parent is already considered. To reduce
    # double counting.
    if component and parent not in dirs_to_component:
      dirs_to_component[directory] = component
      if component not in component_summaries:
        component_summaries[component] = {
            'path': component,
            'dirs': [],
            'summaries': _new_summaries(),
        }
      component_summaries[component]['dirs'].append(inner_dir_summary)
      # Accumulate counts for each component.
      component_summaries[component]['summaries'] = _merge_summary(
          component_summaries[component]['summaries'],
          inner_dir_summary['summaries'])
  return component_summaries


def _write_metadata_in_shards(output_dir, compressed_files, directory_summaries,
                              component_summaries):
  """Splits the metadata in a sharded manner if there are too many files.

  Args:
    output_dir: Absolute path output directory for the generated artifacts.
    compressed_files: A list of json object that stores coverage info for files
                      in compressed format. Used by both per-cl coverage and
                      full-repo coverage.
    directory_summaries: A json object that stores coverage info for
                         directories, and the root src directory is represented
                         as '//'. Used only by full-repo coverage.
    component_summaries: A json object that stores coverage info for components.
                         Used only by full-repo coverage.
  """
  # 'dirs', 'components' and 'summaries' are only meanningful to full-repo
  # coverage.
  compressed_data = {
      'dirs':
          directory_summaries.values() if directory_summaries else None,
      'components':
          component_summaries.values() if component_summaries else None,
      'summaries':
          directory_summaries['//']['summaries']
          if directory_summaries else None,
  }

  # Try to split the files into 30 shards, with each shard having at least
  # 1000 files and at most 2000 files.
  # This is to have smaller data chunk to avoid Out-Of-Memory errors when the
  # data is processed on Google App Engine.
  files_in_a_shard = max(min(len(compressed_files) / 30, 2000), 1000)

  if len(compressed_files) <= files_in_a_shard:
    compressed_data['files'] = compressed_files
  else:
    # There are too many files, and they should be sharded.
    files_slice = []
    index = 0
    while True:
      start = index * files_in_a_shard
      if start >= len(compressed_files):
        break
      files_slice.append(compressed_files[start:start + files_in_a_shard])
      index += 1

    files_dir_name = 'file_coverage'
    os.mkdir(os.path.join(output_dir, files_dir_name))
    file_shard_paths = []
    for i, files in enumerate(files_slice):
      file_name = 'files%d.json.gz' % (i + 1)
      with open(os.path.join(output_dir, files_dir_name, file_name), 'w') as f:
        f.write(zlib.compress(json.dumps({'files': files})))
      file_shard_paths.append(os.path.join(files_dir_name, file_name))
    compressed_data['file_shards'] = file_shard_paths

  with open(os.path.join(output_dir, 'all.json.gz'), 'w') as f:
    f.write(zlib.compress(json.dumps(compressed_data)))


def _generate_metadata(src_path, output_dir, profdata_path, llvm_cov_path,
                       binaries, component_mapping, sources, diff_mapping):
  """Generates code coverage metadata.

  Args:
    src_path: Absolute path to the root checkout.
    output_dir: Output directory for the generated artifacts.
    profdata_path: Absolute path to the merged profdata file.
    llvm_cov_path: Absolute path to the llvm-cov executable.
    binaries: List of absolute path to binaries to get coverage for.
    component_mapping: A json object that stores the mapping from dirs to
                       monorail components. Only meaningful to full-repo
                       coverage.
    sources: List of absolute paths to get coverage for. Only meaningful to
             per-cl coverage.
    diff_mapping: A json object that stores the diff mapping. Only meaningful to
                  per-cl coverage.

  Returns:
    None. This method doesn't return anything, instead, it writes the produced
    metadata to the provided |output_dir|.
  """
  logging.info('Generating coverage metadata ...')
  start_time = time.time()
  # For per-CL code coverage, we don't use the multi-threaded llvm-cov.
  no_sharded_output = diff_mapping is not None
  data = _get_coverage_data_in_json(profdata_path, llvm_cov_path, binaries,
                                    sources, output_dir, no_sharded_output)
  minutes = (time.time() - start_time) / 60
  logging.info(
      'Generating & loading coverage metadata with "llvm-cov export" '
      'took %.0f minutes', minutes)

  logging.info('Processing coverage data ...')
  start_time = time.time()
  compressed_files = []
  directory_summaries = {}
  for datum in data['data']:
    for file_data in datum['files']:
      record = _to_compressed_file_record(src_path, file_data, diff_mapping)
      compressed_files.append(record)

      if component_mapping:
        _add_file_to_directory_summary(directory_summaries, src_path, file_data)

  component_summaries = {}
  if component_mapping:
    component_summaries = _aggregate_dirs_and_components(
        directory_summaries, component_mapping)

  minutes = (time.time() - start_time) / 60
  logging.info('Processing coverage data took %.0f minutes', minutes)

  logging.info('Dumping aggregated data ...')
  start_time = time.time()
  _write_metadata_in_shards(output_dir, compressed_files, directory_summaries,
                            component_summaries)
  minutes = (time.time() - start_time) / 60
  logging.info('Dumping aggregated data took %.0f minutes', minutes)

  # Create an index.html for the metadata directory.
  all_files = []
  for root, _, files in os.walk(output_dir):
    for f in files:
      all_files.append(os.path.relpath(os.path.join(root, f), output_dir))
  with open(os.path.join(output_dir, 'index.html'), 'w') as index_f:
    for f in sorted(all_files):
      index_f.write('<a href="./%s">%s<a>\n' % (f, f))
      index_f.write('<br>')


def _parse_args(args):
  parser = argparse.ArgumentParser(
      description='Generate the coverage data in metadata format')
  parser.add_argument(
      '--src-path',
      required=True,
      type=str,
      help='absolute path to the code checkout')
  parser.add_argument(
      '--output-dir',
      required=True,
      type=str,
      help='absolute path to the directory to store the metadata, must exist')
  parser.add_argument(
      '--profdata-path',
      required=True,
      type=str,
      help='absolute path to the merged profdata')
  parser.add_argument(
      '--llvm-cov',
      required=True,
      type=str,
      help='absolute path to llvm-cov executable')
  parser.add_argument(
      '--binaries',
      nargs='+',
      type=str,
      help='absolute path to binaries to generate the coverage for')
  parser.add_argument(
      '--component-mapping-path',
      type=str,
      help='absolute path to json file mapping dirs to monorail components')
  parser.add_argument(
      '--sources',
      nargs='*',
      type=str,
      help='the source files to generate the coverage for, path should be '
      'relative to the root of the code checkout')
  parser.add_argument(
      '--diff-mapping-path',
      type=str,
      help='absolute path to the file that stores the diff mapping')
  return parser.parse_args(args=args)


def main():
  params = _parse_args(sys.argv[1:])

  # Validate parameters
  if not os.path.exists(params.output_dir):
    raise RuntimeError('Output directory %s must exist' % params.output_dir)

  if not os.path.isfile(params.llvm_cov):
    raise RuntimeError('%s must exist' % params.llvm_cov)
  elif not os.access(params.llvm_cov, os.X_OK):
    logging.info('Setting executable bit of %s', params.llvm_cov)
    os.chmod(params.llvm_cov, stat.S_IRUSR | stat.S_IXUSR | stat.S_IWUSR)
    assert os.access(params.llvm_cov, os.X_OK), 'Failed to set executable bit'

  if not os.path.isfile(params.profdata_path):
    raise RuntimeError('Input data %s is missing' % params.profdata_path)

  if (params.component_mapping_path and
      not os.path.isfile(params.component_mapping_path)):
    raise RuntimeError(
        'Component mapping %s is missing' % params.component_mapping)

  if params.diff_mapping_path and not os.path.isfile(params.diff_mapping_path):
    raise RuntimeError('Diff mapping %s is missing' % params.diff_mapping_path)

  component_mapping = None
  if params.component_mapping_path:
    with open(params.component_mapping_path) as f:
      component_mapping = json.load(f)['dir-to-component']

  sources = params.sources or []
  abs_sources = [os.path.join(params.src_path, s) for s in sources]

  diff_mapping = None
  if params.diff_mapping_path:
    with open(params.diff_mapping_path) as f:
      diff_mapping = json.load(f)

  _generate_metadata(params.src_path, params.output_dir, params.profdata_path,
                     params.llvm_cov, params.binaries, component_mapping,
                     abs_sources, diff_mapping)


if __name__ == '__main__':
  logging.basicConfig(
      format='[%(asctime)s %(levelname)s] %(message)s', level=logging.INFO)
  sys.exit(main())
