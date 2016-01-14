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


def reparse_url(parsed_url, qdict):
  return urlparse.ParseResult(
      scheme=parsed_url.scheme,
      netloc=parsed_url.netloc,
      path=parsed_url.path,
      params=parsed_url.params,
      fragment=parsed_url.fragment,
      query=urllib.urlencode(qdict),
  )


def gitiles_get(parsed_url, handler, attempts):
  # This insanity is due to CreateHttpConn interface :(
  host = parsed_url.netloc
  path = parsed_url.path
  if parsed_url.query:
    path += '?%s' % (parsed_url.query, )

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


def fetch_log_with_paging(qdict, limit, fetch):
  # Log api returns {'log':[list of commits], 'next': hash}.
  last_result = fetch(qdict)
  commits = last_result['log']
  while last_result.get('next') and len(commits) < limit:
    qdict['s'] = last_result.get('next')
    last_result = fetch(qdict)
    # The first commit in `last_result` is not necessarily the parent of the
    # last commit in result so far!  This is because log command can be done on
    # one file object (for example,
    # https://gerrit.googlesource.com/gitiles/+log/1c21279f337da813062950959ac3d39d262883ae/COPYING)
    # Even when getting log for the whole repository, there could be merge
    # commits.
    commits.extend(last_result['log'])
  # Use 'next' field (if any) from last_result, but commits aggregated from
  # all the results. This essentially imitates paging with at least
  # `limit` page size.
  last_result['log'] = commits
  logging.debug('fetched %d commits, next: %s.', len(commits), last_result.get('next'))
  return last_result

def main(arguments):
  parser = create_argparser()
  args = parser.parse_args(arguments)

  parsed_url = urlparse.urlparse(args.url)
  if not parsed_url.scheme.startswith('http'):
    parser.error('Invalid URI scheme (expected http or https): %s' % args.url)

  qdict = {}
  if parsed_url.query:
    qdict.update(urlparse.parse_qs(parsed_url.query))
  # Force the format specified on command-line.
  if qdict.get('format'):
    parser.error('URL must not contain format; use --format command line flag '
                 'instead.')
  qdict['format'] = args.format

  # Choose handler.
  if args.format == 'json':
    def handler(conn):
      return ReadHttpJsonResponse(conn)
  elif args.format == 'text':
    # Text fetching will pack the text into structured JSON.
    def handler(conn):
      result = ReadHttpResponse(conn).read()
      if not result:
        return None
      # Wrap in a structured JSON for export to recipe module.
      return {
        'value': result,
      }

  if args.log_start:
    qdict['s'] = args.log_start

  def fetch(qdict):
    parsed_url_with_query = reparse_url(parsed_url, qdict)
    result = gitiles_get(parsed_url_with_query, handler, args.attempts)
    if not args.quiet:
      logging.info('Read from %s: %s', parsed_url_with_query.geturl(), result)
    return result

  if args.log_limit:
    if args.format != 'json':
      parser.error('--log-limit works with json format only')
    result = fetch_log_with_paging(qdict, args.log_limit, fetch)
  else:
    # Either not a log request, or don't care about paging.
    # So, just return whatever is fetched the first time.
    result = fetch(qdict)

  with open(args.json_file, 'w') as json_file:
    json.dump(result, json_file)
  return 0


def create_argparser():
  parser = argparse.ArgumentParser()
  parser.add_argument('-j', '--json-file', required=True,
      help='Path to json file for output.')
  parser.add_argument('-f', '--format', required=True,
      choices=('json', 'text'))
  parser.add_argument('-u', '--url', required=True,
      help='Url of gitiles. For example, '
           'https://chromium.googlesource.com/chromium/src/+refs. '
           'Insert a/ after domain for authenticated access.')
  parser.add_argument('-a', '--attempts', type=int, default=1,
      help='The number of attempts to make (with exponential backoff) before '
           'failing. If several requests are to be made, applies per each '
           'request separately.')
  parser.add_argument('-q', '--quiet', action='store_true',
      help='Suppress file contents logging output.')
  parser.add_argument('--log-limit', type=int, default=None,
      help='Follow gitiles pages to fetch at least this many commits. By '
           'default, first page with unspecified number of commits is fetched. '
           'Only for https://<hostname>/<repo>/+log/... gitiles request.')
  parser.add_argument('--log-start',
      help='If given, continue fetching log by paging from this commit hash. '
           'This value can be typically be taken from json result of previous '
           'call to log, which returns next page start commit as "next" key. '
           'Only for https://<hostname>/<repo>/+log/... gitiles request.')
  return parser


if __name__ == '__main__':
  logging.basicConfig()
  logging.getLogger().setLevel(logging.INFO)
  sys.exit(main(sys.argv[1:]))
