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
                                slave='unknown', clobber=''):
  """Upload compiler_proxy{,-subproc}.INFO and gomacc.INFO to Google Storage.

  Args:
    override_gsutil: gsutil path to override.
    builder: a string name of a builder.
    master: a string name of a master.
    slave: a string name of a slave.
    clobber: set something if clobber (to be removed)
  """
  latest_subproc_info = GetLatestGomaCompilerProxySubprocInfo()

  builderinfo = {
    'builder': builder,
    'master': master,
    'slave': slave,
    'clobber': True if clobber else False,
    'os': chromium_utils.PlatformName(),
  }
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
  viewer_url = ('http://chromium-build-stats.appspot.com/compiler_proxy_log/'
                + log_path)
  print 'Visualization at %s' % viewer_url

  gomacc_logs = GetListOfGomaccInfoAfterCompilerProxyStart()
  if gomacc_logs:
    for log in gomacc_logs:
      UploadToGomaLogGS(
          log, os.path.basename(log),
          metadata=metadata,
          override_gsutil=override_gsutil)

  return viewer_url

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
  viewer_url = 'http://chromium-build-stats.appspot.com/ninja_log/' + log_path
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
                              slave='unknown', clobber=''):
  """Make Goma exit status counter. This counter indicates compiler_proxy
     has finished without problem, crashed, or killed. This counter will
     be used to alert to goma team.

  Args:
    goma_stats_file: path to goma stats file if any
    goma_crash_report: path to goma crash report file if any
    builder: builder name
    master: master name
    slave: slave name
    clobber: non false if clobber build
  """

  try:
    counter = {
        'name': 'goma/status',
        'value': 1,
        'builder': builder,
        'master': master,
        'slave': slave,
        'clobber': 1 if clobber else 0,
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


def SendGomaStats(goma_stats_file, goma_crash_report, build_data_dir):
  """Send GomaStats monitoring event.

  Note: this function also removes goma_stats_file.
  """
  try:
    goma_options = []
    if goma_stats_file and os.path.exists(goma_stats_file):
      # send GomaStats.
      goma_options = [
          '--build-event-goma-stats-path',
          goma_stats_file,
      ]
    elif goma_crash_report and os.path.exists(goma_crash_report):
      # crash report.
      goma_options = [
          '--build-event-goma-error',
          'GOMA_ERROR_CRASHED',
          '--build-event-goma-crash-report-id-path',
          goma_crash_report,
      ]
    elif IsCompilerProxyKilledByFatalError():
      goma_options = [
          '--build-event-goma-error',
          'GOMA_ERROR_LOG_FATAL',
      ]
    else:
      # unknown error.
      goma_options = [
          '--build-event-goma-error',
          'GOMA_ERROR_UNKNOWN',
      ]
    run_cmd = PLATFORM_RUN_CMD.get(os.name)
    if not run_cmd:
      print 'Unknown os.name: %s' % os.name
      return
    send_monitoring_event_cmd = [
        sys.executable,
        run_cmd,
        'infra.tools.send_monitoring_event',
        '--event-mon-run-type', 'prod',
        '--build-event-type', 'BUILD',
        '--event-mon-timestamp-kind', 'POINT',
        '--event-logrequest-path',
        os.path.join(build_data_dir, 'log_request_proto')
    ] + goma_options
    cmd_filter = chromium_utils.FilterCapture()
    retcode = chromium_utils.RunCommand(
      send_monitoring_event_cmd,
      filter_obj=cmd_filter,
      max_time=30)
    if retcode:
      print('Execution of send_monitoring_event failed with code %s'
            % retcode)
      print '\n'.join(cmd_filter.text)
  except Exception, inst:  # safety net
    print('send_monitoring_event for goma failed: %s' % inst)
  finally:
    try:
      os.remove(goma_stats_file)
    except OSError:  # file does not exist, for ex.
      pass


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
                          builder='unknown', master='unknown', slave='unknown',
                          clobber=''):
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
        'clobber': 1 if clobber else 0,
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


