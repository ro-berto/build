#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to extract size information for chrome, executed by buildbot.

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., chrome-release/build/).

  For a list of command-line options, call this script with '--help'.
"""

import errno
import optparse
import os
import re
import stat
import subprocess
import sys


def get_size(filename):
  return os.stat(filename)[stat.ST_SIZE]


def main_mac(options, args):
  """Print appropriate size information about built Mac targets.

  Returns the first non-zero exit status of any command it executes,
  or zero on success.
  """
  target_dir = os.path.join(os.path.dirname(options.build_dir),
                            'xcodebuild', options.target)

  result = 0
  # Work with either build type.
  base_names = ( 'Chromium', 'Google Chrome' )
  for base_name in base_names:
    app_bundle = base_name + '.app'
    framework_name = base_name + ' Framework'
    framework_bundle = framework_name + '.framework'

    chromium_app_dir = os.path.join(target_dir, app_bundle)
    chromium_executable = os.path.join(chromium_app_dir,
                                       'Contents', 'MacOS', base_name)
    chromium_framework_dir = os.path.join(target_dir, framework_bundle)
    chromium_framework_executable = os.path.join(chromium_framework_dir,
                                                 framework_name)
    if os.path.exists(chromium_executable):
      print_dict = {
        # Remove spaces in the names so any downstream processing is less
        # likely to choke.
        'app_name'         : re.sub('\s', '', base_name),
        'app_bundle'       : re.sub('\s', '', app_bundle),
        'framework_name'   : re.sub('\s', '', framework_name),
        'framework_bundle' : re.sub('\s', '', framework_bundle),
        'app_size'         : get_size(chromium_executable),
        'framework_size'   : get_size(chromium_framework_executable)
      }

      # Collect the segment info out of the App
      p = subprocess.Popen(['size', chromium_executable],
                           stdout=subprocess.PIPE)
      stdout = p.communicate()[0]
      print_dict['app_text'], print_dict['app_data'], print_dict['app_objc'] = \
          re.search('(\d+)\s+(\d+)\s+(\d+)', stdout).groups()
      if result == 0:
        result = p.returncode

      # Collect the segment info out of the Framework
      p = subprocess.Popen(['size', chromium_framework_executable],
                           stdout=subprocess.PIPE)
      stdout = p.communicate()[0]
      print_dict['framework_text'], print_dict['framework_data'], \
        print_dict['framework_objc'] = \
          re.search('(\d+)\s+(\d+)\s+(\d+)', stdout).groups()
      if result == 0:
        result = p.returncode

      # Collect the whole size of the App bundle on disk (include the framework)
      p = subprocess.Popen(['du', '-s', '-k', chromium_app_dir],
                           stdout=subprocess.PIPE)
      stdout = p.communicate()[0]
      du_s = re.search('(\d+)', stdout).group(1)
      if result == 0:
        result = p.returncode
      print_dict['app_bundle_size'] = (int(du_s) * 1024)

      print ("""*RESULT %(app_name)s: %(app_name)s= %(app_size)s bytes
