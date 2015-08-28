#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import json
import os
import subprocess
import sys
import urllib2


"""Wrapper for appurify-client.py which avoids hard-coding credentials."""


def get_from_file(key):
  filepath = os.path.join(os.path.expanduser('~'), '.%s' % key)
  with open(filepath) as f:
    return f.read().rstrip()


def run_no_except(cmd):
  """Run the given command and don't let any exceptions propagate."""
  try:
    return subprocess.check_output(cmd)
  except:
    raise Exception('Command failed')


def main():
  # Find credentials.
  key = get_from_file('appurify_key')
  secret = get_from_file('appurify_secret')

  # Obtain an access token.
  creds_output = run_no_except([
      'appurify-client.py', '--api-key', key, '--api-secret', secret,
      '--action', 'access_token_generate'])
  token = eval(creds_output)['response']['access_token']

  # Run the given command.
  run_no_except(['appurify-client.py', '--access-token', token] + sys.argv[1:])


if __name__ == '__main__':
  main()
