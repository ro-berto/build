#!/usr/bin/env vpython3
# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
import logging
import os
import sys

from google.cloud import bigquery

PROJECT = 'chrome-flakiness'
FETCH_BUILDER_QUERY = """
    SELECT DISTINCT
      bot
    FROM
      `chrome-flakiness.flake_endorser.try_historical_test_data_7_days`
  """
TEST_HISTORY_QUERY = """
    SELECT
      test_id,
      variant_hash,
      variant,
      ARRAY_AGG(invocation) AS invocation,
    FROM
      `chrome-flakiness.flake_endorser.try_historical_test_data_7_days`
    WHERE
      bot = \'{}\'
    GROUP BY
      test_id,
      variant_hash,
      variant
  """


def fetch_builders(bq, args):
  logging.info('Searching for all try builders.')
  query_job = bq.query(FETCH_BUILDER_QUERY)
  rows = query_job.result()
  logging.info('Query complete. Processing results.')
  builders = [row.bot for row in rows]

  with open(args.output_file, 'w') as f:
    json.dump(builders, f)

  return builders


def query_test_history(bq, args):
  builder = args.builder
  logging.info('Searching test history for %s' % builder)
  query = TEST_HISTORY_QUERY.format(builder)
  query_job = bq.query(query)
  query_job.result()
  logging.info('Query completed. Uploading results to GS bucket.')

  gs_bucket_path = args.export_gs_path
  logging.info('GS bucket: %s' % gs_bucket_path)

  dataset_id = str(query_job.destination.dataset_id)
  table_id = query_job.destination.table_id
  dataset_ref = bigquery.DatasetReference(PROJECT, dataset_id)
  table_ref = dataset_ref.table(table_id)

  job_config = bigquery.job.ExtractJobConfig()
  job_config.destination_format = (
      bigquery.job.DestinationFormat.NEWLINE_DELIMITED_JSON)

  extract_job = bq.extract_table(
      table_ref, gs_bucket_path, job_config=job_config)
  extract_job.result()


def format_file(bq, args):
  results = []
  with open(args.file, 'r') as f:
    for line in f:
      results.append(json.loads(line))

  res_json = json.dumps(results)
  with open(args.file, 'w') as f:
    f.write(res_json)

  return res_json


def parse_arguments(args):
  parser = argparse.ArgumentParser()
  subparsers = parser.add_subparsers()

  builder_parser = subparsers.add_parser(
      'builders', help='get list of all supported try builders')
  builder_parser.set_defaults(func=fetch_builders)
  builder_parser.add_argument(
      '--output-file', required=True, help='path to output file for results')

  test_history_parser = subparsers.add_parser(
      'history', help='fetch test history')
  test_history_parser.set_defaults(func=query_test_history)
  test_history_parser.add_argument(
      '--export-gs-path',
      required=True,
      help=('GS bucket path to export the table data to.'))
  test_history_parser.add_argument(
      '--builder', required=True, help='try builder name')

  format_parser = subparsers.add_parser(
      'format', help='format new line delimited json to json format')
  format_parser.set_defaults(func=format_file)
  format_parser.add_argument('--file', required=True, help='path to file')

  return parser.parse_args(args)


def main(args):
  bq = bigquery.client.Client(project=PROJECT)
  args = parse_arguments(args)
  args.func(bq, args)
  sys.exit(0)


if __name__ == '__main__':
  logging.basicConfig(
      format='[%(asctime)s %(levelname)s] %(message)s', level=logging.INFO)
  main(sys.argv[1:])
