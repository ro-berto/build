#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to package a checkout's source and upload it to Google Storage."""


import json
import optparse
import os
import re
import Queue
import sys
import threading
import time

from common import chromium_utils
from slave import slave_utils


FILENAME = 'chromium-src'
EXT = 'tar.bz2'
GSBASE = 'gs://chromium-browser-csindex'
GSACL = 'public-read'
CONCURRENT_TASKS = 8
UNIT_INDEXER = './clang_indexer/bin/external_corpus_compilation_indexer'


class IndexResult(object):
  def __init__(self):
    self.success = True

  def __nonzero__(self):
    return self.success

  def fail(self):
    self.success = False


class IgnoreOutput(chromium_utils.RunCommandFilter):
  def FilterLine(self, _):
    return None

  def FilterDone(self, _):
    return None

def GenerateIndex(compdb_path):
  with open(compdb_path, 'rb') as json_commands_file:
    json_commands = json.load(json_commands_file)

  if not os.path.exists(UNIT_INDEXER):
    raise Exception('ERROR: compilation indexer not found, exiting')

  # Get the absolute path of the indexer as we later execut it in the directory
  # in which the original compilation was executed.
  indexer = os.path.abspath(UNIT_INDEXER)

  queue = Queue.Queue()

  result = IndexResult()

  def _Worker():
    while True:
      directory, command = queue.get()
      command_list = command.split()

      # The command_list starts with the compiler that was used for the
      # compilation. This is expected to be clang/clang++ by the indexer, so we
      # need to modify |command_list| accordingly. Currently, |command_list|
      # starts with the path to the goma executable followed by the path to the
      # clang executable.
      for i in range(len(command_list)):
        if 'clang' in command_list[i]:
          # Shorten the list of commands such that it starts with the path to
          # the clang executable.
          command_list = command_list[i:]
          break

      run = [indexer, '--gid=', '--uid=', '--loas_pwd_fallback_in_corp',
             '--logtostderr', '--'] + command_list
      try:
        # Ignore the result code - indexing success is monitored on a higher
        # level.
        chromium_utils.RunCommand(run, cwd=directory, filter_obj=IgnoreOutput())
      except OSError, e:
        print >> sys.stderr, 'Failed to run %s: %s' % (run, e)
        result.fail()
      finally:
        queue.task_done()

  for entry in json_commands:
    queue.put((entry['directory'], entry['command']))

  for _ in range(CONCURRENT_TASKS):
    t = threading.Thread(target=_Worker)
    t.daemon = True
    t.start()

  queue.join()
  return result


def DeleteIfExists(filename, gs_prefix):
  """Deletes the file (relative to gs_prefix), if it exists."""
  (status, output) = slave_utils.GSUtilListBucket(gs_prefix, ['-l'])
  if status != 0:
    raise Exception('ERROR: failed to get list of files, exiting')

  regex = re.compile(r'\s*\d+\s+([-:\w]+)\s+%s/%s\n' % (gs_prefix, filename))
  if not regex.search(output):
    return

  status = slave_utils.GSUtilDeleteFile('%s/%s' % (gs_prefix, filename))
  if status != 0:
    raise Exception('ERROR: GSUtilDeleteFile error %d. "%s"' % (
        status, '%s/%s' % (gs_prefix, filename)))


