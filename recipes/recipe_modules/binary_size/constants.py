# Copyright 2020 The Chromium Authors. All Rights Reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEFAULT_ANALYZE_TARGETS = [
    '//chrome/android:monochrome_public_minimal_apks',
    '//chrome/android:trichrome_minimal_apks',
    '//tools/binary_size:binary_size_trybot_py',
]
DEFAULT_COMPILE_TARGETS = [
    'monochrome_public_minimal_apks',
    'monochrome_static_initializers',
    'trichrome_minimal_apks',
]
DEFAULT_APK_NAME = 'MonochromePublic.minimal.apks'
DEFAULT_MAPPING_FILE_NAME = 'MonochromePublic.aab.mapping'

EXPECTATIONS_STEP_NAME = 'Checking for expectation failures'

PATCH_FIXED_BUILD_STEP_NAME = (
    'Not measuring binary size because build is broken without patch.')
NDJSON_GS_BUCKET = 'chromium-binary-size-trybot-results'
ARCHIVED_URL_FMT = ('https://storage.googleapis.com/{bucket}/{dest}')
RESULT_JSON_STEP_NAME = 'Read diff results'
RESULTS_STEP_NAME = 'Trybot Results'
PLUGIN_OUTPUT_PROPERTY_NAME = 'binary_size_plugin'

TEST_TIME = 1454371200
TEST_BUILDER = 'android_binary_size'
TEST_BUILDNUMBER = 200
TEST_TIME_FMT = '2016/02/02'
