# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions specific to build slaves, shared by several buildbot scripts.
"""

import datetime
import glob
import optparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

from common import chromium_utils

# These codes used to distinguish true errors from script warnings.
ERROR_EXIT_CODE = 1
WARNING_EXIT_CODE = 88


# Regex matching git comment lines containing svn revision info.
GIT_SVN_ID_RE = re.compile(r'^git-svn-id: .*@([0-9]+) .*$')
# Regex for the master branch commit position.
GIT_CR_POS_RE = re.compile(r'^Cr-Commit-Position: refs/heads/master@{#(\d+)}$')

# Global variables set by command-line arguments (AddArgs, AddOpts).
_ARGS_GSUTIL_PY_PATH = os.environ.get('BUILD_SLAVE_UTILS_GSUTIL_PY_PATH')


# Local errors.
class PageHeapError(Exception):
  pass


# Cache the path to gflags.exe.
_gflags_exe = None


def GitExe():
  return 'git.bat' if chromium_utils.IsWindows() else 'git'


class NotGitWorkingCopy(Exception): pass
class NotAnyWorkingCopy(Exception): pass
class NoCommitPosition(Exception): pass


def GitHash(wc_dir):
  """Finds the current commit hash of the wc_dir."""
  retval, text = chromium_utils.GetStatusOutput(
      [GitExe(), 'rev-parse', 'HEAD'], cwd=wc_dir)
  if retval or 'fatal: Not a git repository' in text:
    raise NotGitWorkingCopy(wc_dir)
  return text.strip()


def GetHashOrRevision(wc_dir):
  """Gets the git hash of wc_dir as a string. Throws NotAnyWorkingCopy if the
  wc_dir isn't a git checkout."""
  try:
    return GitHash(wc_dir)
  except NotGitWorkingCopy:
    pass
  raise NotAnyWorkingCopy(wc_dir)


def GetBuildRevisions(src_dir, revision_dir=None):
  """Parses build revisions out of the provided directories.

  Args:
    src_dir: The source directory to be used to check the revision in.
    revision_dir: If provided, this dir will be used for the build revision
      instead of the mandatory src_dir.

  Returns a tuple of the build revision and (optional) WebKit revision.
  NOTICE: These revisions are strings, since they can be both Subversion numbers
  and Git hashes.
  """
  abs_src_dir = os.path.abspath(src_dir)
  if revision_dir:
    revision_dir = os.path.join(abs_src_dir, revision_dir)
    build_revision = GetHashOrRevision(revision_dir)
  else:
    build_revision = GetHashOrRevision(src_dir)
  return build_revision


def GetZipFileNames(
    mastername, buildnumber, parent_buildnumber, build_revision,
    extract=False, use_try_buildnumber=True):
  base_name = 'full-build-%s' % chromium_utils.PlatformName()

  if 'try' in mastername and use_try_buildnumber:
    if extract:
      if not parent_buildnumber:
        raise Exception('missing parent_buildnumber')
      version_suffix = '_%s' % parent_buildnumber
    else:
      version_suffix = '_%s' % buildnumber
  else:
    version_suffix = '_%s' % build_revision

  return base_name, version_suffix


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
  start_dir = os.path.abspath(start_dir)
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
    description = {True: 'enable', False: 'disable'}
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


def RunPythonCommandInBuildDir(build_dir, target, command_line_args,
                               server_dir=None, filter_obj=None):
  if sys.platform == 'win32':
    python_exe = 'python.exe'
  else:
    os.environ['PYTHONPATH'] = (chromium_utils.FindUpward(build_dir, 'tools',
                                                          'python')
                                + ':' +os.environ.get('PYTHONPATH', ''))
    python_exe = 'python'

  command = [python_exe] + command_line_args
  return chromium_utils.RunCommand(command, filter_obj=filter_obj)


