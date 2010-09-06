#!/usr/bin/python
# Copyright (c) 2006-2008 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A wrapper script to run layout tests on the buildbots.

Runs the run_webkit_tests.py script found in webkit/tools/layout_tests above
this script. For a complete list of command-line options, pass '--help' on the
command line.

To pass additional options to run_webkit_tests without having them interpreted
as options for this script, include them in an '--options="..."' argument. In
addition, a list of one or more tests or test directories, specified relative
to the main webkit test directory, may be passed on the command line.
"""

import optparse
import os
import sys

import chromium_utils
import slave_utils


def main(options, args):
  """Parse options and call run_webkit_tests.py, using Python from the tree."""
  build_dir = os.path.abspath(options.build_dir)

  # Disable the page heap in case it got left enabled by some previous process.
  try:
    slave_utils.SetPageHeap(build_dir, 'test_shell.exe', False)
  except chromium_utils.PathNotFound:
    # If we don't have gflags.exe, report it but don't worry about it.
    print 'Warning: Couldn\'t disable page heap, if it was already enabled.'
    pass

  webkit_tests_dir = chromium_utils.FindUpward(build_dir,
                                              'webkit', 'tools', 'layout_tests')
  run_webkit_tests = os.path.join(webkit_tests_dir, 'run_webkit_tests.py')
  
  slave_name = slave_utils.SlaveBuildName(build_dir)

  command = [run_webkit_tests,
             '--noshow-results',
             '--verbose',  # Verbose output is enabled to support the dashboard.
             '--full-results-html',  # To make debugging failures easier.
             '--clobber-old-results',  # Clobber test results before each run.
            ]

  if options.results_directory:
    # run_webkit_tests expects the results directory to be either an absolute
    # path (starting with '/') or relative to Debug or Release.  We expect it
    # to be relative to the build_dir, which is a parent of Debug or Release.
    # Thus if it's a relative path, we need to move it out one level.
    if not options.results_directory.startswith('/'):
      options.results_directory = os.path.join('..', options.results_directory)
    chromium_utils.RemoveDirectory(options.results_directory)
    command.extend(['--results-directory', options.results_directory])

  if options.target:
    command.extend(['--target', options.target])
  if options.platform:
    command.extend(['--platform', options.platform])

  # Build type is no longer used.
  # TODO(pamg): remove it from the buildbot config too.
  #if options.build_type:
  #  command.extend(['--build-type', options.build_type])

  if options.no_pixel_tests:
    command.append('--no-pixel-tests')
  if options.batch_size:
    command.extend(['--batch-size', options.batch_size])
  if options.run_part:
    command.extend(['--run-part', options.run_part])
  if options.builder_name:
    command.extend(['--builder-name', options.builder_name])
  if options.build_number:
    command.extend(['--build-number', options.build_number])
  command.extend(['--build-name', slave_name])
  if options.test_results_server:
    command.extend(['--test-results-server', options.test_results_server])

  if options.enable_pageheap:
    # If we're actually requesting pageheap checking, complain if we don't have
    # gflags.exe.
    slave_utils.SetPageHeap(build_dir, 'test_shell.exe', True)
    command.append('--time-out-ms=120000')

  # The list of tests is given as arguments.
  command.extend(options.options.split(' '))
  command.extend(args)

  # Nuke anything that appears to be stale chrome items in the temporary
  # directory from previous test runs (i.e.- from crashes or unittest leaks).
  chromium_utils.RemoveChromeTemporaryFiles()

  # Run the the tests
  result = slave_utils.RunPythonCommandInBuildDir(build_dir, options.target,
                                                  command)

  if options.enable_pageheap:
    slave_utils.SetPageHeap(build_dir, 'test_shell.exe', False)

  return result

if '__main__' == __name__:
  option_parser = optparse.OptionParser()
  option_parser.add_option('-o', '--results-directory', default='',
                           help='output results directory')
  option_parser.add_option('', '--build-dir', default='webkit',
                           help='path to main build directory (the parent of '
                                'the Release or Debug directory)')
  option_parser.add_option('', '--target', default='',
      help='test_shell build configuration (Release or Debug)')
  option_parser.add_option('', '--build-type', default='',
      help='build identifier, for custom results and test lists (v8 or kjs)')
  option_parser.add_option('', '--options', default='',
      help='additional options to pass to run_webkit_tests.py')
  option_parser.add_option("", "--platform", default='',
      help=("Platform value passed directly to run_webkit_tests."))
  option_parser.add_option('', '--no-pixel-tests', action='store_true',
                           default=False,
                           help='disable pixel-to-pixel PNG comparisons')
  option_parser.add_option('', '--enable-pageheap', action='store_true',
                           default=False, help='Enable page heap checking')
  option_parser.add_option("", "--batch-size",
                           default=None,
                           help=("Run a the tests in batches (n), after every "
                                 "n tests, the test shell is relaunched."))
  option_parser.add_option("", "--run-part",
                           default=None,
                           help=("Run a specified part (n:l), the nth of lth"
                                 ", of the layout tests"))
  option_parser.add_option("", "--builder-name",
                           default=None,
                           help="The name of the builder running this script.")
  option_parser.add_option("", "--build-number",
                           default=None,
                           help=("The build number of the builder running"
                                 "this script."))
  option_parser.add_option("", "--test-results-server",
                           help=("If specified, upload results json files to "
                                 "this appengine server."))
  options, args = option_parser.parse_args()

  # Disable pageheap checking except on Windows.
  if sys.platform != 'win32':
    options.enable_pageheap = False

  sys.exit(main(options, args))
