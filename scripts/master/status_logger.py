# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Log status events to a file on disk or event collection endpoint."""


import json
import logging
import logging.handlers
import os
import re
import time

from logging.handlers import TimedRotatingFileHandler

import buildbot.status.results

from buildbot.status.base import StatusReceiverMultiService
from twisted.python import log as twisted_log

from common import chromium_utils

from infra_libs import ts_mon

step_durations  = ts_mon.CumulativeDistributionMetric(
    'buildbot/master/builders/steps/durations',
    description='Time (in seconds) from step start to step end',
    units=ts_mon.MetricsDataUnits.SECONDS)

step_counts  = ts_mon.CounterMetric(
    'buildbot/master/builders/steps/count',
    description='Count of step results, per builder and step')

result_count = ts_mon.CounterMetric('buildbot/master/builders/results/count',
    description='Number of items consumed from ts_mon.log by mastermon')
# A custom bucketer with 12% resolution in the range of 1..10**5,
# better suited for build cycle times.
bucketer = ts_mon.GeometricBucketer(
    growth_factor=10**0.05, num_finite_buckets=100)
cycle_times = ts_mon.CumulativeDistributionMetric(
    'buildbot/master/builders/builds/durations', bucketer=bucketer,
    description='Durations (in seconds) that slaves spent actively doing '
                'work towards builds for each builder')
pending_times = ts_mon.CumulativeDistributionMetric(
    'buildbot/master/builders/builds/pending_durations', bucketer=bucketer,
    description='Durations (in seconds) that the master spent waiting for '
                'slaves to become available for each builder')
total_times = ts_mon.CumulativeDistributionMetric(
    'buildbot/master/builders/builds/total_durations', bucketer=bucketer,
    description='Total duration (in seconds) that builds took to complete '
                'for each builder')

pre_test_times = ts_mon.CumulativeDistributionMetric(
    'buildbot/master/builders/builds/pre_test_durations', bucketer=bucketer,
    description='Durations (in seconds) that builds spent before their '
                '"before_tests" step')


