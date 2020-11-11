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

# Path is relative to Chromium output directory.
DEFAULT_SIZE_CONFIG_JSON = 'config/MonochromePublic_size_config.json'

DEFAULT_APK_NAME = 'MonochromePublic.minimal.apks'
DEFAULT_MAPPING_FILE_NAMES = ['MonochromePublic.aab.mapping']

EXPECTATIONS_STEP_NAME = 'Checking for expectation failures'

PATCH_FIXED_BUILD_STEP_NAME = (
    'Not measuring binary size because build is broken without patch.')
NDJSON_GS_BUCKET = 'chromium-binary-size-trybot-results'
ARCHIVED_URL_FMT = ('https://storage.googleapis.com/{bucket}/{dest}')

READ_SIZE_CONFIG_JSON_STEP_NAME = 'Read size config JSON'
READ_ANALYSIS_FILE_VERSION_STRING_STEP_NAME = (
    'Read analysis file version string')
RESULT_JSON_STEP_NAME = 'Read diff results'
RESULTS_STEP_NAME = 'Trybot Results'
PLUGIN_OUTPUT_PROPERTY_NAME = 'binary_size_plugin'

TEST_MAPPING_FILES = ['apks/MonochromePublic.aab.mapping']
TEST_SUPERSIZE_INPUT_FILE = 'apks/MonochromePublic.minimal.apks'
TEST_VERSION_OLD = '0.1'
TEST_VERSION_NEW = '0.5'

TEST_TIME = 1454371200
TEST_BUILDER = 'android_binary_size'
TEST_BUILDNUMBER = 200
TEST_TIME_FMT = '2016/02/02'
