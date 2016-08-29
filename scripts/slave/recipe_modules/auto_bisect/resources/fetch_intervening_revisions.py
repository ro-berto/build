#!/usr/bin/python
#
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Gets list of revisions between two commits and their commit positions.

Example usage:
  ./fetch_intervening_revisions.py 343b531d31 7b43807df3 \
    https://chromium.googlesource.com/chromium/src

Note: Another implementation of this functionality can be found in
findit/common/git_repository.py (https://goo.gl/Rr8j9O) and in the
gitiles recipe module.
"""

import argparse
import json
import os
import re
import sys
import urllib2

_GITILES_PADDING = ')]}\'\n'
_URL_TEMPLATE = ('https://chromium.googlesource.com/%s/+log/%s..%s'
                 '?format=json&n=%d')

# Gitiles paginates the list of commits; since we want to get all of the
# commits at once, the page size should be larger than the largest revision
# range that we expect to get.
_PAGE_SIZE = 512


def fetch_intervening_revisions(start, end, base_url):
  """Fetches a list of revision in between two commits.

  Args:
    start (str): A git commit hash in the Chromium src repository.
    end (str): Another git commit hash, after start.
    base_url (str): A repository gitiles URL.

  Returns:
    A list of pairs (commit hash, commit position), from earliest to latest,
    for all commits in between the two given commits, including the end commit
    but not the start commit.

  Raises:
    urllib2.URLError: The request to gitiles failed.
    ValueError: The response wasn't valid JSON.
    KeyError: The JSON didn't contain the expected data.
  """
  revisions = _fetch_range_from_gitiles(start, end, base_url)
  # The response from gitiles includes the end revision and is ordered
  # from latest to earliest.
  return [_commit_pair(r) for r in reversed(revisions)]


def _fetch_range_from_gitiles(start, end, base_url):
  """Fetches a list of revision dicts from gitiles.

  Make multiple requests to get multiple pages, if necessary.
  """
  revisions = []
  url = '%s/+log/%s..%s?format=json&n=%d' % (base_url, start, end, _PAGE_SIZE)
  current_page_url = url
  while True:
    response = urllib2.urlopen(current_page_url).read()
    response_json = response[len(_GITILES_PADDING):]  # Remove padding.
    response_dict = json.loads(response_json)
    revisions.extend(response_dict['log'])
    if 'next' not in response_dict:
      break
    current_page_url = url + '&s=' + response_dict['next']
  return revisions


def _commit_pair(commit_dict):
  return (commit_dict['commit'],
          _commit_position_from_message(commit_dict['message']))


def _commit_position_from_message(message):
  for line in reversed(message.splitlines()):
    if line.startswith('Cr-Commit-Position:'):
      return line.split('#')[1].split('}')[0]
  return None


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('start')
  parser.add_argument('end')
  parser.add_argument('url')
  args = parser.parse_args()
  revision_pairs = fetch_intervening_revisions(
      args.start, args.end, args.url)
  print json.dumps(revision_pairs)


if __name__ == '__main__':
  main()
