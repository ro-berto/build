deps = {
  "build/third_party/lighttpd":
    "/trunk/deps/third_party/lighttpd@58968",

# TODO(bradnelson): drop this once the runhooks has baked.
  "build/third_party/gsutil":
    "http://gsutil.googlecode.com/svn/trunk/src@43",

# TODO(bradnelson): switch to this once the runhook has baked.
#  "build/third_party/gsutil":
#    "svn://svn.chromium.org/gsutil/trunk/src@43",
#
#  "build/third_party/gsutil/boto":
#    "svn://svn.chromium.org/boto@1",

  "depot_tools":
    "/trunk/tools/depot_tools",
}

# TODO(bradnelson): drop this once the runhooks has baked.
hooks = [
  {
    "pattern": ".",
    "action": ["python", "-c", "import shutil; import os; shutil.rmtree('build/third_party/gsutil/boto', ignore_errors=True); os.system('rd /s /q build\\\\third_party\\\\gsutil\\\\boto'); os.system('svn checkout svn://svn.chromium.org/boto build/third_party/gsutil/boto')"],
  }
]
