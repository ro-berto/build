# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import shutil
import subprocess
import sys
import time

LOGGER = logging.getLogger(__name__)

import requests
from slave import infra_platform

CLIENT_NAME = 'cipd' + infra_platform.exe_suffix()


BINARY_FILE = 0
# copied from
#   https://github.com/luci/recipes-py/blob/master/recipe_engine/step_runner.py
if sys.platform == "win32":
  BINARY_FILE = os.O_BINARY
  # Windows has a bad habit of opening a dialog when a console program
  # crashes, rather than just letting it crash.  Therefore, when a
  # program crashes on Windows, we don't find out until the build times out.
  # This code prevents the dialog from appearing, so that we find out
  # immediately and don't waste time waiting for a human to close the dialog.
  import ctypes
  # SetErrorMode(
  #   SEM_FAILCRITICALERRORS|
  #   SEM_NOGPFAULTERRORBOX|
  #   SEM_NOOPENFILEERRORBOX
  # ).
  #
  # For more information, see:
  # https://msdn.microsoft.com/en-us/library/windows/desktop/ms680621.aspx
  ctypes.windll.kernel32.SetErrorMode(0x0001|0x0002|0x8000)


def _update_client(path, version):
  """Ensures that the client in the provided path is at the given version.

  Will try to use the client's selfupdate mechanism first, and failing that,
  fall back to doing a python-based download of the client.

  When this function returns successfully, the client exists at that path and
  knows its own version (so is guaranteed to be able to respond to `cipd
  version` invocations). Otherwise this will raise an exception.
  """
  client_path = os.path.join(path, CLIENT_NAME)

  # Happy path
  if os.path.exists(client_path):
    if _selfupdate_client(client_path, version, fatal=False):
      return

  # Sad/Fresh path
  _fresh_download(client_path, version)
  # Call selfupdate to write .versions and .cipd_client_cache files
  _selfupdate_client(client_path, version, fatal=True)


def _selfupdate_client(client_path, version, fatal):
  """Invokes the cipd client's `selfupdate` behavior.

  This makes the client attempt to do an in-place update of itself. If the
  client is valid and `version` is the same cipd tag that was previously used to
  download the client, this is a no-network-access no-op.
  """
  try:
    new_env = os.environ.copy()
    new_env['CIPD_HTTP_USER_AGENT_PREFIX'] = (
      'build.git/scripts/slave/cipd_bootstrap_v2.py'
    )
    cmd = [client_path, 'selfupdate' , '-version', version]
    LOGGER.info('Running %r', cmd)
    subprocess.check_call(cmd, env=new_env)
    return True
  except subprocess.CalledProcessError as ex:
    if fatal:
      raise  # will get logged at top
    LOGGER.error('existing client selfupdate had retcode=%d (overwriting)',
                 ex.returncode)
  except OSError as ex:
    if fatal:
      raise  # will get logged at top
    LOGGER.error('bad existing client (overwriting): %s', ex)
  return False


def _fresh_download(client_path, version):
  """Attempts to do a fresh download of client_path directly from the server,
  overwriting any existing client.

  Note that this MAY fail on windows if the existing client is running
  (somehow). We anticipate that this should be a fairly rare occurance and so
  don't complicate the code here to account for it, but it's something to watch
  out for.
  """
  LOGGER.info('Bootstrapping fresh %s', client_path)
  r = requests.get('https://chrome-infra-packages.appspot.com/client', params={
    'version': version,
    'platform': infra_platform.cipd_platform_arch(),
  }, stream=True)

  # use fixed tmp file to avoid cleanup issues.
  tmp_client = client_path+'.tmp'
  start_time = time.time()
  last_print_timestamp = None
  done = 0
  chunk_size = 64 * 1024  # 64KB
  if r.headers.get('transfer-encoding', '').lower() == 'chunked':
    chunk_size = None  # this lets requests use the server's chunk sizes
  fd = os.open(tmp_client, os.O_TRUNC|os.O_WRONLY|os.O_CREAT|BINARY_FILE, 0777)
  try:
    for data in r.iter_content(chunk_size):
      os.write(fd, data)
      done += len(data)
      now = time.time()
      if last_print_timestamp is None or now - last_print_timestamp > 1:
        last_print_timestamp = now
        LOGGER.info('fetched ... %0.2fMB (%0.2f sec)',
                    float(done) / (1024 ** 2), now - start_time)
  finally:
    os.close(fd)
  LOGGER.info('fetched ... %0.2fMB (done)', float(done) / (1024 ** 2))

  for i in range(7):
    try:
      shutil.move(tmp_client, client_path)
      return
    except OSError as ex:
      if i == 6:
        LOGGER.error('failed to rename (%s) after 6 tries. giving up', ex)
        raise

      # sleep a minimum of .1 seconds, up to 1 second
      # with 6 retries, this takes a maximum total time of 3.2 seconds.
      amt = 0.1 * ((i+1)**1.3)
      LOGGER.info(
        'failed to rename (%s), retrying after %0.2f seconds', ex, amt)
      time.sleep(amt)

  raise Exception('impossible')


def _add_to_path(path):
  """Adds `path` to $PATH if it's not already in there.

  If it's already in $PATH, it will be moved to the front.
  """
  cur_path = os.environ.get('PATH', '').split(os.path.pathsep)
  cur_path = [x for x in cur_path if os.path.realpath(x) != path]
  cur_path.insert(0, path)
  os.environ['PATH'] = os.path.pathsep.join(cur_path)


def ensure_cipd_client(path, version):
  """Ensures that a cipd client of the given version exists at the provided
  path.

  The path provided should ONLY be used for housing the cipd client. This
  function will add the provided path to the beginning of the global PATH
  envvar.

  Failure to ensure this version will exit the program.

  Within a given path, this function is NOT concurrency-safe (in order to keep
  it simple).

  Args:
    version (str) - The version of the client to ensure.
    path (str) - The absolute path of the directory to ensure cipd in.
  """
  if not isinstance(version, str):
    raise TypeError('`version` must be a string')
  if not version:
    raise ValueError('`version` is empty')
  if not os.path.isabs(path):
    raise ValueError('`path` is not absolute: %r' % path)

  if not os.path.isdir(path):
    os.makedirs(path)

  LOGGER.info('ensuring cipd client %s @ %s',
              os.path.join(path, CLIENT_NAME), version)

  try:
    _update_client(path, version)
  except Exception:
    LOGGER.exception('caught exception in ensure_cipd_client')
    sys.exit('Failed to ensure cipd client')
  _add_to_path(path)
