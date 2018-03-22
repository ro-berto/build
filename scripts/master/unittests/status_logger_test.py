#!/usr/bin/env vpython
# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib
import json
import os
import tempfile
import shutil
import unittest

import test_env  # pylint: disable=relative-import

from master import status_logger

from infra_libs import ts_mon


### Mock buildbot objects.

class Builder(object):
  name = 'coconuts'


class Properties(object):
  def __init__(self, properties=None):
    # properties is a dict {property name: property value}
    self.__properties = properties or {}

  def __contains__(self, _name):
    return True

  def getProperty(self, name):
    return self.__properties.get(name, 'whatever')


class SourceStamp(object):
  changes = []


class Build(object):
  def __init__(self, steps=None, properties=None):
    self.__steps = steps or []
    self.__properties = properties or {}

  def getNumber(self):
    return 5

  def getBuilder(self):
    return Builder()

  def getSlavename(self):
    return 'cool-m1'

  def getProperty(self, _name):
    return 1427929423.0

  def getProperties(self):
    return Properties(self.__properties)

  def getSourceStamp(self):
    return SourceStamp()

  def getSteps(self):
    return self.__steps

  def getTimes(self):
    return 5000, 6000


class Step(object):
  def __init__(self, step_number=8, result=0, name='reticulating_splines'):
    self.step_number = step_number
    self.__result = result
    self._name = name

  def getName(self):
    return self._name

  def getText(self):
    return 'step text'

  def getTimes(self):
    return 5100, 5500

  def getResults(self):
    return (self.__result, None)


@contextlib.contextmanager
def _make_logger(event_logfile=None, ts_mon_logfile=None,
                 logging_ignore_basedir=None, event_logging=None):
  """Create a status_logger and delete any temp files when done."""
  tempdir = tempfile.mkdtemp(prefix='status-logger')

  logger = status_logger.StatusEventLogger(
      basedir=tempdir, event_logging_dir=tempdir,
      event_logfile=event_logfile, ts_mon_logfile=ts_mon_logfile,
      logging_ignore_basedir=logging_ignore_basedir,
      event_logging=event_logging)
  logger._create_event_logger()
  logger._create_ts_mon_logger()
  yield logger

  if os.path.exists(tempdir):
    shutil.rmtree(tempdir)


### Main test class.

