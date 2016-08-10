deps = {
  'build/scripts/gsd_generate_index':
    'https://chromium.googlesource.com/chromium/tools/gsd_generate_index.git',
  'build/scripts/private/data/reliability':
    'https://chromium.googlesource.com/chromium/src/chrome/test/data/reliability.git',
  'build/scripts/tools/deps2git':
    'https://chromium.googlesource.com/chromium/tools/deps2git.git',
  'build/third_party/gsutil':
    'https://chromium.googlesource.com/external/gsutil/src.git'
    '@5cba434b828da428a906c8197a23c9ae120d2636',
  'build/third_party/gsutil/boto':
    'https://chromium.googlesource.com/external/boto.git'
    '@98fc59a5896f4ea990a4d527548204fed8f06c64',
  'build/third_party/infra_libs':
    'https://chromium.googlesource.com/infra/infra/packages/infra_libs.git'
    '@a13e6745a4edd01fee683e4157ea0195872e64eb',
  'build/third_party/lighttpd':
    'https://chromium.googlesource.com/chromium/deps/lighttpd.git'
    '@9dfa55d15937a688a92cbf2b7a8621b0927d06eb',
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
    "pattern": ".",
    "action": [
      "python", "-u", "build/scripts/common/remove_orphaned_pycs.py",
    ],
  },
  {
    "name": "cros_chromite",
    "pattern": r".*/cros_chromite_pins\.json",
    "action": [
      "python", "build/scripts/tools/runit.py", "python",
      "build/scripts/common/cros_chromite.py", "-v",
    ],
  },
]
