import argparse
import ast
import json
import os
import sys

from slave import build_directory
from slave import performance_log_processor
from slave import results_dashboard

from common import chromium_utils


def _GetDataFromLogProcessor(log_processor):
  charts = {}
  for log_file_name, line_list in log_processor.PerformanceLogs().iteritems():
    if not log_file_name.endswith('-summary.dat'):
      continue
    chart_name = log_file_name.replace('-summary.dat', '')

    if len(line_list) != 1:
      print 'Error: Unexpected log processor line list: %s' % str(line_list)
      continue
    line = line_list[0].rstrip()
    try:
      charts[chart_name] = json.loads(line)
    except ValueError:
      print 'Error: Could not parse JSON: %s' % line
  return charts


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--buildername', type=str, required=True,
                      help='name of the builder running this script.')
  parser.add_argument('--buildnumber', type=str, required=True,
                      help='build number of the builder running this script.')
  parser.add_argument('--logs_file', type=str, required=True,
                      help='The path to the file with the test output log.')
  parser.add_argument('--perf_id', type=str, required=True,
                      help='perf builder ID.')
  parser.add_argument('--perf_config', type=str, required=True,
                      help='perf configuration dictionary (as a string).')
  parser.add_argument('--revision', type=str, required=True,
                      help='revision of this build.')
  parser.add_argument('--test_name', type=str, required=True,
                      help='name of the test.')
  parser.add_argument('--url', type=str, required=True,
                      help='url where to upload perf results.')

  args = parser.parse_args()

  with open(args.logs_file) as f:
    test_logs = f.readlines()

  try:
    args.perf_config = ast.literal_eval(args.perf_config)
    assert type(args.perf_config) is dict, (
        'Value of --perf-config couldn\'t be evaluated into a dict.')
  except (SyntaxError, ValueError):
    parser.error('Failed to parse --perf-config value into a dict: '
                 '%s' % args.perf_config)

  log_processor = performance_log_processor.GraphingLogProcessor(
      revision=args.revision)
  for line in test_logs:
    log_processor.ProcessLine(line)

  charts = _GetDataFromLogProcessor(log_processor)

  results = results_dashboard.MakeListOfPoints(
      charts=charts, bot=args.perf_id, test_name=args.test_name,
      buildername=args.buildername, buildnumber=args.buildnumber,
      supplemental_columns=args.perf_config,
      perf_dashboard_machine_group=chromium_utils.GetActiveMaster())

  build_dir = build_directory.GetBuildOutputDirectory()
  results_dashboard.SendResults(results, args.url, build_dir)

  return 0


if __name__ == '__main__':
  sys.exit(main())
