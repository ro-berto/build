# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Packages that lives in the dart-lang github repo.
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

# Packages that lives in the google github repo.
GOOGLE_PACKAGES = [
  {
    'name' : 'serialization.dart',
  },
]

# Packages that we test from the dart repo.
DART_REPO_SAMPLES = [
  {
    'name' : 'polymer_intl',
  },
  {
    'name' : 'todomvc',
  },
]

DART_REPO_PACKAGES = [

]


PACKAGES = DART_PACKAGES + GOOGLE_PACKAGES + DART_REPO_SAMPLES
