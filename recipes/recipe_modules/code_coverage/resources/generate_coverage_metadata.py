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
import platform
import psutil
import stat
import subprocess
import sys
import tempfile
import time
import zlib

import aggregation_util
import repository_util

IS_WIN = platform.system() == 'Windows'
IS_MAC = platform.system() == 'Darwin'


def _posix_path(rawpath):
  return rawpath.replace(os.sep, '/')


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

  def _get_line_num(segment):
    """Returns line number."""
    return segment[0]

  def _get_col_num(segment):
    """Returns column number."""
    return segment[1]

  def _get_count(segment):
    """Returns number of times this segment is executed."""
    return segment[2]

  def _has_count(segment):
    """Returns True if this segment was instrumented and *not* skipped."""
    return segment[3]

  def _is_region_entry(segment):
    """Retruns True if segment enters a new region."""
    return segment[4]

  line_data = {}
  # Maps a line number to its uncovered sub-line blocks.
  # line# --> list([start_column, end_column])
  block_data = collections.defaultdict(list)

  # The most recent segment that starts from a previous line.
  wrap_segment = None

  current_line_num = 0
  current_line_segments = []
  next_segment_index = 0

  while current_line_num <= _get_line_num(segments[-1]):
    # Calculate the execution count for each line. Follow the logic in llvm-cov:
    # https://github.com/llvm-mirror/llvm/blob/3b35e17b21e388832d7b560a06a4f9eeaeb35330/lib/ProfileData/Coverage/CoverageMapping.cpp#L686
    current_line_num += 1
    if current_line_segments:
      wrap_segment = current_line_segments[-1]

    current_line_segments = []
    while (next_segment_index < len(segments) and
           _get_line_num(segments[next_segment_index]) == current_line_num):
      current_line_segments.append(segments[next_segment_index])
      next_segment_index += 1

    def _is_start_of_region(segment):
      return _has_count(segment) and _is_region_entry(segment)

    line_starts_new_region = any(
        [_is_start_of_region(segment) for segment in current_line_segments])
    is_start_of_skipped_region = (
        current_line_segments and not _has_count(current_line_segments[0]) and
        _is_region_entry(current_line_segments[0]))
    is_coverable = not is_start_of_skipped_region and (
        (wrap_segment and _has_count(wrap_segment)) or line_starts_new_region)
    if not is_coverable:
      continue

    execution_count = 0
    if wrap_segment:
      execution_count = _get_count(wrap_segment)

    for segment in current_line_segments:
      if _is_start_of_region(segment):
        execution_count = max(execution_count, _get_count(segment))

    line_data[current_line_num] = execution_count

    # Calculate the uncovered blocks within the current line. Follow the logic
    # in llvm-cov:
    # https://github.com/llvm-mirror/llvm/blob/993ef0ca960f8ffd107c33bfbf1fd603bcf5c66c/tools/llvm-cov/SourceCoverageViewText.cpp#L114
    if execution_count == 0:
      # Skips calculating uncovered blocks if the whole line is not covered.
      continue

    col_start = 1
    is_block_not_covered = (
        wrap_segment and _has_count(wrap_segment) and
        _get_count(wrap_segment) == 0)
    for segment in current_line_segments:
      col_end = _get_col_num(segment)
      if is_block_not_covered:
        block_data[_get_line_num(segment)].append([col_start, col_end - 1])

      is_block_not_covered = (_has_count(segment) and _get_count(segment) == 0)
      col_start = col_end
    # Handle the last segment.
    if is_block_not_covered:
      last_segment = current_line_segments[-1]
      # Use -1 to indicate block extends to end of line.
      block_data[_get_line_num(last_segment)].append([col_start, -1])

  return line_data, block_data


