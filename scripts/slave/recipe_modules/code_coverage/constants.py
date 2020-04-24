# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This script stores constants accessed from the recipe API."""

DEFAULT_BUCKET_NAME = 'code-coverage-data'

# Name of the file to store the component map.
COMPONENT_MAPPING_FILE_NAME = 'component_mapping_path.json'

# Name of the file to store the line number mapping from bot to Gerrit.
BOT_TO_GERRIT_LINE_NUM_MAPPING_FILE_NAME = (
    'bot_to_gerrit_line_num_mapping.json')

# Valid extensions of source files that supported per coverage tool.
TOOLS_TO_EXTENSIONS_MAP = {
    'clang': [
        '.mm', '.S', '.c', '.hh', '.cxx', '.hpp', '.cc', '.cpp', '.ipp', '.h',
        '.m', '.hxx'
    ],
    'jacoco': ['.java']
}

# Map exclude_sources property value to files that are to be excluded from
# coverage aggregates.
EXCLUDE_SOURCES = {
    'all_test_files':
        r'.*test.*',
    'ios_test_files_and_test_utils':
        r'.+\/test(ing)?\/.+|.+_(unit|int|eg)tests?\.(mm|cc|m)',
}

# Only generate coverage data for CLs in these gerrit projects.
# This is a list of (host, project) pairs
SUPPORTED_PATCH_PROJECTS = [('chromium-review.googlesource.com',
                             'chromium/src')]

# A list of test types supported by code coverage api. The test types are
# defined as str literals and used across multiple places.
SUPPORTED_TEST_TYPES = ['overall', 'unit']

# A mapping of test type str literal to regex of test target names.
# TODO(crbug.com/1071251): This map is correct for iOS tests only currently.
TEST_TYPE_TO_TARGET_NAME_PATTERN_MAP = {'unit': '.+_unittests', 'overall': '.+'}
