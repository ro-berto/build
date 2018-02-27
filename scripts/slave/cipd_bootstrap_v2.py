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
from slave import cipd

CLIENT_NAME = 'cipd' + infra_platform.exe_suffix()


DEFAULT_CIPD_VERSION = 'git_revision:e1abc57be62d198b5c2f487bfb2fa2d2eb0e867c'
STAGING_CIPD_VERSION = 'git_revision:e1abc57be62d198b5c2f487bfb2fa2d2eb0e867c'

PROD = None
STAGING = 'staging'
CANARY = 'canary'

# maps mastername (e.g. chromium.infra) as seen in the buildbot 'mastername'
# property to STAGING or CANARY.
#
# STAGING will get the STAGING_CIPD_VERSION, and CANARY will get 'latest'.
# 'mastername' values not in this map will get DEFAULT_CIPD_VERSION.
MASTER_VERSION = {
  'chromium.infra': STAGING,
  'chromium.infra.cron': STAGING,
}


# Auxiliary binary packages to add to PATH during CIPD installation.
AUX_BINARY_PACKAGES = {
    # Default (production) packages.
    None: (
      cipd.CipdPackage(
          name='infra/tools/luci/vpython/${platform}',
          version='git_revision:e1abc57be62d198b5c2f487bfb2fa2d2eb0e867c'),

      cipd.CipdPackage(
          name='infra/tools/git/${platform}',
          version='git_revision:e1abc57be62d198b5c2f487bfb2fa2d2eb0e867c'),

      ## The Python package installs its binaries into "bin/".
      #cipd.CipdPackage(
          #name='infra/python/cpython/${os}-${arch=386,amd64}',
          #version='version:2.7.13.chromium8'),

      # The Git package installs its binaries into "bin/".
      cipd.CipdPackage(
          name='infra/git/${os=linux,mac}-${arch=386,amd64}',
          version='version:2.15.1.chromium12'),

      cipd.CipdPackage(
          name='infra/git/windows-${arch=386,amd64}',
          version='version:2.15.1.2.chromium12'),

      cipd.CipdPackage(
          name='infra/tools/buildbucket/${platform}',
          version='git_revision:e1abc57be62d198b5c2f487bfb2fa2d2eb0e867c'),

      cipd.CipdPackage(
          name='infra/tools/cloudtail/${platform}',
          version='git_revision:e1abc57be62d198b5c2f487bfb2fa2d2eb0e867c'),

      cipd.CipdPackage(
          name='infra/tools/luci-auth/${platform}',
          version='git_revision:e1abc57be62d198b5c2f487bfb2fa2d2eb0e867c'),
    ),

    STAGING: (
      cipd.CipdPackage(
          name='infra/tools/luci/vpython/${platform}',
          version='git_revision:e1abc57be62d198b5c2f487bfb2fa2d2eb0e867c'),

      cipd.CipdPackage(
          name='infra/tools/git/${platform}',
          version='git_revision:e1abc57be62d198b5c2f487bfb2fa2d2eb0e867c'),

      # The Python package installs its binaries into "bin/".
      cipd.CipdPackage(
          name='infra/python/cpython/${os}-${arch=386,amd64}',
          version='version:2.7.14.chromium14'),

      # The Git package installs its binaries into "bin/".
      cipd.CipdPackage(
          name='infra/git/${os=linux,mac}-${arch=386,amd64}',
          version='version:2.16.2.chromium12'),

      # Note: pinned to same version as *nix above, but kept separate because
      # this is a coincidence and not the norm.
      cipd.CipdPackage(
          name='infra/git/windows-${arch=386,amd64}',
          version='version:2.16.2.chromium12'),

      cipd.CipdPackage(
          name='infra/tools/buildbucket/${platform}',
          version='git_revision:e1abc57be62d198b5c2f487bfb2fa2d2eb0e867c'),

      cipd.CipdPackage(
          name='infra/tools/cloudtail/${platform}',
          version='git_revision:e1abc57be62d198b5c2f487bfb2fa2d2eb0e867c'),

      cipd.CipdPackage(
          name='infra/tools/luci-auth/${platform}',
          version='git_revision:e1abc57be62d198b5c2f487bfb2fa2d2eb0e867c'),
    ),

    CANARY: (
      cipd.CipdPackage(
          name='infra/tools/luci/vpython/${platform}',
          version='latest'),

      cipd.CipdPackage(
          name='infra/tools/git/${platform}',
          version='latest'),

      # The Python package installs its binaries into "bin/".
      #
      # Currently, we only install Python on Windows, since we believe that
      # other platforms make assumptions about package availability.
      cipd.CipdPackage(
          name='infra/python/cpython/${os=windows}-${arch=386,amd64}',
          version='latest'),

      # The Git package installs its binaries into "bin/".
      #
      # Currently, we only install Git on x86 and amd64 platforms because we
      # don't have cross-compile support for Git packages yet.
      cipd.CipdPackage(
          name='infra/git/${os}-${arch=386,amd64}',
          version='latest'),

      cipd.CipdPackage(
          name='infra/tools/buildbucket/${platform}',
          version='latest'),

      cipd.CipdPackage(
          name='infra/tools/cloudtail/${platform}',
          version='latest'),

      cipd.CipdPackage(
          name='infra/tools/luci-auth/${platform}',
          version='latest'),
    ),
}


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

  def _ensure_batfile(client_path):
    base, _ = os.path.splitext(client_path)
    with open(base+".bat", 'w') as f:
      f.write('\n'.join([  # python turns \n into CRLF
        '@set CIPD="%~dp0cipd.exe"',
        '@shift',
        '@%CIPD% %*'
      ]))
