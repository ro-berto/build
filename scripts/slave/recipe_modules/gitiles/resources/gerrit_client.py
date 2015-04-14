#!/usr/bin/python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Simple client for the Gerrit REST API.

Usage:
  ./gerrit_client.py \
    -j /tmp/out.json \
    -u https://chromium.googlesource.com/chromium/src/+log?format=json
"""

import argparse
import json
import logging
import sys
import time
import urlparse

from common import find_depot_tools
from gerrit_util import CreateHttpConn, ReadHttpJsonResponse


class Error(Exception):
  pass


def main(args):
  parsed_url = urlparse.urlparse(args.url)
  if not parsed_url.scheme.startswith('http'):
    raise Error('Invalid URI scheme (expected http or https): %s' % args.url)

  if parsed_url.query:
    path = '%s?%s' % (parsed_url.path, parsed_url.query)
  else:
    path = parsed_url.path

  if args.attempts < 1:
    args.attempts = 1
  retry_delay_seconds = 2
  for i in xrange(args.attempts):
    conn = CreateHttpConn(parsed_url.netloc, path)
    result = ReadHttpJsonResponse(conn)
    logging.info('Read from %s (%d/%d): %s',
        conn.req_params['url'], (i+1), args.attempts, result)
    if result is not None or (i+1) >= args.attempts:
      break

    logging.error("Request returned empty result; sleeping %d seconds",
        retry_delay_seconds)
    time.sleep(retry_delay_seconds)
    retry_delay_seconds *= 2

  with open(args.json_file, 'w') as json_file:
    json.dump(result, json_file)


if __name__ == '__main__':
  logging.basicConfig()
  logging.getLogger().setLevel(logging.INFO)

  parser = argparse.ArgumentParser()
  parser.add_argument(
    '-j',
    '--json-file',
    required=True,
    type=str,
  )
  parser.add_argument(
    '-u',
    '--url',
    required=True,
    type=str,
  )
  parser.add_argument(
    '-a',
    '--attempts',
    type=int,
    default=1,
    help='The number of attempts make (with exponential backoff) before '
         'failing.',
  )

  sys.exit(main(parser.parse_args()))
