#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sends analyze results to event_mon.

Needs to be run via tools/scripts/runit.py"""


import argparse
import json
import sys

from infra_libs import event_mon


def inner_main(args):
  event = event_mon.Event(timestamp_kind='POINT')
  analyze_event = event.proto.analyze_event

  if args.master_name:
    analyze_event.master_name = args.master_name
  if args.builder_name:
    analyze_event.builder_name = args.builder_name
  if args.build_id:
    analyze_event.build_id = args.build_id
  if args.analyze_input:
    analyze_input = json.load(args.analyze_input)
    analyze_event.affected_files.extend(analyze_input['files'])
    analyze_event.input_test_targets.extend(analyze_input['test_targets'])
    analyze_event.input_compile_targets.extend(analyze_input[
        'additional_compile_targets'])
  if args.analyze_output:
    analyze_output = json.load(args.analyze_output)

    if 'test_targets' in analyze_output:
      analyze_event.output_test_targets.extend(analyze_output['test_targets'])
    if 'compile_targets' in analyze_output:
      analyze_event.output_compile_targets.extend(
          analyze_output['compile_targets'])

    if 'error' in analyze_output:
      analyze_event.result = analyze_event.AnalyzeResult.Value('ERROR')
    elif 'invalid_targets' in analyze_output:
      analyze_event.result = analyze_event.AnalyzeResult.Value(
          'INVALID_TARGETS')
      analyze_event.invalid_targets.extend(analyze_output['invalid_targets'])
    elif analyze_output.get('status') == 'Found dependency':
      analyze_event.result = analyze_event.AnalyzeResult.Value(
          'FOUND_DEPENDENCY')
    elif analyze_output.get('status') == 'Found dependency (all)':
      analyze_event.result = analyze_event.AnalyzeResult.Value(
          'FOUND_DEPENDENCY_ALL')
    elif (analyze_output.get('status') ==
          'No compile necessary (all files ignored)'):
      analyze_event.result = analyze_event.AnalyzeResult.Value(
          'ALL_FILES_IGNORED')
    elif (analyze_output.get('status') ==
          'Analyze disabled: matched exclusion'):
      analyze_event.result = analyze_event.AnalyzeResult.Value(
          'MATCHED_EXCLUSION')
    elif (analyze_output.get('status') ==
          'No dependency'):
      analyze_event.result = analyze_event.AnalyzeResult.Value(
          'NO_COMPILE_NECESSARY')

  print event.proto

  if event.send():
    return 0

  return 1


def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('--master-name', help='Buildbot master name')
  parser.add_argument('--builder-name', help='Buildbot builder name')
  parser.add_argument('--build-id', help='Build ID (buildnumber)')
  parser.add_argument('--analyze-input', help='JSON input passed to analyze',
                      type=argparse.FileType('r'))
  parser.add_argument('--analyze-output', help='JSON output from analyze',
                      type=argparse.FileType('r'))
  event_mon.add_argparse_options(parser)
  args = parser.parse_args(argv)
  event_mon.process_argparse_options(args)

  try:
    return inner_main(args)
  finally:
    event_mon.close()


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
