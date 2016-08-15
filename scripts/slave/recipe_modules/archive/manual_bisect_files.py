# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Defines variables necessary to make lightweight linux perf builds.

Declares required files to run manual bisect script on chrome Linux
builds in perf. Binary files that should be stripped to reduce zip file
size are declared. The file list was gotten from the local chrome 
executable path in Linux. (This can be retrieved by typing 'chrome://version'
in chrome and following the executable path. The list needs to be updated if
future chrome versions require additional files.
"""

CHROME_REQUIRED_FILES = [
  'chrome',
  'chrome_100_percent.pak',
  'chrome_200_percent.pak',
  'default_apps',
  'icudtl.dat',
  'libwidevinecdm.so',
  'locales',
  'nacl_helper',
  'nacl_helper_bootstrap',
  'nacl_irt_x86_64.nexe',
  'natives_blob.bin',
  'PepperFlash',
  'product_logo_48.png'
  'resources.pak',
  'snapshot_blob.bin',
  'xdg-mime',
  'xdg-settings',
]


CHROME_STRIP_LIST = [
  'chrome',
  'nacl_helper'
]