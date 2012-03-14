#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# run_slavelastic.py: Runs a test based off of a slavelastic manifest file.

from __future__ import with_statement
import BaseHTTPServer
import cStringIO
import json  # pylint: disable=F0401
import optparse
import os
import platform
import random
import SimpleHTTPServer
import SocketServer
import socket
import subprocess
import sys
import threading
import time
import urllib
import zipfile


DESCRIPTION = """This script takes a slavelastic manifest file, packages it,
and sends a swarm manifest file to the swarm server.  This is expected to be
called as a build step with the cwd as the parent of the src/ directory.
"""

# A global list of shards, used to hold the stdout buffer for each shard.
# This is declared globally so that the HttpHandler would be able to access it.
g_shards = []

class ThreadedHTTPServer(SocketServer.ThreadingMixIn,
                         BaseHTTPServer.HTTPServer):
  pass

class HttpHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
  """Handler that is called to process incoming POST connections
  from swarm slaves.
  """
  def log_message(self, _format, *args):
    pass

  def do_POST(self):
    global g_shards  # pylint: disable=W0602
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    data = self.rfile.read()

    # Decode headers
    headers = {}
    for pair in data.split('&'):
      key, value = pair.split('=')
      headers[urllib.unquote(key)] = urllib.unquote_plus(value)

    # Verbose names for headers
    test_case_name = headers['n']
    config_name = headers['c']
    shard_number = int(headers['i'])
    output = headers['r']
    status = headers['s']

    assert shard_number < len(g_shards), 'Invalid shard # %d' % shard_number
    shard = g_shards[shard_number]
    assert test_case_name == shard.test_case_name
    assert config_name == shard.os_image

    if not shard.hostname:
      shard.hostname = self.client_address[0]

    # Take care of 'result_url'
    if 'result' in self.path.split('/'):
      exit_codes = [int(code) if code else 0 for
          code in headers['x'].split(',')]
      code = max(exit_codes)

      # Need to write to shard before calling passed() or failed(), otherwise
      # a race condition is created and the output may not print.
      if shard.verbose:
        data = data.replace('No output!', '')
        shard.write('\nSwarm test completed, swarm results:\n')
        shard.write(output)

      if status == 'True':
        shard.passed()
      else:
        shard.failed(code)
      return

    # Finally, write to stdout
    shard.write(output)

class Manifest(object):
  def __init__(self, filename, switches):
    """Populates a manifest object.
      Args:
        name - Name of the running test.
        files - A list of files to zip up and transfer over.
    """
    platform_mapping =  {
      'win32': 'Windows',
      'cygwin': 'Windows',
      'linux2': 'Linux',
      'darwin': 'Mac'
      }

    # This can cause problems when
    # |current_platform| != |switches_dict['os_image']|
    # crbug.com/117442
    current_platform = platform_mapping[sys.platform]
    switches_dict = {
      'num_shards': switches.num_shards,
      'os_image': current_platform,
    }
    # Parse manifest file
    data = json.load(open(filename))
    self.name = filename
    self.files = data['files']
    self.command = data['command']
    self.relative_cwd = data['relative_cwd']
    self.hashtable_dir = os.path.join('src', 'out', 'Release')

    self.g_shards = switches.num_shards
    # Random name for the output zip file
    self.zipfile_name = 'swarm_tempfile_%s.zip' % ''.join(random.choice(
        'abcdefghijklmnopqrstuvwxyz0123456789') for x in range(10))
    # Port to listen to stdout coming from the swarm slave, will be set later
    # once the HTTP server is initiated and a free port is found
    self.port = None
    self.tasks = []
    self.current_platform = current_platform
    self.target_platform = switches_dict['os_image']
    self.working_dir = switches.working_dir
    self.block_size = switches.block_size

  def add_task(self, task_name, actions):
    """Appends a new task to the swarm manifest file."""
    self.tasks.append({
          'test_name': task_name,
          'action': actions,
    })

  def zip(self):
    """Zip up all the files in self.files"""
    start_time = time.time()

    zip_file = zipfile.ZipFile(self.zipfile_name, 'w')
    for file_path, info in self.files.iteritems():
      zip_file.write(os.path.join(self.hashtable_dir, info['sha-1']),
                     os.path.join('src', file_path))
    zip_file.close()

    print 'Zipping completed, time elapsed: %f' % (time.time() - start_time)

  def cleanup(self):
    os.remove(self.zipfile_name)

  def to_json(self):
    """Export the current configuration into a swarm-readable manifest file"""
    hostname = socket.gethostbyname(socket.gethostname())
    # pylint: disable=E1103
    filepath = os.path.relpath(self.zipfile_name, '../..').replace('\\', '/')

    # The first path is the python location and doesn't need to be adjusted.
    path_adjusted_command = [self.command[0]]
    for path in self.command[1:]:
      if os.path.isabs(path):
        raise Exception('Given an absolute path, unable to convert for swarm '
                        ' bot:\n' + path)
      else:
        adjusted_path = os.path.join(self.relative_cwd, path)
        adjusted_path = os.path.normpath(adjusted_path)
        path_adjusted_command.append(adjusted_path)

    # TODO(csharp) file attributes should be set from the manifest file.
    # http://crbug.com/116251
    if self.current_platform == 'Linux' or self.current_platform == 'Mac':
      self.add_task('Change permissions',
                    ['chmod', '+x'] + path_adjusted_command[1:])

    self.add_task('Run Test', path_adjusted_command)

    # Clean up
    if self.current_platform == 'Linux' or self.current_platform == 'Mac':
      cleanup_commands = ['rm', '-rf']
    elif self.current_platform == 'Windows':
      cleanup_commands = ['del']
    self.add_task('Clean Up',
                  cleanup_commands + [self.zipfile_name, 'src/'])

    # Call kill_processes.py if on windows
    if self.target_platform == 'Windows':
      self.add_task('Kill Processes',
          [sys.executable, '..\\b\\build\\scripts\\slave\\kill_processes.py'])

    # Construct test case
    test_case = {
      'test_case_name': self.name,
      'data': [
        'http://%s/%s' % (hostname, filepath),
      ],
      'tests': self.tasks,
      'env_vars': {
        'GTEST_TOTAL_SHARDS': '%(num_instances)s',
        'GTEST_SHARD_INDEX': '%(instance_index)s',
      },
      'configurations': [
        {
          'min_instances': self.g_shards,
          'max_instances': self.g_shards,
          'config_name': self.target_platform,
          'dimensions': {
            'os': self.target_platform,
          },
        },
      ],
      'result_url': 'http://%s:%d/result' % (hostname,
                                             self.port),
      'output_destination': {
        'url': 'http://%s:%d' % (hostname, self.port),
        'size': self.block_size,
      },
      'working_dir': self.working_dir,
      'cleanup': 'data',
    }

    return json.dumps(test_case)


