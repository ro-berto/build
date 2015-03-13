#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A script to filter out duplicate analysis targets from a compilation
database. The script takes two compilation database files as input and
removes all compilation units from one database that occur also in the
other database.
"""

import argparse
import json
import os
import sys

def _GetCompilationDatabase(compdb_path):
  with open(compdb_path, 'rb') as json_commands_file:
    return json.load(json_commands_file)

def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('--compdb_input', default=None, required=True,
                      help='path to the compilation database to be filtered')
  parser.add_argument('--compdb_filter', default=None, required=True,
                      help='path to compilation database used for filtering')
  parser.add_argument('--compdb_output', default=None, required=True,
                      help='path of resulting filtered compilation database')
  options = parser.parse_args(argv)
  compilation_database = _GetCompilationDatabase(options.compdb_input)
  compilation_database_filter = _GetCompilationDatabase(options.compdb_filter)

  # Store all files representing the analysis target of a compilation unit in a
  # set. This is used for filtering out duplicates.
  compilation_units = set()
  for entry in compilation_database_filter:
    compilation_units.add(os.path.join(entry['directory'], entry['file']))

  # Now exclude all compilation units whose analysis target already appears in
  # the other compilation database.
  output = []
  for entry in compilation_database:
    if os.path.join(entry['directory'], entry['file']) not in compilation_units:
      output.append(entry)
  with open(options.compdb_output, 'wb') as output_file:
    output_file.write(json.dumps(output, indent=2))
  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
