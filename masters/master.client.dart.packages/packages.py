# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DART_PACKAGES = [
  {
    'name' : 'core-elements',
  },
  {
    'name' : 'dart-protobuf',
  },
  {
    'name' : 'gcloud',
  },
  {
    'name' : 'googleapis_auth',
  },
  {
    'name' : 'html5lib',
  },
  {
    'name' : 'code-transformers',
  },
  {
    'name' : 'observe',
  },
  {
    'name' : 'paper-elements',
  },
  {
    'name' : 'polymer-dart',
  },
  {
    'name' : 'polymer-expressions',
  },
  {
    'name' : 'template-binding',
  },
  {
    'name' : 'web-components',
  },
]

GOOGLE_PACKAGES = [
  {
    'name' : 'serialization.dart',
  },
]

PACKAGES = DART_PACKAGES + GOOGLE_PACKAGES
