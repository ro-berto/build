#!/usr/bin/python
#
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Print the results of the bisection."""

import fileinput
import json
import sys


def main(unused_argv):
  """Parses json from stdin and prints it via _format_results."""
  json_results = ''.join(fileinput.input())
  results = json.loads(json_results)
  print _format_results(results)


def _format_results(results, prefix=''):
  """Recursively prints the contents of the given object.

  Args:
    results: the object to print/iterate over.
    prefix: optional string to prepend to each line (used for nesting)
  """
  # TODO(robertocn): Replace this with an actually readable format
  result_string = ''
  if isinstance(results, list):
    for i in xrange(len(results)):
      item = results[i]
      result_string += prefix + str(i) + ':\n'
      result_string += _format_results(item, prefix + '\t')
  elif isinstance(results, dict):
    for key in results:
      result_string += prefix
      result_string += key + ':\n'
      item = results[key]
      result_string += _format_results(item, prefix + '\t')
  else:
    result_string += prefix
    result_string += str(results) + '\n'
  return result_string

if __name__ == '__main__':
  sys.exit(main(sys.argv))