class RunCommandCaptureFilter(object):
  lines = []

  def FilterLine(self, in_line):
    self.lines.append(in_line)
    return None

  def FilterDone(self, last_bits):
    self.lines.append(last_bits)
    return None


def GSUtilSetup():
  # Get the path to the gsutil script.
  if _ARGS_GSUTIL_PY_PATH:
    # The `gsutil.py` path was supplied on the command-line. Run this through
    # our local Python interpreter.
    #
    # Note: you should not use sys.executable because this function
    # could be used under vpython, which does not work well (crbug.com/793325).
    gsutil = ['python', _ARGS_GSUTIL_PY_PATH, '--']
  else:
    # Fall back to local repository 'gsutil' invocation. NOTE that this requires
    # the standard infra checkout layout, namely that 'depot_tools' is checked
    # out one directory above 'build'.
    gsutil = os.path.join(os.path.dirname(__file__), 'gsutil')
    gsutil = os.path.normpath(gsutil)
    if chromium_utils.IsWindows():
      gsutil += '.bat'
    gsutil = [gsutil]

  # Get the path to the boto file containing the password.
  boto_file = os.path.join(os.path.dirname(__file__), '..', '..', 'site_config',
                           '.boto')

  # Make sure gsutil uses this boto file if it exists.
  if os.path.exists(boto_file):
    os.environ['AWS_CREDENTIAL_FILE'] = boto_file
    os.environ['BOTO_CONFIG'] = boto_file
  return gsutil


def GSUtilGetMetadataField(name, provider_prefix=None):
  """Returns: (str) the metadata field to use with Google Storage

  The Google Storage specification for metadata can be found at:
  https://developers.google.com/storage/docs/gsutil/addlhelp/WorkingWithObjectMetadata
  """
  # Already contains custom provider prefix
  if name.lower().startswith('x-'):
    return name

  # See if it's innately supported by Google Storage
  if name in (
      'Cache-Control',
      'Content-Disposition',
      'Content-Encoding',
      'Content-Language',
      'Content-MD5',
      'Content-Type',
  ):
    return name

  # Add provider prefix
  if not provider_prefix:
    provider_prefix = 'x-goog-meta'
  return '%s-%s' % (provider_prefix, name)


def GSUtilCopy(source, dest, mimetype=None, gs_acl=None, cache_control=None,
               metadata=None, override_gsutil=None, add_quiet_flag=False):
  """Copy a file to Google Storage.

  Runs the following command:
    gsutil -h Content-Type:<mimetype> \
           -h Cache-Control:<cache_control> \
        cp -a <gs_acl> file://<filename> <dest>

  Args:
    source: the source URI
    dest: the destination URI
    mimetype: optional value to add as a Content-Type header
    gs_acl: optional value to add as a canned-acl
    cache_control: optional value to set Cache-Control header
    metadata: (dict) A dictionary of string key/value metadata entries to set
        (see `gsutil cp' '-h' option)
    override_gsutil (list): optional argv to run gsutil
    add_quiet_flag: add the -q (quiet) flag when invoking gsutil

  Returns:
    The status code returned from running the generated gsutil command.
  """

  if not source.startswith('gs://') and not source.startswith('file://'):
    source = 'file://' + source
  if not dest.startswith('gs://') and not dest.startswith('file://'):
    dest = 'file://' + dest
  # The setup also sets up some env variables - for now always run that.
  gsutil = GSUtilSetup()
  # Run the gsutil command. gsutil internally calls command_wrapper, which
  # will try to run the command 10 times if it fails.
  command = list(override_gsutil or gsutil)
  if add_quiet_flag:
    command.append('-q')

  if not metadata:
    metadata = {}
  if mimetype:
    metadata['Content-Type'] = mimetype
  if cache_control:
    metadata['Cache-Control'] = cache_control
  for k, v in sorted(metadata.iteritems(), key=lambda (k, _): k):
    field = GSUtilGetMetadataField(k)
    param = (field) if v is None else ('%s:%s' % (field, v))
    command += ['-h', param]
  command.extend(['cp'])
  if gs_acl:
    command.extend(['-a', gs_acl])
  command.extend([source, dest])
  return chromium_utils.RunCommand(command)


