"""Splits command lines for Windows.

This file calls out to Windows system DLLs, so the function should only be
called when running on a Windows OS.
"""

import sys

from ctypes import POINTER, byref, c_int, c_wchar_p

def WindowsShellSplit(command):
  """Splits a command line string into a parsed list of args."""
  assert sys.platform == 'win32'

  # Import windll only after we're sure we're running on Windows.
  from ctypes import windll

  CommandLineToArgvW = windll.shell32.CommandLineToArgvW
  CommandLineToArgvW.argtypes = [c_wchar_p, POINTER(c_int)]
  CommandLineToArgvW.restype = POINTER(c_wchar_p)

  argc = c_int(0)
  argv = CommandLineToArgvW(c_wchar_p(command), byref(argc))
  return [argv[i] for i in xrange(argc.value)]
