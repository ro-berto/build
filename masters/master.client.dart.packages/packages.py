# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PACKAGES = [
  {
    'name' : 'core-elements',
  },
  {
    'name' : 'paper-elements',
    'package_dependencies' : ['core-elements'],
  },
  {
    'name' : 'dart-protobuf',
  },
  {
    'name' : 'gcloud',
  },
  {
    'name' : 'googleapis_auth',
    'package_dependencies' : [],
  },
]
