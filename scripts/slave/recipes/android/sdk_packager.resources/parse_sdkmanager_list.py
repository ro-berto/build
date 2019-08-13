# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Parses the output of `sdkmanager --list --verbose` into a JSON.

The emitted JSON takes the following form:

  {
    'available': [
      {
        'name': '{package name}',
        'descripition': '{package description}',
        'version', '{package version}',
        'installed location': null
      },
      ... # additional available packages
    ],
    'installed': [
      {
        'name': '{package name}',
        'descripition': '{package description}',
        'version', '{package version}',
        'installed location': '/path/to/installed/location'
      },
      ... # additional installed packages
    ]
  }

If the provided input cannot be parsed, no JSON will be emitted.
"""

from __future__ import print_function

import argparse
import json
import re
import os
import sys


_KNOWN_PACKAGE_INFO_TYPES = [
    'description', 'version', 'installed location']

PACKAGE_INFO_RE = re.compile(r'\s+([a-zA-Z ]+):\s+(.*)$')
PACKAGE_NAME_RE = re.compile(r'^[a-zA-Z0-9;\.\-_]+$')
PACKAGES_HEADER_RE = re.compile(
    r'^([a-z]+) packages:\s*$', flags=re.IGNORECASE)
SEPARATOR_RE = re.compile(r'^[\s-]+$')
UPDATES_HEADER_RE = re.compile(
    r'([a-z]+) updates:', flags=re.IGNORECASE)


def ParseSdkManagerList(raw):

  available_packages = []
  installed_packages = []

  current_package = None
  current_section = None

  for line in raw.splitlines():
    if not line:
      if current_section is not None and current_package:
        current_section.append(current_package)
        current_package = None
      continue

    m = SEPARATOR_RE.match(line)
    if m:
      continue

    m = PACKAGE_INFO_RE.match(line)
    if m:
      info_type = m.group(1).lower()
      info = m.group(2)
      if info_type in _KNOWN_PACKAGE_INFO_TYPES:
        if current_package is None:
          print('Orphaned package description: "%s"' % line)
        else:
          current_package[info_type] = info
      continue

    m = PACKAGE_NAME_RE.match(line)
    if m:
      current_package = {
          'name': m.group(0),
          'description': None,
          'version': None,
          'installed location': None,
      }
      continue

    m = PACKAGES_HEADER_RE.match(line)
    if m:
      header_name = m.group(1).lower()
      if header_name == 'available':
        current_section = available_packages
      elif header_name == 'installed':
        current_section = installed_packages
      else:
        print('Unrecognized header name: "%s"' % header_name)
      continue

    m = UPDATES_HEADER_RE.match(line)
    if m:
      current_section = None
      continue

    # Ignore otherwise.

  if current_section is not None and current_package:
    current_section.append(current_package)

  return {
      'available': available_packages,
      'installed': installed_packages,
  }


def main(raw_args):
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--raw-input', required=True, type=os.path.realpath,
      help='Path from which raw output from `sdkmanager --list --verbose` '
           'will be read.')
  parser.add_argument(
      '--json-output', required=True, type=os.path.realpath,
      help='Path to which the output JSON will be written.')
  args = parser.parse_args(raw_args)

  with open(args.raw_input) as raw_input_file:
    raw = raw_input_file.read()

  parsed = ParseSdkManagerList(raw)
  with open(args.json_output) as json_output_file:
    json.dump(parsed, json_output_file)

  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
