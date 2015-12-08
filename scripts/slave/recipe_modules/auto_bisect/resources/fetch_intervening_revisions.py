#!/usr/bin/python
#
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Gets list of revisions between two commits and their commit positions.

Example usage:
  ./fetch_intervening_revisions.py 343b531d31 7b43807df3
  ./fetch_intervening_revisions.py 235eff9574 1e4681c33f --depot v8
"""

import argparse
import json
import os
import re
import sys
import urllib2

_GITILES_PADDING = ')]}\'\n'
_URL_TEMPLATE = 'https://chromium.googlesource.com/%s/+log/%s..%s?format=json'

# Gitiles paginates the list of commits; since we want to get all of the
# commits at once, the page size should be larger than the largest revision
# range that we expect to get.
_PAGE_SIZE = 2048

_DEPOT_PATH_MAP = {
    'chromium': 'chromium/src',
    'angle': 'angle/angle',
    'v8': 'v8/v8.git',
    'skia': 'skia',
}

def fetch_intervening_revisions(min_rev, max_rev, depot_name):
  """Fetches a list of revision in between two commits.

  Args:
    min_rev (str): A git commit hash in the Chromium src repository.
    max_rev (str): Another git commit hash, after min_rev.
    depot_name (str): A respository name.

  Returns:
    A list of pairs (commit hash, commit position), from earliest to latest,
    for all commits in between the two given commits, not including either
    of the given commits.

  Raises:
    urllib2.URLError: The request to gitiles failed.
    ValueError: The response wasn't valid JSON.
    KeyError: The JSON didn't contain the expected data.
  """
  url = _URL_TEMPLATE % (_DEPOT_PATH_MAP[depot_name], min_rev, max_rev)
  url += '&n=%d' % _PAGE_SIZE
  response = urllib2.urlopen(url).read()
  response_json = response[len(_GITILES_PADDING):]  # Remove padding.
  response_dict = json.loads(response_json)
  intervening_revisions = response_dict['log'][1:]
  return [(r['commit'], _commit_position_from_message(r['message']))
          for r in reversed(intervening_revisions)]


def _commit_position_from_message(message):
  for line in reversed(message.splitlines()):
    if line.startswith('Cr-Commit-Position:'):
      return line.split('#')[1].split('}')[0]
  return None


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('min_rev')
  parser.add_argument('max_rev')
  parser.add_argument(
      '--depot', default='chromium', choices=list(_DEPOT_PATH_MAP))
  args = parser.parse_args()
  revisions = fetch_intervening_revisions(
      args.min_rev, args.max_rev, args.depot)
  print json.dumps(revisions)


if __name__ == '__main__':
  main()
