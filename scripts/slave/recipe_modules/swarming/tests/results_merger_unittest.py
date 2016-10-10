#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# For 'test_env'.
sys.path.insert(
    0, os.path.abspath(os.path.join(THIS_DIR, '..', '..',  '..', 'unittests')))

# Imported for side effects on sys.path.
import test_env

# For results_merger.
sys.path.insert(0, os.path.join(THIS_DIR, '..'))
import results_merger


GOOD_JSON_TEST_RESULT_0 = {
  'tests': {
    'car': {
      'honda': {
        'expected': 'PASS',
        'actual': 'PASS'
      },
      'toyota': {
        'expected': 'FAIL',
        'actual': 'FAIL'
      }
    },
    'computer': {
      'dell': {
        'expected': 'PASS',
        'actual': 'PASS'
      }
    },
  },
  'interrupted': False,
  'path_delimiter': '.',
  'version': 3,
  'seconds_since_epoch': 1406662289.76,
  'num_failures_by_type': {
     'FAIL': 0,
     'PASS': 2
  }
}

GOOD_JSON_TEST_RESULT_1 = {
  'tests': {
    'car': {
      'tesla': {
        'expected': 'PASS',
        'actual': 'PASS'
      },
    },
    'burger': {
      'mcdonald': {
        'expected': 'PASS',
        'actual': 'PASS'
      }
    },
  },
  'interrupted': False,
  'path_delimiter': '.',
  'version': 3,
  'seconds_since_epoch': 1406662283.11,
  'num_failures_by_type': {
     'FAIL': 0,
     'PASS': 2
  }
}

GOOD_JSON_TEST_RESULT_2 = {
  'tests': {
    'car': {
      'mercedes': {
        'expected': 'PASS',
        'actual': 'FAIL'
      },
    },
    'burger': {
      'in n out': {
        'expected': 'PASS',
        'actual': 'PASS'
      }
    },
  },
  'interrupted': True,
  'path_delimiter': '.',
  'version': 3,
  'seconds_since_epoch': 1406662200.01,
  'num_failures_by_type': {
     'FAIL': 1,
     'PASS': 1
  }
}

GOOD_JSON_TEST_RESULT_SLASH_DELIMITER_3 = {
  'tests': {
    'car': {
      'mustang': {
        'expected': 'PASS',
        'actual': 'FAIL'
      },
    },
    'burger': {
      'white castle': {
        'expected': 'PASS',
        'actual': 'PASS'
      }
    },
  },
  'interrupted': True,
  'path_delimiter': '/',
  'version': 3,
  'seconds_since_epoch': 1406662200.01,
  'num_failures_by_type': {
     'FAIL': 1,
     'PASS': 1
  }
}

GOOD_JSON_TEST_RESULT_MERGED = {
  'tests': {
    'car': {
      'tesla': {
        'expected': 'PASS',
        'actual': 'PASS'
      },
      'mercedes': {
        'expected': 'PASS',
        'actual': 'FAIL'
      },
      'honda': {
        'expected': 'PASS',
        'actual': 'PASS'
      },
      'toyota': {
        'expected': 'FAIL',
        'actual': 'FAIL'
      }
    },
    'computer': {
      'dell': {
        'expected': 'PASS',
        'actual': 'PASS'
      }
    },
    'burger': {
      'mcdonald': {
        'expected': 'PASS',
        'actual': 'PASS'
      },
      'in n out': {
        'expected': 'PASS',
        'actual': 'PASS'
      }
    }
  },
  'interrupted': True,
  'path_delimiter': '.',
  'version': 3,
  'seconds_since_epoch': 1406662200.01,
  'num_failures_by_type': {
    'FAIL': 1,
    'PASS': 5
  }
}

INVALID_JSON_TEST_RESULT_UNSUPPORTED_VERSION = {
  'tests': {
    'car': {
      'tesla': {
        'expected': 'PASS',
        'actual': 'PASS'
      }
    },
    'computer': {
      'dell': {
        'expected': 'PASS',
        'actual': 'PASS'
      }
    },
    'burger': {
      'mcdonald': {
        'expected': 'PASS',
        'actual': 'PASS'
      },
      'in n out': {
        'expected': 'PASS',
        'actual': 'PASS'
      }
    }
  },
  'interrupted': True,
  'path_delimiter': '.',
  'version': 5,
  'seconds_since_epoch': 1406662200.01,
  'num_failures_by_type': {
    'FAIL': 1,
    'PASS': 5
  }
}


# These unittests are run in PRESUBMIT, but not by recipe_simulation_test, hence
# to avoid false alert on missing coverage by recipe_simulation_test, we mark
# these code as no cover.
class MergingTest(unittest.TestCase):  # pragma: no cover
  def test_merge_json_test_results_format_ok(self):
    self.maxDiff = None  # Show full diff if assertion fail
    self.assertEquals(results_merger.merge_test_results(
        [GOOD_JSON_TEST_RESULT_0,
         GOOD_JSON_TEST_RESULT_1,
         GOOD_JSON_TEST_RESULT_2]),
        GOOD_JSON_TEST_RESULT_MERGED)

  def test_merge_unsupported_json_test_results_format(self):
    with self.assertRaises(Exception):
      results_merger.merge_test_results(
        [GOOD_JSON_TEST_RESULT_0, INVALID_JSON_TEST_RESULT_0])

  def test_merge_incompatible_json_test_results_format(self):
    with self.assertRaises(Exception):
      results_merger.merge_test_results(
        [GOOD_JSON_TEST_RESULT_0, GOOD_JSON_TEST_RESULT_SLASH_DELIMITER_3])

if __name__ == '__main__':
  unittest.main()  # pragma: no cover
