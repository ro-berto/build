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
  {
    'name' : 'custom-element-apigen',
  },
  {
    'name' : 'smoke',
  },
  # Packages in the github project google
  {
    'name' : 'serialization.dart',
    'github_project' : 'google'
  },
  # Github samples
  {
    'name' : 'sample-dcat',
    'is_sample' : True,
  },
  {
    'name' : 'sample-dgrep',
    'is_sample' : True,
  },
  {
    'name' : 'sample-sunflower',
    'is_sample' : True,
  },
  {
    'name' : 'sample-todomvc-polymer',
    'is_sample' : True,
  },
  {
    'name' : 'sample-dartiverse-search',
    'is_sample' : True,
  },
  {
    'name' : 'sample-clock',
    'is_sample' : True,
  },
  {
    'name' : 'sample-gauge',
    'is_sample' : True,
  },
  {
    'name' : 'sample-google-maps',
    'is_sample' : True,
  },
  {
    'name' : 'sample-jsonp',
    'is_sample' : True,
  },
  {
    'name' : 'sample-multi-touch',
    'is_sample' : True,
  },
  {
    'name' : 'sample-polymer-intl',
    'is_sample' : True,
  },
  {
    'name' : 'sample-searchable-list',
    'is_sample' : True,
  },
  {
    'name' : 'sample-solar',
    'is_sample' : True,
  },
  {
    'name' : 'sample-spirodraw',
    'is_sample' : True,
  },
  {
    'name' : 'sample-swipe',
    'is_sample' : True,
  },
  {
    'name' : 'sample-tracker',
    'is_sample' : True,
  },
]

GITHUB_PACKAGES = [
  p for p in PACKAGES if (not p.get('is_sample') and not p.get('is_repo'))
]

GITHUB_SAMPLES = [
  p for p in PACKAGES if (p.get('is_sample') and not p.get('is_repo'))
]