else:
  def _ensure_batfile(_client_path):
    pass


def all_cipd_packages():
  """Generator which yields all referenced CIPD packages."""
  package_name = 'infra/tools/cipd/${platform}'
  yield cipd.CipdPackage(name=package_name, version=DEFAULT_CIPD_VERSION)
  yield cipd.CipdPackage(name=package_name, version=STAGING_CIPD_VERSION)
  for packages in AUX_BINARY_PACKAGES.itervalues():
    for pkg in packages:
      yield pkg


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
    # Check to make sure current architecture matches what we expect.
    if _arch_match(client_path):
      if _selfupdate_client(client_path, version, fatal=False):
        return

  # Sad/Fresh path
  _fresh_download(client_path, version)
  # Call selfupdate to write .versions and .cipd_client_cache files
  _selfupdate_client(client_path, version, fatal=True)


def _arch_match(client_path):
  """Checks the current cipd client has an architecture which matches the
  architecture we'd get if we did a fresh download."""
  try:
    output = subprocess.check_output([client_path, 'version'])
  except subprocess.CalledProcessError as ex:
    LOGGER.error('existing client failed version check retcode=%d',
                 ex.returncode)
    return False

  # plat will be e.g. 'linux-amd64'
  plat = infra_platform.cipd_platform()
  for line in output.splitlines():
    if line.endswith(plat):
      LOGGER.info('existing client matches platform: %s', plat)
      return True

  return False


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
    _ensure_batfile(client_path)
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
  plat = infra_platform.cipd_platform()
  LOGGER.info('Bootstrapping fresh %s for version [%s] on platform [%s]',
              client_path, version, plat)
  r = requests.get('https://chrome-infra-packages.appspot.com/client', params={
    'version': version,
    'platform': plat,
  }, stream=True)
  r.raise_for_status()

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
  """Adds `path` to $PATH if it exists and is not already in there.

  If it's already in $PATH, it will be moved to the front.
  """
  if not os.path.isdir(path):
    return

  cur_path = os.environ.get('PATH', '').split(os.path.pathsep)
  cur_path = [x for x in cur_path if os.path.realpath(x) != path]
  cur_path.insert(0, path)
  os.environ['PATH'] = os.path.pathsep.join(cur_path)
  return path


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
  return filter(bool, [_add_to_path(path)])


