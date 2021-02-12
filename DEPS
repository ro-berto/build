# The dependencies listed here ARE NOT USED on masters and slave machines.
# If changing something here you must also change it in these repos:
#   https://chrome-internal.googlesource.com/chrome/tools/build/slave.DEPS
#   https://chrome-internal.googlesource.com/chrome/tools/build/master.DEPS
#   https://chrome-internal.googlesource.com/chrome/tools/build/internal.DEPS
deps = {
  'build/scripts/gsd_generate_index':
    'https://chromium.googlesource.com/chromium/tools/gsd_generate_index.git',
  'build/scripts/private/data/reliability':
    'https://chromium.googlesource.com/chromium/src/chrome/test/data/reliability.git',
  'build/third_party/gsutil':
    'https://chromium.googlesource.com/external/gsutil/src.git'
    + '@5cba434b828da428a906c8197a23c9ae120d2636',
  'build/third_party/gsutil/boto':
    'https://chromium.googlesource.com/external/boto.git'
    + '@98fc59a5896f4ea990a4d527548204fed8f06c64',
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