class TestRunShard(object):
  """Instance of a shard running a test.  This object stores all output until it
  is ready to be printed out"""
  PENDING = 0
  PASSED = 1
  FAILED = 2
  def __init__(self, manifest, index, verbose=False):
    self._buffer = cStringIO.StringIO()
    self._event = threading.Event()
    self._lock = threading.Lock()
    self.manifest = manifest
    self.test_case_name = manifest.name
    self.os_image = manifest.target_platform
    self.status = TestRunShard.PENDING
    self.exit_code = 0
    self.end_time = None
    self.hostname = None
    self.index = index
    self.verbose = verbose

  def get_hostname(self):
    while not self.hostname and self.status == TestRunShard.PENDING:
      self._event.wait()
    return self.hostname

  def read(self):
    """Read stdout data out of the buffer.  Returns an empty string if EOF."""
    if self.status == TestRunShard.PENDING:
      self._event.wait()
    with self._lock:
      result = self._buffer.getvalue()
      self._buffer = cStringIO.StringIO()
      self._event.clear()
    return result

  def write(self, data):
    """Write stdout data into the buffer."""
    if data:
      with self._lock:
        self._buffer.write(data)
        self._event.set()

  def failed(self, code):
    self.status = TestRunShard.FAILED
    self.end_time = time.time()
    self.exit_code = code if code else 42  # Make sure this is non-zero
    self._event.set()

  def passed(self):
    self.status = TestRunShard.PASSED
    self.end_time = time.time()
    self.exit_code = 0
    self._event.set()


def _get_first_number(line):
  for part in line.split():
    if part.isdigit():
      return int(part)

  print 'No number in :'
  print line
  return 0


class TestSummary(object):
  def __init__(self):
    self.test_passed_count = 0
    self.failed_tests = []
    self.disabled_test_count  = 0
    self.ignored_test_count = 0

  def AddSummaryData(self, buf):
    lines = buf.splitlines()

    for line in lines:
      if '[  PASSED  ]' in line:
        self.test_passed_count += _get_first_number(line)
      elif '[  FAILED  ]' in line:
        if ', listed below' not in line:
          self.failed_tests.append(line)
      elif 'DISABLED' in line:
        self.disabled_test_count += _get_first_number(line)
      elif 'failures' in line:
        self.ignored_test_count += _get_first_number(line)

  def Output(self):
    output = []

    output.append('[  PASSED  ] %i tests.' % self.test_passed_count)
    if self.failed_tests:
      output.append('[  FAILED  ] failed tests listed below:')
      output.extend(self.failed_tests)
    output.append('%i FAILED TESTS' % len(self.failed_tests))
    output.append('%i DISABLED TESTS' % self.disabled_test_count)
    output.append('%i tests with ignored failures (FAILS prefix)' %
                 self.ignored_test_count)

    return output


