# Copyright 2020 The LUCI Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.


PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
  'chromiumdash',
]

def RunSteps(api):
  api.chromiumdash.releases('Android', 'Beta', 1)
  api.chromiumdash.milestones(3, only_branched=True)
  api.chromiumdash.fetch_commit_info('abcdefg')


def GenTests(api):
  yield api.test('basic')
