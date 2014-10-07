# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Packages that we test:
#   We default to github-project dart-lang
#   is_sample means that we will append sample to the name
#   is_repo means if something is living in the dart repository, we will add
#     this to the name as well.
PACKAGES = [
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
  # Packages in the github project google
  {
    'name' : 'serialization.dart',
    'github_project' : 'google'
  },
  # Repo samples
  {
    'name' : 'polymer_intl',
    'is_sample' : True,
    'is_repo' : True
  },
  {
    'name' : 'todomvc',
    'is_sample' : True,
    'is_repo' : True
  },
]

GITHUB_PACKAGES = [
  p for p in PACKAGES if (not p.get('is_sample') and not p.get('is_repo'))
]

DART_REPO_SAMPLES = [
  p for p in PACKAGES if p.get('is_sample') and p.get('is_repo')
]
