deps = {
  'depot_tools':
    'https://chromium.googlesource.com/chromium/tools/depot_tools.git',
}

hooks = [
  {
    "name": "remove_orphaned_pycs",
    "pattern": ".",
    "action": [
      "python", "-u", "build/scripts/common/remove_orphaned_pycs.py",
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
