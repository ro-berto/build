# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import sys
from strategies import strategies


def main(argv):
  """Entrypoint for the execution of a strategy on a swarming task."""
  print(argv)


if __name__ == '__main__':
  main(sys.argv)
