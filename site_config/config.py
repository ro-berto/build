#!/usr/bin/python
# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Declares a number of site-dependent variables for use by scripts.

A typical use of this module would be

  import chromium_config as config

  v8_url = config.Master.v8_url
"""

import os
import sys

from twisted.spread import banana

# Override config_default with a config_private file.
try:
  import config_private
except ImportError:
  import config_default as config_private

from common import chromium_utils

# By default, the banana's string size limit is 640kb, which is unsufficient
# when passing diff's around. Raise it to 100megs. Do this here since the limit
# is enforced on both the server and the client so both need to raise the
# limit.
banana.SIZE_LIMIT = 100 * 1024 * 1024


class Master(config_private.Master):
  """Buildbot master configuration options."""

  trunk_url = (config_private.Master.server_url +
               config_private.Master.repo_root + '/trunk')

  webkit_trunk_url = (config_private.Master.webkit_root_url + '/trunk')

  trunk_url_src = trunk_url + '/src'
  o3d_url = trunk_url_src + '/o3d'
  nacl_trunk_url = 'svn://svn.chromium.org/native_client/trunk'
  nacl_url = nacl_trunk_url + '/src/native_client'
  nacl_sdk_trunk_url = 'https://nativeclient-sdk.googlecode.com/svn/trunk'
  nacl_sdk_url = nacl_sdk_trunk_url + '/src'
  nacl_ports_trunk_url = 'https://naclports.googlecode.com/svn/trunk'
  nacl_ports_url = nacl_ports_trunk_url + '/src'
  gears_url = 'http://gears.googlecode.com/svn/trunk'
  gyp_trunk_url = 'http://gyp.googlecode.com/svn/trunk'
  branch_url = (config_private.Master.server_url +
                config_private.Master.repo_root + '/branches')
  merge_branch_url = branch_url + '/chrome_webkit_merge_branch'
  merge_branch_url_src = merge_branch_url + '/src'

  v8_url = 'http://v8.googlecode.com/svn'
  v8_branch_url = (v8_url + '/branches')
  v8_bleeding_edge = v8_branch_url + '/bleeding_edge';
  es5conform_root_url =  "https://es5conform.svn.codeplex.com/svn/"
  es5conform_revision = 62998

  # Default target platform if none was given to the factory.
  default_platform = 'win32'

  # Used by the waterfall display.
  project_url = 'http://www.chromium.org'

  # Base URL for perf test results.
  perf_base_url = 'http://build.chromium.org/buildbot/perf'

  # Suffix for perf URL.
  perf_report_url_suffix = 'report.html?history=150'

  # Directory in which to save perf-test output data files.
  perf_output_dir = '~/www/perf'

  # URL pointing to builds and test results.
  archive_url = 'http://build.chromium.org/buildbot'

  # File in which to save a list of graph names.
  perf_graph_list = 'graphs.dat'

  # Magic step return code inidicating "warning(s)" rather than "error".
  retcode_warnings = 88

  bot_password = None

  @staticmethod
  def GetBotPassword():
    """Returns the slave password retrieved from a local file, or None.

    The slave password is loaded from a local file next to this module file, if
    it exists.  This is a function rather than a variable so it's not called
    when it's not needed.

    We can't both make this a property and also keep it static unless we use a
    <metaclass, which is overkill for this usage.
    """
    # Note: could be overriden by config_private.
    if not Master.bot_password:
      # If the bot_password has been requested, the file is required to exist
      # if not overriden in config_private.
      bot_password_path = os.path.join(os.path.dirname(__file__),
                                       '.bot_password')
      Master.bot_password = open(bot_password_path).read().strip('\n\r')
    return Master.bot_password


class Installer(config_private.Installer):
  """Installer configuration options."""

  # Executable name.
  installer_exe = 'mini_installer.exe'

  # Section in that file containing applicable values.
  file_section = 'CHROME'

  # File holding current version information.
  version_file = 'VERSION'

  # Output of mini_installer project.
  output_file = 'packed_files.txt'


class Archive(config_private.Archive):
  """Build and data archival options."""

  # List of symbol files archived by official and dev builds.
  # It really sucks to have to hard-code these here.
  # TODO(cpu): rlz_pdb.dll dropped from list. http://b/1716253
  # TODO(robertshield): This is no longer used as of changes
  # to the official build scripts. Remove this as soon as
  # those changes land.
  symbols_to_archive = ['chrome_dll.pdb', 'chrome_exe.pdb',
                        'mini_installer.pdb', 'setup.pdb']

  # TODO(thestig) Add 64-bit symbols once we get there.
  symbols_to_archive_linux = ['chrome.breakpad.ia32']

  # Binary to archive on the source server with the sourcified symbols.
  symsrc_binaries = ['chrome.exe', 'chrome.dll',
                     'servers\\npchrome_frame.dll',
                     'servers\\chrome_launcher.exe']

  # List of symbol files to save, but not to upload to the symbol server
  # (generally because they have no symbols and thus would produce an error).
  # TODO(jungshik): make the name of icudt dll independent of the ICU version.
  # For now, we list both icudt{38,42}.dll because this script is used by
  # pre-ICU 4.2 builds as well.
  symbols_to_skip_upload = [
      'icudt38.dll', 'icudt42.dll', 'rlz.dll', 'avcodec-52.dll',
      'avformat-52.dll', 'avutil-50.dll', 'gcswf32.dll', 'd3dx9_42.dll',
      'D3DCompiler_42.dll',]

  if os.environ.get('CHROMIUM_BUILD', '') == '_google_chrome':
    exes_to_skip_entirely = []
  else:
    # Skip any filenames (exes, symbols, etc.) starting with these strings
    # entirely, typically because they're not built for this distribution.
    exes_to_skip_entirely = ['rlz']

  # Extra files to archive in official mode.
  if chromium_utils.IsWindows():
    official_extras = [
      ['setup.exe'],
      ['chrome.packed.7z'],
      ['chrome_frame.packed.7z'],
      ['patch.packed.7z'],
      ['obj', 'mini_installer', 'mini_installer_exe_version.rc'],
      ['courgette.exe'],
    ]
  else:
    official_extras = []

  # Installer to archive.
  installer_exe = Installer.installer_exe

  # Test files to archive.
  # TODO(jungshik): make the name of icudt dll independent of the ICU version.
  # For now, we list both icudt{38,42}.dll because this script is used by
  # pre-ICU 4.2 builds as well.
  tests_to_archive = ['reliability_tests.exe',
                      'test_shell.exe',
                      'automated_ui_tests.exe',
                      'icudt38.dll',
                      'icudt42.dll',
                      'plugins\\npapi_layout_test_plugin.dll',
                     ]

  # Archive everything in these directories, using glob.
  test_dirs_to_archive = ['fonts']
  # Create these directories, initially empty, in the archive.
  test_dirs_to_create = ['plugins', 'fonts']

  # Directories in which to store built files, for dev, official, and full
  # builds. (We don't use the full ones yet.)
  archive_host = config_private.Archive.archive_host
  www_dir_base = config_private.Archive.www_dir_base
  www_dir_base_dev = www_dir_base + 'snapshots'
  www_dir_base_official = www_dir_base + 'official_builds'
  www_dir_base_full = 'unused'
  symbol_dir_base_dev = www_dir_base_dev
  symbol_dir_base_full = www_dir_base_full
  symbol_dir_base_official = www_dir_base_official

  # Where to find layout test results by default, above the build directory.
  layout_test_result_dir = 'layout-test-results'

  # Where to save layout test results.
  layout_test_result_archive = www_dir_base + 'layout_test_results'

  # Where to save gtest JSON results.
  gtest_result_archive = www_dir_base + 'gtest_results'

class Distributed(config_private.Distributed):
  # File holding current version information.
  version_file = Installer.version_file
