# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest
from xml.etree import ElementTree

import mock

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,
                os.path.abspath(os.path.join(THIS_DIR, os.pardir, 'resources')))

import generate_coverage_metadata_for_java as generator
import repository_util


class GenerateCoverageMetadataForJavaTest(unittest.TestCase):

  INITIAL_METADATA_INPUT = {
      'files': [{
          'path': '//dir/file.java',
          'lines': [{
              'first': 1,
              'last': 1,
              'count': 1,
          }],
          'summaries': [{
              'name': 'line',
              'covered': 1,
              'total': 1,
          }],
      }],
      'summaries': [{
          'name': 'line',
          'covered': 1,
          'total': 1,
      }]
  }

  FILE_REVISIONS = {
      '//dir/file.java': ('hash1', 1234),
      '//dir2/file2.java': ('hash2', 5678),
  }

  COMPONENT_MAPPING = {'dir': 'Test>Component'}

  XML_COUNTER_INPUT = """
  <report name="JaCoCo Coverage Report">
    <counter type="INSTRUCTION" missed="1" covered="1"/>
    <counter type="BRANCH" missed="1" covered="1"/>
    <counter type="LINE" missed="1" covered="1"/>
    <counter type="COMPLEXITY" missed="1" covered="1"/>
    <counter type="METHOD" missed="1" covered="1"/>
    <counter type="CLASS" missed="1" covered="1"/>
  </report>
  """

  XML_COUNTER_INPUT_MISSING_BRANCH = """
  <report name="JaCoCo Coverage Report">
    <counter type="INSTRUCTION" missed="1" covered="1"/>
    <counter type="LINE" missed="1" covered="1"/>
    <counter type="COMPLEXITY" missed="1" covered="1"/>
    <counter type="METHOD" missed="1" covered="1"/>
    <counter type="CLASS" missed="1" covered="1"/>
  </report>
  """

  XML_JACOCO_INPUT = """
  <report name="JaCoCo Coverage Report">
    <package name="dir">
      <sourcefile name="file.java">
        <line nr="1" mi="0" ci="1" mb="0" cb="0"/>
        <counter type="INSTRUCTION" missed="0" covered="1"/>
        <counter type="LINE" missed="0" covered="1"/>
        <counter type="COMPLEXITY" missed="0" covered="1"/>
        <counter type="METHOD" missed="0" covered="1"/>
        <counter type="CLASS" missed="0" covered="1"/>
      </sourcefile>
    </package>
    <counter type="INSTRUCTION" missed="0" covered="1"/>
    <counter type="LINE" missed="0" covered="1"/>
    <counter type="COMPLEXITY" missed="0" covered="1"/>
    <counter type="METHOD" missed="0" covered="1"/>
    <counter type="CLASS" missed="0" covered="1"/>
  </report>
  """

  @mock.patch.object(os, 'walk')
  def test_get_files_with_suffix(self, mock_walk):
    mock_input_dir_walk = [
        ('/b/some/path', ['0', '1', '2', '3'], ['summary.json']),
        ('/b/some/path/0', [],
         ['output.json', 'default-1.exec', 'default-2.exec']),
        ('/b/some/path/1', [],
         ['output.json', 'default-3.exec', 'default-4.exec']),
    ]
    mock_walk.return_value = mock_input_dir_walk

    expected_output = [
        '/b/some/path/0/default-1.exec', '/b/some/path/0/default-2.exec',
        '/b/some/path/1/default-3.exec', '/b/some/path/1/default-4.exec'
    ]
    actual_output = generator.get_files_with_suffix('/b/some/path', '.exec')
    self.assertListEqual(expected_output, actual_output)

  @mock.patch.object(os, 'walk')
  def test_get_files_with_suffix_if_there_is_no_match(self, mock_walk):
    mock_input_dir_walk = [
        ('/b/some/path', ['0', '1', '2', '3'], ['summary.json']),
        ('/b/some/path/0', [],
         ['output.json', 'default-1.exec', 'default-2.exec']),
        ('/b/some/path/1', [],
         ['output.json', 'default-3.exec', 'default-4.exec']),
    ]
    mock_walk.return_value = mock_input_dir_walk

    actual_output = generator.get_files_with_suffix('/b/some/path', '.exe')
    self.assertListEqual([], actual_output)

  def test_get_coverage_metric_summaries(self):
    root = ElementTree.fromstring(self.XML_COUNTER_INPUT)
    expected_result = [
        {
            'name': 'instruction',
            'covered': 1,
            'total': 2,
        },
        {
            'name': 'branch',
            'covered': 1,
            'total': 2,
        },
        {
            'name': 'line',
            'covered': 1,
            'total': 2,
        },
        {
            'name': 'complexity',
            'covered': 1,
            'total': 2,
        },
        {
            'name': 'method',
            'covered': 1,
            'total': 2,
        },
        {
            'name': 'class',
            'covered': 1,
            'total': 2,
        },
    ]

    actual_result = generator.get_coverage_metric_summaries(root)
    self.assertListEqual(actual_result, expected_result)

  def test_get_coverage_metric_summaries_missing_metric(self):
    root = ElementTree.fromstring(self.XML_COUNTER_INPUT_MISSING_BRANCH)
    expected_result = [
        {
            'name': 'instruction',
            'covered': 1,
            'total': 2,
        },
        {
            'name': 'branch',
            'covered': 0,
            'total': 0,
        },
        {
            'name': 'line',
            'covered': 1,
            'total': 2,
        },
        {
            'name': 'complexity',
            'covered': 1,
            'total': 2,
        },
        {
            'name': 'method',
            'covered': 1,
            'total': 2,
        },
        {
            'name': 'class',
            'covered': 1,
            'total': 2,
        },
    ]

    actual_result = generator.get_coverage_metric_summaries(root)
    self.assertListEqual(actual_result, expected_result)

  @mock.patch.object(os.path, 'isfile')
  @mock.patch.object(repository_util, 'GetFileRevisions')
  def test_generate_json_coverage_metadata(self, mock_get_file_revisions,
                                           mock_os_path_isfile):
    mock_get_file_revisions.return_value = self.FILE_REVISIONS
    mock_os_path_isfile = True
    root = ElementTree.fromstring(self.XML_JACOCO_INPUT)

    expected_output = {
        'files': [{
            'branches': [],
            'timestamp':
                1234,
            'lines': [{
                'count': 1,
                'last': 1,
                'first': 1
            }],
            'path':
                '//dir/file.java',
            'summaries': [{
                'covered': 1,
                'total': 1,
                'name': 'instruction'
            }, {
                'covered': 0,
                'total': 0,
                'name': 'branch'
            }, {
                'covered': 1,
                'total': 1,
                'name': 'line'
            }, {
                'covered': 1,
                'total': 1,
                'name': 'complexity'
            }, {
                'covered': 1,
                'total': 1,
                'name': 'method'
            }, {
                'covered': 1,
                'total': 1,
                'name': 'class'
            }],
            'revision':
                'hash1'
        }],
        'dirs': [{
            'dirs': [{
                'path':
                    '//dir/',
                'name':
                    'dir/',
                'summaries': [{
                    'covered': 1,
                    'total': 1,
                    'name': 'instruction'
                }, {
                    'covered': 0,
                    'total': 0,
                    'name': 'branch'
                }, {
                    'covered': 1,
                    'total': 1,
                    'name': 'line'
                }, {
                    'covered': 1,
                    'total': 1,
                    'name': 'complexity'
                }, {
                    'covered': 1,
                    'total': 1,
                    'name': 'method'
                }, {
                    'covered': 1,
                    'total': 1,
                    'name': 'class'
                }]
            }],
            'path':
                '//',
            'summaries': [{
                'covered': 1,
                'total': 1,
                'name': 'instruction'
            }, {
                'covered': 0,
                'total': 0,
                'name': 'branch'
            }, {
                'covered': 1,
                'total': 1,
                'name': 'line'
            }, {
                'covered': 1,
                'total': 1,
                'name': 'complexity'
            }, {
                'covered': 1,
                'total': 1,
                'name': 'method'
            }, {
                'covered': 1,
                'total': 1,
                'name': 'class'
            }],
            'files': []
        },
                 {
                     'dirs': [],
                     'path':
                         '//dir/',
                     'summaries': [{
                         'covered': 1,
                         'total': 1,
                         'name': 'instruction'
                     }, {
                         'covered': 0,
                         'total': 0,
                         'name': 'branch'
                     }, {
                         'covered': 1,
                         'total': 1,
                         'name': 'line'
                     }, {
                         'covered': 1,
                         'total': 1,
                         'name': 'complexity'
                     }, {
                         'covered': 1,
                         'total': 1,
                         'name': 'method'
                     }, {
                         'covered': 1,
                         'total': 1,
                         'name': 'class'
                     }],
                     'files': [{
                         'path':
                             '//dir/file.java',
                         'name':
                             'file.java',
                         'summaries': [{
                             'covered': 1,
                             'total': 1,
                             'name': 'instruction'
                         }, {
                             'covered': 0,
                             'total': 0,
                             'name': 'branch'
                         }, {
                             'covered': 1,
                             'total': 1,
                             'name': 'line'
                         }, {
                             'covered': 1,
                             'total': 1,
                             'name': 'complexity'
                         }, {
                             'covered': 1,
                             'total': 1,
                             'name': 'method'
                         }, {
                             'covered': 1,
                             'total': 1,
                             'name': 'class'
                         }]
                     }]
                 }],
        'summaries': [{
            'covered': 1,
            'total': 1,
            'name': 'instruction'
        }, {
            'covered': 0,
            'total': 0,
            'name': 'branch'
        }, {
            'covered': 1,
            'total': 1,
            'name': 'line'
        }, {
            'covered': 1,
            'total': 1,
            'name': 'complexity'
        }, {
            'covered': 1,
            'total': 1,
            'name': 'method'
        }, {
            'covered': 1,
            'total': 1,
            'name': 'class'
        }],
        'components': [{
            'dirs': [{
                'path':
                    '//dir/',
                'name':
                    'dir/',
                'summaries': [{
                    'covered': 1,
                    'total': 1,
                    'name': 'instruction'
                }, {
                    'covered': 0,
                    'total': 0,
                    'name': 'branch'
                }, {
                    'covered': 1,
                    'total': 1,
                    'name': 'line'
                }, {
                    'covered': 1,
                    'total': 1,
                    'name': 'complexity'
                }, {
                    'covered': 1,
                    'total': 1,
                    'name': 'method'
                }, {
                    'covered': 1,
                    'total': 1,
                    'name': 'class'
                }]
            }],
            'path':
                'Test>Component',
            'summaries': [{
                'covered': 1,
                'total': 1,
                'name': 'instruction'
            }, {
                'covered': 0,
                'total': 0,
                'name': 'branch'
            }, {
                'covered': 1,
                'total': 1,
                'name': 'line'
            }, {
                'covered': 1,
                'total': 1,
                'name': 'complexity'
            }, {
                'covered': 1,
                'total': 1,
                'name': 'method'
            }, {
                'covered': 1,
                'total': 1,
                'name': 'class'
            }]
        }]
    }

    actual_output = generator.generate_json_coverage_metadata(
        '', root, ['dir'], self.COMPONENT_MAPPING)
    self.assertDictEqual(expected_output, actual_output)

  @mock.patch.object(repository_util, 'GetFileRevisions')
  def test_generate_json_coverage_metadata_skip_auto_generated_files(
      self, mock_get_file_revisions):
    mock_get_file_revisions.return_value = self.FILE_REVISIONS
    root = ElementTree.fromstring(self.XML_JACOCO_INPUT)

    actual_output = generator.generate_json_coverage_metadata(
        '', root, [], self.COMPONENT_MAPPING)
    self.assertEqual([], actual_output['files'])


if __name__ == '__main__':
  unittest.main()
