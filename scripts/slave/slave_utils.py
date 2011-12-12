# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions specific to build slaves, shared by several buildbot scripts.
"""

import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time

from common import chromium_utils
import config


# Local errors.
class PageHeapError(Exception): pass


# Cache the path to gflags.exe.
_gflags_exe = None

def SubversionExe():
  # TODO(pamg): move this into platform_utils to support Mac and Linux.
  if chromium_utils.IsWindows():
    return 'svn.bat' # Find it in the user's path.
  elif chromium_utils.IsLinux() or chromium_utils.IsMac():
    return 'svn' # Find it in the user's path.
  else:
    raise NotImplementedError(
          'Platform "%s" is not currently supported.' % sys.platform)

def SubversionCat(wc_dir):
  """Output the content of specified files or URLs in SVN.
  """
  try:
    return chromium_utils.GetCommandOutput([SubversionExe(), 'cat',
                                            wc_dir])
  except chromium_utils.ExternalError:
    return None

def SubversionRevision(wc_dir):
  """Finds the last svn revision of a working copy by running 'svn info',
  and returns it as an integer.
  """
  svn_regexp = re.compile(r'.*Revision: (\d+).*', re.DOTALL)
  try:
    svn_info = chromium_utils.GetCommandOutput([SubversionExe(), 'info',
                                               wc_dir])
    return_value = re.sub(svn_regexp, r'\1', svn_info)
    if (return_value.isalnum()):
      return int(return_value)
    else:
      return 0
  except chromium_utils.ExternalError:
    return 0

def SubversionLastChangedRevision(wc_dir):
  """Finds the svn revision where this file/dir was last edited by running
  'svn info', and returns it as an integer.
  """
  svn_regexp = re.compile(r'.*Last Changed Rev: (\d+).*', re.DOTALL)
  try:
    svn_info = chromium_utils.GetCommandOutput([SubversionExe(), 'info',
                                               wc_dir])
    return_value = re.sub(svn_regexp, r'\1', svn_info)
    if (return_value.isalnum()):
      return int(return_value)
    else:
      return 0
  except chromium_utils.ExternalError:
    return 0


def SlaveBuildName(chrome_dir):
  """Extracts the build name of this slave (e.g., 'chrome-release') from the
  leaf subdir of its build directory.
  """
  return os.path.basename(SlaveBaseDir(chrome_dir))


def SlaveBaseDir(chrome_dir):
  """Finds the full path to the build slave's base directory (e.g.
  'c:/b/chrome/chrome-release').  This is assumed to be the parent of the
  shallowest 'build' directory in the chrome_dir path.

  Raises chromium_utils.PathNotFound if there is no such directory.
  """
  result = ''
  prev_dir = ''
  curr_dir = chrome_dir
  while prev_dir != curr_dir:
    (parent, leaf) = os.path.split(curr_dir)
    if leaf == 'build':
      # Remember this one and keep looking for something shallower.
      result = parent
    if leaf == 'slave':
      # We are too deep, stop now.
      break
    prev_dir = curr_dir
    curr_dir = parent
  if not result:
    raise chromium_utils.PathNotFound('Unable to find slave base dir above %s' %
                                    chrome_dir)
  return result


def GetStagingDir(start_dir):
  """Creates a chrome_staging dir in the starting directory. and returns its
  full path.
  """
  staging_dir = os.path.join(SlaveBaseDir(start_dir), 'chrome_staging')
  chromium_utils.MaybeMakeDirectory(staging_dir)
  return staging_dir


def SetPageHeap(chrome_dir, exe, enable):
  """Enables or disables page-heap checking in the given executable, depending
  on the 'enable' parameter.  gflags_exe should be the full path to gflags.exe.
  """
  global _gflags_exe
  if _gflags_exe is None:
    _gflags_exe = chromium_utils.FindUpward(chrome_dir,
                                          'tools', 'memory', 'gflags.exe')
  command = [_gflags_exe]
  if enable:
    command.extend(['/p', '/enable', exe, '/full'])
  else:
    command.extend(['/p', '/disable', exe])
  result = chromium_utils.RunCommand(command)
  if result:
    description = {True: 'enable', False:'disable'}
    raise PageHeapError('Unable to %s page heap for %s.' %
                        (description[enable], exe))


def LongSleep(secs):
  """A sleep utility for long durations that avoids appearing hung.

  Sleeps for the specified duration.  Prints output periodically so as not to
  look hung in order to avoid being timed out.  Since this function is meant
  for long durations, it assumes that the caller does not care about losing a
  small amount of precision.

  Args:
    secs: The time to sleep, in seconds.
  """
  secs_per_iteration = 60
  time_slept = 0

  # Make sure we are dealing with an integral duration, since this function is
  # meant for long-lived sleeps we don't mind losing floating point precision.
  secs = int(round(secs))

  remainder = secs % secs_per_iteration
  if remainder > 0:
    time.sleep(remainder)
    time_slept += remainder
    sys.stdout.write('.')
    sys.stdout.flush()

  while time_slept < secs:
    time.sleep(secs_per_iteration)
    time_slept += secs_per_iteration
    sys.stdout.write('.')
    sys.stdout.flush()

  sys.stdout.write('\n')


def _XvfbPidFilename(slave_build_name):
  """Returns the filename to the Xvfb pid file.  This name is unique for each
  builder. This is used by the linux builders."""
  return os.path.join(tempfile.gettempdir(),
                      'xvfb-' + slave_build_name  + '.pid')


def StartVirtualX(slave_build_name, build_dir):
  """Start a virtual X server and set the DISPLAY environment variable so sub
  processes will use the virtual X server.  Also start icewm. This only works
  on Linux and assumes that xvfb and icewm are installed.

  Args:
    slave_build_name: The name of the build that we use for the pid file.
        E.g., webkit-rel-linux.
    build_dir: The directory where binaries are produced.  If this is non-empty,
        we try running xdisplaycheck from |build_dir| to verify our X
        connection.
  """
  # We use a pid file to make sure we don't have any xvfb processes running
  # from a previous test run.
  StopVirtualX(slave_build_name)

  # Start a virtual X server that we run the tests in.  This makes it so we can
  # run the tests even if we didn't start the tests from an X session.
  proc = subprocess.Popen(["Xvfb", ":9", "-screen", "0", "1024x768x24", "-ac"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  xvfb_pid_filename = _XvfbPidFilename(slave_build_name)
  open(xvfb_pid_filename, 'w').write(str(proc.pid))
  os.environ['DISPLAY'] = ":9"

  # Verify that Xvfb has started by using xdisplaycheck.
  if len(build_dir) > 0:
    xdisplaycheck_path = os.path.join(build_dir, 'xdisplaycheck')
    if os.path.exists(xdisplaycheck_path):
      print "Verifying Xvfb has started..."
      xdisplayproc = subprocess.Popen([xdisplaycheck_path],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT)
      # Wait for xdisplaycheck to exit.
      xdisplayproc.communicate()
      if xdisplayproc.poll() != 0:
        print "Xvfb return code (None if still running):", proc.poll()
        print "Xvfb stdout and stderr:", proc.communicate()
        raise Exception(xdisplayproc.communicate()[0])
      print "...OK"
  # Some ChromeOS tests need a window manager.
  subprocess.Popen("icewm", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def StopVirtualX(slave_build_name):
  """Try and stop the virtual X server if one was started with StartVirtualX.
  When the X server dies, it takes down the window manager with it.
  If a virtual x server is not running, this method does nothing."""
  xvfb_pid_filename = _XvfbPidFilename(slave_build_name)
  if os.path.exists(xvfb_pid_filename):
    # If the process doesn't exist, we raise an exception that we can ignore.
    try:
      os.kill(int(open(xvfb_pid_filename).read()), signal.SIGKILL)
    except OSError:
      pass
    os.remove(xvfb_pid_filename)

def RunPythonCommandInBuildDir(build_dir, target, command_line_args):
  if sys.platform == 'win32':
    python_exe = 'python.exe'

    setup_mount = chromium_utils.FindUpward(build_dir,
                                            'third_party',
                                            'cygwin',
                                            'setup_mount.bat')

    chromium_utils.RunCommand([setup_mount])
  else:
    os.environ['PYTHONPATH'] = (chromium_utils.FindUpward(build_dir,
        'tools', 'python') + ":" + os.environ.get('PYTHONPATH', ''))
    python_exe = 'python'

  if chromium_utils.IsLinux():
    slave_name = SlaveBuildName(build_dir)
    StartVirtualX(slave_name, os.path.join(build_dir, '..', 'out', target))

  command = [python_exe]

  # The list of tests is given as arguments.
  command.extend(command_line_args)

  result = chromium_utils.RunCommand(command)

  if chromium_utils.IsLinux():
    StopVirtualX(slave_name)

  return result


def GetActiveMaster():
  """Parses all the slaves.cfg and returns the name of the active master
  determined by the host name. Returns None otherwise."""
  hostname = socket.getfqdn().split('.', 1)[0].lower()
  for master in chromium_utils.ListMasters():
    path = os.path.join(master, 'slaves.cfg')
    for slave in chromium_utils.RunSlavesCfg(path):
      if slave.get('hostname', None) == hostname:
        return slave['master']


def CopyFileToArchiveHost(src, dest_dir):
  """A wrapper method to copy files to the archive host.
  It calls CopyFileToDir on Windows and SshCopyFiles on Linux/Mac.
  TODO: we will eventually want to change the code to upload the
  data to appengine.

  Args:
      src: full path to the src file.
      dest_dir: destination directory on the host.
  """
  host = config.Archive.archive_host
  if not os.path.exists(src):
    raise chromium_utils.ExternalError('Source path "%s" does not exist' % src)
  chromium_utils.MakeWorldReadable(src)
  if chromium_utils.IsWindows():
    chromium_utils.CopyFileToDir(src, dest_dir)
  elif chromium_utils.IsLinux() or chromium_utils.IsMac():
    chromium_utils.SshCopyFiles(src, host, dest_dir)
  else:
    raise NotImplementedError(
        'Platform "%s" is not currently supported.' % sys.platform)


def MaybeMakeDirectoryOnArchiveHost(dest_dir):
  """A wrapper method to create a directory on the archive host.
  It calls MaybeMakeDirectory on Windows and SshMakeDirectory on Linux/Mac.

  Args:
      dest_dir: destination directory on the host.
  """
  host = config.Archive.archive_host
  if chromium_utils.IsWindows():
    chromium_utils.MaybeMakeDirectory(dest_dir)
    print 'saving results to %s' % dest_dir
  elif chromium_utils.IsLinux() or chromium_utils.IsMac():
    chromium_utils.SshMakeDirectory(host, dest_dir)
    print 'saving results to "%s" on "%s"' % (dest_dir, host)
  else:
    raise NotImplementedError(
        'Platform "%s" is not currently supported.' % sys.platform)

def GSUtilSetup():
  # Get the path to the gsutil script.
  gsutil = os.path.join(os.path.dirname(__file__), 'gsutil')
  gsutil = os.path.normpath(gsutil)
  if chromium_utils.IsWindows():
    gsutil = gsutil + '.bat'

  # Get the path to the boto file containing the password.
  boto_file = os.path.join(os.path.dirname(__file__), '..', '..', 'site_config',
                           '.boto')

  # Make sure gsutil uses this boto file.
  os.environ['AWS_CREDENTIAL_FILE'] = boto_file
  return gsutil

def GSUtilCopyFile(filename, gs_base, subdir=None, mimetype=None):
  """Copy a file to Google Storage."""

  source = 'file://' + filename
  dest = gs_base
  if subdir:
    # HACK(nsylvain): We can't use normpath here because it will break the
    # slashes on Windows.
    if subdir == '..':
      dest = os.path.dirname(gs_base)
    else:
      dest = '/'.join([gs_base, subdir])
  dest = '/'.join([dest, os.path.basename(filename)])

  gsutil = GSUtilSetup()

  # Run the gsutil command. gsutil internally calls command_wrapper, which
  # will try to run the command 10 times if it fails.
  command = [gsutil]
  if mimetype :
    command.extend(['-h', 'Content-Type:%s' % mimetype])
  command.extend(['cp', '-a', 'public-read', source, dest])
  return chromium_utils.RunCommand(command)

def GSUtilCopyDir(src_dir, gs_base, dest_dir=None):
  """Create a list of files in a directory and pass each to GSUtilCopyFile."""

  # Walk the source directory and find all the files.
  # Alert if passed a file rather than a directory.
  if os.path.isfile(src_dir):
    assert os.path.isdir(src_dir), '%s must be a directory' % src_dir

  # Get the list of all files in the source directory.
  file_list = []
  for root, _, files in os.walk(src_dir):
    file_list.extend((os.path.join(root, name) for name in files))

  # Find the absolute path of the source directory so we can use it below.
  base = os.path.abspath(src_dir) + os.sep

  for file in file_list:
    # Strip the base path off so we just have the relative file path.
    path = file.partition(base)[2]

    # If we have been given a destination directory, add that to the path.
    if dest_dir:
        path = os.path.join(dest_dir, path)

    # Trim the filename and last slash off to create a destination path.
    path = path.rpartiton(os.sep + os.path.basename(path))[0]

    # If we're on windows, we need to reverse slashes, gsutil wants posix paths.
    if chromium_utils.IsWindows():
      path = path.replace('\\', '/')

    # Pass the file off to copy.
    status = GSUtilCopyFile(file, gs_base, path)

    # Bail out on any failure.
    if status:
      return status

  return 0

# Python doesn't support the type of variable scope in nested methods needed
# to avoid the global output variable.  This variable should only ever be used
# by GSUtilListBucket.
command_output = ''
def GSUtilListBucket(gs_base):
  """List the contents of a Google Storage bucket."""

  gsutil = GSUtilSetup()

  # Run the gsutil command. gsutil internally calls command_wrapper, which
  # will try to run the command 10 times if it fails.
  global command_output
  command_output = ''
  def GatherOutput(line):
    global command_output
    command_output += line + '\n'
  command = [gsutil, 'ls', '-l', gs_base]
  status = chromium_utils.RunCommand(command, parser_func=GatherOutput)
  return (status, command_output)