def GSUtilCopyFile(filename, gs_base, subdir=None, mimetype=None, gs_acl=None,
                   cache_control=None, metadata=None, override_gsutil=None,
                   dest_filename=None, add_quiet_flag=False):
  """Copies a file to Google Storage.

  Runs the following command:
    gsutil -h Content-Type:<mimetype> \
        -h Cache-Control:<cache_control> \
        cp -a <gs_acl> file://<filename> <gs_base>/<subdir>/<dest_filename>

  Args:
    filename: the file to upload
    gs_base: the bucket to upload the file to
    subdir: optional subdirectory within the bucket
    mimetype: optional value to add as a Content-Type header
    gs_acl: optional value to add as a canned-acl
    override_gsutil (list): optional argv to run gsutil
    dest_filename: optional destination filename; if not specified, then the
        destination filename will be the source filename without the path
    add_quiet_flag: add the -q (quiet) flag when invoking gsutil

  Returns:
    The status code returned from running the generated gsutil command.
  """

  source = filename
  if not (filename.startswith('gs://') or filename.startswith('file://')):
    source = 'file://' + filename
  dest = gs_base
  if subdir:
    # HACK(nsylvain): We can't use normpath here because it will break the
    # slashes on Windows.
    if subdir == '..':
      dest = os.path.dirname(gs_base)
    else:
      dest = '/'.join([gs_base, subdir])
  if dest_filename is None:
    dest_filename = os.path.basename(filename)
  dest = '/'.join([dest, dest_filename])
  return GSUtilCopy(source, dest, mimetype, gs_acl, cache_control,
                    metadata=metadata, override_gsutil=override_gsutil,
                    add_quiet_flag=add_quiet_flag)


def GSUtilCopyDir(src_dir, gs_base, dest_dir=None, gs_acl=None,
                  cache_control=None, add_quiet_flag=False):
  """Uploads the directory and its contents to Google Storage."""

  if os.path.isfile(src_dir):
    assert os.path.isdir(src_dir), '%s must be a directory' % src_dir

  command = GSUtilSetup()
  command += ['-m']
  if add_quiet_flag:
    command.append('-q')
  if cache_control:
    command.extend(['-h', 'Cache-Control:%s' % cache_control])
  command.extend(['cp', '-R'])
  if gs_acl:
    command.extend(['-a', gs_acl])
  if dest_dir:
    command.extend([src_dir, gs_base + '/' + dest_dir])
  else:
    command.extend([src_dir, gs_base])
  return chromium_utils.RunCommand(command)

def GSUtilDownloadFile(src, dst):
  """Copy a file from Google Storage."""
  # Run the gsutil command. gsutil internally calls command_wrapper, which
  # will try to run the command 10 times if it fails.
  command = GSUtilSetup()
  command.extend(['cp', src, dst])
  return chromium_utils.RunCommand(command)


def GSUtilMoveFile(source, dest, gs_acl=None):
  """Move a file on Google Storage."""

  gsutil = GSUtilSetup()

  # Run the gsutil command. gsutil internally calls command_wrapper, which
  # will try to run the command 10 times if it fails.
  command = gsutil + ['mv', source, dest]
  status = chromium_utils.RunCommand(command)

  if status:
    return status

  if gs_acl:
    command = gsutil + ['setacl', gs_acl, dest]
    status = chromium_utils.RunCommand(command)

  return status


def GSUtilDeleteFile(filename):
  """Delete a file on Google Storage."""

  # Run the gsutil command. gsutil internally calls command_wrapper, which
  # will try to run the command 10 times if it fails.
  command = GSUtilSetup()
  command.extend(['rm', filename])
  return chromium_utils.RunCommand(command)


