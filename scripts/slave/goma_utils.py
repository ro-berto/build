# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions specific to handle goma related info.
"""

import base64
import datetime
import getpass
import glob
import gzip
import json
import multiprocessing
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import time

from common import chromium_utils
from slave import slave_utils

# The Google Cloud Storage bucket to store logs related to goma.
GOMA_LOG_GS_BUCKET = 'chrome-goma-log'

# Platform dependent location of run command.
PLATFORM_RUN_CMD = {
    # os.name: run_cmd to use.
    'nt': 'C:\\infra-python\\run.py',
    'posix': '/opt/infra-python/run.py',
}

TIMESTAMP_PATTERN = re.compile('(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})')
TIMESTAMP_FORMAT = '%Y/%m/%d %H:%M:%S'


def GetShortHostname():
  """Get this machine's short hostname in lower case."""
  return socket.gethostname().split('.')[0].lower()


def GetGomaLogDirectory():
  """Get goma's log directory.

  Returns:
    a string of a directory name where goma's log may exist.

  Raises:
    chromium_utils.PathNotFound if it cannot find an available log directory.
  """
  candidates = ['GLOG_log_dir', 'GOOGLE_LOG_DIR', 'TEST_TMPDIR']
  default_dir = None
  if chromium_utils.IsWindows():
    candidates.extend(['TMP', 'TEMP', 'USERPROFILE'])
    # Note: I believe one of environment variables is set for usual Windows
    # environment, let me avoid to check the Windows directory, which we
    # need to use win32api on Python.
  else:
    candidates.extend(['TMPDIR', 'TMP'])
    default_dir = '/tmp'

  for candidate in candidates:
    value = os.environ.get(candidate)
    if value and os.path.isdir(value):
      return value
  if default_dir:
    return default_dir
  raise chromium_utils.PathNotFound('Cannot find Goma log directory.')


def GetLatestGlogInfoFile(pattern):
  """Get a filename of the latest google glog INFO file.

  Args:
    pattern: a string of INFO file pattern.

  Returns:
    the latest glog INFO filename in fullpath.  Or, None if not found.
  """
  dirname = GetGomaLogDirectory()
  info_pattern = os.path.join(dirname, '%s.*.INFO.*' % pattern)
  candidates = glob.glob(info_pattern)
  if not candidates:
    return None
  return sorted(candidates, reverse=True)[0]


def GetLatestGomaCompilerProxyInfo():
  """Get a filename of the latest goma comiler_proxy.INFO."""
  return GetLatestGlogInfoFile('compiler_proxy')


def GetLatestGomaCompilerProxySubprocInfo():
  """Get a filename of the latest goma comiler_proxy-subproc.INFO."""
  return GetLatestGlogInfoFile('compiler_proxy-subproc')


def GetListOfGomaccInfoAfterCompilerProxyStart():
  """Returns list of gomacc.INFO generated after compiler_proxy starts.

  Returns:
    list of gomacc.INFO file path strings.
  """
  compiler_proxy_start_time = GetCompilerProxyStartTime()
  recent_gomacc_infos = []
  logs = glob.glob(os.path.join(GetGomaLogDirectory(), 'gomacc.*.INFO.*'))
  for log in logs:
    timestamp = GetLogFileTimestamp(log)
    if timestamp and timestamp > compiler_proxy_start_time:
      recent_gomacc_infos.append(log)
  return recent_gomacc_infos


def UploadToGomaLogGS(file_path, gs_filename,
                      text_to_append=None,
                      metadata=None,
                      override_gsutil=None):
  """Upload a file to Google Cloud Storage (gs://chrome-goma-log).

  Note that the uploaded file would automatically be gzip compressed.

  Args:
    file_path: a path of a file to be uploaded.
    gs_filename: a name of a file in Google Storage.
    metadata: (dict) A dictionary of string key/value metadata entries.
    text_to_append: an addtional text to be added to a file in GS.

  Returns:
    a stored path name without the bucket name in GS.
  """
  hostname = GetShortHostname()
  today = datetime.datetime.utcnow().date()
  log_path = '%s/%s/%s.gz' % (
    today.strftime('%Y/%m/%d'), hostname, gs_filename)
  gs_path = 'gs://%s/%s' % (GOMA_LOG_GS_BUCKET, log_path)
  temp = tempfile.NamedTemporaryFile(delete=False)
  try:
    with temp as f_out:
      with gzip.GzipFile(fileobj=f_out) as gzipf_out:
        with open(file_path) as f_in:
          shutil.copyfileobj(f_in, gzipf_out)
        if text_to_append:
          gzipf_out.write(text_to_append)
    slave_utils.GSUtilCopy(temp.name, gs_path,
                           metadata=metadata, override_gsutil=override_gsutil)
    print "Copied log file to %s" % gs_path
  finally:
    os.remove(temp.name)
  return log_path


