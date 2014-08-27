deps = {
  "build/scripts/gsd_generate_index":
    "/trunk/tools/gsd_generate_index",

  "build/scripts/private/data/reliability":
    "/trunk/src/chrome/test/data/reliability",

  "build/third_party/gsutil":
    "svn://svn.chromium.org/gsutil/trunk/src@263",

  "build/third_party/gsutil/boto":
    "svn://svn.chromium.org/boto@7",

  "build/third_party/lighttpd":
    "/trunk/deps/third_party/lighttpd@58968",

  "build/scripts/tools/deps2git":
    "svn://svn.chromium.org/chrome/trunk/tools/deps2git@291329",

  "commit-queue":
    "/trunk/tools/commit-queue",

  "depot_tools":
    "/trunk/tools/depot_tools",
}

deps_os = {
  "unix": {
    "build/third_party/cbuildbot_chromite":
      "https://chromium.googlesource.com/chromiumos/chromite.git",

    "build/third_party/xvfb":
      "/trunk/tools/third_party/xvfb",
  },
}

hooks = [
  {
    # Removes lone *.pyc files which have no corresponding *.py files.
    # TODO(sergiyb): This is not called by gclient, when build/ repo is checked
    # out recursively via DEPS at recursion level 2. This is a bug in glcient,
    # which needs to be fixed.
    "name": "remove_lone_pyc_files",
    "pattern": ".",
    "action": [
        "python", "scripts/tools/remove_lone_pyc_files.py",
    ],
  },
]