# Python doesn't support the type of variable scope in nested methods needed
# to avoid the global output variable.  This variable should only ever be used
# by GSUtilListBucket.
command_output = ''


def GSUtilListBucket(gs_base, args):
  """List the contents of a Google Storage bucket."""

  gsutil = GSUtilSetup()

  # Run the gsutil command. gsutil internally calls command_wrapper, which
  # will try to run the command 10 times if it fails.
  global command_output
  command_output = ''

  def GatherOutput(line):
    global command_output
    command_output += line + '\n'
  command = gsutil + ['ls'] + args + [gs_base]
  status = chromium_utils.RunCommand(command, parser_func=GatherOutput)
  return (status, command_output)


def LogAndRemoveFiles(temp_dir, regex_pattern):
  """Removes files in |temp_dir| that match |regex_pattern|.
  This function prints out the name of each directory or filename before
  it deletes the file from disk."""
  regex = re.compile(regex_pattern)
  if not os.path.isdir(temp_dir):
    return
  for dir_item in os.listdir(temp_dir):
    if regex.search(dir_item):
      full_path = os.path.join(temp_dir, dir_item)
      print 'Removing leaked temp item: %s' % full_path
      try:
        if os.path.islink(full_path) or os.path.isfile(full_path):
          os.remove(full_path)
        elif os.path.isdir(full_path):
          chromium_utils.RemoveDirectory(full_path)
        else:
          print 'Temp item wasn\'t a file or directory?'
      except OSError, e:
        print >> sys.stderr, e
        # Don't fail.


def RemoveOldSnapshots(desktop):
  """Removes ChromiumSnapshot files more than one day old. Such snapshots are
  created when certain tests timeout (e.g., Chrome Frame integration tests)."""
  # Compute the file prefix of a snapshot created one day ago.
  yesterday = datetime.datetime.now() - datetime.timedelta(1)
  old_snapshot = yesterday.strftime('ChromiumSnapshot%Y%m%d%H%M%S')
  # Collect snapshots at least as old as that one created a day ago.
  to_delete = []
  for snapshot in glob.iglob(os.path.join(desktop, 'ChromiumSnapshot*.png')):
    if os.path.basename(snapshot) < old_snapshot:
      to_delete.append(snapshot)
  # Delete the collected snapshots.
  for snapshot in to_delete:
    print 'Removing old snapshot: %s' % snapshot
    try:
      os.remove(snapshot)
    except OSError, e:
      print >> sys.stderr, e


def RemoveChromeDesktopFiles():
  """Removes Chrome files (i.e. shortcuts) from the desktop of the current user.
  This does nothing if called on a non-Windows platform."""
  if chromium_utils.IsWindows():
    desktop_path = os.environ['USERPROFILE']
    desktop_path = os.path.join(desktop_path, 'Desktop')
    LogAndRemoveFiles(desktop_path, r'^(Chromium|chrome) \(.+\)?\.lnk$')
    RemoveOldSnapshots(desktop_path)


def RemoveJumpListFiles():
  """Removes the files storing jump list history.
  This does nothing if called on a non-Windows platform."""
  if chromium_utils.IsWindows():
    custom_destination_path = os.path.join(os.environ['USERPROFILE'],
                                           'AppData',
                                           'Roaming',
                                           'Microsoft',
                                           'Windows',
                                           'Recent',
                                           'CustomDestinations')
    LogAndRemoveFiles(custom_destination_path, '.+')