class StatusLoggerTest(unittest.TestCase):

  def setUp(self):
    super(StatusLoggerTest, self).setUp()
    ts_mon.reset_for_unittest(disable=True)

  def testNormalInitialization(self):
    with _make_logger() as logger:
      self.assertTrue(logger._event_logging)

  def testDisableLogger(self):
    with _make_logger(event_logging=False) as logger:
      self.assertFalse(logger._event_logging)

  def testConfigureEndpointsAbsolutePath(self):
    with _make_logger(logging_ignore_basedir=True,
                      event_logfile='/tmp/events_custom.log',
                      ts_mon_logfile='/tmp/ts_mon_custom.log') as logger:
      self.assertTrue(logger._event_logging_dir)
      self.assertEqual(logger._event_logfile, '/tmp/events_custom.log')
      self.assertEqual(logger._ts_mon_logfile, '/tmp/ts_mon_custom.log')

  def testConfigureEndpoints(self):
    with _make_logger(event_logfile='events_custom.log',
                      ts_mon_logfile='ts_mon_custom.log') as logger:
      self.assertTrue(logger._event_logging_dir)
      self.assertIn('events_custom.log', logger._event_logfile)
      self.assertIn('ts_mon_custom.log', logger._ts_mon_logfile)

  def testStartBuild(self):
    with _make_logger() as logger:  # event_logging=True is the default
      logger.buildStarted('coconuts', Build())
      self.assertTrue(os.path.isdir(logger._event_logging_dir))
      self.assertTrue(os.path.exists(logger._event_logfile))
      # Ensure we added valid json
      with open(logger._event_logfile, 'r') as f:
        content = f.read()
        self.assertTrue(content)
        json.loads(content)

  def testStartStep(self):
    with _make_logger() as logger:
      logger.stepStarted(Build(), Step())
      self.assertTrue(os.path.isdir(logger._event_logging_dir))
      self.assertTrue(os.path.exists(logger._event_logfile))
      # Ensure we added valid json
      with open(logger._event_logfile, 'r') as f:
        content = f.read()
        self.assertTrue(content)
        json.loads(content)

  def testStopBuild(self):
    with _make_logger() as logger:
      logger.buildFinished('coconuts', Build(), 0)
      self.assertTrue(os.path.isdir(logger._event_logging_dir))
      self.assertTrue(os.path.exists(logger._event_logfile))
      # Ensure we added valid json
      with open(logger._event_logfile, 'r') as f:
        content = f.read()
        self.assertTrue(content)
        json.loads(content)

  def testReportsPatchURL(self):
    with _make_logger() as logger:
      mock_build = Build(
          properties={
              'patch_storage': 'gerrit',
              'patch_gerrit_url': 'https://chromium-review.googlesource.com',
              'patch_project': 'chromium/src',
              'patch_issue': '808725',
              'patch_set': '1',
          })
      logger.buildFinished('coconuts', mock_build, 0)
      self.assertTrue(os.path.isdir(logger._event_logging_dir))
      self.assertTrue(os.path.exists(logger._event_logfile))
      # Ensure we added valid json
      with open(logger._event_logfile, 'r') as f:
        content = f.read()
        self.assertTrue(content)
        parsed = json.loads(content)
        self.assertEqual(
            parsed['build-event-patch-url'],
            'https://chromium-review.googlesource.com/c/chromium/src/'
            '+/808725/1')

  def testReportsBBucketID(self):
    with _make_logger() as logger:
      mock_build = Build(properties={'buildbucket': '{"build":{"id":123}}'})
      logger.buildFinished('coconuts', mock_build, 0)
      self.assertTrue(os.path.isdir(logger._event_logging_dir))
      self.assertTrue(os.path.exists(logger._event_logfile))
      # Ensure we added valid json
      with open(logger._event_logfile, 'r') as f:
        content = f.read()
        self.assertTrue(content)
        parsed = json.loads(content)
        self.assertEqual(parsed['build-event-bbucket-id'], 123)

  def testReportsBuildCategory(self):
    with _make_logger() as logger:
      mock_build = Build(properties={'category': 'cq_experimental'})
      logger.buildFinished('coconuts', mock_build, 0)
      self.assertTrue(os.path.isdir(logger._event_logging_dir))
      self.assertTrue(os.path.exists(logger._event_logfile))
      # Ensure we added valid json
      with open(logger._event_logfile, 'r') as f:
        content = f.read()
        self.assertTrue(content)
        parsed = json.loads(content)
        self.assertEqual(parsed['build-event-category'], 'cq_experimental')

  def testReportsFailType(self):
    with _make_logger() as logger:
      mock_build = Build(properties={'failure_type': 'INVALID_TEST_RESULTS'})
      logger.buildFinished('coconuts', mock_build, 0)
      self.assertTrue(os.path.isdir(logger._event_logging_dir))
      self.assertTrue(os.path.exists(logger._event_logfile))
      # Ensure we added valid json
      with open(logger._event_logfile, 'r') as f:
        content = f.read()
        self.assertTrue(content)
        parsed = json.loads(content)
        self.assertEqual(
            parsed['build-event-fail-type'], 'INVALID_TEST_RESULTS')

  def testDoesNotReportGotRevisionFromSVN(self):
    with _make_logger() as logger:
      mock_build = Build(properties={'got_revision': '12345'})
      logger.buildFinished('coconuts', mock_build, 0)
      self.assertTrue(os.path.isdir(logger._event_logging_dir))
      self.assertTrue(os.path.exists(logger._event_logfile))
      # Ensure we added valid json
      with open(logger._event_logfile, 'r') as f:
        content = f.read()
        self.assertTrue(content)
        parsed = json.loads(content)
        self.assertNotIn('build-event-head-revision-git-hash', parsed)

  def testReportsGitRevisionHash(self):
    with _make_logger() as logger:
      mock_build = Build(properties={
        'got_revision': '773ceaef513c9e81fde791b6fe4612fd46cfb7fd'})
      logger.buildFinished('coconuts', mock_build, 0)
      self.assertTrue(os.path.isdir(logger._event_logging_dir))
      self.assertTrue(os.path.exists(logger._event_logfile))
      # Ensure we added valid json
      with open(logger._event_logfile, 'r') as f:
        content = f.read()
        self.assertTrue(content)
        parsed = json.loads(content)
        self.assertEqual(parsed['build-event-head-revision-git-hash'],
                         '773ceaef513c9e81fde791b6fe4612fd46cfb7fd')

  def testStopStep(self):
    steps = [Step(step_number=1),
             Step(step_number=2, result=1),
             Step(step_number=3)]
    with _make_logger() as logger:
      logger.stepFinished(Build(steps=steps), steps[-1], [0])
      self.assertTrue(os.path.isdir(logger._event_logging_dir))
      self.assertTrue(os.path.exists(logger._event_logfile))

      # Ensure we added valid json
      with open(logger._event_logfile, 'r') as f:
        content = f.read()
        self.assertTrue(content)
        json.loads(content)

      # Ensure we wrote the correct json line.
      expected = {
          "slave": "cool-m1",
          "builder": "coconuts",
          "timestamp": 5500,
          "step_result": "success",
          "subproject_tag": "whatever",
          "project_id": "whatever",
      }
      with open(logger._ts_mon_logfile, 'r') as f:
        line = f.read()
        d = json.loads(line)
        self.assertEqual(expected, d)

  def testBotUpdateStepMonitor(self):
    properties = {'patch_project': '',
                  'subproject_tag': ''}
    step = Step(step_number=1, name='bot_update 1')
    build = Build(steps=[step], properties=properties)
    with _make_logger() as logger:
      logger.stepFinished(build, step, [0])
    expected_fields = {
        'slave': build.getSlavename(),
        'builder': build.getBuilder().name,
        'master': logger.master_dir,
        'result': 'success',
        'step_name': 'bot_update',
        'subproject_tag': '',
        'project_id': ''
    }
    duration_dist = status_logger.step_durations.get(expected_fields)
    started, finished  = step.getTimes()
    self.assertEqual(duration_dist.count, 1)
    self.assertEqual(duration_dist.sum, finished - started)
    self.assertEqual(1, status_logger.step_counts.get(expected_fields))

  def testStepStepWithMissingProject(self):
    properties = {'patch_project': '',
                  'subproject_tag': ''}
    steps = [Step(step_number=1),
             Step(step_number=2, result=1),
             Step(step_number=3)]
    with _make_logger() as logger:
      logger.stepFinished(Build(steps=steps, properties=properties),
                          steps[-1],
                          [0])
      self.assertTrue(os.path.isdir(logger._event_logging_dir))
      self.assertTrue(os.path.exists(logger._event_logfile))

      # Ensure we added valid json
      with open(logger._event_logfile, 'r') as f:
        content = f.read()
        self.assertTrue(content)
        json.loads(content)

      # Ensure we wrote the correct json line.
      expected = {
          "slave": "cool-m1",
          "builder": "coconuts",
          "timestamp": 5500,
          "step_result": "success",
      }
      with open(logger._ts_mon_logfile, 'r') as f:
        line = f.read()
        d = json.loads(line)
        self.assertEqual(expected, d)


if __name__ == '__main__':
  unittest.main()