def UploadGomaCompilerProxyInfo(override_gsutil=None,
                                builder='unknown', master='unknown',
                                slave='unknown',
                                builder_id=None, is_luci=False,
                                is_experimental=False):
  """Upload compiler_proxy{,-subproc}.INFO and gomacc.INFO to Google Storage.

  Args:
    override_gsutil: gsutil path to override.
    builder: a string name of a builder.
    master: a string name of a master.
    slave: a string name of a slave.
    builder_id: a dictionary that represents BuilderID.
    is_luci: True if this is LUCI.
    is_experimental: True if this is experimental build.
  """
  latest_subproc_info = GetLatestGomaCompilerProxySubprocInfo()

  builderinfo = {
    'builder': builder,
    'master': master,
    'slave': slave,
    'os': chromium_utils.PlatformName(),
    'is_luci': is_luci,
    'is_experimental': is_experimental,
  }
  if builder_id:
    builderinfo['builder_id'] = builder_id

  # Needs to begin with x-goog-meta for custom metadata.
  # https://cloud.google.com/storage/docs/gsutil/addlhelp/WorkingWithObjectMetadata#custom-metadata
  metadata = {
    'x-goog-meta-builderinfo': json.dumps(builderinfo)
  }

  if latest_subproc_info:
    UploadToGomaLogGS(latest_subproc_info,
                      os.path.basename(latest_subproc_info),
                      metadata=metadata,
                      override_gsutil=override_gsutil)
  else:
    print 'No compiler_proxy-subproc.INFO to upload'
  latest_info = GetLatestGomaCompilerProxyInfo()
  if not latest_info:
    print 'No compiler_proxy.INFO to upload'
    return
  # Since a filename of compiler_proxy.INFO is fairly unique,
  # we might be able to upload it as-is.
  log_path = UploadToGomaLogGS(
      latest_info, os.path.basename(latest_info),
      metadata=metadata,
      override_gsutil=override_gsutil)
  viewer_url = ('https://chromium-build-stats.appspot.com/compiler_proxy_log/'
                + log_path)
  print 'Visualization at %s' % viewer_url

  gomacc_logs = GetListOfGomaccInfoAfterCompilerProxyStart()
  if gomacc_logs:
    UploadGomaccInfo(gomacc_logs,
                     metadata=metadata,
                     override_gsutil=override_gsutil)
  return viewer_url


def UploadGomaccInfo(gomacc_logs,
                     metadata=None,
                     override_gsutil=None):
  """Upload gomacc logs if any

  Args:
    gomacc_logs: An array that contains paths to gomacc logs
    override_gsutil: gsutil path to override
    metadata: metadata which will be attached as gs metadata
  """

  temp_file = tempfile.NamedTemporaryFile(delete=False)
  try:
    with tarfile.TarFile(fileobj=temp_file, mode='w') as tf:
      for log in gomacc_logs:
        tf.add(log, arcname=os.path.basename(log))

    # Taking the first name as gomacc log filename on gs.
    gs_tarfile_name = os.path.basename(gomacc_logs[0]) + '.tar'

    # Since UploadToGomaLogGS opens temp_file.name, we have to
    # close the file here. Otherwise this will fail on Win.
    temp_file.close()

    UploadToGomaLogGS(temp_file.name, gs_tarfile_name,
                      metadata=metadata,
                      override_gsutil=override_gsutil)
  finally:
    if not temp_file.closed:
      temp_file.close()
    os.remove(temp_file.name)

