#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import base64
import json
import os
import sys
import zlib

sys.path.insert(0,
    os.path.join(os.path.dirname(__file__), os.pardir))
    # (/path/to/build/scripts)
import common.env
common.env.Install()

from common import chromium_utils

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-o', '--out', default=sys.stdout,
      help='Write the output content here. If omitted, output will be written '
           'to STDOUT.')
  def add_value_arg(p):
    p.add_argument('value', nargs='?',
        help='The intput content. If omitted, content will be read from STDIN.')
  subparsers = parser.add_subparsers()

  # encode
  p = subparsers.add_parser('encode')
  def encode(value, out):
    obj = json.loads(value)
    out.write(chromium_utils.b64_gz_json_encode(obj))
  p.set_defaults(func=encode)
  add_value_arg(p)

  # decode
  p = subparsers.add_parser('decode')
  def decode(value, out):
    obj = chromium_utils.convert_gz_json_type(value)
    json.dump(obj, out, sort_keys=True, separators=(',', ':'))
  p.set_defaults(func=decode)
  add_value_arg(p)

  opts = parser.parse_args()

  # Read input value.
  value = opts.value
  if not value:
    value = sys.stdin.read()

  # Generate output.
  opts.func(value, opts.out)
  return 0


if __name__ == '__main__':
  sys.exit(main())