def RemoveTempDirContents():
  """Obliterate the entire contents of the temporary directory, excluding
  paths in sys.argv.
  """
  temp_dir = os.path.abspath(tempfile.gettempdir())
  print 'Removing contents of %s' % temp_dir

  print '  Inspecting args for files to skip'
  whitelist = set()
  whitelist_parents = set()
  for i in sys.argv:
    try:
      if '=' in i:
        i = i.split('=')[1]
      low = os.path.abspath(i.lower())
      whitelist.add(low)
      while low.startswith(temp_dir.lower()):
        whitelist_parents.add(low)
        low = os.path.dirname(low)
    except TypeError:
      # If the argument is too long, windows will freak out and pop a TypeError.
      pass
  if whitelist:
    print '  Whitelisting:'
    for w in whitelist:
      print '    %r' % w

  start_time = time.time()
  for root, dirs, files in os.walk(temp_dir):
    for f in files:
      p = os.path.join(root, f)
      if p.lower() not in whitelist:
        try:
          os.remove(p)
        except OSError:
          pass
      else:
        print '  Keeping file %r (whitelisted)' % p
    for d in dirs[:]:
      p = os.path.join(root, d)
      if p.lower() in whitelist:
        print '  Keeping dir %r (whitelisted)' % p
        # This dir was whitelisted, so we shouldn't recurse into it.
        dirs.remove(d)
      elif p.lower() in whitelist_parents:
        print '  Keeping dir %r (parent of a whitelisted dir/file)' % p
      else:
        try:
          # TODO(iannucci): Make this deal with whitelisted items which are
          # inside of |d|

          # chromium_utils.RemoveDirectory gives access denied error when called
          # in this loop.
          shutil.rmtree(p, ignore_errors=True)
          # Remove it so that os.walk() doesn't try to recurse into
          # a non-existing directory.
          dirs.remove(d)
        except OSError:
          pass
  print '   Removing temp contents took %.1f s' % (time.time() - start_time)


def RemoveChromeTemporaryFiles():
  """A large hammer to nuke what could be leaked files from unittests or
  files left from a unittest that crashed, was killed, etc."""
  # NOTE: print out what is cleaned up so the bots don't timeout if
  # there is a lot to cleanup and also se we see the leaks in the
  # build logs.
  # At some point a leading dot got added, support with and without it.
  kLogRegex = r'^\.?(com\.google\.Chrome|org\.chromium)\.'
  if chromium_utils.IsWindows():
    RemoveTempDirContents()
    RemoveChromeDesktopFiles()
    RemoveJumpListFiles()
  elif chromium_utils.IsLinux():
    LogAndRemoveFiles(tempfile.gettempdir(), kLogRegex)
    LogAndRemoveFiles('/dev/shm', kLogRegex)
  elif chromium_utils.IsMac():
    nstempdir_path = '/usr/local/libexec/nstempdir'
    if os.path.exists(nstempdir_path):
      ns_temp_dir = chromium_utils.GetCommandOutput([nstempdir_path]).strip()
      if ns_temp_dir:
        LogAndRemoveFiles(ns_temp_dir, kLogRegex)
    for i in ('Chromium', 'Google Chrome'):
      # Remove dumps.
      crash_path = '%s/Library/Application Support/%s/Crash Reports' % (
          os.environ['HOME'], i)
      LogAndRemoveFiles(crash_path, r'^.+\.dmp$')
  else:
    raise NotImplementedError(
        'Platform "%s" is not currently supported.' % sys.platform)


def WriteLogLines(logname, lines, perf=None):
  logname = logname.rstrip()
  lines = [line.rstrip() for line in lines]
  for line in lines:
    print '@@@STEP_LOG_LINE@%s@%s@@@' % (logname, line)
  if perf:
    perf = perf.rstrip()
    print '@@@STEP_LOG_END_PERF@%s@%s@@@' % (logname, perf)
  else:
    print '@@@STEP_LOG_END@%s@@@' % logname


