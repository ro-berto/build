#!/usr/bin/python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Get a Chromium build, executed by buildbot slaves for Chromebot.

This script will download Chrome build, test files, and breakpad symbol files
with option to extract.

If (--build) option is omitted, latest build will be downloaded instead.
If (--build-url) option is ommited, a latest build will be downloaded from:
  http://commondatastorage.googleapis.com/chromium-browser-snapshots/

Required option:
  get_chromium_build.py --platform=PLATFORM
"""

import httplib
import optparse
import os
import shutil
import sys
import urlparse
import urllib
import urllib2
import zipfile

from common import chromium_utils


def RemovePath(path):
  """Remove the given dir."""
  if os.path.isdir(path):
    shutil.rmtree(path)


def MoveFile(path, new_path):
  """Move all content in |path| to |new_path|.

  Create |new_path| if it doesn't exist.
  """
  if not os.path.isdir(new_path):
    os.makedirs(new_path)
  for root, dirnames, fnames in os.walk(path):
    for fname in fnames:
      shutil.move(os.path.join(root, fname), new_path)
    for dirname in dirnames:
      shutil.move(os.path.join(root, dirname), new_path)
  RemovePath(path)


def UnzipAndRemove(zip_file, dest):
  """Unzip and remove zip file."""
  z = zipfile.ZipFile(zip_file)
  for f in z.namelist():
    if f.endswith('/'):
      os.makedirs(os.path.join(dest, f))
    else:
      z.extract(f, dest)
  z.close()
  os.remove(zip_file)


def DoesURLExist(url):
  """Determines whether a resource exists at the given URL."""
  _, netloc, path, _, _, _ = urlparse.urlparse(url)
  conn = httplib.HTTPConnection(netloc)
  try:
    conn.request('HEAD', path)
  except httplib.HTTPException:
    return False
  response = conn.getresponse()
  if response.status == 302:  # Redirect; follow it.
    return DoesURLExist(response.getheader('location'))
  return response.status == 200


class GetBuild(object):
  """Class for downloading the build."""

  def __init__(self, options):
    super(GetBuild, self).__init__()
    self._build_dir = None
    self._build_id = None
    self._chrome_zip_name = None
    self._chrome_zip_url = None
    self._options = options
    self._symbol_dir = None
    self._symbol_url = None
    self._symbol_name = None
    self._target_dir = None
    self._test_name = None
    self._test_url = None
    self._urlmap = {}

    self._base_url = ('http://commondatastorage.googleapis.com/'
                      'chromium-browser-snapshots/')

    # Mapping from platform to build file name in
    # .../PLATFORM/VERSION/
    self.AddMapping(
        key='mac',
        chrome_zip='Mac/%s/chrome-mac.zip',
        test='Mac/%s/chrome-mac.test/reliability_tests',
        symbol='Mac/%s/chrome-mac-syms.zip',
        lastchange='Mac/LAST_CHANGE')

    self.AddMapping(
        key='win',
        chrome_zip='Win/%s/chrome-win32.zip',
        test='Win/%s/chrome-win32.test/reliability_tests.exe',
        symbol='Win/%s/chrome-win32-syms.zip',
        lastchange='Win/LAST_CHANGE')

    self.AddMapping(
        key='linux',
        chrome_zip='Linux/%s/chrome-linux.zip',
        test='Linux/%s/chrome-linux.test/reliability_tests',
        symbol='Linux/%s/chrome-lucid32bit-syms.zip',
        lastchange='Linux/LAST_CHANGE')

    self.AddMapping(
        key='linux64',
        chrome_zip='Linux_x64/%s/chrome-linux.zip',
        test='Linux_x64/%s/chrome-linux.test/reliability_tests',
        symbol='Linux_x64/%s/chrome-lucid64bit-syms.zip',
        lastchange='Linux_x64/LAST_CHANGE')

  def AddMapping(self, key, **kwargs):
    self._urlmap[key] = kwargs

  def GetURL(self, file_type):
    """Get full url path to file.

    Args:
      file_type: String ('chrome_zip', 'test', 'symbol', 'lastchange').
    """
    url = self._base_url + self._urlmap[self._options.platform][file_type]
    if file_type == 'lastchange':
      return url
    return url % self._build_id

  def GetDownloadFileName(self, file_type):
    """Get file base name from |_urlmap|."""
    return os.path.basename(self._urlmap[self._options.platform][file_type])

  def GetLastestRevision(self):
    """Get the latest revision number from web file."""
    last_change_url = self.GetURL('lastchange')
    try:
      url_handler = urllib2.urlopen(last_change_url)
      latest = int(url_handler.read())
      return latest
    except IOError:
      print('Could not retrieve the latest revision.', last_change_url)
      return None

  def ProcessArgs(self):
    """Make sure we have proper args; setup download and extracting paths."""
    if not self._options.platform in ('win', 'linux', 'linux64'):
      print 'Unsupported platform.' % self._options.platform
      return False

    if self._options.build_url and not self._options.build_url.endswith('/'):
      self._options.build_url += '/'

    # Get latest build if no |build_url| and |build| is provided.
    if not self._options.build_url and not self._options.build:
      self._build_id = self.GetLastestRevision()
      if not self._build_id:
        return False

    self._build_dir = self._options.build_dir
    self._target_dir = os.path.join(self._build_dir, self._options.target_dir)
    self._symbol_dir = os.path.join(self._build_dir, 'breakpad_syms')

    self._chrome_zip_name = self.GetDownloadFileName('chrome_zip')
    self._test_name = self.GetDownloadFileName('test')
    self._symbol_name = self.GetDownloadFileName('symbol')

    # Set download URLs.
    if self._options.build_url:
      self._chrome_zip_url = self._options.build_url + self._chrome_zip_name
      self._test_url = self._options.build_url + self._test_name
      self._symbol_url = self._options.build_url + self._symbol_name
    else:
      self._chrome_zip_url = self.GetURL('chrome_zip')
      self._test_url = self.GetURL('test')
      self._symbol_url = self.GetURL('symbol')
    return True

  def CleanUp(self):
    """Clean up current directory (e.g. delete prev downloads)."""
    print 'Cleaning these paths: '
    print self._target_dir, self._symbol_dir
    RemovePath(self._target_dir)
    RemovePath(self._symbol_dir)
    return True

  def DownloadAndExtractFiles(self):
    """Download and extract files."""
    if not DoesURLExist(self._chrome_zip_url):
      print 'URL does not exist : ' + self._chrome_zip_url
      return False

    os.makedirs(self._target_dir)
    os.chmod(self._target_dir, 0755)

    # Download and extract Chrome zip.
    print 'Downloading URL: ' + self._chrome_zip_url
    dest = os.path.join(self._target_dir, self._chrome_zip_name)
    urllib.urlretrieve(self._chrome_zip_url, dest)
    if self._options.extract:
      UnzipAndRemove(dest, self._build_dir)
      extracted_dir = os.path.splitext(self._chrome_zip_name)[0]
      MoveFile(os.path.join(self._build_dir, extracted_dir), self._target_dir)

    # Download test file.
    print 'Downloading URL: ' + self._test_url
    urllib.urlretrieve(self._test_url,
                       os.path.join(self._target_dir, self._test_name))

    # Download and extract breakpad symbols.  Skip if doesn't exist.
    if DoesURLExist(self._symbol_url):
      print 'Downloading URL: ' + self._symbol_url
      dest = os.path.join(self._target_dir, self._symbol_name)
      urllib.urlretrieve(self._symbol_url, dest)
      if self._options.extract:
        UnzipAndRemove(dest, self._build_dir)
        extracted_dir = os.path.splitext(self._symbol_name)[0]
        MoveFile(os.path.join(self._build_dir, extracted_dir),
                 self._symbol_dir)

    # Set permissions.
    for path, _, fnames in os.walk(self._target_dir):
      for fname in fnames:
        os.chmod(os.path.join(path, fname), 0755)
    return True

  def Main(self):
    """main() routine for GetBuild.  Fetch everything.

    Returns:
      Value suitable for process exit code (e.g. 0 on success).
    """
    if (not self.ProcessArgs() or
        not self.CleanUp() or
        not self.DownloadAndExtractFiles()):
      return 1

    # See scripts/master/factory/commands.py's SetBuildPropertyShellCommand
    print 'BUILD_PROPERTY build_id=%s' % self._build_id
    return 0


def main():
  option_parser = optparse.OptionParser()

  option_parser.add_option('--build-url',
                           help='URL where to find the build to extract.  '
                                'If ommited, default URL will be used.')
  option_parser.add_option('--extract', action='store_true',
                            help='Extract downloaded files.  Default: True.')
  option_parser.add_option('--platform',
                           help='builder platform. Required.')
  option_parser.add_option('--build',
                            help='Specify the build number we should download.'
                                 ' E.g. "45644"')
  build_dir = os.getcwd()
  option_parser.add_option('--build-dir', default=build_dir,
                           help='Path to main build directory (the parent of '
                                'the Release or Debug directory)')
  target_dir = os.path.join(build_dir, 'Release')
  option_parser.add_option('--target-dir', default=target_dir,
                           help='Build target to archive (Release)')
  chromium_utils.AddPropertiesOptions(option_parser)

  options, args = option_parser.parse_args()
  if args:
    option_parser.error('Args not supported.')
  gb = GetBuild(options)
  return gb.Main()


if '__main__' == __name__:
  sys.exit(main())
