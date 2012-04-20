#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# run_slavelastic.py: Runs a test based off of a slavelastic manifest file.

from __future__ import with_statement
import json
import optparse
import os
import platform
import random
import socket
import sys
import time
import urllib2
import zipfile


DESCRIPTION = """This script takes a slavelastic manifest file, packages it,
and sends a swarm manifest file to the swarm server.  This is expected to be
called as a build step with the cwd as the parent of the src/ directory.
"""

class Manifest(object):
  run_test_path = os.path.join(
      'src', 'tools', 'isolate', 'run_test_from_archive.py')

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
    self.manifest_name = filename

    self.g_shards = switches.num_shards
    # Random name for the output zip file
    self.zipfile_name = 'swarm_tempfile_%s.zip' % ''.join(random.choice(
        'abcdefghijklmnopqrstuvwxyz0123456789') for x in range(10))
    self.tasks = []
    self.current_platform = current_platform
    self.target_platform = switches_dict['os_image']
    self.working_dir = switches.working_dir
    self.test_name = switches.test_name

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
    zip_file.write(self.manifest_name)
    zip_file.write(self.run_test_path)
    zip_file.close()

    print 'Zipping completed, time elapsed: %f' % (time.time() - start_time)

  def cleanup(self):
    os.remove(self.zipfile_name)

  def to_json(self):
    """Export the current configuration into a swarm-readable manifest file"""
    hostname = socket.gethostbyname(socket.gethostname())
    # pylint: disable=E1103
    filepath = os.path.relpath(self.zipfile_name, '../..').replace('\\', '/')

    url = 'http://%s/hashtable/' % hostname
    self.add_task(
        'Run Test',
        ['python', self.run_test_path, '-m', self.manifest_name, '-r', url])

    # Clean up
    if self.current_platform == 'Linux' or self.current_platform == 'Mac':
      cleanup_commands = ['rm', '-rf']
    elif self.current_platform == 'Windows':
      cleanup_commands = ['del']
    self.add_task('Clean Up', cleanup_commands + [self.zipfile_name])

    # Call kill_processes.py if on windows
    if self.target_platform == 'Windows':
      self.add_task('Kill Processes',
          [sys.executable, '..\\b\\build\\scripts\\slave\\kill_processes.py'])

    # Construct test case
    test_case = {
      'test_case_name': self.test_name,
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
      'working_dir': self.working_dir,
      'cleanup': 'data',
    }

    return json.dumps(test_case)


def main():
  """Packages up a Slavelastic test and send it to swarm.  Receive output from
  all shards and print it to stdout.

  Args
    slavelastic manifest file
    number of shards
    ...
  """
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
  parser.add_option('-u', '--url', default='http://localhost:8080',
                    help='Specify the url of the Swarm server. '
                    'Defaults to %default')
  parser.add_option('-t', '--test_name',
                    help='Specify the name to give the swarm test request. '
                    'Defaults to the given filename')
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
  if not options.test_name:
    options.test_name = filename

  # Parses manifest file
  print "Parsing file %s..." % filename
  manifest = Manifest(filename, options)

  # Zip up relevent files
  print "Zipping up files..."
  manifest.zip()

  # Send test requests off to swarm.
  print 'Sending test requests to swarm'
  test_url = options.url.rstrip('/') + '/test'
  manifest_text = manifest.to_json()
  result = urllib2.urlopen(test_url, manifest_text).read()

  # Check that we can read the output as a JSON string
  try:
    json.loads(result)
  except (ValueError, TypeError), e:
    print 'Request failed:'
    print result
    print e
    return 1

  return 0

if __name__ == '__main__':
  sys.exit(main())
