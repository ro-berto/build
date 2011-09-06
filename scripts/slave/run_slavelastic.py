#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# run_slavelastic.py: Runs a test based off of a slavelastic manifest file.


import BaseHTTPServer
import cStringIO
import json
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
called by runtest.py with the cwd as the parent of the src/ directory.
"""

# A global list of shards, used to hold the stdout buffer for each shard.
# This is declared globally so that the HttpHandler would be able to access it.
g_shards = []

class ThreadedHTTPServer(SocketServer.ThreadingMixIn,
                         BaseHTTPServer.HTTPServer):
  pass

class HttpHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
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
      shard.write('\nSwarm test completed, swarm results:\n')
      data = data.replace('No output!', '')
      exit_codes = [int(code) if code else 0 for
          code in headers['x'].split(',')]
      code = max(exit_codes)
      # Need to write to shard before calling passed() or failed(), otherwise
      # a race condition is created and the output may not print.
      shard.write(output)
      if status == 'True':
        shard.passed()
      else:
        shard.failed(code)
      return

    # Finally, write to stdout
    shard.write(output)


class Manifest():
  def __init__(self, filename, switches):
    """Populates a manifest object.
      Args:
        name - Name of the running test.
        files - A list of files to zip up and transfer over.
    """
    manifest_file = sys.stdin
    if filename != '-':
      manifest_file = open(filename)
    switches_dict = {
      'target': switches.target,
      'num_shards': switches.num_shards,
      'os_image': switches.os_image,
    }
    self.data = eval(manifest_file.read() % switches_dict)
    manifest_file.close()
    self.name = self.data['name']
    self.files = self.data['files']
    self.g_shards = switches.num_shards
    self.target = switches.target
    # Random name for the output zip file
    self.zipfile_name = 'swarm_tempfile_%s.zip' % ''.join(random.choice(
        'abcdefghijklmnopqrstuvwxyz0123456789') for x in range(10))
    # Port to listen to stdout coming from the swarm slave, will be set later
    # once the HTTP server is initiated and a free port is found
    self.port = None
    self.switches = switches

  def zip(self):
    """Zip up all the files in self.files"""
    if os.name == 'posix':
      zip_args = ['zip', '-r', '-1', self.zipfile_name]
      zip_args.extend(self.files)
      p = subprocess.Popen(zip_args)
      p.wait()
      p = subprocess.Popen(['chmod', '755', self.zipfile_name])
      p.wait()
    elif os.name == 'nt':
      dest_zip = zipfile.ZipFile(self.zipfile_name, 'w')
      for filename in self.files:
        dest_zip.write(filename)
      dest_zip.close()

  @staticmethod
  def cleanup():
    if os.name == 'posix':
      remove_command = ['rm', '-rf']
    elif os.name == 'nt':
      remove_command = ['del']
    else:
      raise Exception('Unknown OS: %s' % os.name)  # Unreachable
    p = subprocess.Popen(remove_command + ['swarm_tempfile_*.zip'])
    p.wait()

  def to_json(self):
    """Export the current configuration into a swarm-readable manifest file"""
    hostname = socket.gethostbyname(socket.gethostname())
    filepath = os.path.relpath(self.zipfile_name, '../..').replace('\\', '/')
    startvxfb_filepath = os.path.relpath('startvx_fb.zip', '../..').replace(
        '\\', '/')
    test_case = {
      'test_case_name': self.name,
      'data': [
        'http://%s/%s' % (hostname, filepath),
        'http://%s/%s' % (hostname, startvxfb_filepath)
      ],
      'tests': [],
      'env_vars': {
        'GTEST_TOTAL_SHARDS': '%(num_instances)s',
        'GTEST_SHARD_INDEX': '%(instance_index)s',
        'DISPLAY': ':9'
      },
      'configurations': [
        {
          'min_instances': self.switches.num_shards,
          'max_instances': self.switches.num_shards,
          'config_name': self.switches.os_image,
          'dimensions': {
            'image': self.switches.os_image
          }
        },
      ],
      'result_url': 'http://%s:%d/result' % (hostname,
                                             self.port),
      'output_destination': {
        'url': 'http://%s:%d' % (hostname, self.port),
        'size': self.switches.block_size,
      },
      'working_dir': self.switches.working_dir,
      'cleanup': 'data'
    }

    # Gclient Sync
    test_case['tests'].append({
          'test_name': 'Gclient Sync',
          'action': ['gclient', 'sync'],
    })

    # Linux specific stuff
    if os.name == 'posix':
      # Chmod the executables, since zip don't preserve permissions
      test_case['tests'].append({
            'test_name': 'Change permissions',
            'action': ['chmod', '+x'] + self.data['files'],
      })
      # Kill off the x server, just incase
      test_case['tests'].append({
            'test_name': 'Stop X Server forcefully',
            'action': ['killall', 'Xvfb']
      })
      # Start up the x server again
      test_case['tests'].append({
          'test_name': 'Start X Server and Frame Buffer',
          'action': ['python', 'start_vxfb.py',
                     os.path.basename(os.path.abspath('..')), '.']
      })

    # Run the tests
    test_case['tests'].append({
          'test_name': 'Run Test',
          'action': [self.files[0]],
    })

    # Clean up
    if os.name == 'posix':
      test_case['tests'].append({
            'test_name': 'Clean Up',
            'action': [
              'rm', '-rf', 'swarm_tempfile*.zip',
            ] + self.files
      })
    elif os.name == 'nt':
      test_case['tests'].append({
            'test_name': 'Clean Up',
            'action': [
              'del', 'swarm_tempfile*.zip',
            ] + self.files
    })

    return json.dumps(test_case)


class TestRunShard():
  """Instance of a shard running a test.  This object stores all output until it
  is ready to be printed out"""
  PENDING = 0
  PASSED = 1
  FAILED = 2
  def __init__(self, manifest, index):
    self._buffer = cStringIO.StringIO()
    self._event = threading.Event()
    self._lock = threading.Lock()
    self.manifest = manifest
    self.test_case_name = manifest.name
    self.os_image = manifest.switches.os_image
    self.status = TestRunShard.PENDING
    self.exit_code = 0
    self.end_time = None
    self.hostname = None
    self.index = index

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
  parser.add_option('-w', '--working_dir', dest='working_dir',
                    default='/swarm_tests', help='Desired working direction on '
                    'the swarm slave side.  Defaults to /swarm_tests or '
                    'C:\swarm_tests.')
  parser.add_option('-m', '--min_shards', dest='min_shards', type='int',
                    default=1, help='Minimum number of shards to request.  '
                    'CURRENTLY NOT SUPPORTED.')
  parser.add_option('-s', '--num_shards', dest='num_shards', type='int',
                    default=1, help='Desired number of shards to request.  '
                    'Must be greater than or equal to min_shards.')
  parser.add_option('-o', '--os_image', dest='os_image', help='Swarm OS image '
                    'to request.  Defaults to the current platform.')
  parser.add_option('-t', '--target', dest='target', default='Release',
                    help='Compiled target, defaults to Release')
  parser.add_option('-n', '--hostname', dest='hostname', default='localhost',
                    help='Specify the hostname of the Swarm server. '
                    'Defaults to Localhost')
  parser.add_option('-p', '--port', dest='port', type='int', default=8080,
                    help='Specify the port of the Swarm server. '
                    'Defaults to 8080')
  parser.add_option('-b', '--block_size', dest='block_size', type='int',
                    default=64, help='Specify the desired size of a stdout '
                    'block.  Defaults to 64 bytes.')
  (options, args) = parser.parse_args()
  if not args:
    args.append('-')
  elif len(args) > 1:
    parser.error('Must specify only one filename.')
  filename = args[0]
  if not options.os_image:
    options.os_image = '%s %d' % (platform.uname[0], 32)

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
    shard = TestRunShard(manifest, shard_num)
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
  p = subprocess.Popen(['python', '../../../scripts/tools/swarm/post_test.py',
                        '-n', options.hostname, '-p', str(options.port), '-v'],
                        stdin=subprocess.PIPE, stdout=sys.stdout,
                        stderr=sys.stderr)
  p.stdin.write(manifest.to_json())
  p.stdin.close()
  exit_code = p.wait()
  start_time = time.time()

  # Listen to output_destination
  shard_times = []
  for shard in g_shards:
    print
    print '===================================================================='
    print 'Begin output from shard index %d (%s)' % (shard.index,
                                                     shard.get_hostname())
    print '===================================================================='
    print
    while True:
      buf = shard.read()
      if not buf:
        break
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
  print 'All tests completed, run times:'
  for i in range(len(shard_times)):
    print 'Shard index %d (%s): %3f s. (Exit code: %d)' % (i,
        g_shards[i].hostname, shard_times[i], g_shards[i].exit_code)
  print 'Total time: %f' % (time.time() - start_time)
  return exit_code

if __name__ == '__main__':
  sys.exit(main())