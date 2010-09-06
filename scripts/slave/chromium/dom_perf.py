#!/usr/bin/python
# Copyright (c) 2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to run the dom perf tests, used by the buildbot slaves.

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., chrome-release/build/).

  For a list of command-line options, call this script with '--help'.
"""

import logging
import optparse
import os
import sys

import chromium_utils
import simplejson as json
import slave_utils

# So we can import google.*_utils below with native Pythons.
sys.path.append(os.path.abspath('src/tools/python'))

USAGE = '%s [options]' % os.path.basename(sys.argv[0])

URL = 'file:///%s/run.html?run=all%s&reportInJS=1&tags=buildbot_trunk,revision_%s'

def print_result(top, name, score_string, refbuild):
  prefix = ''
  if top:
    prefix = '*'
  score = int(round(float(score_string)))
  score_label = 'score'
  if refbuild:
    score_label = 'score_ref'
  print ('%sRESULT %s: %s= %d score (bigger is better)' %
         (prefix, name, score_label, score))

def main(options, args):
  """Using the target build configuration, run the dom perf test."""

  build_dir = os.path.abspath(options.build_dir)
  if chromium_utils.IsWindows():
    test_exe_name = 'url_fetch_test.exe'
  else:
    test_exe_name = 'url_fetch_test'
  if chromium_utils.IsMac():
    build_dir = os.path.join(os.path.dirname(build_dir), 'xcodebuild')
  elif chromium_utils.IsLinux():
    build_dir = os.path.join(os.path.dirname(build_dir), 'sconsbuild')
    slave_utils.StartVirtualX(options.target,
                              os.path.join(build_dir, options.target))
  test_exe_path = os.path.join(build_dir, options.target, test_exe_name)
  if not os.path.exists(test_exe_path):
    raise chromium_utils.PathNotFound('Unable to find %s' % test_exe_path)

  # Find the current revision to pass to the test.
  build_revision = slave_utils.SubversionRevision(build_dir)

  # Compute the path to the test data.
  src_dir = os.path.dirname(build_dir)
  data_dir = os.path.join(src_dir, 'data')
  dom_perf_dir = os.path.join(data_dir, 'dom_perf')

  iterations = ''  # Default
  if options.target == 'Debug':
    iterations = '&minIterations=1'

  def run_and_print(use_refbuild):
    # Windows used to write to the root of C:, but that doesn't work
    # on Vista so we write into the build folder instead.
    suffix = ''
    if (use_refbuild):
      suffix = '_ref'
    output_file = os.path.join(build_dir, options.target,
                               'dom_perf_result_%s%s.txt' % (build_revision,
                                                             suffix))

    url = URL % (dom_perf_dir, iterations, build_revision)
    url_flag = '--url=%s' % url

    command = [test_exe_path,
               '--wait_cookie_name=__domperf_finished',
               '--jsvar=__domperf_result',
               '--jsvar_output=%s' % output_file,
               url_flag]
    if use_refbuild:
      command.append('--reference_build')

    print "Executing: "
    print command
    result = chromium_utils.RunCommand(command)

    # Open the resulting file and display it.
    file = open(output_file, 'r')
    data = json.loads(''.join(file.readlines()))
    file.close()

    print_result(True, 'Total', data['BenchmarkRun']['totalScore'], 
                 use_refbuild)
    for suite in data['BenchmarkSuites']:
      print_result(False, suite['name'], suite['score'], use_refbuild)

    return result

  result = run_and_print(False)
  result &= run_and_print(True)

  if chromium_utils.IsLinux():
    slave_utils.StopVirtualX(options.target)

  return result


if '__main__' == __name__:
  # Initialize logging.
  log_level = logging.INFO
  logging.basicConfig(level=log_level,
                      format='%(asctime)s %(filename)s:%(lineno)-3d'
                             ' %(levelname)s %(message)s',
                      datefmt='%y%m%d %H:%M:%S')

  option_parser = optparse.OptionParser(usage=USAGE)

  option_parser.add_option('', '--target', default='Release',
                           help='build target (Debug or Release)')
  option_parser.add_option('', '--build-dir', default='chrome',
                           help='path to main build directory (the parent of '
                                'the Release or Debug directory)')
  options, args = option_parser.parse_args()

  sys.exit(main(options, args))
