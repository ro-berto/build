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
    '@5cba434b828da428a906c8197a23c9ae120d2636',
  'build/third_party/gsutil/boto':
    'https://chromium.googlesource.com/external/boto.git'
    '@98fc59a5896f4ea990a4d527548204fed8f06c64',
  'build/third_party/infra_libs':
    'https://chromium.googlesource.com/infra/infra/packages/infra_libs.git'
    '@5449f9992033c08541ffbfa62941e248f734a097',
  'build/third_party/pyasn1':
    'https://chromium.googlesource.com/external/github.com/etingof/pyasn1.git'
    '@4181b2379eeae3d6fd9f4f76d0e6ae3789ed56e7',
  'build/third_party/pyasn1-modules':
    'https://chromium.googlesource.com/external/github.com/etingof/pyasn1-modules.git'
    '@956fee4f8e5fd3b1c500360dc4aa12dc5a766cb2',
  'build/third_party/python-rsa':
    'https://chromium.googlesource.com/external/github.com/sybrenstuvel/python-rsa.git'
    '@version-3.1.4',
  'depot_tools':
    'https://chromium.googlesource.com/chromium/tools/depot_tools.git',
}

deps_os = {
  'unix': {
    'build/third_party/xvfb':
      'https://chromium.googlesource.com/chromium/tools/third_party/xvfb.git',
  },
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
    "name": "cros_chromite",
    "pattern": r".*/cros_chromite_pins\.json",
    "action": [
      "python", "build/scripts/tools/runit.py",
      "--with-third-party-lib", "--", "python",
      "build/scripts/common/cros_chromite.py", "-v",
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