RESULT %(app_name)s-__TEXT: __TEXT= %(app_text)s bytes
RESULT %(app_name)s-__DATA: __DATA= %(app_data)s bytes
RESULT %(app_name)s-__OBJC: __OBJC= %(app_objc)s bytes
*RESULT %(framework_name)s: %(framework_name)s= %(framework_size)s bytes
RESULT %(framework_name)s-__TEXT: __TEXT= %(framework_text)s bytes
RESULT %(framework_name)s-__DATA: __DATA= %(framework_data)s bytes
RESULT %(framework_name)s-__OBJC: __OBJC= %(framework_objc)s bytes
*RESULT %(app_bundle)s: %(app_bundle)s= %(app_bundle_size)s bytes""") % (
        print_dict)
      # Found a match, don't check the other base_names.
      return result
  # If no base_names matched, fail script.
  return 66


def main_linux(options, args):
  """Print appropriate size information about built Linux targets.

  Returns the first non-zero exit status of any command it executes,
  or zero on success.
  """
  target_dir = os.path.join(os.path.dirname(options.build_dir), 'out',
                            options.target)
  chrome = os.path.join(target_dir, 'chrome')

  result = 0

  print "*RESULT chrome: chrome= %s bytes" % get_size(chrome)

  p = subprocess.Popen(['size', chrome], stdout=subprocess.PIPE)
  stdout = p.communicate()[0]
  text, data, bss = re.search('(\d+)\s+(\d+)\s+(\d+)', stdout).groups()
  if result == 0:
    result = p.returncode
  print "RESULT chrome-text: text= %s bytes" % text
  print "RESULT chrome-data: data= %s bytes" % data
  print "RESULT chrome-bss: bss= %s bytes" % bss

  # Find the number of files with at least one static initializer.
  # First determine if we're 32 or 64 bit
  p = subprocess.Popen(['readelf', '-h', chrome], stdout=subprocess.PIPE)
  stdout = p.communicate()[0]
  elf_class_line = re.search('Class:.*$', stdout, re.MULTILINE).group(0)
  elf_class = re.split('\W+', elf_class_line)[1]
  if elf_class == "ELF32":
    word_size = 4
  else:
    word_size = 8

  # Then find the size of the .ctors section.
  p = subprocess.Popen(['readelf', '-SW', chrome], stdout=subprocess.PIPE)
  stdout = p.communicate()[0]
  size_line = re.search('.ctors.*$', stdout, re.MULTILINE).group(0)
  size = re.split('\W+', size_line)[5]
  size = int(size, 16)
  # The first entry is always 0 and the last is -1 as guards.
  # So subtract 2 from the count.
  count = (size / word_size) - 2
  print "*RESULT chrome-si: initializers= %s files" % count

  files = [
    'chrome.pak',
    'libffmpegsumo.so',
    'libgcflashplayer.so',
    'libpdf.so',
    'libppGoogleNaClPluginChrome.so',
    'nacl_irt_x86_64.nexe',
  ]

  for filename in files:
    path = os.path.join(target_dir, filename)
    try:
      size = get_size(path)
    except OSError, e:
      if e.errno == errno.ENOENT:
        continue  # Don't print anything for missing files.
      raise
    print "*RESULT %s: %s= %s bytes" % (filename, filename, size)

  return result


def main_win(options, args):
  """Print appropriate size information about built Windows targets.

  Returns the first non-zero exit status of any command it executes,
  or zero on success.
  """
  target_dir = os.path.join(options.build_dir, options.target)
  chrome_dll = os.path.join(target_dir, 'chrome.dll')
  chrome_exe = os.path.join(target_dir, 'chrome.exe')
  mini_installer_exe = os.path.join(target_dir, 'mini_installer.exe')
  setup_exe = os.path.join(target_dir, 'setup.exe')

  result = 0

  print "*RESULT chrome.dll: chrome.dll= %s bytes" % get_size(chrome_dll)

  print "*RESULT chrome.exe: chrome.exe= %s bytes" % get_size(chrome_exe)

  fmt = "*RESULT mini_installer.exe: mini_installer.exe= %s bytes"
  print fmt % get_size(mini_installer_exe)

  print "*RESULT setup.exe: setup.exe= %s bytes" % get_size(setup_exe)

  return result


def main():
  if sys.platform in ('win32', 'cygwin'):
    default_platform = 'win'
  elif sys.platform.startswith('darwin'):
    default_platform = 'mac'
  elif sys.platform == 'linux2':
    default_platform = 'linux'
  else:
    default_platform = None

  main_map = {
    'linux' : main_linux,
    'mac' : main_mac,
    'win' : main_win,
  }
  platforms = sorted(main_map.keys())

  option_parser = optparse.OptionParser()
  option_parser.add_option('', '--target',
                           default='Release',
                           help='build target (Debug, Release) '
                                '[default: %default]')
  option_parser.add_option('', '--build-dir',
                           default='chrome',
                           metavar='DIR',
                           help='directory in which build was run '
                                '[default: %default]')
  option_parser.add_option('', '--platform',
                           default=default_platform,
                           help='specify platform (%s) [default: %%default]'
                                % ', '.join(platforms))

  options, args = option_parser.parse_args()

  real_main = main_map.get(options.platform)
  if not real_main:
    if options.platform is None:
      sys.stderr.write('Unsupported sys.platform %s.\n' % repr(sys.platform))
    else:
      sys.stderr.write('Unknown platform %s.\n' % repr(options.platform))
    msg = 'Use the --platform= option to specify a supported platform:\n'
    sys.stderr.write(msg + '    ' + ' '.join(platforms) + '\n')
    return 2
  return real_main(options, args)


if '__main__' == __name__:
  sys.exit(main())