def _to_compressed_format(line_data, block_data):
  """Turns output of `_extract_coverage_info` to a compressed format."""
  line_data = sorted(line_data.items(), key=lambda x: x[0])
  lines = []
  # Aggregate contiguous blocks of lines with the exact same hit count.
  last_index = 0
  for i in xrange(1, len(line_data) + 1):
    is_continous_line = (
        i < len(line_data) and line_data[i][0] == line_data[i - 1][0] + 1)
    has_same_count = (
        i < len(line_data) and line_data[i][1] == line_data[i - 1][1])

    # Merge two lines iff they have continous line number and exactly the same
    # count. For example: (101, 10) and (102, 10).
    if (is_continous_line and has_same_count):
      continue

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
    line_data (dict): A mapping from line number to corresponding
                      execution count. 
    block_data (dict): A mapping from line number to a list of sub-line blocks
                      where the code is not covered. A block is represented by
                      two integers [start_column, end_column].
    line_mapping(dict): A map that maps from local diff's line number to Gerrit
                      diff's line number as well as the line itself.

  Returns:
    A tuple of line_data and block with line numbers being rebased.
  """
  rebased_line_data = {}
  for line_num, count in line_data.iteritems():

    if str(line_num) not in line_mapping:
      continue

    rebased_line_num = line_mapping[str(line_num)][0]
    rebased_line_data[rebased_line_num] = count

  rebased_block_data = {}
  for line_num, subline_blocks in block_data.iteritems():
    if str(line_num) not in line_mapping:
      continue

    rebased_line_num = line_mapping[str(line_num)][0]
    rebased_block_data[rebased_line_num] = subline_blocks

  return rebased_line_data, rebased_block_data


def _drop_data_for_unmodified_lines(line_data, block_data, unmodified_lines):
  """Drops unmodified lines(as compared to reference commit) from coverage data.
  
  Args:
    line_data (dict): A mapping from line number to corresponding
                      execution count. 
    block_data (dict): A mapping from line number to a list of sub-line blocks
                      where the code is not covered. A block is represented by
                      two integers [start_column, end_column].
    unmodified_lines (list): A list containing line numbers which have not
                            been modified since the reference commit.

  Returns:
    A tuple (referenced_line_data, referenced_block_data) with same structure
    as `line_data` and `block_data` with data for `unmodified_lines` removed.
  """
  referenced_line_data = {}
  for line_num, count in line_data.iteritems():
    if line_num in unmodified_lines:
      continue
    referenced_line_data[line_num] = count

  rebased_block_data = {}
  for line_num, subline_blocks in block_data.iteritems():
    if line_num in unmodified_lines:
      continue
    rebased_block_data[line_num] = subline_blocks

  return referenced_line_data, rebased_block_data


def _calculate_line_summary_metrics(line_data):
  """Calculates summary metrics for a file.

  This method only returns 'line' summary, as arg line_data
  (presumably) have data for some of the lines removed. As a result, other
  summary metrics like 'regions' and 'functions' are not feasible to calculate.
  See `_get_clang_summary_metrics()` for contrast.

  Args:
    line_data (dict): Mapping from line number to corresponding execution count.
  Returns:
      A list that conforms to the Metric proto at
      https://chromium.googlesource.com/infra/infra/+/refs/heads/master/appengine/findit/model/proto/code_coverage.proto
  """
  covered = 0
  for _, count in line_data.iteritems():
    if count > 0:
      covered += 1
  return [{'name': 'line', 'covered': covered, 'total': len(line_data)}]


def _to_compressed_file_record(src_path,
                               file_coverage_data,
                               diff_mapping=None,
                               reference_commit=None):
  """Converts the given Clang file coverage data to coverage metadata format.

  Coverage metadata format:
  https://chromium.googlesource.com/infra/infra/+/refs/heads/master/appengine/findit/model/proto/code_coverage.proto

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
    reference_commit: Hash of a past commit. Passing this in arguments would
                  also generate file record relative to that commit i.e.
                  only those lines would be considered in file record which
                  were modified/added after the said commit.

  Returns:
    A tuple containing two elements, each of which is a json conforming to
    `File` proto. The first element represents the default file coverage while 
    the second element represents coverage relative to reference_commit. If
    `reference_commit` is not provided, second element is None.
  """
  segments = file_coverage_data['segments']
  if not segments:
    return None

  filename = file_coverage_data['filename']
  rel_file_path = os.path.relpath(filename, src_path)
  # TODO(crbug.com/1010267) Remove prefixes when Clang supports relative paths
  # for coverage.
  prefixes = [
      src_path,
      r'C:\botcode\w',  # crbug.com/1010267
      '/b/f/w',  # crbug.com/1061603
      '/b/s/w/ir/cache/builder/src',  #crbug.com/1208128
      '/this/path/is/set'  #crbug.com/1208128
  ]
  coverage_path = os.path.normpath(filename)
  for prefix in prefixes:
    if coverage_path.startswith(prefix):
      coverage_path = coverage_path[len(prefix):]
      break
  coverage_path = _posix_path(coverage_path).lstrip('/')

  line_data, block_data = _extract_coverage_info(segments)

  if diff_mapping is not None and rel_file_path in diff_mapping:
    line_mapping = diff_mapping[rel_file_path]
    line_data, block_data = _rebase_line_and_block_data(line_data, block_data,
                                                        line_mapping)

  lines, uncovered_blocks = _to_compressed_format(line_data, block_data)
  data = {
      'path':  # Convert filesystem path to a source-absolute (GN-style) path.
          '//' + coverage_path,
      'lines':
          lines,
      'summaries':
          _get_clang_summary_metrics(file_coverage_data['summary']),
  }
  if uncovered_blocks:
    data['uncovered_blocks'] = uncovered_blocks

  referenced_data = None
  if reference_commit:
    unmodified_lines = repository_util.GetUnmodifiedLinesSinceCommit(
        src_path, coverage_path, reference_commit)
    referenced_line_data, referenced_block_data = (
        _drop_data_for_unmodified_lines(line_data, block_data,
                                        unmodified_lines))
    referenced_lines, referenced_uncovered_blocks = _to_compressed_format(
        referenced_line_data, referenced_block_data)
    referenced_data = {
        'path':  # Convert filesystem path to a source-absolute (GN-style) path.
            '//' + coverage_path,
        'lines':
            referenced_lines,
        'summaries':
            _calculate_line_summary_metrics(referenced_line_data),
    }
    if referenced_uncovered_blocks:
      referenced_data['uncovered_blocks'] = referenced_uncovered_blocks
  return data, referenced_data


def _compute_llvm_args(profdata_path,
                       llvm_cov_path,
                       build_dir,
                       binaries,
                       sources=None,
                       num_threads=None,
                       exclusions=None,
                       summary_only=False,
                       arch=None):
  # Use as many cpu cores as possible for parallel processing of huge data.
  # Leave 5 cpu cores out for other processes in the bot.
  num_threads_arg = num_threads or max(10, psutil.cpu_count() - 5)

  # TODO(crbug.com/1068345): llvm-cov fails with a thread resource
  # unavailable exception if using more than one thread in iOS builder.
  if IS_MAC and arch == 'x86_64':
    num_threads_arg = 1

  args = [
      llvm_cov_path,
      'export',
      '-skip-expansions',
      '-skip-functions',
      '-num-threads',
      str(num_threads_arg),
      '-compilation-dir',
      build_dir,
  ]

  if exclusions:
    args.extend(['-ignore-filename-regex', exclusions])

  if summary_only:
    args.append('-summary-only')

  if arch:
    # The number of -arch=some_arch arguments needs to be the same as the number
    # of binaries passed to llvm-cov command. Nth entry in the arch list
    # corresponds to the Nth specified binary.
    args.extend(['-arch=%s' % arch] * len(binaries))

  args.extend(['-instr-profile', profdata_path, binaries[0]])
  for b in binaries[1:]:
    args.append('-object')
    args.append(b)
  args.extend(sources or [])

  return args


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
    if IS_WIN or IS_MAC:
      logging.info('llvm-cov Memory: '
                   'RSS=%s,  VMS=%s', bytes_to_gb(p_mem.rss),
                   bytes_to_gb(p_mem.vms))
    else:
      logging.info('llvm-cov Memory: '
                   'RSS=%s,  VMS=%s, shared=%s', bytes_to_gb(p_mem.rss),
                   bytes_to_gb(p_mem.vms), bytes_to_gb(p_mem.shared))

    os_vm = psutil.virtual_memory()
    if IS_WIN or IS_MAC:
      logging.info('OS virtual Memory: '
                   'available=%s, used=%s, free=%s',
                   bytes_to_gb(os_vm.available), bytes_to_gb(os_vm.used),
                   bytes_to_gb(os_vm.free))
    else:
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
    if not IS_MAC:
      p_disk_io = proc.io_counters()
      logging.info('llvm-cov disk io: write=%s, read=%s',
                   bytes_to_gb(p_disk_io.write_bytes),
                   bytes_to_gb(p_disk_io.read_bytes))
  except psutil.Error:  # The process might already have finished.
    pass
  # TODO(crbug.com/1203700): Remove the except block after psutil is in a newer
  # version.
  except ValueError as error:
    logging.warning('ValueError caught when showing system info: %s', error)


def _get_coverage_data_in_json(profdata_path, llvm_cov_path, build_dir,
                               binaries, sources, output_dir, exclusions, arch):
  """Returns a json object of the coverage info."""
  coverage_json_file = os.path.join(output_dir, 'coverage.json')
  error_out_file = os.path.join(output_dir, 'llvm_cov.stderr.log')
  p = None
  try:

    with open(coverage_json_file, 'w') as f_out, open(error_out_file,
                                                      'w') as f_error:
      args = _compute_llvm_args(
          profdata_path,
          llvm_cov_path,
          build_dir,
          binaries,
          sources,
          exclusions=exclusions,
          arch=arch)
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
        logging.error('Subprocess returned error %d', p.returncode)
        with open(error_out_file) as error_f:
          logging.error('--------dumping stderr from %s -----', error_out_file)
          print error_f.read()
        sys.exit(p.returncode)

  logging.info('---------------------Processing metadata--------------------')
  if p and p.returncode == 0:
    with open(coverage_json_file, 'r') as f:
      return json.load(f)


def _split_metadata_in_shards_if_necessary(output_dir, files_dir,
                                           compressed_files,
                                           directory_summaries,
                                           component_summaries):
  """Splits the metadata in a sharded manner if there are too many files.

  Args:
    output_dir: Absolute path output directory for the generated artifacts.
    files_dir: Subdirectory of output directory containing the generated 
              artifacts.
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

    os.mkdir(os.path.join(output_dir, files_dir))
    file_shard_paths = []
    for i, files in enumerate(files_slice):
      file_name = 'files%d.json.gz' % (i + 1)
      with open(os.path.join(output_dir, files_dir, file_name), 'wb') as f:
        f.write(zlib.compress(json.dumps({'files': files})))
      path = os.path.normpath(os.path.join(files_dir, file_name))
      file_shard_paths.append(_posix_path(path))
    compressed_data['file_shards'] = file_shard_paths

  return compressed_data


