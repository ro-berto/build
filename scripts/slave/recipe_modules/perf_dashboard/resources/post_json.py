# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Standalone python script to post a json blob to a given url."""

import argparse
import json
import os
import sys

# Add requests to path
RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(
  RESOURCE_DIR, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(BASE_DIR, 'third_party', 'requests_1_2_3'))

import requests


def main():
  args = parse_arguments()
  data = json.load(sys.stdin)
  response = requests.post(args.url, data=data)
  print_response(response, args.output)


def parse_arguments():
  parser = argparse.ArgumentParser()
  parser.add_argument('url', help='URL to post to.')
  parser.add_argument('-o', '--output',
                      help='Output file for response in JSON format.')
  return parser.parse_args()


def print_response(response, output_file=None):
  result = {
    'status_code': response.status_code,
    'text': response.text,
  }

  if output_file:
    output_file = open(output_file, 'w')
  else:
    output_file = sys.stdout

  json.dump(result, output_file, indent=4, sort_keys=True)


if __name__ == '__main__':
  sys.exit(main())
