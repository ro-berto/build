#!/usr/bin/env python
# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import textwrap
import unittest

THIS_DIR = os.path.dirname(__file__)

sys.path.insert(
    0, os.path.abspath(os.path.join(THIS_DIR, '..', 'sdk_packager.resources')))
import parse_sdkmanager_list


class PackageInfoReTest(unittest.TestCase):

  def testValid(self):
    description_line = '      Description: A sample package description'
    m = parse_sdkmanager_list.PACKAGE_INFO_RE.match(description_line)
    self.assertTrue(m)
    self.assertEquals('Description', m.group(1))
    self.assertEquals('A sample package description', m.group(2))

  def testValidWithTabs(self):
    version_line = '\tVersion:\t1.2.3'
    m = parse_sdkmanager_list.PACKAGE_INFO_RE.match(version_line)
    self.assertTrue(m)
    self.assertEquals('Version', m.group(1))
    self.assertEquals('1.2.3', m.group(2))


class PackageNameReTest(unittest.TestCase):

  def testNameNoSemicolons(self):
    name_line = 'emulator'
    m = parse_sdkmanager_list.PACKAGE_NAME_RE.match(name_line)
    self.assertTrue(m)
    self.assertEquals('emulator', m.group(0))

  def testNameWithSemicolons(self):
    name_line = 'system-images;android-28;google_apis;x86'
    m = parse_sdkmanager_list.PACKAGE_NAME_RE.match(name_line)
    self.assertTrue(m)
    self.assertEquals('system-images;android-28;google_apis;x86', m.group(0))

  def testLeadingWhitespace(self):
    name_line = '  emulator'
    m = parse_sdkmanager_list.PACKAGE_NAME_RE.match(name_line)
    self.assertFalse(m)


class ParseSdkManagerListTest(unittest.TestCase):

  def testSingleAvailablePackage(self):
    raw = textwrap.dedent(
        '''\
        Available Packages:
        ----------------------------
        emulator
            Description:      Android Emulator
            Version:          29.0.11
        ''')
    result = parse_sdkmanager_list.ParseSdkManagerList(raw)
    expected = {
        'available': [
            {
                'name': 'emulator',
                'description': 'Android Emulator',
                'version': '29.0.11',
                'installed location': None,
            },
        ],
        'installed': [],
    }
    self.assertEquals(expected, result)

  def testMultipleAvailablePackages(self):
    raw = textwrap.dedent(
        '''\
        Available Packages:
        ----------------------------
        emulator
            Description:      Android Emulator
            Version:          29.0.11

        system-images;android-28;google_apis;x86
            Description:      Google APIs Intel x86 Atom System Image
            Version:          9
        ''')
    result = parse_sdkmanager_list.ParseSdkManagerList(raw)
    expected = {
        'available': [
            {
                'name': 'emulator',
                'description': 'Android Emulator',
                'version': '29.0.11',
                'installed location': None,
            },
            {
                'name': 'system-images;android-28;google_apis;x86',
                'description': 'Google APIs Intel x86 Atom System Image',
                'version': '9',
                'installed location': None,
            },
        ],
        'installed': [],
    }
    self.assertEquals(expected, result)

  def testSingleInstalledPackage(self):
    raw = textwrap.dedent(
        '''\
        Installed packages:
        ----------------------------
        emulator
            Description:        Android Emulator
            Version:            29.0.11
            Installed Location: /path/to/the/emulator
        ''')
    result = parse_sdkmanager_list.ParseSdkManagerList(raw)
    expected = {
        'available': [],
        'installed': [
            {
                'name': 'emulator',
                'description': 'Android Emulator',
                'version': '29.0.11',
                'installed location': '/path/to/the/emulator',
            },
        ],
    }
    self.assertEquals(expected, result)

  def testMultipleInstalledPackages(self):
    raw = textwrap.dedent(
        '''\
        Installed packages:
        ----------------------------
        emulator
            Description:        Android Emulator
            Version:            29.0.11
            Installed Location: /path/to/the/emulator

        system-images;android-28;google_apis;x86
            Description:        Google APIs Intel x86 Atom System Image
            Version:            9
            Installed Location: /system-images/android-28/google_apis/x86
        ''')
    result = parse_sdkmanager_list.ParseSdkManagerList(raw)
    expected = {
        'available': [],
        'installed': [
            {
                'name': 'emulator',
                'description': 'Android Emulator',
                'version': '29.0.11',
                'installed location': '/path/to/the/emulator',
            },
            {
                'name': 'system-images;android-28;google_apis;x86',
                'description': 'Google APIs Intel x86 Atom System Image',
                'version': '9',
                'installed location':
                    '/system-images/android-28/google_apis/x86',
            },
        ],
    }
    self.assertEquals(expected, result)

  def testAvailableAndInstalledPackages(self):
    raw = textwrap.dedent(
        '''\
        Installed packages:
        ----------------------------
        system-images;android-28;google_apis;x86
            Description:        Google APIs Intel x86 Atom System Image
            Version:            9
            Installed Location: /system-images/android-28/google_apis/x86

        Available Packages:
        ----------------------------
        emulator
            Description:      Android Emulator
            Version:          29.0.11
        ''')
    result = parse_sdkmanager_list.ParseSdkManagerList(raw)
    expected = {
        'available': [
            {
                'name': 'emulator',
                'description': 'Android Emulator',
                'version': '29.0.11',
                'installed location': None,
            },
        ],
        'installed': [
            {
                'name': 'system-images;android-28;google_apis;x86',
                'description': 'Google APIs Intel x86 Atom System Image',
                'version': '9',
                'installed location':
                    '/system-images/android-28/google_apis/x86',
            },
        ],
    }
    self.assertEquals(expected, result)

  def testUpdatesAvailable(self):
    # Ensures that the parser silently ignores any update information.
    raw = textwrap.dedent(
        '''\
        Installed packages:
        ----------------------------
        emulator
            Description:        Android Emulator
            Version:            29.0.9
            Installed Location: /path/to/the/emulator

        Available Packages:
        ----------------------------
        emulator
            Description:      Android Emulator
            Version:          29.0.11

        Available Updates:
        ----------------------------
        emulator
            Installed Version: 29.0.9
            Available Version: 29.0.11
        ''')
    result = parse_sdkmanager_list.ParseSdkManagerList(raw)
    expected = {
        'available': [
            {
                'name': 'emulator',
                'description': 'Android Emulator',
                'version': '29.0.11',
                'installed location': None,
            },
        ],
        'installed': [
            {
                'name': 'emulator',
                'description': 'Android Emulator',
                'version': '29.0.9',
                'installed location': '/path/to/the/emulator',
            },
        ],
    }
    self.assertEquals(expected, result)

  def testOnlyInfo(self):
    raw = textwrap.dedent(
        '''\
            Description: more stuff

        Installed packages:
        ''')
    result = parse_sdkmanager_list.ParseSdkManagerList(raw)
    expected = {
        'available': [],
        'installed': [],
    }
    self.assertEquals(expected, result)


if __name__ == '__main__':
  unittest.main(buffer=True)
