hooks = [
  {
    "name": "remove_orphaned_pycs",
    "pattern": ".",
    "action": [
      "python3", "-u", "build/hook-scripts/remove_orphaned_pycs.py",
    ],
  },
  {
    "name": "vpython_sync",
    "pattern": ".",
    "action": [
      "vpython",
      "-vpython-spec", "build/.vpython",
      "-vpython-tool", "install",
    ],
  },
]
