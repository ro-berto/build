#!/usr/bin/env vpython
# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import re
import sys
import unittest

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(THIS_DIR, os.pardir)))

import constants


class ConstantsTest(unittest.TestCase):

  def test_ios_excluded_sources_regex_matches_test_file(self):
    """Tests test files are matched by ios exclude pattern"""
    ios_pattern = constants.EXCLUDE_SOURCES['ios_test_files_and_test_utils']
    files = [
        '/b/s/w/ir/cache/builder/src/ios/web/web_view/'
        'wk_web_view_util_unittest.mm',
        '/b/s/w/ir/cache/builder/src/ios/web/web_state/'
        'page_display_state_unittest.mm',
        '/b/s/w/ir/cache/builder/src/ios/chrome/browser/'
        'signin/gaia_auth_fetcher_ios_ns_url_session_bridge_unittests.mm',
        '/b/s/w/ir/cache/builder/src/ios/web/web_state/'
        'web_state_observer_inttest.mm',
        '/b/s/w/ir/cache/builder/src/base/bit_cast_unittest.cc',
        '/b/s/w/ir/cache/builder/src/components/services/quarantine/'
        'common_unittests.cc',
        '/b/s/w/ir/cache/builder/src/ios/chrome/browser/metrics/ukm_egtest.mm',
        '/b/s/w/ir/cache/builder/src/third_party/webrtc/modules/'
        'audio_processing/test/apmtest.m',
        '/b/s/w/ir/cache/builder/src/services/audio/test/'
        'audio_system_to_service_adapter_test.cc',
    ]
    filtered_files = filter(lambda s: re.match(ios_pattern, s), files)
    self.assertEqual(len(files), len(filtered_files))

  def test_ios_excluded_sources_regex_matches_test_util(self):
    """Tests test util files are matched by ios exclude pattern"""
    ios_pattern = constants.EXCLUDE_SOURCES['ios_test_files_and_test_utils']
    files = [
        '/b/s/w/ir/cache/builder/src/net/test/url_request/'
        'url_request_hanging_read_job.cc',
        '/b/s/w/ir/cache/builder/src/ios/web/test/fakes/'
        'crw_fake_wk_frame_info.mm',
        '/b/s/w/ir/cache/builder/src/ios/chrome/test/earl_grey2/'
        'smoke_egtest.mm',
        '/b/s/w/ir/cache/builder/src/ios/web_view/test/observer.mm',
        '/b/s/w/ir/cache/builder/src/ios/testing/earl_grey/'
        'app_launch_configuration.mm',
        '/b/s/w/ir/cache/builder/src/testing/coverage_util_ios.mm',
        '/b/s/w/ir/cache/builder/src/ios/testing/perf/startupLoggers.mm',
    ]
    filtered_files = filter(lambda s: re.match(ios_pattern, s), files)
    self.assertEqual(len(files), len(filtered_files))

  def test_ios_excluded_sources_regex_not_match_unexluded_files(self):
    """Tests non test related files are not matched by ios exclude pattern"""
    ios_pattern = constants.EXCLUDE_SOURCES['ios_test_files_and_test_utils']
    files = [
        '/b/s/w/ir/cache/builder/src/ios/chrome/browser/signin/'
        'signin_browser_state_info_updater.mm',
        '/b/s/w/ir/cache/builder/src/base/mac/scoped_sending_event.mm',
        '/b/s/w/ir/cache/builder/src/ios/chrome/test_network_connection/'
        'test_network_view_controller.mm',
        '/b/s/w/ir/cache/builder/src/service/media/test_audio/'
        'test_audio_port.cc',
        '/b/s/w/ir/cache/builder/src/some/random/non/test_related/file.cc',
    ]
    filtered_files = filter(lambda s: re.match(ios_pattern, s), files)
    self.assertEqual(0, len(filtered_files))


if __name__ == '__main__':
  unittest.main()