def install_cipd_packages(dest, *packages):
  """Bootstraps CIPD in |dest| and installs requested |packages|.

  Args:
    dest (str): The CIPD installation root.
    packages (list of CipdPackage): The set of CIPD packages to install.
  """
  # Build our CIPD manifest. We'll pass it via STDIN.
  manifest = '\n'.join('%s %s' % (pkg.name, pkg.version) for pkg in packages)

  cmd = [
      CLIENT_NAME,
      'ensure',
      '-ensure-file', '-',
      '-root', dest,
  ]

  LOGGER.info('Executing CIPD command: %s\nManifest:\n%s', cmd, manifest)
  proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT)
  stdout, _ = proc.communicate(input=manifest)
  if proc.returncode != 0:
    LOGGER.error('CIPD exited with non-zero return code (%s):\n%s',
        proc.returncode, stdout)
    raise ValueError('Failed to install CIPD packages (%d)' % (
        proc.returncode,))


def install_auxiliary_path_packages(dest, track):
  """Installs the set of auxiliary binary packages into PATH.

  Args:
    dest (str): The CIPD root directory to install into and add to PATH.
    track (str): The track to use, either STAGING, CANARY, or None (PROD).
  """
  ret = []
  packages = AUX_BINARY_PACKAGES.get(track, AUX_BINARY_PACKAGES[None])
  if packages:
    if not os.path.isdir(dest):
      os.makedirs(dest)

    install_cipd_packages(dest, *packages)

    # Add the packages to PATH. Add "/bin" first, since it's where raw
    # Python/Git reside. Add "dest" second so that wrappers will be preferred
    # to underlying binaries.
    ret.append(_add_to_path(os.path.join(dest, 'bin')))
    ret.append(_add_to_path(dest))

  # reverse ret so it goes [<dest>, <dest>/bin], preferring wrappers to
  # underlying binaries (as above).
  return reversed(filter(bool, ret))


def high_level_ensure_cipd_client(b_dir, mastername, track=None):
  """Ensures that <b_dir>/cipd_client/ contains the cipd (or cipd.exe) client.

  Also sets the $CIPD_CACHE_DIR envvar to <b_dir>/c/cipd.

  Will use mastername to determine which version of the client to ensure. See
  MASTER_VERSION in this module to see how the version lookup works.

  Raises an exception if this fails.

  Args:
    b_dir (str): The path to the "/b" directory.
    mastername (str): The master name, used to determine automatic track.
    track (str): Explicitly specify which track to use, either STAGING, CANARY,
        or PROD (None) to automatically choose a track based on |mastername|.

  Returns the list of paths added to $PATH.
  """
  LOGGER.info('bootstrapping CIPD')

  b_dir = os.path.abspath(b_dir)
  cipd_dir = os.path.join(b_dir, 'cipd_client')
  cipd_version = DEFAULT_CIPD_VERSION
  if not track:
    track = MASTER_VERSION.get(mastername)
  if track == STAGING:
    LOGGER.info("using staging revision")
    cipd_version = STAGING_CIPD_VERSION
  elif track == CANARY:
    LOGGER.info("using canary revision (latest)")
    cipd_version = 'latest'

  os.environ['CIPD_CACHE_DIR'] = os.path.join(b_dir, 'c', 'cipd')
  ret = ensure_cipd_client(cipd_dir, cipd_version)

  ret.extend(install_auxiliary_path_packages(
    os.path.join(b_dir, 'cipd_path_tools'), track))
  os.environ['VPYTHON_VIRTUALENV_ROOT'] = os.path.join(b_dir, 'c', 'vpython')

  # return a dedup'd list of everything in ret
  return [x for i, x in enumerate(ret) if x not in ret[:i]]
