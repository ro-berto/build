deps = {
  "build/scripts/gsd_generate_index":
    "svn://svn.chromium.org/chrome/trunk/tools/gsd_generate_index",

  "build/scripts/private/data/reliability":
    "svn://svn.chromium.org/chrome/trunk/src/chrome/test/data/reliability",

  "build/third_party/gsutil":
    "svn://svn.chromium.org/gsutil/trunk/src@263",

  "build/third_party/gsutil/boto":
    "svn://svn.chromium.org/boto@7",

  "build/third_party/lighttpd":
    "svn://svn.chromium.org/chrome/trunk/deps/third_party/lighttpd@58968",

  "build/scripts/tools/deps2git":
    "svn://svn.chromium.org/chrome/trunk/tools/deps2git",

  "depot_tools":
    "svn://svn.chromium.org/chrome/trunk/tools/depot_tools",
}

deps_os = {
  "unix": {
    "build/third_party/xvfb":
      "svn://svn.chromium.org/chrome/trunk/tools/third_party/xvfb",
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
    "pattern": r".*/cros_chromite\.py",
    "action": [
      "python", "build/scripts/tools/runit.py", "python",
          "build/scripts/common/cros_chromite.py", "-v",
    ],
  },
]
