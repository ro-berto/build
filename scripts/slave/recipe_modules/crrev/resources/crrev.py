#!/usr/bin/python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions for getting commit information from crrev.com.

Example usage:
  ./crrev.py commit_hash 368595
  ./crrev.py commit_position 10b9b4435e25fb8ede2122482426ae81c7980630
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..', '..', '..', '..'))
import common.env
common.env.Install()

import requests

_BASE_URL = 'https://cr-rev.appspot.com/_ah/api/crrev/v1'


def commit_hash(position):
  """Converts a commit position to a commit hash.

  Args:
    commit_position: An (int) commit position number in the chromium/src repo.

  Returns:
    A git commit hash as a string.

  Raises:
    ValueError: Couldn't convert this commit position to a commit hash.
  """
  url = '%s/%s/%s' % (_BASE_URL, 'redirect', position)
  response = requests.get(url, verify=True)
  if response.status_code == 404:
    raise ValueError('Commit not found: %s' % position)
  response_dict = json.loads(response.text)
  if response_dict.get('redirect_type') != 'GIT_FROM_NUMBER':
    raise ValueError('Unexpected redirect type %r for query %r.' %
                     (response_dict.get('redirect_type'), position))
  return response_dict['git_sha']


def commit_position(git_hash):
  """Converts a git hash to a commit position.

  Only works for repositories that have commit positions (e.g. chromium/src).

  Args:
    git_hash: A string with the full git hash.

  Returns:
    An int representing the commit position.

  Raises:
    ValueError: git_hash doesn't map to a commit, or the repository doesn't
        have commit positions.
  """
  commit = _commit_info(git_hash)
  if 'number' not in commit:
    raise ValueError("%s is in %s, which doesn't have commit positions." %
                     (git_hash, commit['repo']))
  return int(commit['number'])


def _commit_info(git_hash):
  """Returns information about a commit.

  Args:
    git_hash: A string with the full git hash.

  Returns:
    A dict with information about the commit. For example:
    {
      'git_sha': '0d30216f14e3f5620de722412d76cbdb7759ec42',
      'repo': 'chromium/src',
      'numberings': [
        {
          'number': '347565',
          'numbering_type': 'COMMIT_POSITION',
          'numbering_identifier': 'refs/heads/master'
        }
      ],
      'number': '347565',
      'project': 'chromium',
      'redirect_url': 'https://chromium.googlesource.com/chromium/src/+/0d30..',
      'kind': 'crrev#commitItem',
      'etag': '"kuKkspxlsT40mYsjSiqyueMe20E/QU1czZbwY_HKY12vV6JRLFPh2lI"'
    }

  Raises:
    ValueError: git_hash doesn't map to a commit.
  """
  url = '%s/%s/%s' % (_BASE_URL, 'commit', git_hash)
  response = requests.get(url, verify=True)
  if response.status_code == 404:
    raise ValueError('No commit with git hash %s.' % git_hash)
  return json.loads(response.text)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('request_type',
                      choices=['commit_hash', 'commit_position'])
  parser.add_argument('query')
  args = parser.parse_args()
  if args.request_type == 'commit_hash':
    print commit_hash(int(args.query))
  else:
    print commit_position(args.query)


if __name__ == '__main__':
  main()
