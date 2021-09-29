#!/usr/bin/env vpython3

# [VPYTHON:BEGIN]
# wheel: <
#   name: "infra/python/wheels/psutil/${vpython_platform}"
#   version: "version:5.8.0.chromium.2"
# >
# [VPYTHON:END]

import psutil
import sys


def main():
  assert len(sys.argv) == 2, 'PID is the 1st and only argument to this script.'
  pid = int(sys.argv[1])
  proc = psutil.Process(pid)
  print(proc.memory_full_info())


if __name__ == '__main__':
  sys.exit(main())
