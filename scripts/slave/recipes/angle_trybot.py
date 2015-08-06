# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'properties',
  'step',
]

def RunSteps(api):
  change_url = api.properties['event.change.url']
  api.step('print_gerrit_url', ['echo', 'Tryjob triggered: %s' % change_url])

def GenTests(api):
  gerrit_test_args = {
    'event.change.id': 'test.change.id',
    'event.change.number': 0,
    'event.change.url': 'test.url',
    'event.patchSet.ref': 'test.patch.ref'
  }
  yield api.test('basic') + api.properties(**gerrit_test_args)