def UploadNinjaLog(
    outdir, compiler, command, exit_status, override_gsutil=None):
  """Upload .ninja_log to Google Cloud Storage (gs://chrome-goma-log),
  in the same folder with goma's compiler_proxy.INFO.

  Args:
    outdir: a directory that contains .ninja_log.
    compiler: compiler used for the build.
    command: command line.
    exit_status: ninja's exit status.
  """
  ninja_log_path = os.path.join(outdir, '.ninja_log')
  try:
    st = os.stat(ninja_log_path)
    mtime = datetime.datetime.fromtimestamp(st.st_mtime)
  except OSError, e:
    print e
    return

  cwd = os.getcwd()
  platform = chromium_utils.PlatformName()

  # info['cmdline'] should be list of string for
  # go struct on chromium-build-stats.
  if isinstance(command, str) or isinstance(command, unicode):
    command = [command]

  info = {'cmdline': command,
          'cwd': cwd,
          'platform': platform,
          'exit': exit_status,
          'env': {}}
  for k, v in os.environ.iteritems():
    info['env'][k] = v
  if compiler:
    info['compiler'] = compiler

  # TODO(tikuta): Remove this after compile.py removed.
  if os.path.basename(sys.argv[0]) == 'compile.py':
    info['argv'] = sys.argv

  compiler_proxy_info = GetLatestGomaCompilerProxyInfo()
  if compiler_proxy_info:
    info['compiler_proxy_info'] = compiler_proxy_info

  username = getpass.getuser()
  hostname = GetShortHostname()
  pid = os.getpid()
  ninja_log_filename = 'ninja_log.%s.%s.%s.%d' % (
      hostname, username, mtime.strftime('%Y%m%d-%H%M%S'), pid)
  additional_text = '# end of ninja log\n' + json.dumps(info)
  log_path = UploadToGomaLogGS(
      ninja_log_path, ninja_log_filename, text_to_append=additional_text,
      override_gsutil=override_gsutil)
  viewer_url = 'https://chromium-build-stats.appspot.com/ninja_log/' + log_path
  print 'Visualization at %s' % viewer_url

  return viewer_url

def IsCompilerProxyKilledByFatalError():
  """Returns true if goma compiler_proxy is killed by CHECK or LOG(FATAL)."""
  info_file = GetLatestGomaCompilerProxyInfo()
  if not info_file:
    return False
  fatal_pattern = re.compile(r'^F\d{4} \d{2}:\d{2}:\d{2}\.\d{6} ')
  with open(info_file) as f:
    for line in f.readlines():
      if fatal_pattern.match(line):
        return True
  return False


def MakeGomaExitStatusCounter(goma_stats_file, goma_crash_report,
                              builder='unknown', master='unknown',
                              slave='unknown'):
  """Make Goma exit status counter. This counter indicates compiler_proxy
     has finished without problem, crashed, or killed. This counter will
     be used to alert to goma team.

  Args:
    goma_stats_file: path to goma stats file if any
    goma_crash_report: path to goma crash report file if any
    builder: builder name
    master: master name
    slave: slave name
  """

  try:
    counter = {
        'name': 'goma/status',
        'value': 1,
        'builder': builder,
        'master': master,
        'slave': slave,
        'os': chromium_utils.PlatformName(),
    }
    if goma_stats_file and os.path.exists(goma_stats_file):
      counter['status'] = 'success'
    elif goma_crash_report and os.path.exists(goma_crash_report):
      counter['status'] = 'crashed'
    elif IsCompilerProxyKilledByFatalError():
      counter['status'] = 'killed'
    else:
      counter['status'] = 'unknown'

    start_time = GetCompilerProxyStartTime()
    if start_time:
      counter['start_time'] = int(time.mktime(start_time.timetuple()))

    return counter
  except Exception as ex:
    print('error while generating status counter: %s' % ex)
    return None


def GetLogFileTimestamp(glog_log):
  """Returns timestamp when the given glog log was created.

  Args:
    glog_log: a filename of a google-glog log.

  Returns:
    datetime instance when the logfile was created.
    Or, returns None if not a glog file.

  Raises:
    IOError if this function cannot open glog_log.
  """
  with open(glog_log) as f:
    matched = TIMESTAMP_PATTERN.search(f.readline())
    if matched:
      return datetime.datetime.strptime(matched.group(1), TIMESTAMP_FORMAT)
  return None


def GetCompilerProxyStartTime():
  """Returns timestamp when the latest compiler_proxy started.

  Returns:
    datetime instance of timestamp when the latest compiler_proxy start.
    Or, returns None if not a glog file.
  """
  return GetLogFileTimestamp(GetLatestGomaCompilerProxyInfo())


def SendCountersToTsMon(counters):
  """Send goma status counter to ts_mon.

  Args:
    counters: a list of data which is sent to ts_mon.
  """

  if not counters:
    print('No counter to send to ts_mon is specified')
    return

  try:
    run_cmd = PLATFORM_RUN_CMD.get(os.name)
    if not run_cmd:
      print 'Unknown os.name: %s' % os.name
      return

    counters_json = []
    for c in counters:
      c_json = json.dumps(c)
      # base64 encode on windows because it doesn't like json
      # on the command-line.
      if os.name == 'nt':
        c_json = base64.b64encode(c_json)
      counters_json.append('--counter')
      counters_json.append(c_json)

    cmd = [sys.executable,
           run_cmd,
           'infra.tools.send_ts_mon_values', '--verbose',
           '--ts-mon-target-type', 'task',
           '--ts-mon-task-service-name', 'goma-client',
           '--ts-mon-task-job-name', 'default']
    cmd.extend(counters_json)
    cmd_filter = chromium_utils.FilterCapture()
    retcode = chromium_utils.RunCommand(cmd, filter_obj=cmd_filter,
                                        max_time=30)
    if retcode:
      print('Execution of send_ts_mon_values failed with code %s'
            % retcode)
      print '\n'.join(cmd_filter.text)
  except Exception as ex:
    print('error while sending counters to ts_mon: counter=%s: %s'
          % (counters, ex))


