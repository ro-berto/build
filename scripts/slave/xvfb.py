# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions to setup xvfb, which is used by the linux machines.
"""

import os
import platform
import signal
import subprocess
import tempfile

def _XvfbPidFilename(slave_build_name):
  """Returns the filename to the Xvfb pid file.  This name is unique for each
  builder. This is used by the linux builders."""
  return os.path.join(tempfile.gettempdir(),
                      'xvfb-' + slave_build_name  + '.pid')


def StartVirtualX(slave_build_name, build_dir, with_wm=True, server_dir=None):
  """Start a virtual X server and set the DISPLAY environment variable so sub
  processes will use the virtual X server.  Also start icewm. This only works
  on Linux and assumes that xvfb and icewm are installed.

  Args:
    slave_build_name: The name of the build that we use for the pid file.
        E.g., webkit-rel-linux.
    build_dir: The directory where binaries are produced.  If this is non-empty,
        we try running xdisplaycheck from |build_dir| to verify our X
        connection.
    with_wm: Whether we add a window manager to the display too.
    server_dir: Directory to search for the server executable.
  """
  # We use a pid file to make sure we don't have any xvfb processes running
  # from a previous test run.
  StopVirtualX(slave_build_name)

  # Figure out which X server to try.
  cmd = "Xvfb"
  if server_dir and os.path.exists(server_dir):
    cmd = os.path.join(server_dir, 'Xvfb.' + platform.architecture()[0])
    if not os.path.exists(cmd):
      cmd = os.path.join(server_dir, 'Xvfb')
    if not os.path.exists(cmd):
      print "No Xvfb found in designated server path:", server_dir
      raise Exception("No virtual server")

  # Start a virtual X server that we run the tests in.  This makes it so we can
  # run the tests even if we didn't start the tests from an X session.
  proc = subprocess.Popen([cmd, ":9", "-screen", "0", "1024x768x24", "-ac"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  xvfb_pid_filename = _XvfbPidFilename(slave_build_name)
  open(xvfb_pid_filename, 'w').write(str(proc.pid))
  os.environ['DISPLAY'] = ":9"

  # Verify that Xvfb has started by using xdisplaycheck.
  if build_dir:
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

  if with_wm:
    # Some ChromeOS tests need a window manager.
    subprocess.Popen("icewm", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print "Window manager (icewm) started."
  else:
    print "No window manager required."



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