def DetermineGomaJobs():
  # We would like to speed up build on Windows a bit, since it is slowest.
  number_of_processors = 0
  try:
    number_of_processors = multiprocessing.cpu_count()
  except NotImplementedError:
    print 'cpu_count() is not implemented, using default value 50.'
    return 50

  assert number_of_processors > 0

  # When goma is used, 10 * number_of_processors is basically good in
  # various situations according to our measurement. Build speed won't
  # be improved if -j is larger than that.
  #
  # Since Mac had process number limitation before, we had to set
  # the upper limit to 50. Now that the process number limitation is 2000,
  # so we would be able to use 10 * number_of_processors.
  # For safety, we'd like to set the upper limit to 200.
  #
  # Note that currently most try-bot build slaves have 8 processors.
  if chromium_utils.IsMac() or chromium_utils.IsWindows():
    return min(10 * number_of_processors, 200)

  # For Linux, we also would like to use 10 * cpu. However, not sure
  # backend resource is enough, so let me set Linux and Linux x64 builder
  # only for now.
  hostname = GetShortHostname()
  if hostname in (
      ['build14-m1', 'build48-m1'] +
      # Also increasing cpus for v8/blink trybots.
      ['build%d-m4' % x for x in xrange(45, 48)] +
      # Also increasing cpus for LTO buildbots.
      ['slave%d-c1' % x for x in [20, 33] + range(78, 108)] +
      # Also increasing cpus for Findit trybots.
      ['slave%d-c4' % x for x in [799] + range(873, 878)]):
    return min(10 * number_of_processors, 200)

  return 50


def StopGomaClientAndUploadInfo(options, env, exit_status):
  """Stop goma compiler_proxy and upload goma-related information.

  Args:
    options (Option) : options to specify where to store goma-related info.
    env (dict)       : used when goma_ctl command executes.
    exit_status (int): exit_status sent to monitoring system.
  """
  goma_ctl_cmd = [sys.executable,
                  os.path.join(options.goma_dir, 'goma_ctl.py')]

  tsmon_counters = []
  if options.goma_jsonstatus:
    chromium_utils.RunCommand(
        goma_ctl_cmd + ['jsonstatus', options.goma_jsonstatus], env=env)
    counter = MakeGomaStatusCounter(
        options.goma_jsonstatus,
        exit_status,
        builder=options.buildbot_buildername,
        master=options.buildbot_mastername,
        slave=options.buildbot_slavename,
        clobber=options.buildbot_clobber)
    if counter:
      tsmon_counters.append(counter)

  # If goma compiler_proxy crashes, there could be crash dump.
  if options.build_data_dir:
    env['GOMACTL_CRASH_REPORT_ID_FILE'] = os.path.join(options.build_data_dir,
                                                       'crash_report_id_file')
  # We must stop the proxy to dump GomaStats.
  chromium_utils.RunCommand(goma_ctl_cmd + ['stop'], env=env)
  override_gsutil = None
  if options.gsutil_py_path:
    # Needs to add '--', otherwise gsutil options will be passed to gsutil.py.
    override_gsutil = [sys.executable, options.gsutil_py_path, '--']
  UploadGomaCompilerProxyInfo(override_gsutil=override_gsutil,
                              builder=options.buildbot_buildername,
                              master=options.buildbot_mastername,
                              slave=options.buildbot_slavename,
                              clobber=options.buildbot_clobber)

  # Upload GomaStats to make it monitored.
  if env.get('GOMA_DUMP_STATS_FILE'):
    # MakeGomaExitStatusCounter should be callbed before SendGomaStats,
    # since SendGomaStats removes stats file.
    counter = MakeGomaExitStatusCounter(
        env['GOMA_DUMP_STATS_FILE'],
        options.build_data_dir,
        builder=options.buildbot_buildername,
        master=options.buildbot_mastername,
        slave=options.buildbot_slavename,
        clobber=options.buildbot_clobber)
    if counter:
      tsmon_counters.append(counter)
    SendGomaStats(env['GOMA_DUMP_STATS_FILE'],
                  env.get('GOMACTL_CRASH_REPORT_ID_FILE'),
                  options.build_data_dir)

  if tsmon_counters:
    SendCountersToTsMon(tsmon_counters)