def MakeGomaStatusCounter(json_file, exit_status,
                          builder='unknown', master='unknown', slave='unknown'):
  """Make latest Goma status counter which will be sent to ts_mon.

  Args:
    json_file: json filename string that has goma_ctl.py jsonstatus.
    exit_status: integer exit status of the build.

  Returns:
    counter dict if succeeded. None if failed.
  """
  json_statuses = {}
  try:
    with open(json_file) as f:
      json_statuses = json.load(f)

    if not json_statuses:
      print('no json status is recorded in %s' % json_file)
      return None

    if len(json_statuses.get('notice', [])) != 1:
      print('unknown json statuses style: %s' % json_statuses)
      return None

    json_status = json_statuses['notice'][0]
    if json_status['version'] != 1:
      print('unknown version: %s' % json_status)
      return None

    infra_status = json_status.get('infra_status')

    result = 'success'

    if exit_status is None:
      result = 'exception'
    elif exit_status != 0:
      result = 'failure'
      if (exit_status < 0 or
          not infra_status or
          infra_status['ping_status_code'] != 200 or
          infra_status.get('num_user_error', 0) > 0):
        result = 'exception'

    num_failure = 0
    ping_status_code = 0
    if infra_status:
      num_failure = infra_status['num_exec_compiler_proxy_failure']
      ping_status_code = infra_status['ping_status_code']

    counter = {
        'name': 'goma/failure',
        'value': num_failure,
        'builder': builder,
        'master': master,
        'slave': slave,
        'os': chromium_utils.PlatformName(),
        'ping_status_code': ping_status_code,
        'result': result}
    start_time = GetCompilerProxyStartTime()
    if start_time:
      counter['start_time'] = int(time.mktime(start_time.timetuple()))
    return counter

  except Exception as ex:
    print('error while making goma status counter for ts_mon: jons_file=%s: %s'
          % (json_file, ex))
    return None


def MakeGomaFailureReasonCounter(json_file, exit_status,
                                 builder='unknown', master='unknown',
                                 slave='unknown'):
  """Make latest Goma failure reason counter which will be sent to ts_mon.

  Args:
    json_file: json filename string that has goma_ctl.py jsonstatus.
    exit_status: integer exit status of the build.

  Returns:
    counter dict if succeeded. None if failed.
  """
  try:
    with open(json_file) as f:
      json_statuses = json.load(f)

    if not json_statuses:
      print('no json status is recorded in %s' % json_file)
      return None

    if len(json_statuses.get('notice', [])) != 1:
      print('unknown json statuses style: %s' % json_statuses)
      return None

    json_status = json_statuses['notice'][0]
    if json_status['version'] != 1:
      print('unknown version: %s' % json_status)
      return None

    infra_status = json_status.get('infra_status')

    result = 'success'
    reason = 'OK'

    if infra_status is None:
      reason = 'GOMA_SETUP_FAILURE'
    elif infra_status.get('ping_status_code', 200) != 200:
      reason = 'GOMA_PING_FAILURE'
    elif infra_status.get('num_user_error', 0) > 0:
      reason = 'GOMA_BUILD_ERROR'

    if exit_status is None:
      if reason == 'OK':
        # Maybe some failure on goma set up?
        reason = 'EXIT_STATUS_IS_NONE'
    elif exit_status != 0:
      result = 'failure'

    if reason != 'OK':
      result = 'exception'

    counter = {
        'name': 'goma/failure_reason',
        'value': 1,
        'builder': builder,
        'master': master,
        'slave': slave,
        'os': chromium_utils.PlatformName(),
        'result': result,
        'exception_reason': reason}
    start_time = GetCompilerProxyStartTime()
    if start_time:
      counter['start_time'] = int(time.mktime(start_time.timetuple()))
    return counter

  except Exception as ex:
    print('error while making goma status counter for ts_mon: jons_file=%s: %s'
          % (json_file, ex))
    return None