def _get_per_target_coverage_summary(profdata_path, llvm_cov_path, build_dir,
                                     binaries, arch):
  logging.info('Generating per-target coverage summaries ...')
  summaries = {}
  for binary in binaries:
    args = _compute_llvm_args(
        profdata_path,
        llvm_cov_path,
        build_dir, [binary],
        summary_only=True,
        arch=arch)
    try:
      output = subprocess.check_output(args)
      summaries[binary] = json.loads(output)['data'][0]['totals']
    except subprocess.CalledProcessError as e:
      logging.warn('Summary for binary %s failed with return code %d', binary,
                   e.returncode)
      logging.warn('%s', e.output)
      continue
    except (ValueError, TypeError):
      logging.warn('Invalid JSON output for binary %s', binary)
      logging.warn('%s', output)
      continue
  logging.info('Done generating per-target coverage summaries')
  return summaries


def _generate_metadata(src_path,
                       output_dir,
                       profdata_path,
                       llvm_cov_path,
                       build_dir,
                       binaries,
                       component_mapping,
                       sources,
                       diff_mapping=None,
                       reference_commit=None,
                       exclusions=None,
                       arch=None):
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
    reference_commit: Hash of the commit used to generate coverage reports
                      restricted to lines of code merged after it.
                      Only meaningful for full-codebase coverage.
    exclusions: A regex string to exclude matches from aggregation.
    arch: A string indicating the architecture of the binaries.

  Returns:
    A tuple (data, referenced_data, summaries) where:
    data: A data structure that can be serialized according to the
                    coverage metadata format.
    referenced_data: A data structure containing coverage info 
                    referenced against a past commit, that can be serialized
                    according to the coverage metadata format.                 
    summaries: A dict that maps binary name to a summary of that binary's
               coverage data.
  """
  assert not (bool(diff_mapping) and bool(reference_commit)
             ), "Atmost one of diff_mapping or reference_commit can be present"
  logging.info('Generating coverage metadata ...')
  start_time = time.time()
  data = _get_coverage_data_in_json(profdata_path, llvm_cov_path, build_dir,
                                    binaries, sources, output_dir, exclusions,
                                    arch)
  minutes = (time.time() - start_time) / 60
  logging.info(
      'Generating & loading coverage metadata with "llvm-cov export" '
      'took %.0f minutes', minutes)

  logging.info('Processing coverage data ...')
  start_time = time.time()
  files_coverage = []
  files_referenced_coverage = []
  for datum in data['data']:
    for file_data in datum['files']:
      record, referenced_record = _to_compressed_file_record(
          src_path, file_data, diff_mapping, reference_commit)
      files_coverage.append(record)
      if reference_commit:
        files_referenced_coverage.append(referenced_record)

  per_directory_coverage = {}
  per_component_coverage = {}
  if diff_mapping is None:
    per_directory_coverage, per_component_coverage = (
        aggregation_util.get_aggregated_coverage_data_from_files(
            files_coverage, component_mapping))
    if reference_commit:
      per_directory_referenced_coverage, per_component_referenced_coverage = (
          aggregation_util.get_aggregated_coverage_data_from_files(
              files_referenced_coverage, component_mapping))

  summaries = _get_per_target_coverage_summary(profdata_path, llvm_cov_path,
                                               build_dir, binaries, arch)

  if diff_mapping is None:
    repository_util.AddGitRevisionsToCoverageFilesMetadata(
        files_coverage, src_path, 'DEPS')
    if reference_commit:
      repository_util.AddGitRevisionsToCoverageFilesMetadata(
          files_referenced_coverage, src_path, 'DEPS')

  minutes = (time.time() - start_time) / 60
  logging.info('Processing coverage data took %.0f minutes', minutes)

  logging.info('Dumping aggregated data ...')
  start_time = time.time()

  compressed_data = _split_metadata_in_shards_if_necessary(
      output_dir, 'files_coverage', files_coverage, per_directory_coverage,
      per_component_coverage)
  compressed_referenced_data = None
  if reference_commit:
    compressed_referenced_data = _split_metadata_in_shards_if_necessary(
        output_dir, 'files_referenced_coverage', files_referenced_coverage,
        per_directory_referenced_coverage, per_component_referenced_coverage)
  minutes = (time.time() - start_time) / 60
  logging.info('Generating coverage metadata took %.0f minutes', minutes)

  return compressed_data, compressed_referenced_data, summaries


def _get_clang_summary_metrics(clang_summary):
  """Converts Clang summary format to metadata format.

  Args:
    clang_summary (dict): A dict whose keys are ('lines', 'regions',
                          'functions'), and corresponding values are other
                          dicts with format: {'covered': int, 'count': int}.

  Returns:
    A list that conforms to the Metric proto at
    https://chromium.googlesource.com/infra/infra/+/refs/heads/master/appengine/findit/model/proto/code_coverage.proto
  """
  # Clang uses 'lines', 'regions', 'functions', whereas it's preferrable to use
  # singular forms in metadata format.
  return [{
      'name': k[:-1],
      'covered': v['covered'],
      'total': v['count']
  } for k, v in sorted(clang_summary.iteritems())]


def _create_index_html(output_dir):
  """Creates an index.html that lists the files within the directory.

  output_dir: The directory to create index.html for.
  """
  all_files = []
  for root, _, files in os.walk(output_dir):
    for f in files:
      all_files.append(os.path.relpath(os.path.join(root, f), output_dir))
  with open(os.path.join(output_dir, 'index.html'), 'w') as index_f:
    for f in sorted(all_files):
      f = _posix_path(f)
      index_f.write('<a href="./%s">%s<a>\n' % (f, f))
      index_f.write('<br>')


def _parse_args(args):
  parser = argparse.ArgumentParser(
      description='Generate the coverage data in metadata format')
  parser.add_argument(
      '--build-dir',
      required=True,
      type=str,
      help='absolute path to the build directory')
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
      '--dir-metadata-path',
      type=str,
      help='absolute path to json file mapping dirs to metadata')
  parser.add_argument(
      '--sources',
      nargs='*',
      type=str,
      help='the source files to generate the coverage for, path should be '
      'relative to the root of the code checkout')
  parser.add_argument(
      '--reference-commit',
      type=str,
      help='Hash of the commit used to generate coverage reports '
      'restricted to lines of code merged after it')
  parser.add_argument(
      '--diff-mapping-path',
      type=str,
      help='absolute path to the file that stores the diff mapping')
  parser.add_argument(
      '--exclusion-pattern',
      type=str,
      help='regex pattern for sources to exclude from aggregation')
  parser.add_argument(
      '--arch',
      type=str,
      help='architecture of binaries',
  )
  return parser.parse_args(args=args)


def main():
  params = _parse_args(sys.argv[1:])

  # Validate parameters
  if not os.path.exists(params.build_dir):
    raise RuntimeError('Build directory %s must exist' % params.build_dir)
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

  if (params.dir_metadata_path and
      not os.path.isfile(params.dir_metadata_path)):
    raise RuntimeError('Dir metadata %s is missing' % params.dir_metadata_path)

  if params.diff_mapping_path and not os.path.isfile(params.diff_mapping_path):
    raise RuntimeError('Diff mapping %s is missing' % params.diff_mapping_path)

  component_mapping = None
  if params.dir_metadata_path:
    with open(params.dir_metadata_path) as f:
      component_mapping = {
          d: md['monorail']['component']
          for d, md in json.load(f)['dirs'].iteritems()
          if 'monorail' in md and 'component' in md['monorail']
      }

  sources = params.sources or []
  abs_sources = [os.path.join(params.src_path, s) for s in sources]

  diff_mapping = None
  if params.diff_mapping_path:
    with open(params.diff_mapping_path) as f:
      diff_mapping = json.load(f)

  assert (component_mapping is None) or (diff_mapping is None), (
      'component_mapping (for full-repo coverage) and diff_mapping '
      '(for per-cl coverage) cannot be specified at the same time.')

  data, referenced_data, summaries = _generate_metadata(
      params.src_path, params.output_dir, params.profdata_path, params.llvm_cov,
      params.build_dir, params.binaries, component_mapping, abs_sources,
      diff_mapping, params.reference_commit, params.exclusion_pattern,
      params.arch)

  with open(os.path.join(params.output_dir, 'all.json.gz'), 'wb') as f:
    f.write(zlib.compress(json.dumps(data)))
  with open(os.path.join(params.output_dir, 'all_referenced.json.gz'),
            'wb') as f:
    f.write(zlib.compress(json.dumps(referenced_data)))
  with open(os.path.join(params.output_dir, 'per_target_summaries.json'),
            'wb') as f:
    json.dump(summaries, f)
  _create_index_html(params.output_dir)


if __name__ == '__main__':
  logging.basicConfig(
      format='[%(asctime)s %(levelname)s] %(message)s', level=logging.INFO)
  sys.exit(main())
