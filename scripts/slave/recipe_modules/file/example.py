# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


DEPS = [
  'file',
  'raw_io',
]


TEST_CONTENTS = {
  'simple': 'abcde',
  'spaces': 'abcde fgh',
  'symbols': '! ~&&',
  'multiline': '''ab
cd
efg
''',
}


def GenSteps(api):
  for name, content in TEST_CONTENTS.iteritems():
    api.file.write('write_%s' % name, 'tmp_file.txt', content)
    actual_content = api.file.read(
        'read_%s' % name, 'tmp_file.txt',
        test_data=content
    )
    msg = 'expected %s but got %s' % (content, actual_content)
    assert actual_content == content, msg


def GenTests(api):
  yield api.test('file_io')

