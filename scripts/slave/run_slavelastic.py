#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# run_slavelastic.py: Runs a test based off of a slavelastic manifest file.

import glob
import hashlib
import json
import optparse
import os
import socket
import sys
import time
import urllib
import urllib2
import zipfile


DESCRIPTION = """This script takes a slavelastic manifest file, packages it,
and sends a swarm manifest file to the swarm server.  This is expected to be
called as a build step with the cwd as the parent of the src/ directory.
"""

CLEANUP_SCRIPT_NAME = 'swarm_cleanup.py'
CLEANUP_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   CLEANUP_SCRIPT_NAME)

WINDOWS_SCRIPT_NAME = 'kill_processes.py'
WINDOWS_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   WINDOWS_SCRIPT_NAME)

HANDLE_EXE = 'handle.exe'
HANDLE_EXE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               '..', '..', 'third_party', 'psutils',
                               HANDLE_EXE)


class Manifest(object):
  RUN_TEST_PATH = os.path.join(
      'src', 'tools', 'isolate', 'run_test_from_archive.py')

  def __init__(self, manifest_hash, test_name, shards, switches):
    """Populates a manifest object.
      Args:
        manifest_hash - The manifest's sha-1 that the slave is going to fetch.
        shards - The number of swarm shards to request.
        test_name - The name to give the test request.
        switches - An object with properties to apply to the test request.
    """
    platform_mapping =  {
      'darwin': 'Mac',
      'cygwin': 'Windows',
      'linux2': 'Linux',
      'win32': 'Windows'
      }

    self.manifest_hash = manifest_hash
    self.shards = shards

    # Random name for the output zip file
    self.zipfile_name = test_name + '.zip'
    self.tasks = []
    self.target_platform = platform_mapping[switches.os_image]
    self.working_dir = switches.working_dir
    self.test_name = test_name
    self.data_url = switches.data_url
    self.data_dest_dir = switches.data_dest_dir

  def add_task(self, task_name, actions, time_out=600):
    """Appends a new task to the swarm manifest file."""
    self.tasks.append({
          'test_name': task_name,
          'action': actions,
          'time_out': time_out
    })

  def zip(self):
    """Zip up all the files necessary to run a shard."""
    start_time = time.time()

    zip_file = zipfile.ZipFile(
        os.path.join(self.data_dest_dir, self.zipfile_name),
        'w')
    zip_file.write(self.RUN_TEST_PATH)
    zip_file.write(CLEANUP_SCRIPT_PATH, CLEANUP_SCRIPT_NAME)

    if self.target_platform == 'Windows':
      zip_file.write(WINDOWS_SCRIPT_PATH, WINDOWS_SCRIPT_NAME)
      zip_file.write(HANDLE_EXE_PATH, HANDLE_EXE)

    zip_file.close()

    print 'Zipping completed, time elapsed: %f' % (time.time() - start_time)

  def to_json(self):
    """Export the current configuration into a swarm-readable manifest file"""
    self.add_task(
        'Run Test',
        ['python', self.RUN_TEST_PATH, '--hash', self.manifest_hash,
         '--remote', self.data_url])

    # Clean up
    self.add_task('Clean Up', ['python', CLEANUP_SCRIPT_NAME])

    # Call kill_processes.py if on windows
    if self.target_platform == 'Windows':
      self.add_task('Kill Processes',
          ['python', WINDOWS_SCRIPT_NAME,
           '--handle_exe', HANDLE_EXE])

    vlan = ''
    if '-m1' in self.data_url:
      vlan = 'm1'
    elif '-m4' in self.data_url:
      vlan = 'm4'

    # Construct test case
    test_case = {
      'test_case_name': self.test_name,
      'data': [
        urllib.quote(self.data_url + '/' + self.zipfile_name, ':/'),
      ],
      'tests': self.tasks,
      'env_vars': {
        'GTEST_TOTAL_SHARDS': '%(num_instances)s',
        'GTEST_SHARD_INDEX': '%(instance_index)s',
      },
      'configurations': [
        {
          'min_instances': self.shards,
          'config_name': self.target_platform,
          'dimensions': {
            'os': self.target_platform,
            'vlan': vlan
          },
        },
      ],
      'working_dir': self.working_dir,
      'cleanup': 'data',
    }

    return json.dumps(test_case)


