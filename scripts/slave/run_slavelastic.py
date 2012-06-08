#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# run_slavelastic.py: Runs a test based off of a slavelastic manifest file.

from __future__ import with_statement
import glob
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

class Manifest(object):
  run_test_path = os.path.join(
      'src', 'tools', 'isolate', 'run_test_from_archive.py')

  def __init__(self, filename, test_name, switches):
    """Populates a manifest object.
      Args:
        filename - The manifest with the test details.
        test_name - The name to give the test request.
        switches - An object with properties to apply to the test request.
    """
    platform_mapping =  {
      'darwin': 'Mac',
      'cygwin': 'Windows',
      'linux2': 'Linux',
      'win32': 'Windows'
      }

    self.manifest_name = filename

    self.g_shards = switches.num_shards
    # Random name for the output zip file
    self.zipfile_name = test_name + '.zip'
    self.tasks = []
    self.target_platform = platform_mapping[switches.os_image]
    self.working_dir = switches.working_dir
    self.test_name = test_name
    self.data_url = switches.data_url
    self.data_dest_dir = switches.data_dest_dir

  def add_task(self, task_name, actions):
    """Appends a new task to the swarm manifest file."""
    self.tasks.append({
          'test_name': task_name,
          'action': actions,
    })

  def zip(self):
    """Zip up all the files in self.files"""
    start_time = time.time()

    zip_file = zipfile.ZipFile(
        os.path.join(self.data_dest_dir, self.zipfile_name),
        'w')
    zip_file.write(self.manifest_name)
    zip_file.write(self.run_test_path)
    zip_file.close()

    print 'Zipping completed, time elapsed: %f' % (time.time() - start_time)

  def to_json(self):
    """Export the current configuration into a swarm-readable manifest file"""
    self.add_task(
        'Run Test',
        ['python', self.run_test_path, '-m', self.manifest_name,
         '-r', self.data_url])

    # Clean up
    # TODO(csharp) This can be removed once the swarm cleanup parameter is
    # properly handled.
    if self.target_platform == 'Linux' or self.target_platform == 'Mac':
      cleanup_commands = ['rm', '-rf']
    elif self.target_platform == 'Windows':
      cleanup_commands = ['del']
    self.add_task('Clean Up', cleanup_commands + ['*.zip'])

    # Call kill_processes.py if on windows
    if self.target_platform == 'Windows':
      self.add_task('Kill Processes',
          [sys.executable, '..\\b\\build\\scripts\\slave\\kill_processes.py'])

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
          'min_instances': self.g_shards,
          'max_instances': self.g_shards,
          'config_name': self.target_platform,
          'dimensions': {
            'os': self.target_platform,
          },
        },
      ],
      'working_dir': self.working_dir,
      'cleanup': 'data',
    }

    return json.dumps(test_case)


def ProcessManifest(filename, options):
  """Process the manifest file and send off the swarm test request."""
  # Parses manifest file
  print "Parsing file %s..." % filename

  file_name_tail = os.path.split(filename)[1]
  test_name = os.path.splitext(file_name_tail)[0]
  test_full_name = options.test_name_prefix + test_name

  manifest = Manifest(filename, test_full_name, options)

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
      usage='%prog [options] [filenames]',
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
  parser.add_option('-v', '--verbose', action='store_true',
                    help='Print verbose logging')
  (options, args) = parser.parse_args()

  if not args:
    parser.error('Must specify at least one filename')

  if not options.os_image:
    parser.error('Must specify an os image')
  if not options.hashtable_dir:
    parser.error('Must specify the hashtable directory')
  if not options.data_dest_dir:
    parser.error('Must specify the server directory')

  # Remove the old data if there is any
  if os.path.isdir(options.data_dest_dir):
    print 'Removing old swarm files...'
    for filename in glob.glob(os.path.join(options.data_dest_dir, '*.zip')):
      os.remove(filename)

  # Send off the swarm test requests.
  highest_exit_code = 0
  for filename in args:
    highest_exit_code = max(highest_exit_code,
                            ProcessManifest(filename, options))

  return highest_exit_code


if __name__ == '__main__':
  sys.exit(main())
