#!/usr/bin/python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A simple client for the crrev.com API.

API Explorer page: https://goo.gl/5ThLDm

Example usage:
  ./crrev_client.py redirect/368595
  ./crrev_client.py numbering/10b9b4435e25fb8ede2122482426ae81c7980630
"""

import argparse
import json
import logging
import os
import sys
import time
import urllib

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..', '..', '..', '..'))
import common.env
common.env.Install()

import requests

_BASE_URI = 'https://cr-rev.appspot.com/_ah/api/crrev/v1'


def crrev_get(path, params, attempts):
  """Makes a GET request to the crrev API.

  Args:
    path: Request path with query string.
    params: A dict or pair-list of query parameters.
    attempts: Number of attempts to retry the request.

  Returns:
    The object parsed from the response JSON.
  """
  assert attempts >= 1
  retry_delay_seconds = 1
  for attempt in range(1, attempts + 1):
    url = '%s/%s?%s' % (_BASE_URI, path, urllib.urlencode(params))
    try:
      response = requests.get(url, verify=True)
      if response.status_code == 404:
        raise ValueError('Response status 404 for request to %s.' % url)
      return json.loads(response.text)
    except requests.RequestException as e:
      if attempt >= attempts:
        raise
      logging.exception('Failed to request from crrev: %s', e)

    logging.info('Sleeping %d seconds before retry (%d/%d).',
                 retry_delay_seconds, attempt, attempts)
    time.sleep(retry_delay_seconds)
    retry_delay_seconds *= 2


def main(args):
  parser = argparse.ArgumentParser()
  parser.add_argument('path', help='Path + query to add onto the base URL.')
  parser.add_argument('--params-file', help='Request parameter JSON file.')
  parser.add_argument('--attempts', type=int, default=1,
                      help='Number of times to retry.')
  args = parser.parse_args(args)
  params = {}
  if args.params_file:
    params = json.load(open(args.params_file))
  return json.dumps(crrev_get(args.path, params, args.attempts), indent=2)


if __name__ == '__main__':
  print main(sys.argv[1:])
