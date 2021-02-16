# The dependencies listed here ARE NOT USED on masters and slave machines.
# If changing something here you must also change it in these repos:
#   https://chrome-internal.googlesource.com/chrome/tools/build/slave.DEPS
#   https://chrome-internal.googlesource.com/chrome/tools/build/master.DEPS
#   https://chrome-internal.googlesource.com/chrome/tools/build/internal.DEPS
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
