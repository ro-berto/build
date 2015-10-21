#!/usr/bin/python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Simple client for the Gerrit REST API.

Usage:
  ./gerrit_client.py \
    -j /tmp/out.json \
    -u https://chromium.googlesource.com/chromium/src/+log?format=json \
"""

import argparse
import json
import logging
import sys
import time
import urllib
import urlparse

from common import find_depot_tools
from gerrit_util import CreateHttpConn, ReadHttpResponse, ReadHttpJsonResponse


class Error(Exception):
  pass


def gitiles_get(parsed_url, handler, attempts):
  host = parsed_url.netloc
  path = parsed_url.path
  if parsed_url.query:
    path += '?%s' % (parsed_url.query,)

  retry_delay_seconds = 1
  attempt = 1
  while True:
    try:
      return handler(CreateHttpConn(host, path))
    except Exception as e:
      if attempt >= attempts:
        raise
      logging.exception('Failed to perform Gitiles operation: %s', e)

    # Retry from previous loop.
    logging.error('Sleeping %d seconds before retry (%d/%d)...',
        retry_delay_seconds, attempt, attempts)
    time.sleep(retry_delay_seconds)
    retry_delay_seconds *= 2
    attempt += 1


def main(args):
  parsed_url = urlparse.urlparse(args.url)
  if not parsed_url.scheme.startswith('http'):
    raise Error('Invalid URI scheme (expected http or https): %s' % args.url)

  # Force the format specified on command-line.
  qdict = {}
  if parsed_url.query:
    qdict.update(urlparse.parse_qs(parsed_url.query))

  f = qdict.get('format')
  if f:
    # Load the latest format specification.
    f = f[-1]
  else:
    # Default to JSON.
    f = 'json'

  # Choose handler.
  if f == 'json':
    def handler(conn):
      return ReadHttpJsonResponse(conn)
  elif f == 'text':
    # Text fetching will pack the text into structured JSON.
    def handler(conn):
      result = ReadHttpResponse(conn).read()
      if not result:
        return None
      # Wrap in a structured JSON for export to recipe module.
      return {
        'value': result,
      }
  else:
    raise ValueError('Unknown format: %s' % (f,))

  result = gitiles_get(parsed_url, handler, args.attempts)
  if not args.quiet:
    logging.info('Read from %s: %s', parsed_url.geturl(), result)
  with open(args.json_file, 'w') as json_file:
    json.dump(result, json_file)
  return 0


if __name__ == '__main__':
  logging.basicConfig()
  logging.getLogger().setLevel(logging.INFO)

  parser = argparse.ArgumentParser()
  parser.add_argument('-j', '--json-file', required=True)
  parser.add_argument('-u', '--url', required=True)
  parser.add_argument('-a', '--attempts', type=int, default=1,
      help='The number of attempts make (with exponential backoff) before '
           'failing.')
  parser.add_argument('-q', '--quiet', action='store_true',
      help='Suppress file contents logging output.')

  sys.exit(main(parser.parse_args()))