def Setup(options, env):
  """Sets up goma if necessary.

  If using the Goma compiler, first call goma_ctl to ensure the proxy is
  available, and returns (True, instance of cloudtail subprocess).
  If it failed to start up compiler_proxy, modify options.compiler
  and options.goma_dir, modify env to GOMA_DISABLED=true,
  and returns (False, None).
  """
  cloudtail_pid_file = options.cloudtail_pid_file

  if cloudtail_pid_file and os.path.exists(cloudtail_pid_file):
    os.remove(cloudtail_pid_file)

  if options.compiler not in ('goma', 'goma-clang'):
    # Unset goma_dir to make sure we'll not use goma.
    options.goma_dir = None
    return False, None

  if options.goma_fail_fast:
    # startup fails when initial ping failed.
    env['GOMA_FAIL_FAST'] = 'true'
  else:
    # If a network error continues 30 minutes, compiler_proxy make the compile
    # failed.  When people use goma, they expect using goma is faster than
    # compile locally. If goma cannot guarantee that, let it make compile
    # as error.
    env['GOMA_ALLOWED_NETWORK_ERROR_DURATION'] = '1800'

  if options.goma_max_active_fail_fallback_tasks:
    env['GOMA_MAX_ACTIVE_FAIL_FALLBACK_TASKS'] = (
        options.goma_max_active_fail_fallback_tasks)

  # Caches CRLs in GOMA_CACHE_DIR.
  # Since downloading CRLs is usually slow, caching them may improves
  # compiler_proxy start time.
  if not os.path.exists(options.goma_cache_dir):
    os.mkdir(options.goma_cache_dir, 0700)
  env['GOMA_CACHE_DIR'] = options.goma_cache_dir

  # Enable DepsCache. DepsCache caches the list of files to send goma server.
  # This will greatly improve build speed when cache is warmed.
  if options.goma_deps_cache_file:
    env['GOMA_DEPS_CACHE_FILE'] = options.goma_deps_cache_file
  else:
    # TODO(shinyak): GOMA_DEPS_CACHE_DIR will be removed from goma in future.
    # GOMA_DEPS_CACHE_FILE should be used.
    env['GOMA_DEPS_CACHE_DIR'] = (
      options.goma_deps_cache_dir or options.target_output_dir)

  if options.goma_hermetic:
    env['GOMA_HERMETIC'] = options.goma_hermetic
  if options.goma_enable_remote_link:
    env['GOMA_ENABLE_REMOTE_LINK'] = options.goma_enable_remote_link
  if options.goma_enable_localoutputcache:
    env['GOMA_LOCAL_OUTPUT_CACHE_DIR'] = (
        os.path.join(options.goma_cache_dir, 'localoutputcache'))
  if options.goma_store_local_run_output:
    env['GOMA_STORE_LOCAL_RUN_OUTPUT'] = options.goma_store_local_run_output

  if options.build_data_dir:
    env['GOMA_DUMP_STATS_FILE'] = os.path.join(options.build_data_dir,
                                               'goma_stats_proto')

  if options.goma_service_account_json_file:
    env['GOMA_SERVICE_ACCOUNT_JSON_FILE'] = \
        options.goma_service_account_json_file
  goma_start_command = ['restart']
  goma_ctl_cmd = [sys.executable,
                  os.path.join(options.goma_dir, 'goma_ctl.py')]
  result = chromium_utils.RunCommand(goma_ctl_cmd + goma_start_command, env=env)
  if not result:
    # goma started sucessfully.
    # Making cloudtail to upload the latest log.

    cloudtail_path = '/opt/infra-tools/cloudtail'
    if chromium_utils.IsWindows():
      cloudtail_path = 'C:\\infra-tools\\cloudtail'

    try:

      cloudtail_proc = subprocess.Popen(
          [cloudtail_path, 'tail', '--project-id', 'goma-logs',
           '--service-account-json', options.cloudtail_service_account_json,
           '--log-id', 'goma_compiler_proxy', '--path',
           '--buffering-time', '60',
           GetLatestGomaCompilerProxyInfo()])

      if cloudtail_pid_file:
        with open(cloudtail_pid_file,'w') as f:
          f.write('%d' % cloudtail_proc.pid)
    except Exception as e:
      print 'failed to invoke cloudtail: %s' % e
      return True, None
    return True, cloudtail_proc

  StopGomaClientAndUploadInfo(options, env, -1)

  if options.goma_disable_local_fallback:
    print 'error: failed to start goma; fallback has been disabled'
    raise Exception('failed to start goma')

  print 'warning: failed to start goma. falling back to non-goma'
  # Drop goma from options.compiler
  options.compiler = options.compiler.replace('goma-', '')
  if options.compiler == 'goma':
    options.compiler = None
  # Reset options.goma_dir.
  options.goma_dir = None
  env['GOMA_DISABLED'] = '1'
  return False, None


def Teardown(options, env, exit_status, cloudtail_proc):
  """Tears down goma if necessary. """
  cloudtail_pid_file = options.cloudtail_pid_file

  if options.goma_dir:
    StopGomaClientAndUploadInfo(options, env, exit_status)

  if cloudtail_proc:
    cloudtail_proc.terminate()
    cloudtail_proc.wait()
  elif cloudtail_pid_file:
    with open(cloudtail_pid_file) as f:
      pid = int(f.read())
      os.kill(pid, signal.SIGTERM)
    os.remove(cloudtail_pid_file)