def main():
  """Packages up a Slavelastic test and send it to swarm.  Receive output from
  all shards and print it to stdout.

  Args
    slavelastic manifest file
    number of shards
    ...
  """
  global g_shards
  # Parses arguments
  parser = optparse.OptionParser(usage='%prog [options] [filename]',
                                 description=DESCRIPTION)
  parser.add_option('-w', '--working_dir', default='swarm_tests',
                    help='Desired working direction on the swarm slave side. '
                    'Defaults to %default.')
  parser.add_option('-m', '--min_shards', type='int', default=1,
                    help='Minimum number of shards to request. CURRENTLY NOT '
                    'SUPPORTED.')
  parser.add_option('-s', '--num_shards', type='int', default=1,
                    help='Desired number of shards to request. Must be '
                    'greater than or equal to min_shards.')
  parser.add_option('-o', '--os_image',
                    help='Swarm OS image to request.  Defaults to the '
                    'current platform.')
  parser.add_option('-n', '--hostname', default='localhost',
                    help='Specify the hostname of the Swarm server. '
                    'Defaults to %default')
  parser.add_option('-p', '--port', type='int', default=8080,
                    help='Specify the port of the Swarm server. '
                    'Defaults to %default')
  parser.add_option('-b', '--block_size', type='int', default=64,
                    help='Specify the desired size of a stdout block. '
                    'Defaults to %default bytes.')
  parser.add_option('-v', '--verbose', action='store_true',
                    help='Print verbose logging')
  (options, args) = parser.parse_args()
  if not args:
    parser.error('Must specify one filename.')
  elif len(args) > 1:
    parser.error('Must specify only one filename.')
  filename = args[0]
  if not options.os_image:
    options.os_image = '%s %d' % (platform.uname()[0], 32)

  # Parses manifest file
  print "Parsing file %s..." % filename
  manifest = Manifest(filename, options)

  # Zip up relevent files
  print "Zipping up files..."
  manifest.zip()

  # Set up HTTP listeners
  print "Setting up listeners..."
  g_shards = []
  for shard_num in range(options.num_shards):
    shard = TestRunShard(manifest, shard_num, options.verbose)
    g_shards.append(shard)
  server = ThreadedHTTPServer(('', 0), HttpHandler)
  server_done = threading.Event()
  def server_runner(server, server_done):
    while not server_done.is_set():
      server.handle_request()
  server_thread = threading.Thread(target=server_runner,
                                   args=[server, server_done])
  server_thread.daemon = True
  server_thread.start()
  port = server.server_address[1]
  manifest.port = port

  # Call post_test.py
  print "Calling post test..."

  if options.verbose:
    process_stdout = sys.stdout
    process_stderr = sys.stderr
  else:
    process_stdout = subprocess.PIPE
    process_stderr = subprocess.PIPE

  # TODO(csharp): Find a better way to store and call swarm.
  p = subprocess.Popen([sys.executable,
                        '../../../scripts/tools/swarm/post_test.py',
                        '-n', options.hostname, '-p', str(options.port), '-v'],
                       stdin=subprocess.PIPE, stdout=process_stdout,
                       stderr=process_stderr)
  manifest_text = manifest.to_json()
  print 'Sending manifest: %s' % manifest_text
  p.communicate(manifest_text)
  exit_code = p.wait()
  start_time = time.time()

  # Listen to output_destination
  shard_times = []
  summary_total = TestSummary()
  for shard in g_shards:
    print
    print '===================================================================='
    print 'Begin output from shard index %d (%s)' % (shard.index,
                                                     shard.get_hostname())
    print '===================================================================='
    print
    output_in_summary = False
    while True:
      buf = shard.read()
      if not buf:
        break

      if output_in_summary:
        summary_total.AddSummaryData(buf)
        continue

      summary_index = buf.rfind('[  PASSED  ]')
      if summary_index >= 0:
        output_in_summary = True
        summary_total.AddSummaryData(buf[summary_index:])
        buf = buf[:summary_index - 1]

      sys.stdout.write(buf)
    print
    print '===================================================================='
    print 'End output from shard index %d (%s). Return %d' % (shard.index,
        shard.get_hostname(), shard.exit_code)
    print '===================================================================='
    print
    exit_code = max(exit_code, shard.exit_code)
    shard_times.append(shard.end_time - start_time)
  # Exit with highest exit code
  server_done.set()
  manifest.cleanup()  # Delete temp zip file

  print '\n'.join(summary_total.Output())
  print

  if options.verbose:
    print 'All tests completed, run times:'
    for i in range(len(shard_times)):
      print 'Shard index %d (%s): %3f s. (Exit code: %d)' % (i,
          g_shards[i].hostname, shard_times[i], g_shards[i].exit_code)
      print 'Total time: %f' % (time.time() - start_time)
  return exit_code

if __name__ == '__main__':
  sys.exit(main())