class StatusEventLogger(StatusReceiverMultiService):
  """Log status events to a file on disk or event collection endpoint.

  Files on disk are rotated, while the event collection endpoint is contacted
  through a script in the infra/infra repository (separate checkout).

  A file, .logstatus, is used to configure the logger. If it exists then
  file logging is enabled. If it parses as json, the keys event_logging,
  file_logging, logging_ignore_basedir, logfile, can be used to configure the
  logger at runtime.
  """

  DEFAULT_LOGGING_IGNORE_BASEDIR = False

  def __init__(self, basedir=None, event_logging_dir=None,
               event_logfile=None, ts_mon_logfile=None,
               logging_ignore_basedir=None, event_logging=None):
    """Create a StatusEventLogger.

    Args:
      basedir: the basedir of the configuration and log files. Set to the
               service's parent directory by default, mainly overridden for
               testing.
      event_logging_dir: directory where to write events. This object adds the
               master name to the path. Mainly overridden for testing.
      event_logfile: file name for writing events.
      ts_mon_logfile: file name for writing ts_mon metrics.
      logging_ignore_basedir (bool): when True, do not prepend
               event_logging_dir to event_logfile and ts_mon_logfile.
      event_logging (bool or None): enables logging events to event pipeline.
               Default: enabled.
    """
    self._basedir = basedir
    self.master_dir = os.path.basename(os.path.abspath(os.curdir))

    self.logging_ignore_basedir = (
        logging_ignore_basedir or self.DEFAULT_LOGGING_IGNORE_BASEDIR)

    self._event_logging_dir = os.path.join(
      event_logging_dir or '/var/log/chrome-infra',
      'status_logger-' + self.master_dir)

    event_logfile = event_logfile or 'events.log'
    ts_mon_logfile = ts_mon_logfile or 'ts_mon.log'

    if not self.logging_ignore_basedir:
      event_logfile = os.path.join(self._event_logging_dir, event_logfile)
      ts_mon_logfile = os.path.join(self._event_logging_dir, ts_mon_logfile)

    self._event_logfile = event_logfile
    self._ts_mon_logfile = ts_mon_logfile

    # Will be initialized in startService.
    self.event_logger = None
    self.ts_mon_logger = None
    self.status = None
    self._last_checked_active = 0
    self._event_logging = event_logging if event_logging is not None else True
    # Can't use super because StatusReceiverMultiService is an old-style class.
    StatusReceiverMultiService.__init__(self)

  def as_dict(self):
    return {
        'basedir': self.basedir,
        'event_logging': self._event_logging,
        'logging_ignore_basedir': self.logging_ignore_basedir,
    }

  @staticmethod
  def _get_requested_at_millis(build):
    return int(build.getProperty('requestedAt') * 1000)

  @property
  def basedir(self):
    """Returns dynamic or preset basedir.

    self.parent doesn't exist until the service is running, so this has to be
    here instead of precomputing the logfile in __init__.
    """
    return self._basedir or self.parent.basedir

  def _canonical_file(self, filename, ignore_basedir=False):
    """Returns an absolute path for a config or log file."""
    if ignore_basedir:
      full_filename = filename
    else:
      full_filename = os.path.join(self.basedir, filename)
    return chromium_utils.AbsoluteCanonicalPath(full_filename)

  def send_build_result(
      self, scheduled, started, finished, builder_name, bot_name, result,
      project_id=None, subproject_tag=None, steps=None, pre_test_time_s=None):
    """Log a build result for ts_mon.

    This allows computing metrics for builds in mastermon.
    """
    d = {
        'timestamp_ms': finished * 1000,
        'builder': builder_name,
        'slave': bot_name,
        'result': result.lower(),
        'duration_s': finished - started,
        'pending_s': started - scheduled,
        'total_s': finished - scheduled,
    }
    if project_id:
      d['project_id'] = project_id
    if subproject_tag:
      d['subproject_tag'] = subproject_tag
    if steps:
      d['steps'] = steps
    if pre_test_time_s is not None:
      d['pre_test_time_s'] = pre_test_time_s
    self.ts_mon_logger.info(json.dumps(d))

  def send_step_result(
      self, timestamp, builder_name, bot_name,
      step_result, project_id, subproject_tag):
    """Log step results for ts_mon

    Args:
      timestamp(int): when the event was generated (end of a step). Seconds
        since the Unix epoch.
      builder_name(str): name of the builder the steps are part of.
      bot_name(str): name of the machine running the build.
      step_result (str): result for this step.
      project_id(str): 'project' as shown on the codereview.
      subproject_tag(str): a mention of a subproject. Mostly used to distinguish
        between chromium and blink CLs in the chromium project.
    """
    # The presence of the field 'step_result' is how the collecting daemon
    # tells the difference between this case and the one from send_build_result.
    d = {
      'timestamp': timestamp,
      'builder': builder_name,
      'step_result': step_result,
      'slave': bot_name,
    }

    if project_id:
      d['project_id'] = project_id
    if subproject_tag:
      d['subproject_tag'] = subproject_tag

    self.ts_mon_logger.info(json.dumps(d))


  def send_build_event(self, timestamp_kind, timestamp, build_event_type,
                       bot_name, builder_name, build_number, build_scheduled_ts,
                       step_name=None, step_text=None, step_number=None,
                       result=None, extra_result_code=None, patch_url=None,
                       bbucket_id=None, category=None,
                       head_revision_git_hash=None):
    """Log a build/step event for event_mon."""

    if self._event_logging:
      # List options to pass to send_monitoring_event, without the --, to save
      # a bit of space.
      d = {'event-mon-timestamp-kind': timestamp_kind,
           'event-mon-event-timestamp': timestamp,
           'event-mon-service-name': 'buildbot/master/%s' % self.master_dir,
           'build-event-type': build_event_type,
           'build-event-hostname': bot_name,
           'build-event-build-name': builder_name,
           'build-event-build-number': build_number,
           'build-event-build-scheduling-time': build_scheduled_ts,
         }
      if step_name:
        d['build-event-step-name'] = step_name
        d['build-event-step-text'] = step_text
        d['build-event-step-number'] = step_number
      if result:
        d['build-event-result'] = result.upper()
      if extra_result_code:
        d['build-event-extra-result-code'] = extra_result_code
      if patch_url:
        d['build-event-patch-url'] = patch_url
      if bbucket_id:
        d['build-event-bbucket-id'] = bbucket_id
      if category:
        d['build-event-category'] = category
      if head_revision_git_hash:
        d['build-event-head-revision-git-hash'] = head_revision_git_hash

      self.event_logger.info(json.dumps(d))

  def _create_logging_dir(self):
    """Make sure the logging directory exists.

    Try to create the directory if it doesn't exist, returns False if it
    fails.

    Returns:
      logs_dir_exists(bool): True is the directory is available

    """
    event_logging_dir_exists = os.path.isdir(self._event_logging_dir)
    if not event_logging_dir_exists:
      try:
        os.mkdir(self._event_logging_dir)
      except OSError:
        twisted_log.msg('Logging directory cannot be created, no events will '
                        'be written:', self._event_logging_dir)
      else:
        event_logging_dir_exists = True

    return event_logging_dir_exists

  def _create_ts_mon_logger(self):
    """Set up a logger for ts_mon events.

    If the destination directory does not exist, ignore data sent to
    ts_mon_logger.
    """

    event_logging_dir_exists = self._create_logging_dir()
    logger = logging.getLogger(__name__ + '_ts_mon')
    # Remove handlers that may already exist. This is useful when changing the
    # log file name.
    for handler in logger.handlers:
      handler.flush()
      logger.handlers = []

    logger.propagate = False
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')

    if event_logging_dir_exists:
      # Use delay=True so we don't unnecessary open a new file.
      # Also use WatchedFileHandler because it'll be rotated by an external
      # process.
      handler = logging.handlers.WatchedFileHandler(self._ts_mon_logfile,
                                                    encoding='utf-8',
                                                    delay=True)
    else:
      handler = logging.NullHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    self.ts_mon_logger = logger

  def _create_event_logger(self):
    """Set up a logger for monitoring events.

    If the destination directory does not exist, ignore data sent to
    event_logger.
    """
    event_logging_dir_exists = self._create_logging_dir()

    logger = logging.getLogger(__name__ + '_event')
    # Remove handlers that may already exist. This is useful when changing the
    # log file name.
    for handler in logger.handlers:
      handler.flush()
      logger.handlers = []

    logger.propagate = False
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')

    if event_logging_dir_exists:
      # Use delay=True so we don't unnecessarily open a new file.
      handler = TimedRotatingFileHandler(self._event_logfile, backupCount=1440,
                                         when='M', interval=1, delay=True)
    else:
      handler = logging.NullHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    self.event_logger = logger

  def _get_patch_url(self, build_properties):
    # TODO(sergiyb): Add support for Gerrit.
    patch_url = None
    if ('issue' in build_properties and 'patchset' in build_properties and
        'rietveld' in build_properties):
      patch_url = '%s/%s#ps%s' % (
          build_properties.getProperty('rietveld'),
          build_properties.getProperty('issue'),
          build_properties.getProperty('patchset'))
    return patch_url

  def _get_bbucket_id(self, build_properties):
    """Retrieves buildbucket id from build properties.

    Returns None when buildbucket properties are missing or malformed.
    """
    if 'buildbucket' not in build_properties:
      return

    try:
      bbucket_props = json.loads(
          build_properties.getProperty('buildbucket'))
    except (ValueError, TypeError) as e:
      twisted_log.msg('Failed to parse buildbucket property as JSON: %s' % e)
      return

    if isinstance(bbucket_props, dict):
      build = bbucket_props.get('build', {})
      if isinstance(build, dict):
        return build.get('id')
      else:
        twisted_log.msg('Build inside buildbucket property is not a dict')
    else:
      twisted_log.msg('Buildbucket property is not a dict')

  def _get_head_revision_git_hash(self, build_properties):
    if 'got_revision' in build_properties:
      revision = build_properties.getProperty('got_revision').lower()
      if re.match('^[0-9a-f]{40}$', revision):
        return revision


  def startService(self):
    """Start the service and subscribe for updates."""
    self._create_event_logger()
    self._create_ts_mon_logger()

    StatusReceiverMultiService.startService(self)
    self.status = self.parent.getStatus()
    self.status.subscribe(self)

  # Unused, but is required by the API to enable other events.
  def builderAdded(self, builderName, builder):
    # Must return self in order to subscribe to builderChangedState and
    # buildStarted/Finished events.
    return self

  def buildStarted(self, builderName, build):
    build_number = build.getNumber()
    bot = build.getSlavename()
    started, _ = build.getTimes()
    properties = build.getProperties()
    self.send_build_event(
        'BEGIN', started * 1000, 'BUILD', bot, builderName, build_number,
        self._get_requested_at_millis(build),
        patch_url=self._get_patch_url(properties),
        bbucket_id=self._get_bbucket_id(properties),
        category=properties.getProperty('category'))
    # Must return self in order to subscribe to stepStarted/Finished events.
    return self

  def stepStarted(self, build, step):
    bot = build.getSlavename()
    builder_name = build.getBuilder().name
    build_number = build.getNumber()
    step_name = step.getName()
    step_text = ' '.join(step.getText())
    started, _ = step.getTimes()
    properties = build.getProperties()
    self.send_build_event(
        'BEGIN', started * 1000, 'STEP', bot, builder_name, build_number,
        self._get_requested_at_millis(build),
        step_name=step_name, step_text=step_text, step_number=step.step_number,
        patch_url=self._get_patch_url(properties),
        bbucket_id=self._get_bbucket_id(properties),
        category=properties.getProperty('category'))
    # Must return self in order to subscribe to logStarted/Finished events.
    return self

  def stepFinished(self, build, step, results):
    builder_name = build.getBuilder().name
    build_number = build.getNumber()
    bot = build.getSlavename()
    step_name = step.getName()
    step_text = ' '.join(step.getText())
    started, finished = step.getTimes()
    properties = build.getProperties()
    self.send_build_event(
        'END', finished * 1000, 'STEP', bot, builder_name, build_number,
        self._get_requested_at_millis(build),
        step_name=step_name, step_text=step_text, step_number=step.step_number,
        result=buildbot.status.results.Results[results[0]],
        patch_url=self._get_patch_url(properties),
        bbucket_id=self._get_bbucket_id(properties),
        category=properties.getProperty('category'))

    # Send step result to ts-mon
    properties = build.getProperties()
    project_id = properties.getProperty('patch_project')
    subproject_tag = properties.getProperty('subproject_tag')
    step_result = buildbot.status.results.Results[step.getResults()[0]]

    self.send_step_result(
      finished,
      builder_name,
      bot,
      step_result,
      project_id,
      subproject_tag)

    if re.match('bot_update|update_scripts', step_name):
      values = {
          'slave': bot,
          'project_id': project_id,
          'builder': builder_name,
          'result': step_result,
          'subproject_tag': subproject_tag,
          'step_name': step_name.split()[0],
          'master': self.master_dir
      }
      fields = { key: value if value is not None else ''
                for key, value in values.iteritems() }
      step_durations.add(finished - started, fields=fields)
      step_counts.increment(fields=fields)

  def buildFinished(self, builderName, build, results):
    build_number = build.getNumber()
    bot = build.getSlavename()
    started, finished = build.getTimes()

    # Calculate when build was scheduled if possible. Use build started
    # timestamp as initial approximation.
    scheduled = started
    source_stamp = build.getSourceStamp()
    if source_stamp and source_stamp.changes:
      scheduled = source_stamp.changes[0].when

    properties = build.getProperties()
    extra_result_code = properties.getProperty('extra_result_code')

    self.send_build_event(
        'END', finished * 1000, 'BUILD', bot, builderName, build_number,
        self._get_requested_at_millis(build),
        result=buildbot.status.results.Results[results],
        extra_result_code=extra_result_code,
        patch_url=self._get_patch_url(properties),
        bbucket_id=self._get_bbucket_id(properties),
        category=properties.getProperty('category'),
        head_revision_git_hash=self._get_head_revision_git_hash(properties))

    pre_test_time_s = None
    for step in build.getSteps():
      if step.getName() == 'mark: before_tests':
        step_started, _ = step.getTimes()
        pre_test_time_s = step_started - started

    # It's important that the recipe does not generate unbounded number
    # of step names (e.g. one for each git revision), to avoid stream
    # explosion in the monitoring system. Another alternative is for the recipe
    # to clearly mark such dynamic steps - e.g. add "(dynamic)" to the name,
    # and exclude such steps here.
    WHITELISTED_RECIPES = [
      'chromium_trybot',
    ]
    steps_to_send = []
    if properties.getProperty('recipe') in WHITELISTED_RECIPES:
      for step in build.getSteps():
        step_started, step_finished = step.getTimes()
        steps_to_send.append({
          'step_name': step.getName(),
          'duration_s': step_finished - step_started,
          'result': buildbot.status.results.Results[step.getResults()[0]],
        })

    # If property doesn't exist, this function returns None.
    # Note: this is not true for build.getProperty(), it raises KeyError.
    project_id = properties.getProperty('patch_project')
    subproject_tag = properties.getProperty('subproject_tag')

    fields = {
        'master': 'deprecated',
        'builder': builderName,
        'slave': bot,
        'result': buildbot.status.results.Results[results].lower(),
        'project_id': project_id if project_id else 'unknown',
        'subproject_id': subproject_tag if subproject_tag else 'unknown',
    }
    result_count.increment(fields)
    cycle_times.add(finished - started, fields=fields)
    pending_times.add(started - scheduled, fields=fields)
    total_times.add(finished - scheduled, fields=fields)
    if pre_test_time_s:
      pre_test_times.add(pre_test_time_s, fields=fields)

    # TODO(sergeyberezin): remove this when all masters are restarted,
    # and all graphs and alerts are migrated to the new metrics. Do
    # this before turning down mastermon - to avoid accumulating logs.
    self.send_build_result(
        scheduled, started, finished, builderName, bot,
        buildbot.status.results.Results[results],
        project_id, subproject_tag, steps=steps_to_send,
        pre_test_time_s=pre_test_time_s)
