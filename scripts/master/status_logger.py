# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Log status events to a file on disk or event collection endpoint."""


import json
import logging
import os
import time

from logging.handlers import TimedRotatingFileHandler

from buildbot.status.base import StatusReceiverMultiService
from twisted.internet.utils import getProcessOutputAndValue
from twisted.python import log as twisted_log

from common import chromium_utils


class StatusEventLogger(StatusReceiverMultiService):
  """Log status events to a file on disk or event collection endpoint.

  Files on disk are rotated, while the event collection endpoint is contacted
  through a script in the infra/infra repository (separate checkout).

  A file, .logstatus, is used to configure the logger. If it exists then
  file logging is enabled. If it parses as json, the keys infra_pipeline,
  file_logging, infra_runpy, logging_ignore_basedir, logfile,
  monitoring_script and log_pipeline_calls can be used to configure the logger
  at runtime.
  """

  DEFAULT_INFRA_RUNPY = '/home/chrome-bot/infra/run.py'
  DEFAULT_MONITORING_SCRIPT = 'infra.tools.send_monitoring_event'
  DEFAULT_MONITORING_TYPE = 'dry'
  DEFAULT_LOGGING_IGNORE_BASEDIR = False
  DEFAULT_LOG_PIPELINE_CALLS = False

  def __init__(self, logfile='status.log', configfile='.logstatus',
               basedir=None):
    """Create a StatusEventLogger.

    Args:
      logfile: base filename for events to be written to.
      configfile: the name of the configuration file.
      basedir: the basedir of the configuration and log files. Set to the
               service's parent directory by default, mainly overridden for
               testing.
    """
    self._logfile = self._original_logfile = logfile
    self._configfile = configfile
    self._basedir = basedir
    self.master_dir = os.path.basename(os.path.abspath(os.curdir))

    # These are defaults which may be overridden.
    self.infra_runpy = self.DEFAULT_INFRA_RUNPY
    self.monitoring_script = self.DEFAULT_MONITORING_SCRIPT
    self.monitoring_type = self.DEFAULT_MONITORING_TYPE
    self.logging_ignore_basedir = self.DEFAULT_LOGGING_IGNORE_BASEDIR
    self.log_pipeline_calls = self.DEFAULT_LOG_PIPELINE_CALLS

    # Will be initialized in startService.
    self.logger = None
    self.status = None
    self._active = False
    self._last_checked_active = 0
    self._pipeline = False
    self._logging = False
    # Can't use super because StatusReceiverMultiService is an old-style class.
    StatusReceiverMultiService.__init__(self)

  def as_dict(self):
    return {
        'basedir': self.basedir,
        'configfile': self.configfile,
        'file_logging': self._logging,
        'infra_pipeline': self._pipeline,
        'infra_runpy': self.infra_runpy,
        'log_pipeline_calls': self.log_pipeline_calls,
        'logfile': self.logfile,
        'logging_ignore_basedir': self.logging_ignore_basedir,
        'monitoring_script': self.monitoring_script,
        'monitoring_type': self.monitoring_type,
    }

  def _configure(self, config_data):
    old_config = self.as_dict()

    self._logging = config_data.get(
        'file_logging', True)  # Preserve old behavior.
    self._pipeline = config_data.get(
        'infra_pipeline')
    self.infra_runpy = config_data.get(
        'infra_runpy', self.DEFAULT_INFRA_RUNPY)
    self._logfile = config_data.get(
        'logfile', self._original_logfile)
    self.log_pipeline_calls = config_data.get(
        'log_pipeline_calls', self.DEFAULT_LOG_PIPELINE_CALLS)
    self.logging_ignore_basedir = config_data.get(
        'logging_ignore_basedir', self.DEFAULT_LOGGING_IGNORE_BASEDIR)
    self.monitoring_script = config_data.get(
        'monitoring_script', self.DEFAULT_MONITORING_SCRIPT)
    self.monitoring_type = config_data.get(
        'monitoring_type', self.DEFAULT_MONITORING_TYPE)

    new_config = self.as_dict()
    if new_config != old_config:
      twisted_log.msg(
          'Configuration change detected. Old:\n%s\n\nNew:\n%s\n' % (
              json.dumps(old_config, sort_keys=True, indent=2),
              json.dumps(new_config, sort_keys=True, indent=2)))

  @staticmethod
  def _get_requested_at_millis(build):
    return int(build.getProperty('requestedAt') * 1000)

  @property
  def basedir(self):
    """Returns dynamic or preset basedir.

    self.parent doesn't exist until the service is running, so this has to be
    here instead of precomputing the logfile and configfile in __init__.
    """
    return self._basedir or self.parent.basedir

  def _canonical_file(self, filename, ignore_basedir=False):
    """Returns an absolute path for a config or log file."""
    if ignore_basedir:
      full_filename = filename
    else:
      full_filename = os.path.join(self.basedir, filename)
    return chromium_utils.AbsoluteCanonicalPath(full_filename)

  @property
  def configfile(self):
    return self._canonical_file(self._configfile)

  @property
  def logfile(self):
    return self._canonical_file(
        self._logfile, ignore_basedir=self.logging_ignore_basedir)

  @property
  def active(self):
    now = time.time()
    # Cache the value for self._active for one minute.
    if now - self._last_checked_active > 60:
      active_before = self._active
      self._active = os.path.isfile(self.configfile)

      if not self._active and active_before:
        twisted_log.msg('Disabling status_logger.')

      if self._active:
        # Test if it parses as json, otherwise use defaults.
        data = {}
        try:
          with open(self.configfile) as f:
            data = json.load(f)
        except ValueError as err:
          twisted_log.msg("status_logger config file parsing failed: %s\n%s"
                          % (self.configfile, err), logLevel=logging.ERROR)
        self._configure(data)

        if not active_before:
          twisted_log.msg(
              'Enabling status_logger. file_logger: %s / pipeline %s' % (
                  self._logging, self._pipeline))
      else:
        self._configure({'file_logging': False})  # Reset to defaults.

      self._last_checked_active = now
    return self._active

  def _construct_monitoring_event_args(
      self, timestamp_kind, build_event_type, bot_name,
      builder_name, build_number, build_scheduled_ts,
      step_name=None, step_number=None):
    args = [
        self.monitoring_script,
        '--event-mon-run-type=%s' % self.monitoring_type,
        '--event-mon-timestamp-kind=%s' % timestamp_kind,
        '--event-mon-service-name=buildbot/master/%s' % self.master_dir,
        '--build-event-type=%s' % build_event_type,
        '--build-event-hostname=%s' % bot_name,
        '--build-event-build-name=%s' % builder_name,
        '--build-event-build-number=%d' % build_number,
        '--build-event-build-scheduling-time=%d' % build_scheduled_ts,
    ]
    if step_name:
      args.append('--build-event-step-name=%s' % step_name)
      args.append('--build-event-step-number=%s' % step_number)
    return self.infra_runpy, args

  def _subprocess_spawn(self, cmd, args):
    """Spawns a subprocess and registers a logging error handler."""
    cmd = chromium_utils.AbsoluteCanonicalPath(cmd)
    full_cmd = map(str, [cmd] + args)

    if self.log_pipeline_calls:
      twisted_log.msg('Calling %s.' % full_cmd)
    d = getProcessOutputAndValue(cmd, args)
    def handleErrCode(res):
      out, err, code = res
      if code != 0:
        twisted_log.msg('error running %s: %d\n%s\n%s' % (
            full_cmd, code, out, err), logLevel=logging.ERROR)
    d.addCallback(handleErrCode)
    return d

  def send_build_event(self, timestamp_kind, build_event_type, bot_name,
                       builder_name, build_number, build_scheduled_ts,
                       step_name=None, step_number=None):
    if self.active and self._pipeline:
      return self._subprocess_spawn(
          *self._construct_monitoring_event_args(
              timestamp_kind, build_event_type, bot_name, builder_name,
              build_number, build_scheduled_ts, step_name=step_name,
              step_number=step_number))
    return None

  def startService(self):
    """Start the service and subscribe for updates."""
    logger = logging.getLogger(__name__)
    logger.propagate = False
    logger.setLevel(logging.INFO)
    # %(bbEvent)19s because builderChangedState is 19 characters long
    formatter = logging.Formatter('%(asctime)s - %(bbEvent)19s - %(message)s')
    # Use delay=True so we don't open an empty file while self.active=False.
    handler = TimedRotatingFileHandler(
        self._canonical_file(self.logfile),
        when='H', interval=1, delay=True)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    self.logger = logger

    StatusReceiverMultiService.startService(self)
    self.status = self.parent.getStatus()
    self.status.subscribe(self)

  def log(self, event, message, *args):
    """Simple wrapper for log. Passes string formatting args through."""
    if self.active and self._logging:
      self.logger.info(message, *args, extra={'bbEvent': event})

  def requestSubmitted(self, request):
    builderName = request.getBuilderName()
    self.log('requestSubmitted', '%s, %r', builderName, request)

  def requestCancelled(self, builder, request):
    builderName = builder.getName()
    self.log('requestCancelled', '%s, %r', builderName, request)

  def buildsetSubmitted(self, buildset):
    reason = buildset.getReason()
    self.log('buildsetSubmitted', '%r, %s', buildset, reason)

  def builderAdded(self, builderName, builder):
    # Use slavenames rather than getSlaves() to just get strings.
    slaves = builder.slavenames
    self.log('builderAdded', '%s, %r', builderName, slaves)
    # Must return self in order to subscribe to builderChangedState and
    # buildStarted/Finished events.
    return self

  def builderChangedState(self, builderName, state):
    self.log('builderChangedState', '%s, %r', builderName, state)

  def buildStarted(self, builderName, build):
    build_number = build.getNumber()
    bot = build.getSlavename()
    self.log('buildStarted', '%s, %d, %s', builderName, build_number, bot)
    self.send_build_event(
        'BEGIN', 'BUILD', bot, builderName, build_number,
        self._get_requested_at_millis(build))
    # Must return self in order to subscribe to stepStarted/Finished events.
    return self

  def buildETAUpdate(self, build, ETA):
    # We don't actually care about ETA updates; they happen on a periodic clock.
    pass

  def changeAdded(self, change):
    self.log('changeAdded', '%r', change)

  def stepStarted(self, build, step):
    bot = build.getSlavename()
    builder_name = build.getBuilder().name
    build_number = build.getNumber()
    step_name = step.getName()
    self.log('stepStarted', '%s, %d, %s', builder_name, build_number, step_name)
    self.send_build_event(
        'BEGIN', 'STEP', bot, builder_name, build_number,
        self._get_requested_at_millis(build),
        step_name=step_name, step_number=step.step_number)
    # Must return self in order to subscribe to logStarted/Finished events.
    return self

  def stepTextChanged(self, build, step, text):
    build_name = build.getBuilder().name
    build_number = build.getNumber()
    step_name = step.getName()
    self.log('stepTextChanged', '%s, %d, %s, %s',
             build_name, build_number, step_name, text)

  def stepText2Changed(self, build, step, text2):
    build_name = build.getBuilder().name
    build_number = build.getNumber()
    step_name = step.getName()
    self.log('stepText2Changed', '%s, %d, %s, %s',
             build_name, build_number, step_name, text2)

  def stepETAUpdate(self, build, step, ETA, expectations):
    # We don't actually care about ETA updates; they happen on a periodic clock.
    pass

  def logStarted(self, build, step, log):
    build_name = build.getBuilder().name
    build_number = build.getNumber()
    step_name = step.getName()
    log_name = log.getName()
    log_file = log.filename
    self.log('logStarted', '%s, %d, %s, %s, %s',
             build_name, build_number, step_name, log_name, log_file)
    # Create an attr on the stateful log object to count its chunks.
    # pylint: disable=protected-access
    log.__num_chunks = 0
    # pylint: enable=protected-access
    # Must return self in order to subscribe to logChunk events.
    return self

  def logChunk(self, _build, _step, log, _channel, _text):
    # Like the NSA, we only want to process metadata.
    log.__num_chunks += 1

  def logFinished(self, build, step, log):
    build_name = build.getBuilder().name
    build_number = build.getNumber()
    step_name = step.getName()
    log_name = log.getName()
    log_file = log.filename
    # Access to protected member __num_chunks. pylint: disable=W0212
    log_chunks = log.__num_chunks
    self.log('logFinished', '%s, %d, %s, %s, %s, %d',
             build_name, build_number, step_name,
             log_name, log_file, log_chunks)

  def stepFinished(self, build, step, results):
    builder_name = build.getBuilder().name
    build_number = build.getNumber()
    bot = build.getSlavename()
    step_name = step.getName()
    self.log('stepFinished', '%s, %d, %s, %r',
             builder_name, build_number, step_name, results)
    self.send_build_event(
        'END', 'STEP', bot, builder_name, build_number,
        self._get_requested_at_millis(build),
        step_name=step_name, step_number=step.step_number)

  def buildFinished(self, builderName, build, results):
    build_number = build.getNumber()
    bot = build.getSlavename()
    self.log('buildFinished', '%s, %d, %s, %r',
             builderName, build_number, bot, results)
    self.send_build_event(
        'END', 'BUILD', bot, builderName, build_number,
        self._get_requested_at_millis(build))

  def builderRemoved(self, builderName):
    self.log('builderRemoved', '%s', builderName)

  def slaveConnected(self, slaveName):
    self.log('slaveConnected', '%s', slaveName)

  def slaveDisconnected(self, slaveName):
    self.log('slaveDisconnected', '%s', slaveName)
