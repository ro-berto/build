#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
import operator
import os
import subprocess
import sys
import tempfile


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))


BLACKLISTED_MASTERS = [
    'master.chromium.reserved',
    'master.chromiumos.unused',
    'master.client.reserved',
    'master.reserved',
    'master.tryserver.reserved',
]


def getMasterConfig(path):
  with tempfile.NamedTemporaryFile() as f:
    subprocess.check_call([
        os.path.join(BASE_DIR, 'scripts', 'tools', 'runit.py'),
        os.path.join(BASE_DIR, 'scripts', 'tools', 'dump_master_cfg.py'),
        os.path.join(path),
        f.name])
    return json.load(f)


def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('--only-nonrecipe', action='store_true')
  args = parser.parse_args()

  data = []

  for master in os.listdir(os.path.join(BASE_DIR, 'masters')):
    if master in BLACKLISTED_MASTERS:
      continue

    path = os.path.join(BASE_DIR, 'masters', master)
    if not os.path.isdir(path):
      continue

    config = getMasterConfig(path)
    for builder in config['builders']:
      try:
        recipe = builder['factory']['properties'].get(
            'recipe', ['<no recipe>'])[0]
      except Exception as e:
        recipe = '<error: %r>' % e

      if (args.only_nonrecipe and
          recipe != '<no recipe>' and
          not recipe.startswith('<error:')):
        continue
      data.append({
        'master': master,
        'builder': builder['name'],
        'recipe': recipe,
      })

  master_padding = max(len(row['master']) for row in data)
  builder_padding = max(len(row['builder']) for row in data)

  pattern = '%%-%ds | %%-%ds | %%s' % (master_padding, builder_padding)
  for row in sorted(data, key=operator.itemgetter('master', 'builder')):
    print pattern % (row['master'], row['builder'], row['recipe'])

  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
