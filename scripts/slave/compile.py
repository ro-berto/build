#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to build chrome, executed by buildbot.

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., chrome-release/build/).

  For a list of command-line options, call this script with '--help'.
"""

import optparse
import os
import re
import shutil
import socket
import sys

from common import chromium_utils
from slave import slave_utils


# Path of the scripts/slave/ checkout on the slave, found by looking at the
# current compile.py script's path's dirname().
SLAVE_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
# Path of the build/ checkout on the slave, found relative to the
# scripts/slave/ directory.
BUILD_DIR = os.path.dirname(os.path.dirname(SLAVE_SCRIPTS_DIR))


def ReadHKLMValue(path, value):
  """Retrieve the install path from the registry for Visual Studio 8.0 and
  Incredibuild."""
  # Only available on Windows.
  # pylint: disable=F0401
  import win32api, win32con
  try:
    regkey = win32api.RegOpenKeyEx(win32con.HKEY_LOCAL_MACHINE,
                                   path, 0, win32con.KEY_READ)
    value = win32api.RegQueryValueEx(regkey, value)[0]
    win32api.RegCloseKey(regkey)
    return value
  except win32api.error:
    return None


def common_mac_settings(command, options, env, compiler=None):
  """
  Sets desirable Mac environment variables and command-line options
  that are common to the Xcode builds.
  """
  compiler = options.compiler
  assert compiler in (None, 'clang', 'goma')

  if compiler == 'goma':
    print 'using goma'
    env['PATH'] = options.goma_dir + ':' + env['PATH']
    command.insert(0, 'goma-xcodebuild')
    return

  if compiler == 'clang':
    clang_binary = os.path.join(os.path.dirname(options.build_dir),
        'third_party', 'llvm-build', 'Release+Asserts', 'bin', 'clang++')
    clang_binary = os.path.abspath(clang_binary)
    # TODO(thakis): Remove this once the webkit canary waterfall has been
    #               restarted.
    if not os.path.isfile(clang_binary):
      clang_binary = 'clang++'
    env['CC'] = clang_binary
    return

  # Most of the bot hostnames are in one of two patterns:
  #   base###.subnet.domain
  #   base###-m##.subnet.domain
  # The "base" and "subnet" are used to pull a list of distccd servers for
  # compilation.  That way, the files can easily be tweaked to affect all of
  # the bots in a given location.
  # 10.5 and 10.6 get different Xcode versions with slightly different versions
  # of gcc and the SDKs, so a different set of hosts is needed for each
  # toolchain.
  uname_tuple = os.uname()
  full_hostname = socket.getfqdn()
  os_revision = uname_tuple[2]
  split_full_hostname = full_hostname.split('.', 2)
  if len(split_full_hostname) >= 3:
    hostname_only = split_full_hostname[0]
    hostname_subnet = split_full_hostname[1]
    name_match = re.match('([a-zA-Z]+)(\d+)(-m\d+)?$', hostname_only)
    if name_match:
      base_hostname = name_match.groups()[0]
      os_names = { '9': '10_5', '10': '10_6' }
      os_name = os_names[os_revision.split('.', 1)[0]]
      distcc_hosts_filename = '%s_%s-%s' % \
          ( hostname_subnet, base_hostname, os_name )
      this_directory = os.path.dirname(os.path.abspath(__file__))
      distcc_hosts_file_path = \
          os.path.join(this_directory, 'mac_distcc_hosts',
                       distcc_hosts_filename)
      if os.path.exists(distcc_hosts_file_path):
        command.extend(['-buildhostsfile', distcc_hosts_file_path])
        if os_name == '10_6':
          # pump --startup will bail if there DISTCC_HOSTS doesn't have valid
          # ,cpp entries.  Xcode 3.2.x can fall into this trap because it
          # tries to collect real host status for this step.  Work around this
          # by manually invoking pump around xcodebuild with enough of
          # a DISTCC_HOSTS so it always starts. (radr://8151956)
          env['DISTCC_HOSTS'] = 'dummy,cpp,lzo'
          command.insert(0, "pump")


def main_xcode(options, args):
  """Interprets options, clobbers object files, and calls xcodebuild.
  """
  # If the project isn't in args, add all.xcodeproj to simplify configuration.
  command = ['xcodebuild', '-configuration', options.target]

  # TODO(mmoss) Support the old 'args' usage until we're confident the master is
  # switched to passing '--solution' everywhere.
  if not '-project' in args:
    # TODO(mmoss) Temporary hack to ignore the Windows --solution flag that is
    # passed to all builders. This can be taken out once the master scripts are
    # updated to only pass platform-appropriate --solution values.
    if (not options.solution or
        os.path.splitext(options.solution)[1] != '.xcodeproj'):
      options.solution = 'all.xcodeproj'
    command.extend(['-project', options.solution])

  if options.xcode_target:
    command.extend(['-target', options.xcode_target])

  if not options.goma_dir:
    options.goma_dir = os.path.join(BUILD_DIR, 'goma', 'mac10.6')

  # Note: this clobbers all targets, not just Debug or Release.
  if options.clobber:
    build_output_dir = os.path.join(os.path.dirname(options.build_dir),
        'xcodebuild')
    chromium_utils.RemoveDirectory(build_output_dir)

  env = os.environ.copy()
  common_mac_settings(command, options, env, options.compiler)

  # Add on any remaining args
  command.extend(args)

  os.chdir(options.build_dir)

  # If using the Goma compiler, first call goma_ctl with ensure_start
  # (or restart in clobber mode) to ensure the proxy is available.
  goma_ctl_cmd = [os.path.join(options.goma_dir, 'goma_ctl.sh')]

  if options.compiler == 'goma':
    goma_key = os.path.join(options.goma_dir, 'goma.key')
    env = os.environ.copy()
    env['GOMA_COMPILER_PROXY_DAEMON_MODE'] = 'true'
    if os.path.exists(goma_key):
      env['GOMA_API_KEY_FILE'] = goma_key
    if options.clobber:
      chromium_utils.RunCommand(goma_ctl_cmd + ['restart'], env=env)
    else:
      chromium_utils.RunCommand(goma_ctl_cmd + ['ensure_start'], env=env)

  # Run the build.
  return chromium_utils.RunCommand(command, env=env)


DISTRIBUTION_FILE = '/etc/lsb-release'
def get_ubuntu_codename():
  if not os.path.exists(DISTRIBUTION_FILE):
    return None
  dist_file = open(DISTRIBUTION_FILE, 'r')
  dist_text = dist_file.read().strip()
  dist_file.close()
  codename = None
  for line in dist_text.splitlines():
    match_data = re.match(r'^DISTRIB_CODENAME=(\w+)$', line)
    if match_data:
      codename = match_data.group(1)
  return codename


def common_linux_settings(command, options, env, crosstool=None, compiler=None):
  """
  Sets desirable Linux environment variables and command-line options
  that are common to the Make and SCons builds.
  """
  assert compiler in (None, 'clang', 'goma')
  if options.mode == 'google_chrome' or options.mode == 'official':
    env['CHROMIUM_BUILD'] = '_google_chrome'

  if options.mode == 'official':
    # Official builds are always Google Chrome.
    env['OFFICIAL_BUILD'] = '1'
    env['CHROME_BUILD_TYPE'] = '_official'

  # Don't stop at the first error.
  command.append('-k')

  # Set jobs parallelization based on number of cores.
  jobs = os.sysconf('SC_NPROCESSORS_ONLN')

  # Test if we can use ccache.
  ccache = ''
  if os.path.exists('/usr/bin/ccache'):
    # The default CCACHE_DIR is $HOME/.ccache which, on some of our
    # bots, is over NFS.  This is intentional.  Talk to thestig or
    # mmoss if you have questions.
    ccache = 'ccache '

  # Setup crosstool environment variables.
  if crosstool:
    env['AR'] = crosstool + '-ar'
    env['AS'] = crosstool + '-as'
    env['CC'] = ccache + crosstool + '-gcc'
    env['CXX'] = ccache + crosstool + '-g++'
    env['LD'] = crosstool + '-ld'
    env['RANLIB'] = crosstool + '-ranlib'
    command.append('-j%d' % jobs)
    # Don't use build-in rules.
    command.append('-r')
    # For now only build chrome, as other things will break.
    command.append('chrome')
    return

  if compiler == 'goma':
    print 'using goma'
    env['CC'] = 'gcc'
    env['CXX'] = 'g++'
    env['PATH'] = options.goma_dir + ':' + env['PATH']
    goma_jobs = 100
    if jobs < goma_jobs:
      jobs = goma_jobs
    command.append('-j%d' % jobs)
    return

  if compiler == 'clang':
    clang_dir = os.path.abspath(os.path.join(
        slave_utils.SlaveBaseDir(options.build_dir), 'build', 'src',
        'third_party', 'llvm-build', 'Release+Asserts', 'bin'))
    if os.path.isdir(clang_dir):
      env['CC'] = os.path.join(clang_dir, 'clang')
      env['CXX'] = os.path.join(clang_dir, 'clang++')
    else:
      # TODO(thakis): Remove this branch once the FYI waterfall has been
      #               restarted.
      env['CC'] = 'clang'
      env['CXX'] = 'clang++'

    # We intentionally don't reuse the ccache/distcc modifications,
    # as they don't work with clang.
    command.append('-j%d' % jobs)
    command.append('-r')
    return

  # Use gcc and g++ by default.
  cc = 'gcc'
  cpp = 'g++'

  # Test if we can use distcc.  Fastbuild servers currently support uname()
  # machine results of i686 or x86_64.
  distcc_bin_exists = os.path.exists('/usr/bin/distcc')
  codename = get_ubuntu_codename()
  machine = os.uname()[4]
  distcc_hosts_path = os.path.join(SLAVE_SCRIPTS_DIR, 'linux_distcc_hosts',
                                   '%s-%s' % (codename, machine))
  hostname = socket.getfqdn().split('.')[0]
  hostname_match = re.match('([a-zA-Z]+)(\d+)(-m\d+)?$', hostname)
  if (distcc_bin_exists and codename and machine and
      os.path.exists(distcc_hosts_path) and hostname_match):
    distcc_file = open(distcc_hosts_path, 'r')
    distcc_text = distcc_file.read().strip()
    distcc_file.close()
    env['DISTCC_HOSTS'] = ' '.join(distcc_text.splitlines())
    print('Distcc enabled:')
    print('ENV["DISTCC_HOSTS"] = "%s"' % env['DISTCC_HOSTS'])

    cc = 'distcc ' + cc
    cpp = 'distcc ' + cpp
    distcc_jobs = 12
    if jobs < distcc_jobs:
      jobs = distcc_jobs
  else:
    print('Distcc disabled:')
    print('  distcc_bin_exists: %s' % distcc_bin_exists)
    print('  codename: %s' % codename)
    print('  machine: %s' % machine)
    print('  distcc_hosts_path: %s' % distcc_hosts_path)
    print('  hostname: %s' % hostname)

  cc = ccache + cc
  cpp = ccache + cpp

  # Export our settings into our copy of the environment.
  print('ENV[\"CC\"] = \"%s\"' % cc)
  print('ENV[\"CXX\"] = \"%s\"' % cpp)
  env['CC'] = cc
  env['CXX'] = cpp
  command.append('-j%d' % jobs)


def main_make(options, args):
  """Interprets options, clobbers object files, and calls make.
  """
  options.build_dir = os.path.abspath(options.build_dir)
  src_dir = os.path.join(slave_utils.SlaveBaseDir(options.build_dir), 'build',
                         'src')
  # TODO(mmoss) Temporary hack to ignore the Windows --solution flag that is
  # passed to all builders. This can be taken out once the master scripts are
  # updated to only pass platform-appropriate --solution values.
  if options.solution and os.path.splitext(options.solution)[1] != '.Makefile':
    options.solution = None

  command = ['make']
  if options.solution:
    command.extend(['-f', options.solution])
    working_dir = options.build_dir
  else:
    # If no solution file (i.e. sub-project *.Makefile) is specified, try to
    # build from the top-level Makefile.
    working_dir = src_dir

  if not options.goma_dir:
    options.goma_dir = os.path.join(BUILD_DIR, 'goma')
  if options.clobber:
    build_output_dir = os.path.join(working_dir, 'out', options.target)
    chromium_utils.RemoveDirectory(build_output_dir)

  # Lots of test-execution scripts hard-code 'sconsbuild' as the output
  # directory.  Accomodate them.
  # TODO:  remove when build_dir is properly parameterized in tests.
  sconsbuild = os.path.join(working_dir, 'sconsbuild')
  if os.path.islink(sconsbuild):
    if os.readlink(sconsbuild) != 'out':
      os.remove(sconsbuild)
  elif os.path.exists(sconsbuild):
    dead = sconsbuild + '.dead'
    if os.path.isdir(dead):
      shutil.rmtree(dead)
    elif os.path.isfile(dead):
      os.remove(dead)
    os.rename(sconsbuild, sconsbuild+'.dead')
  if not os.path.lexists(sconsbuild):
    os.symlink('out', sconsbuild)

  os.chdir(working_dir)
  env = os.environ.copy()
  common_linux_settings(command, options, env, options.crosstool,
      options.compiler)

  command.append('BUILDTYPE=' + options.target)

  # V=1 prints the actual executed command
  if options.verbose:
    command.extend(['V=1'])
  command.extend(options.build_args + args)

  # Force serial linking, otherwise too many links make bots run out of memory
  # (scons does this with 'scons_variable_settings' in common.gypi).
  env['LINK'] = 'flock %s/linker.lock \$(CXX)' % sconsbuild

  # If using the Goma compiler, first call goma_ctl with ensure_start
  # (or restart in clobber mode) to ensure the proxy is available.
  goma_ctl_cmd = [os.path.join(options.goma_dir, 'goma_ctl.sh')]

  if options.compiler == 'goma':
    goma_key = os.path.join(options.goma_dir, 'goma.key')
    env = os.environ.copy()
    env['GOMA_COMPILER_PROXY_DAEMON_MODE'] = 'true'
    if os.path.exists(goma_key):
      env['GOMA_API_KEY_FILE'] = goma_key
    if options.clobber:
      chromium_utils.RunCommand(goma_ctl_cmd + ['restart'], env=env)
    else:
      chromium_utils.RunCommand(goma_ctl_cmd + ['ensure_start'], env=env)

  # Run the build.
  return chromium_utils.RunCommand(command, env=env)


def main_scons(options, args):
  """Interprets options, clobbers object files, and calls scons.
  """
  options.build_dir = os.path.abspath(options.build_dir)
  if options.clobber:
    build_output_dir = os.path.join(os.path.dirname(options.build_dir),
                                    'sconsbuild', options.target)
    chromium_utils.RemoveDirectory(build_output_dir)

  os.chdir(options.build_dir)

  if sys.platform == 'win32':
    command = ['hammer.bat']
  else:
    command = ['hammer']

  env = os.environ.copy()
  if sys.platform == 'linux2':
    common_linux_settings(command, options, env)
  else:
    command.extend(['-k'])

  command.extend([
      # Force scons to always check for dependency changes.
      '--implicit-deps-changed',
      '--mode=' + options.target,
  ])

  # Here's what you can uncomment if you need to see more info
  # about what the build is doing on a slave:
  #
  #   VERBOSE=1 (a setting in our local SCons config) replaces
  #   the "Compiling ..." and "Linking ..." lines with the
  #   actual executed command line(s)
  #
  #   --debug=explain (a SCons option) will tell you why SCons
  #   is deciding to rebuild thing (the target doesn't exist,
  #   which .h file(s) changed, etc.)
  #
  #command.extend(['--debug=explain', 'VERBOSE=1'])
  command.extend(options.build_args + args)
  return chromium_utils.RunCommand(command, env=env)

def main_scons_v8(options, args):
  """Interprets options, clobbers object files, and calls scons.
  """
  options.build_dir = os.path.abspath(options.build_dir)
  if options.clobber:
    build_output_dir = os.path.join(options.build_dir,
                                    'obj')
    chromium_utils.RemoveDirectory(build_output_dir)

  os.chdir(options.build_dir)
  if sys.platform == 'win32':
    command = [
        'python',
        '../third_party/scons/scons.py',
        ('env=PATH:'
            'C:\\Program Files\\Microsoft Visual Studio 9.0\\VC\\bin;'
            'C:\\Program Files\\Microsoft Visual Studio 9.0\\Common7\\IDE;'
            'C:\\Program Files\\Microsoft Visual Studio 9.0\\Common7\\Tools'
            ',INCLUDE:'
            'C:\\Program Files\\Microsoft Visual Studio 9.0\\VC\\include;'
            'C:\\Program Files\\Microsoft SDKs\\Windows\\v6.0A\\Include'
            ',LIB:'
            'C:\\Program Files\\Microsoft Visual Studio 9.0\\VC\\lib;'
            'C:\\Program Files\\Microsoft SDKs\\Windows\\v6.0A\\Lib')
    ]
  else:
    command = ['python', '../third_party/scons/scons.py']

  env = os.environ.copy()
  if sys.platform == 'linux2':
    common_linux_settings(command, options, env)
  else:
    command.extend(['-k'])

  command.extend([
      # Force scons to always check for dependency changes.
      'mode=' + options.target,
      'sample=shell'
  ])

  command.extend(options.build_args + args)
  return chromium_utils.RunCommand(command, env=env)



def main_win(options, args):
  """Interprets options, clobbers object files, and calls the build tool.
  """
  # Prefer the version specified in the .sln. When devenv.com is used at the
  # command line to start a build, it doesn't accept sln file from a different
  # version.
  if not options.msvs_version:
    sln = open(os.path.join(options.build_dir, options.solution), 'rU')
    header = sln.readline().strip()
    sln.close()
    if header.endswith('10.00'):
      options.msvs_version = '9'
    elif header.endswith('9.00'):
      options.msvs_version = '8'
    else:
      print >> sys.stderr, "Unknown sln header:\n" + header
      return 1

  REG_ROOT = 'SOFTWARE\\Microsoft\\VisualStudio\\'
  devenv = ReadHKLMValue(REG_ROOT + options.msvs_version + '.0', 'InstallDir')
  if devenv:
    devenv = os.path.join(devenv, 'devenv.com')
  else:
    print >> sys.stderr, ("MSVS %s was requested but is not installed." %
        options.msvs_version)
    return 1

  ib = ReadHKLMValue('SOFTWARE\\Xoreax\\IncrediBuild\\Builder', 'Folder')
  if ib:
    ib = os.path.join(ib, 'BuildConsole.exe')

  if ib and os.path.exists(ib) and not options.no_ib:
    tool = ib
    tool_options = ['/Cfg=%s|Win32' % options.target]
    if options.project:
      tool_options.extend(['/Prj=%s' % options.project])
  else:
    tool = devenv
    tool_options = ['/Build', options.target]
    if options.project:
      tool_options.extend(['/Project', options.project])

  options.build_dir = os.path.abspath(options.build_dir)
  build_output_dir = os.path.join(options.build_dir, options.target)
  if options.clobber:
    print('Deleting %s...' % build_output_dir)
    chromium_utils.RemoveDirectory(build_output_dir)
  else:
    # Remove the log file so it doesn't grow without limit,
    chromium_utils.RemoveFile(build_output_dir, 'debug.log')
    # Remove the chrome.dll version resource so it picks up the new svn
    # revision, unless user explicitly asked not to remove it. See
    # Bug 1064677 for more details.
    if not options.keep_version_file:
      chromium_utils.RemoveFile(build_output_dir, 'obj', 'chrome_dll',
                                'chrome_dll_version.rc')

  env = os.environ.copy()
  if options.mode == 'google_chrome' or options.mode == 'official':
    env['CHROMIUM_BUILD'] = '_google_chrome'

  if options.mode == 'official':
    # Official builds are always Google Chrome.
    env['OFFICIAL_BUILD'] = '1'
    env['CHROME_BUILD_TYPE'] = '_official'

  if not options.solution:
    options.solution = 'all.sln'

  # jsc builds need another environment variable.
  # TODO(nsylvain): We should have --js-engine option instead.
  if options.solution.find('_kjs') != -1:
    env['JS_ENGINE_TYPE'] = '_kjs'

  result = -1
  solution = os.path.join(options.build_dir, options.solution)
  command = [tool, solution] + tool_options + args
  errors = []
  # Examples:
  # midl : command line error MIDL1003 : error returned by the C
  #   preprocessor (-1073741431)
  #
  # Error executing C:\PROGRA~2\MICROS~1\Common7\Tools\Bin\Midl.Exe (tool
  #    returned code: 1282)
  #
  # cl : Command line error D8027 : cannot execute 'C:\Program Files
  #    (x86)\Microsoft Visual Studio 8\VC\bin\c2.dll'
  #
  # Warning: Could not delete file "c:\b\slave\win\build\src\build\Debug\
  #    chrome.dll" : Access is denied
  # --------------------Build System Warning--------------------------------
  #    -------
  # Could not delete file:
  #     Could not delete file "c:\b\slave\win\build\src\build\Debug\
  #        chrome.dll" : Access is denied
  #     (Automatically running xgHandle on first 10 files that could not be
  #        deleted)
  #     Searching for '\Device\HarddiskVolume1\b\slave\win\build\src\build\
  #        Debug\chrome.dll':
  #     No handles found.
  #     (xgHandle utility returned code: 0x00000000)
  known_toolset_bugs = [
    '\\c2.dll',
    'Midl.Exe (tool returned code: 1282)',
    'LINK : fatal error LNK1102: out of memory',
  ]
  def scan(line):
    for known_line in known_toolset_bugs:
      if known_line in line:
        errors.append(line)
        break

  result = chromium_utils.RunCommand(
      command, parser_func=scan, env=env, universal_newlines=True)
  if errors:
    print('Retrying a clobber build because of:')
    print('\n'.join(('  ' + l for l in errors)))
    print('Deleting %s...' % build_output_dir)
    chromium_utils.RemoveDirectory(build_output_dir)
    result = chromium_utils.RunCommand(command, env=env)
  return result


def real_main():
  option_parser = optparse.OptionParser()
  option_parser.add_option('', '--clobber', action='store_true', default=False,
                           help='delete the output directory before compiling')
  option_parser.add_option('', '--keep-version-file', action='store_true',
                           default=False,
                           help='do not delete the chrome_dll_version.rc file '
                                'before compiling (ignored if --clobber is '
                                'used')
  option_parser.add_option('', '--target', default='Release',
                           help='build target (Debug or Release)')
  option_parser.add_option('', '--solution', default=None,
                           help='name of solution/sub-project to build')
  option_parser.add_option('', '--project', default=None,
                           help='name of project to build')
  option_parser.add_option('', '--build-dir', default='build',
                           help='path to directory containing solution and in '
                                'which the build output will be placed')
  option_parser.add_option('', '--mode', default='dev',
                           help='build mode (dev or official) controlling '
                                'environment variables set during build')
  option_parser.add_option('', '--build-tool', default=None,
                           help='specify build tool (ib, vs, scons, xcode)')
  option_parser.add_option('', '--build-args', action='append', default=[],
                           help='arguments to pass to the build tool')
  option_parser.add_option('', '--compiler', default=None,
                           help='specify alternative compiler (e.g. clang)')
  if chromium_utils.IsWindows():
    # Windows only.
    option_parser.add_option('', '--no-ib', action='store_true', default=False,
                             help='use Visual Studio instead of IncrediBuild')
    option_parser.add_option('', '--msvs_version',
                             help='VisualStudio version to use')
  if chromium_utils.IsLinux():
    # For linux to arm cross compile.
    option_parser.add_option('', '--crosstool', default=None,
                             help='optional path to crosstool toolset')
  if chromium_utils.IsMac():
    # Mac only.
    option_parser.add_option('', '--xcode-target', default=None,
                             help='Target from the xcodeproj file')
  if chromium_utils.IsLinux() or chromium_utils.IsMac():
    option_parser.add_option('', '--goma-dir', default=None,
                             help='specify goma directory')
  option_parser.add_option('--verbose', action='store_true')

  options, args = option_parser.parse_args()

  if options.build_tool is None:
    if chromium_utils.IsWindows():
      main = main_win
    elif chromium_utils.IsMac():
      main = main_xcode
    elif chromium_utils.IsLinux():
      main = main_make
    else:
      print('Please specify --build-tool.')
      return 1
  else:
    build_tool_map = {
        'ib' : main_win,
        'vs' : main_win,
        'make' : main_make,
        'scons' : main_scons,
        'xcode' : main_xcode,
        'scons_v8' : main_scons_v8,
    }
    main = build_tool_map.get(options.build_tool)
    if not main:
      sys.stderr.write('Unknown build tool %s.\n' % repr(options.build_tool))
      return 2

  return main(options, args)


if '__main__' == __name__:
  sys.exit(real_main())
