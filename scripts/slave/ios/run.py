#!/usr/bin/python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Run an iOS GTest app.

Sample usage:
  ./run.py \
  -a src/xcodebuild/Release-iphoneos/base_unittests.app \
  -b some-archive \
  -j /tmp/out.json
  -p iPhone 5 \
  -v 7.1

  Installs base_unittests.app in an iPhone 5 simulator running iOS 8.1,
  runs it, uploads the test's Documents directory to gs://some-archive,
  and outputs summary JSON to out.json.
"""

import argparse
import json
import sys

# pylint: disable=relative-import
from test_runner import SimulatorTestRunner, TestRunnerError


def main(args):
  summary = {}
  test_runner = None

  try:
    test_runner = SimulatorTestRunner(
      args.app,
      args.iossim,
      args.platform,
      args.version,
      xcode_version=args.xcode_version,
      gs_bucket=args.bucket,
    )

    return 0 if test_runner.Launch() else 1
  except TestRunnerError as e:
    summary['step_text'] = '%s%s' % (
      e.__class__.__name__, ': %s' % e.args[0] if e.args else '')

    # test_runner.Launch returns 0 on success, 1 on failure, so return 2
    # on exception to distinguish between a test failure, and a failure
    # to launch the test at all.
    return 2
  finally:
    if test_runner:
      summary.update(test_runner.summary)

    if args.json_file:
      with open(args.json_file, 'w') as f:
        json.dump(summary, f)


if __name__ == '__main__':
  parser = argparse.ArgumentParser()

  parser.add_argument(
    '-a',
    '--app',
    help='Compiled .app to run.',
    metavar='app',
    required=True,
    type=str,
  )
  parser.add_argument(
    '-b',
    '--bucket',
    help='Google Storage bucket to upload test data to.',
    metavar='path',
    type=str,
  )
  parser.add_argument(
    '-i',
    '--iossim',
    help='Compiled iossim to run the app on.',
    metavar='iossim',
    required=True,
    type=str,
  )
  parser.add_argument(
    '-j',
    '--json_file',
    help='Location to write a JSON summary.',
    metavar='file',
    type=str,
  )
  parser.add_argument(
    '-p',
    '--platform',
    help='Platform to simulate.',
    metavar='sim',
    required=True,
    type=str,
  )
  parser.add_argument(
    '-v',
    '--version',
    help='Version of iOS the simulator should run.',
    metavar='ver',
    required=True,
    type=str,
  )
  parser.add_argument(
    '-x',
    '--xcode-version',
    help='Version of Xcode to use.',
    metavar='ver',
    type=str,
  )

  sys.exit(main(parser.parse_args()))