def ZipAndUpload(bucket, archive, *targets):
  """Uploads a zipped archive to the specified Google Storage bucket.

  Args:
    bucket: Google Storage bucket to upload to.
    archive: Name of the .zip archive.
    *targets: List of targets that should be included in the archive.

  Returns:
    Path to the uploaded archive on Google Storage.
  """
  local_archive = os.path.join(tempfile.mkdtemp(archive), archive)
  zip_cmd = [
    'zip',
    '-9',
    '--filesync',
    '--recurse-paths',
    '--symlinks',
    local_archive,
  ]
  zip_cmd.extend(targets)

  chromium_utils.RunCommand(zip_cmd)
  GSUtilCopy(local_archive, 'gs://%s/%s' % (bucket, archive))
  return 'https://storage.cloud.google.com/%s/%s' % (bucket, archive)


def GetPerfDashboardRevisions(
    build_properties, main_revision, point_id=None):
  """Fills in the same revisions fields that process_log_utils does."""
  return GetPerfDashboardRevisionsWithProperties(
    build_properties.get('got_webrtc_revision'),
    build_properties.get('got_v8_revision'),
    build_properties.get('version'),
    build_properties.get('git_revision'),
    main_revision, point_id)


def GetPerfDashboardRevisionsWithProperties(
    got_webrtc_revision, got_v8_revision, version, git_revision, main_revision,
    point_id=None):
  """Fills in the same revisions fields that process_log_utils does."""

  versions = {}
  versions['rev'] = main_revision
  versions['webrtc_git'] = got_webrtc_revision
  versions['v8_rev'] = got_v8_revision
  versions['ver'] = version
  versions['git_revision'] = git_revision
  versions['point_id'] = point_id
  # There are a lot of "bad" revisions to check for, so clean them all up here.
  for key in versions.keys():
    if not versions[key] or versions[key] == 'undefined':
      del versions[key]
  return versions


def GetMainRevision(build_properties, build_dir, revision=None):
  """Return revision to use as the numerical x-value in the perf dashboard.

  This will be used as the value of "rev" in the data passed to
  results_dashboard.SendResults.

  In order or priority, this function could return:
    1. The value of the --revision flag (IF it can be parsed as an int).
    2. The value of "got_[src_]revision_cp" in build properties.
  """
  if revision and revision.isdigit():
    return revision
  commit_pos_num = _GetCommitPos(build_properties)
  if commit_pos_num is not None:
    return commit_pos_num

  raise NoCommitPosition(
    'No valid revision supplied, and the build has no commit position.\n'
    'revision: %s\n' % revision)


def GetRevision(in_directory):
  """Returns the SVN revision, git commit position, or git hash.

  Args:
    in_directory: A directory in the repository to be checked.

  Returns:
    An SVN revision as a string if the given directory is in a SVN repository,
    or a git commit position number, or if that's not available, a git hash.
    If all of that fails, an empty string is returned.
  """
  import xml.dom.minidom
  if not os.path.exists(os.path.join(in_directory, '.svn')):
    if _IsGitDirectory(in_directory):
      svn_rev = _GetGitCommitPosition(in_directory)
      if svn_rev:
        return svn_rev
      return _GetGitRevision(in_directory)
    else:
      return ''

  # Note: Not thread safe: http://bugs.python.org/issue2320
  output = subprocess.Popen(['svn', 'info', '--xml'],
                            cwd=in_directory,
                            shell=(sys.platform == 'win32'),
                            stdout=subprocess.PIPE).communicate()[0]
  try:
    dom = xml.dom.minidom.parseString(output)
    return dom.getElementsByTagName('entry')[0].getAttribute('revision')
  except xml.parsers.expat.ExpatError:
    return ''
  return ''


def _GetCommitPos(build_properties):
  """Extracts the commit position from the build properties, if its there."""
  if 'got_revision_cp' in build_properties:
    commit_pos = build_properties['got_revision_cp']
  elif 'got_src_revision_cp' in build_properties:
    commit_pos = build_properties['got_src_revision_cp']
  else:
    return None
  match = re.search(r'{#(\d+)}', commit_pos)
  if not match:
    return None
  return int(match.group(1))


