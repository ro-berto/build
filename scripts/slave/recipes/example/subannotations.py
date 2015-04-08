# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'python',
  'step',
]

def GenSteps(api):
  result = api.python.inline('subannotator',
      """
      import sys
      print 'Some output...'
      print '@@@BUILD_STEP a build step@@@'
      print 'Some output inside a build step'
      print '@@@STEP_TEXT@this is step text@@@'
      print '@@@BUILD_STEP another build step@@@'
      """,
      allow_subannotations=True)
  result.presentation.step_text = 'Wooot!'

  api.python.inline('disallowed subannotator',
      """
      import sys
      print 'Some output...'
      print '@@@BUILD_STEP a unique build step@@@'
      print 'Some output inside a build step'
      print '@@@STEP_TEXT@this is step text@@@'
      print '@@@BUILD_STEP another build step@@@'
      """)

  api.python.inline('subannotator',
      """
      import sys
      print 'Some output...'
      print '@@@BUILD_STEP a unique build step@@@'
      print 'Some output inside a build step'
      print '@@@STEP_TEXT@this is step text@@@'
      print '@@@BUILD_STEP another build step@@@'
      sys.exit(1)
      """,
      allow_subannotations=True)

  api.step('post run', ['echo', 'post_run'])

def GenTests(api):
  yield api.test('basic')
