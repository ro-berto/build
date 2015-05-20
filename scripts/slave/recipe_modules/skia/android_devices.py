# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import collections


DEFAULT_SDK_ROOT = '/home/chrome-bot/android-sdk-linux'
MAC_SDK_ROOT = '/Users/chrome-bot/adt-bundle-mac-x86_64-20140702/sdk'

SlaveInfo = collections.namedtuple('SlaveInfo',
                                   'serial android_sdk_root has_root')

SLAVE_INFO = {
  'skiabot-mac-10_8-compile-000':
      SlaveInfo('noserial', MAC_SDK_ROOT, True),
  'skiabot-mac-10_8-compile-001':
      SlaveInfo('noserial', MAC_SDK_ROOT, True),
  'skiabot-mac-10_8-compile-002':
      SlaveInfo('noserial', MAC_SDK_ROOT, True),
  'skiabot-mac-10_8-compile-003':
      SlaveInfo('noserial', MAC_SDK_ROOT, True),
  'skiabot-mac-10_8-compile-004':
      SlaveInfo('noserial', MAC_SDK_ROOT, True),
  'skiabot-mac-10_8-compile-005':
      SlaveInfo('noserial', MAC_SDK_ROOT, True),
  'skiabot-mac-10_8-compile-006':
      SlaveInfo('noserial', MAC_SDK_ROOT, True),
  'skiabot-mac-10_8-compile-007':
      SlaveInfo('noserial', MAC_SDK_ROOT, True),
  'skiabot-mac-10_8-compile-008':
      SlaveInfo('noserial', MAC_SDK_ROOT, True),
  'skiabot-mac-10_8-compile-009':
      SlaveInfo('noserial', MAC_SDK_ROOT, True),
  'skiabot-shuttle-ubuntu12-galaxys3-001':
      SlaveInfo('4df713b8244a21cf', DEFAULT_SDK_ROOT, False),
  'skiabot-shuttle-ubuntu12-galaxys3-002':
      SlaveInfo('32309a56e9b3a09f', DEFAULT_SDK_ROOT, False),
  'skiabot-shuttle-ubuntu12-galaxys4-001':
      SlaveInfo('4d0032a5d8cb6125', DEFAULT_SDK_ROOT, False),
  'skiabot-shuttle-ubuntu12-galaxys4-002':
      SlaveInfo('4d00353cd8ed61c3', DEFAULT_SDK_ROOT, False),
  'skiabot-shuttle-ubuntu12-nexus5-001':
      SlaveInfo('03f61449437cc47b', DEFAULT_SDK_ROOT, True),
  'skiabot-shuttle-ubuntu12-nexus5-002':
      SlaveInfo('018dff3520c970f6', DEFAULT_SDK_ROOT, True),
  'skiabot-shuttle-ubuntu12-nexus7-001':
      SlaveInfo('015d210a13480604', DEFAULT_SDK_ROOT, True),
  'skiabot-shuttle-ubuntu12-nexus7-002':
      SlaveInfo('015d18848c280217', DEFAULT_SDK_ROOT, True),
  'skiabot-shuttle-ubuntu12-nexus7-003':
      SlaveInfo('015d16897c401e17', DEFAULT_SDK_ROOT, True),
  'skiabot-shuttle-ubuntu12-nexus9-001':
      SlaveInfo('HT43RJT00022', DEFAULT_SDK_ROOT, True),
  'skiabot-shuttle-ubuntu12-nexus9-002':
      SlaveInfo('HT4AEJT03112', DEFAULT_SDK_ROOT, True),
  'skiabot-shuttle-ubuntu12-nexus9-003':
      SlaveInfo('HT4ADJT03339', DEFAULT_SDK_ROOT, True),
  'skiabot-shuttle-ubuntu12-nexus10-001':
      SlaveInfo('R32C801B5LH', DEFAULT_SDK_ROOT, True),
  'skiabot-shuttle-ubuntu12-nexus10-003':
      SlaveInfo('R32CB017X2L', DEFAULT_SDK_ROOT, True),
  'skiabot-shuttle-ubuntu12-nexusplayer-001':
      SlaveInfo('D76C708B', DEFAULT_SDK_ROOT, True),
  'skiabot-shuttle-ubuntu12-nexusplayer-002':
      SlaveInfo('8AB5139A', DEFAULT_SDK_ROOT, True),
  'default':
      SlaveInfo('noserial', DEFAULT_SDK_ROOT, False),
}
