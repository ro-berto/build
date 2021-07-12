# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This script stores constants accessed from the recipe API."""

DEFAULT_BUCKET_NAME = 'code-coverage-data'

# Name of the file to store the directory metadata.
DIR_METADATA_FILE_NAME = 'dir_metadata.json'

# Name of the file to store the line number mapping from bot to Gerrit.
BOT_TO_GERRIT_LINE_NUM_MAPPING_FILE_NAME = (
    'bot_to_gerrit_line_num_mapping.json')

# Valid extensions of source files that supported per coverage tool.
TOOLS_TO_EXTENSIONS_MAP = {
    'clang': [
        '.mm', '.S', '.c', '.hh', '.cxx', '.hpp', '.cc', '.cpp', '.ipp', '.h',
        '.m', '.hxx'
    ],
    'jacoco': ['.java'],
    'v8': ['.js']
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

# A mapping of platform to test target names regex. This is used to filter
# the test targets to be run for a certain test type. See SUPPORTED_TEST_TYPES
# above.

# Keys in the dict are platforms that support multiple test types. If a platform
# isn't in the keys, the default test type will be "overall" and the test
# pattern will be '.+' i.e. all tests would run
PLATFORM_TO_TARGET_NAME_PATTERN_MAP = {
    'ios': {
        'unit': '(boringssl_crypto_|boringssl_ssl_'
                '|.+_unit)tests',
        'overall': '.+'
    },
    'linux': {
        'unit': '(absl_hardening|blink_python|boringssl_crypto|boringssl_ssl'
                '|content_shell_crash|crashpad|cronet|ipc|metrics_python'
                '|vr_pixel|.*unit).*test.*',
        'overall': '.+'
    },
    'mac': {
        'unit': '(absl_hardening|boringssl_crypto|boringssl_ssl|crashpad'
                '|cronet|ipc|.*unit).*test.*',
        'overall': '.+'
    },
    'win': {
        'unit': '(absl_hardening|boringssl_crypto|boringssl_ssl|crashpad'
                '|cronet|ipc|vr_pixel|.*unit).*test.*',
        'overall': '.+'
    },
    'chromeos': {
        'unit': '(crashpad|ipc|.*unit).*test.*',
        'overall': '.+'
    },
    'android': {
        'unit': '(.*unit).*test.*',
        'overall': '.+'
    }
}
PLATFORM_TO_TARGET_NAME_PATTERN_MAP[
    'linux64'] = PLATFORM_TO_TARGET_NAME_PATTERN_MAP['linux']