def main():
  option_parser = optparse.OptionParser()
  chromium_utils.AddPropertiesOptions(option_parser)
  option_parser.add_option('--path-to-compdb', default=None,
                           help='path to the compilation database')
  option_parser.add_option(
      '--environment', default=None,
      help='Environment, used as path prefix for the GS bucket')
  options, _ = option_parser.parse_args()
  if not options.path_to_compdb:
    option_parser.error('--path-to-compdb is required')
  if not options.environment:
    option_parser.error('--environment is required')

  print '%s: Cleaning up old data...' % time.strftime('%X')
  # Clean up any source archives from previous runs.
  package_filename = options.factory_properties.get(
      'package_filename', FILENAME)
  chromium_utils.RemoveFilesWildcards(
      '%s-*.%s.partial' % (package_filename, EXT))
  # Clean up index files from previous runs.
  chromium_utils.RemoveFilesWildcards(
      '*.index', os.path.join('src/out', os.curdir))


  if not os.path.exists('src'):
    raise Exception('ERROR: no src directory to package, exiting')

  try:
    revision_upload_path = chromium_utils.GetSortableUploadPathForSortKey(
        *chromium_utils.GetBuildSortKey(options)
    )
  except chromium_utils.NoIdentifiedRevision:
    revision_upload_path = 'NONE'
  completed_filename = '%s-%s.%s' % (
      package_filename,
      revision_upload_path,
      EXT)
  partial_filename = '%s.partial' % completed_filename
  # Check if the file (still) exists.
  if os.path.exists(partial_filename):
    raise Exception('ERROR: %s already exists, exiting' % partial_filename)

  print '%s: Index generation...' % time.strftime('%X')
  indexing_successful = GenerateIndex(options.path_to_compdb)

  print '%s: Creating tar file...' % time.strftime('%X')
  packaging_successful = True
  find_command = ['find', 'src/', 'build/', 'infra/', 'tools/', '/usr/include/',
                  '-type', 'f',
                  # The only files under src/out we want to package up
                  # are index files....
                  '(', '-regex', r'^src/out/.*\.index$', '-o',
                      '(',
                         # ... and generated sources...
                         '-regex', r'^src/out/.*/gen/.*', '-a',
                         '(', '-name', '*.h', '-o', '-name', '*.cc', '-o',
                              '-name', '*.cpp', '-o', '-name', '*.js',
                              ')', '-a',
                         # ... but none of the NaCL stuff.
                         '!', '-regex', '^src/out/[^/]*/gen/lib[^/]*/.*', '-a',
                         '!', '-regex', '^src/out/[^/]*/gen/sdk/.*', '-a',
                         '!', '-regex', '^src/out/[^/]*/gen/tc_.*',
                       ')', '-o',
                       '!', '-regex', '^src/out/.*', ')', '-a',
                  # Exclude all .svn directories, the native client toolchain
                  # and the llvm build directory, and perf/data files.
                  '!', '-regex', r'.*/\.svn/.*', '-a',
                  '!', '-regex', r'.*/\.git/.*', '-a',
                  '!', '-regex', r'^src/native_client/toolchain/.*', '-a',
                  '!', '-regex', r'^src/native_client/.*/testdata/.*', '-a',
                  '!', '-regex', r'^src/third_party/llvm-build/.*', '-a',
                  '!', '-regex', r'^src/.*/\.cvsignore', '-a',
                  '!', '-regex', r'^src/chrome/tools/test/reference_build/.*',
                  '-a',
                  '!', '-regex', r'^tools/perf/data/.*']

  try:
    if chromium_utils.RunCommand(find_command,
                                 pipes=[['tar', '-T-', '-cjvf',
                                         partial_filename]]) != 0:
      raise Exception('ERROR: failed to create %s, exiting' % partial_filename)

    gs_prefix = GSBASE
    if options.environment != 'prod':
      gs_prefix = '%s/%s' % (GSBASE, options.environment)
    print '%s: Cleaning up google storage...' % time.strftime('%X')
    DeleteIfExists(completed_filename, gs_prefix)
    DeleteIfExists(partial_filename, gs_prefix)

    print '%s: Uploading...' % time.strftime('%X')
    status = slave_utils.GSUtilCopyFile(
        partial_filename, gs_prefix, gs_acl=GSACL)
    if status != 0:
      raise Exception('ERROR: GSUtilCopyFile error %d. "%s" -> "%s"' % (
          status, partial_filename, gs_prefix))

    print '%s: Finalizing google storage...' % time.strftime('%X')
    status = slave_utils.GSUtilMoveFile(
        '%s/%s' % (gs_prefix, partial_filename),
        '%s/%s' % (gs_prefix, completed_filename),
        gs_acl=GSACL)
    if status != 0:
      raise Exception('ERROR: GSUtilMoveFile error %d. "%s" -> "%s"' % (
          status, '%s/%s' % (gs_prefix, partial_filename),
          '%s/%s' % (gs_prefix, completed_filename)))

    (status, output) = slave_utils.GSUtilListBucket(gs_prefix, ['-l'])
    if status != 0:
      raise Exception('ERROR: failed to get list of files, exiting')

    regex = re.compile(r'\s*\d+\s+([-:\w]+)\s+%s/%s\n' % (gs_prefix,
                                                          completed_filename))
    match_data = regex.search(output)
    modified_time = None
    if match_data:
      modified_time = match_data.group(1)
    if not modified_time:
      raise Exception('ERROR: could not get modified_time, exiting')
    print 'Last modified time: %s' % modified_time

    print '%s: Deleting old archives on google storage...' % time.strftime('%X')
    regex = re.compile(r'\s*\d+\s+([-:\w]+)\s+(%s/.*%s.*)\n' % (gs_prefix, EXT))
    last_week = int(time.time()) - 7 * 24 * 60 * 60
    for match_data in regex.finditer(output):
      timestamp = int(time.strftime(
          '%s', time.strptime(match_data.group(1), '%Y-%m-%dT%H:%M:%S')))
      if timestamp < last_week:
        print 'Deleting %s...' % match_data.group(2)
        status = slave_utils.GSUtilDeleteFile(match_data.group(2))
        if status != 0:
          raise Exception('ERROR: GSUtilDeleteFile error %d. "%s"' % (
              status, match_data.group(2)))

  except Exception, e:
    print str(e)
    packaging_successful = False

  finally:
    print '%s: Done.' % time.strftime('%X')

  if not (indexing_successful and packaging_successful):
    return 1

  return 0


if '__main__' == __name__:
  sys.exit(main())