def _GetGitCommitPositionFromLog(log):
  """Returns either the commit position or svn rev from a git log."""
  # Parse from the bottom up, in case the commit message embeds the message
  # from a different commit (e.g., for a revert).
  for r in [GIT_CR_POS_RE, GIT_SVN_ID_RE]:
    for line in reversed(log.splitlines()):
      m = r.match(line.strip())
      if m:
        return m.group(1)
  return None


def _GetGitCommitPosition(dir_path):
  """Extracts the commit position or svn revision number of the HEAD commit."""
  git_exe = 'git.bat' if sys.platform.startswith('win') else 'git'
  p = subprocess.Popen(
      [git_exe, 'log', '-n', '1', '--pretty=format:%B', 'HEAD'],
      cwd=dir_path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  (log, _) = p.communicate()
  if p.returncode != 0:
    return None
  return _GetGitCommitPositionFromLog(log)


def _GetGitRevision(in_directory):
  """Returns the git hash tag for the given directory.

  Args:
    in_directory: The directory where git is to be run.

  Returns:
    The git SHA1 hash string.
  """
  git_exe = 'git.bat' if sys.platform.startswith('win') else 'git'
  p = subprocess.Popen(
      [git_exe, 'rev-parse', 'HEAD'],
      cwd=in_directory, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  (stdout, _) = p.communicate()
  return stdout.strip()


def _IsGitDirectory(dir_path):
  """Checks whether the given directory is in a git repository.

  Args:
    dir_path: The directory path to be tested.

  Returns:
    True if given directory is in a git repository, False otherwise.
  """
  git_exe = 'git.bat' if sys.platform.startswith('win') else 'git'
  with open(os.devnull, 'w') as devnull:
    p = subprocess.Popen([git_exe, 'rev-parse', '--git-dir'],
                         cwd=dir_path, stdout=devnull, stderr=devnull)
    return p.wait() == 0


def AddArgs(parser):
  """Adds slave_utils common arguments to the supplied argparse parser.

  Args:
      parser (argparse.ArgumentParser): The argument parser to augment.

  Returns: callable(args)
      A callback function that should be invoked with the parsed args. This
      completes the processing and loads the result of the parsing into
      slave_utils.
  """
  group = parser.add_argument_group(title='Common `slave_utils.py` Options')
  group.add_argument('--slave-utils-gsutil-py-path', metavar='PATH',
      help='The path to the `gsutil.py` command to use for Google Storage '
           'operations. This file lives in the <depot_tools> repository.')

  return _AddArgsCallback


def AddOpts(parser):
  """Adds slave_utils common arguments to the supplied optparse parser.

  Args:
      parser (optparse.OptionParser): The argument parser to augment.

  Returns: callable(opts)
      A callback function that should be invoked with the parsed opts. This
      completes the processing and loads the result of the parsing into
      slave_utils.
  """
  group = optparse.OptionGroup(parser, 'Common `slave_utils.py` Options')
  group.add_option('--slave-utils-gsutil-py-path', metavar='PATH',
      help='The path to the `gsutil` command to use for Google Storage '
           'operations. This file lives in the <depot_tools> repository.')
  parser.add_option_group(group)

  return _AddArgsCallback


def _AddArgsCallback(opts):
  """
  Internal callback supplied by AddArgs and AddOpts. Designed to work with
  both argparse and optparse results.
  """
  global _ARGS_GSUTIL_PY_PATH
  _ARGS_GSUTIL_PY_PATH = opts.slave_utils_gsutil_py_path


def GetPassthroughArgs(opts):
  """Returns (list): A list of slave_utils arguments that can be forwarded to
      other slave_utils-args-aware scrpts.

  Args:
      opts: Either the parsed argparse results or the optparse options
          component. The respective parser must have had args/opts added via
          AddArgs/AddOpts.
  """
  args = []
  if opts.slave_utils_gsutil_py_path:
    args += ['--slave-utils-gsutil-py-path', opts.slave_utils_gsutil_py_path]
  return args
