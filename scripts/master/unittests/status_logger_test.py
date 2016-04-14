#!/usr/bin/env python
# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib
import json
import os
import tempfile
import shutil
import unittest

import test_env  # pylint: disable=W0611,W0403

from master import status_logger


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
  def __init__(self, step_number=8, result=0):
    self.step_number = step_number
    self.__result = result

  def getName(self):
    return 'reticulating_splines'

  def getText(self):
    return 'step text'

  def getTimes(self):
    return 5100, 5500

  def getResults(self):
    return (self.__result, None)


@contextlib.contextmanager
def _make_logger(file_content=None):
  """Create a status_logger and delete any temp files when done."""
  tempdir = tempfile.mkdtemp(prefix='status-logger')

  filename = 'logstatus'
  if file_content is None:
    filename = 'does_not_exist'
  else:
    with open(os.path.join(tempdir, filename), 'w') as f:
      if not file_content:
        f.write('\n')
      else:
        f.write(json.dumps(file_content))

  logger = status_logger.StatusEventLogger(
    configfile=filename, basedir=tempdir, event_logging_dir=tempdir)
  logger._create_logger()
  logger._create_event_logger()
  logger._create_ts_mon_logger()
  yield logger

  if os.path.exists(tempdir):
    shutil.rmtree(tempdir)


### Main test class.

class StatusLoggerTest(unittest.TestCase):
  def testNoFile(self):
    with _make_logger() as logger:
      self.assertTrue(logger)

  def testNormalInitialization(self):
    with _make_logger('') as logger:
      self.assertTrue(logger.active)
      self.assertTrue(logger._logging)

  def testDisableLogger(self):
    with _make_logger({'file_logging': False}) as logger:
      self.assertTrue(logger.active)
      self.assertFalse(logger._logging)

  def testConfigureEndpoints(self):
    config_dict = {
        'logfile': '/tmp/bummer',
        'logging_ignore_basedir': True,
    }
    with _make_logger(config_dict) as logger:
      self.assertTrue(logger.active)
      self.assertTrue(logger._logging)
      self.assertTrue(logger._event_logging_dir)
      self.assertEqual(logger.logfile, '/tmp/bummer')

  def testStartBuild(self):
    config_dict = {
        'file_logging': True,
        'event_logging': True,
    }
    with _make_logger(config_dict) as logger:
      logger.buildStarted('coconuts', Build())
      self.assertTrue(os.path.exists(logger.logfile))
      self.assertTrue(os.path.isdir(logger._event_logging_dir))
      self.assertTrue(os.path.exists(logger._event_logfile))
      # Ensure we added valid json
      with open(logger._event_logfile, 'r') as f:
        content = f.read()
        self.assertTrue(content)
        json.loads(content)

  def testStartStep(self):
    config_dict = {
        'file_logging': True,
        'event_logging': True,
    }
    with _make_logger(config_dict) as logger:
      logger.stepStarted(Build(), Step())
      self.assertTrue(os.path.exists(logger.logfile))
      self.assertTrue(os.path.isdir(logger._event_logging_dir))
      self.assertTrue(os.path.exists(logger._event_logfile))
      # Ensure we added valid json
      with open(logger._event_logfile, 'r') as f:
        content = f.read()
        self.assertTrue(content)
        json.loads(content)

  def testStopBuild(self):
    config_dict = {
        'file_logging': True,
        'event_logging': True,
    }
    with _make_logger(config_dict) as logger:
      logger.buildFinished('coconuts', Build(), 0)
      self.assertTrue(os.path.exists(logger.logfile))
      self.assertTrue(os.path.isdir(logger._event_logging_dir))
      self.assertTrue(os.path.exists(logger._event_logfile))
      # Ensure we added valid json
      with open(logger._event_logfile, 'r') as f:
        content = f.read()
        self.assertTrue(content)
        json.loads(content)

  def testStopStep(self):
    config_dict = {
        'file_logging': True,
        'event_logging': True,
    }
    steps = [Step(step_number=1),
             Step(step_number=2, result=1),
             Step(step_number=3)]
    with _make_logger(config_dict) as logger:
      logger.stepFinished(Build(steps=steps), steps[-1], [0])
      self.assertTrue(os.path.exists(logger.logfile))
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

  def testStepStepWithMissingProject(self):
    config_dict = {
        'file_logging': True,
        'event_logging': True,
    }
    properties = {'patch_project': '',
                  'subproject_tag': ''}
    steps = [Step(step_number=1),
             Step(step_number=2, result=1),
             Step(step_number=3)]
    with _make_logger(config_dict) as logger:
      logger.stepFinished(Build(steps=steps, properties=properties),
                          steps[-1],
                          [0])
      self.assertTrue(os.path.exists(logger.logfile))
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
