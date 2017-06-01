# Copyright (c) 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'halt',
]

def RunSteps(api):
  api.halt('Fake failure')

def GenTests(api):
  yield api.test('basic') + api.step_data('Recipe failed. Reason: Fake failure',
                                          retcode = 1)
