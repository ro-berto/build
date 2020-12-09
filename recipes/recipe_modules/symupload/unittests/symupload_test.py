#!/usr/bin/env vpython
# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import mock
import os
import unittest
import subprocess
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,
                os.path.abspath(os.path.join(THIS_DIR, os.pardir, 'resources')))

import symupload


class SymuploadTest(unittest.TestCase):

  def test_args(self):
    all_args = [
        '--artifacts',
        '/some/out/dir/artifact1,/some/out/dir/artifact2',
        '--api-key-file',
        '/some/path/api_key_file.txt',
        '--binary-path',
        '/some/symupload',
        '--build-dir',
        '/some/out/dir/',
        '--platform',
        'mac',
        '--server-urls',
        'https://some.url.com,https://some.url2.com',
    ]

    args = symupload.parse_arguments(all_args)

    artifacts = args.artifacts.split(',')
    self.assertEqual(len(artifacts), 2)
    self.assertTrue(artifacts[0] == '/some/out/dir/artifact1')
    self.assertTrue(args.api_key_file == '/some/path/api_key_file.txt')
    self.assertTrue(args.binary_path == '/some/symupload')
    self.assertTrue(args.build_dir == '/some/out/dir/')
    self.assertTrue(args.platform == 'mac')
    server_urls = args.server_urls.split(',')
    self.assertEqual(len(server_urls), 2)
    self.assertTrue(server_urls[1], 'https://some.url2.com')

  def test_build_args(self):
    platform = 'win'
    artifact = '/some/out/dir/artifact1'
    server_url = 'https://some.url.com'
    api_key = 'sample_key'

    build_args = symupload.build_args(platform, artifact, server_url, api_key)
    self.assertTrue(['-p', artifact, server_url, api_key], build_args)

    for platform in ['mac', 'linux']:
      build_args = symupload.build_args(platform, artifact, server_url, api_key)
      self.assertTrue(
          ['-p', 'sym-upload-v2', '-k', api_key, artifact, server_url],
          build_args)

  @mock.patch('symupload.os')
  def test_read_api_key_not_existent(self, mock_os):
    mock_os.path.exists.return_value = False
    key = symupload.read_api_key('/not/existent/path')
    self.assertFalse(key)

  @mock.patch('symupload.os')
  def test_read_api_key(self, mock_os):
    path = '/some/path/api_key_file.txt'
    key_content = 'fake_key'

    mock_os.path.exists.return_value = True
    with mock.patch('symupload.open',
                    mock.mock_open(read_data=key_content)) as m:
      result = symupload.read_api_key(path)
      m.assert_called_once_with(path, 'r')
      self.assertEqual(result, key_content)

  def test_sanitized_args(self):
    platform = 'win'
    artifact = '/some/out/dir/artifact1'
    server_url = 'https://some.url.com'
    api_key = 'sample_key'
    build_args = symupload.build_args(platform, artifact, server_url, api_key)
    sanitized_args = symupload.sanitize_args(build_args, api_key)
    self.assertTrue(sanitized_args[3] == '********')

    for platform in ['mac', 'linux']:
      build_args = symupload.build_args(platform, artifact, server_url, api_key)
      sanitized_args = symupload.sanitize_args(build_args, api_key)
      self.assertTrue(sanitized_args[3] == '********')

  @mock.patch('symupload.subprocess')
  @mock.patch('symupload.os')
  def test_basic(self, mock_os, mock_subprocess):
    mock_os.path.exists.return_value = True
    mock_subprocess.check_output.side_effect = ['help_cmd', 'success!']
    path = '/some/path/api_key_file.txt'
    all_args = [
        '--artifacts',
        '/some/out/dir/artifact1',
        '--api-key-file',
        path,
        '--binary-path',
        '/some/symupload',
        '--build-dir',
        '/some/out/dir/',
        '--platform',
        'mac',
        '--server-urls',
        'https://some.url.com',
    ]
    key_content = 'fake_key'
    with mock.patch('symupload.open',
                    mock.mock_open(read_data=key_content)) as m:
      ret_code = symupload.main(all_args)
      m.assert_called_once_with(path, 'r')
      self.assertTrue(ret_code == 0)

  @mock.patch('symupload.subprocess.check_output')
  @mock.patch('symupload.os')
  def test_retcode2(self, mock_os, mock_subprocess):
    artifact = '/some/out/dir/artifact2'
    binary_path = '/some/symupload'
    key_content = 'fake_key'
    path = '/some/path/api_key_file.txt'
    server_url = 'https://some.url2.com'

    mock_os.path.exists.return_value = True
    error = subprocess.CalledProcessError(
        returncode=2,
        cmd=('/some/symupload -p ' + artifact + ' ' + server_url + ' ' +
             key_content),
        output='already exists!')
    mock_subprocess.side_effect = ['help_cmd', error]

    all_args = [
        '--artifacts',
        artifact,
        '--api-key-file',
        path,
        '--binary-path',
        binary_path,
        '--build-dir',
        '/some/out/dir/',
        '--platform',
        'win',
        '--server-urls',
        server_url,
    ]

    with mock.patch('symupload.open', mock.mock_open(read_data=key_content)):
      ret_code = symupload.main(all_args)
      # retcode 2 should still be treated as retcode 0
      self.assertTrue(ret_code == 0)

  @mock.patch('symupload.subprocess.check_output')
  @mock.patch('symupload.os')
  def test_retcode_nonzero(self, mock_os, mock_subprocess):
    artifact = '/some/out/dir/artifact'
    binary_path = '/some/symupload'
    key_content = 'fake_key'
    path = '/some/path/api_key_file.txt'
    server_url = 'https://some.url.com'

    mock_os.path.exists.return_value = True
    error = subprocess.CalledProcessError(
        returncode=1,
        cmd=('/some/symupload -p ' + artifact + ' ' + server_url + ' ' +
             key_content),
        output='already exists!')
    mock_subprocess.side_effect = ['help_cmd', error, 'success!']

    all_args = [
        '--artifacts', artifact + ',' + '/some/out/dir/artifact2',
        '--api-key-file', path, '--binary-path', binary_path, '--build-dir',
        '/some/out/dir/', '--platform', 'win', '--server-urls', server_url
    ]

    with mock.patch('symupload.open', mock.mock_open(read_data=key_content)):
      ret_code = symupload.main(all_args)
      self.assertTrue(ret_code == 1)


if __name__ == '__main__':
  unittest.main()