def ProcessManifest(filepath, shards, options):
  """Process the manifest file and send off the swarm test request."""
  test_name = os.path.splitext(os.path.basename(filepath))[0]
  test_full_name = options.test_name_prefix + test_name

  if not os.path.exists(filepath):
    print ("Manifest file, %s, not found. Unable to send swarm request "
           "for %s" % (filepath, test_full_name))
    return 1

  # Parses manifest file
  print "Parsing file %s..." % filepath
  file_sha1 = hashlib.sha1(open(filepath, 'rb').read()).hexdigest()
  manifest = Manifest(file_sha1, test_full_name, shards, options)

  # Zip up relevent files
  print "Zipping up files..."
  manifest.zip()

  # Send test requests off to swarm.
  print 'Sending test requests to swarm'
  test_url = options.swarm_url + '/test'
  manifest_text = manifest.to_json()
  try:
    result = urllib2.urlopen(test_url, manifest_text).read()

    # Check that we can read the output as a JSON string
    json.loads(result)
  except (ValueError, TypeError, urllib2.URLError) as e:
    print 'Failed to send test for ' + test_name
    print e
    return 1

  return 0


def main():
  """Packages up a Slavelastic test and send it to swarm.  Receive output from
  all shards and print it to stdout.

  Args
    slavelastic manifest file
    number of shards
    ...
  """
  # Parses arguments
  parser = optparse.OptionParser(
      usage='%prog [options]',
      description=DESCRIPTION)
  parser.add_option('-w', '--working_dir', default='swarm_tests',
                    help='Desired working direction on the swarm slave side. '
                    'Defaults to %default.')
  parser.add_option('-o', '--os_image',
                    help='Swarm OS image to request.')
  parser.add_option('-u', '--swarm-url', default='http://localhost:8080',
                    help='Specify the url of the Swarm server. '
                    'Defaults to %default')
  parser.add_option('-d', '--data-url', default=('http://%s/' %
                      socket.gethostbyname(socket.gethostname())),
                    help='The url where the test data can be retrieved from. '
                    'Defaults to %default')
  parser.add_option('--hashtable-dir',
                    help='The path to the hashtable directory storing the test '
                    'data')
  parser.add_option('--data-dest-dir',
                    help='The directory where all the test data needs to be'
                    'placed to get served to the swarm bots')
  parser.add_option('-t', '--test-name-prefix', default='',
                    help='Specify the prefix to give the swarm test request. '
                    'Defaults to %default')
  parser.add_option('-n', '--manifest_name', action='append',
                    help='The name of a manifest to send to swarm. This may '
                    'be given multiple times to send multiple manifests.')
  parser.add_option('-s', '--shards', type='int', action='append',
                    help='The number of shards to request for a manifest. '
                    'This must be listed once for each -n.')
  parser.add_option('-v', '--verbose', action='store_true',
                    help='Print verbose logging')
  (options, args) = parser.parse_args()

  if args:
    parser.error('Unknown args, ' + args)

  if not options.os_image:
    parser.error('Must specify an os image')
  if not options.hashtable_dir:
    parser.error('Must specify the hashtable directory')
  if not options.data_dest_dir:
    parser.error('Must specify the server directory')

  if len(options.manifest_name) != len(options.shards):
    parser.error('Number of min shards given doesn\'t match the number '
                 'of manifests')

  # Remove the old data if there is any
  if os.path.isdir(options.data_dest_dir):
    print 'Removing old swarm files...'
    for filename in glob.glob(os.path.join(options.data_dest_dir,
                                           options.test_name_prefix + '*.zip')):
      os.remove(filename)

  # Send off the swarm test requests.
  highest_exit_code = 0
  for i in range(len(options.manifest_name)):
    highest_exit_code = max(highest_exit_code,
                            ProcessManifest(options.manifest_name[i],
                                            options.shards[i],
                                            options))

  return highest_exit_code


if __name__ == '__main__':
  sys.exit(main())
