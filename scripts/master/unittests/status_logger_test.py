#!/usr/bin/env python
# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib
import json
import os
import tempfile
import unittest

import test_env  # pylint: disable=W0611

from master import status_logger


### Mock buildbot objects.

class Builder(object):
  name = 'coconuts'


class Build(object):
  def getNumber(self):
    return 5

  def getBuilder(self):
    return Builder()

  def getSlavename(self):
    return 'cool-m1'

  def getProperty(self, _name):
    return 1427929423.0


class Step(object):
  step_number = 8
  def getName(self):
    return 'reticulating_splines'


### Base test class.

class LoggerTestBase(unittest.TestCase):
  def setUp(self):
    self.called_programs = []

  def _redirect_spawn(self, logger):
    """Mock out StatusEventLogger's _subprocess_spawn()."""
    called_programs = self.called_programs
    def _fake_subprocess_spawn(cmd, args):
      called_programs.append((cmd, args))
      return None
    logger._subprocess_spawn = _fake_subprocess_spawn


  @contextlib.contextmanager
  def _make_logger(self, file_content=None):
    """Create a status_logger and delete any temp files when done."""
    fp = tempfile.NamedTemporaryFile(delete=False)
    filename = fp.name

    if file_content is None:
      filename = '/does_not_exist'
    elif not file_content:
      fp.write('\n')
    else:
      fp.write(json.dumps(file_content))
    fp.close()

    logger = status_logger.StatusEventLogger(configfile=filename, basedir='/')
    self._redirect_spawn(logger)
    yield logger
    if os.path.exists(fp.name):
      os.remove(fp.name)


### Main test class.

class StatusLoggerTest(LoggerTestBase):
  def testNoFile(self):
    with self._make_logger() as logger:
      self.assertTrue(logger)

  def testNormalInitialization(self):
    with self._make_logger('') as logger:
      self.assertTrue(logger.active)
      self.assertFalse(logger._pipeline)
      self.assertTrue(logger._logging)

  def testDisableLogger(self):
    with self._make_logger({'file_logging': False}) as logger:
      self.assertTrue(logger.active)
      self.assertFalse(logger._pipeline)
      self.assertFalse(logger._logging)

  def testPipelineInitialization(self):
    with self._make_logger({'infra_pipeline': True}) as logger:
      self.assertTrue(logger.active)
      self.assertTrue(logger._pipeline)

      self.assertEqual(logger.infra_runpy, '/home/chrome-bot/infra/run.py')
      self.assertEqual(
          logger.monitoring_script, 'infra.tools.send_monitoring_event')
      self.assertEqual(logger.monitoring_type, 'dry')

  def testConfigureEndpoints(self):
    config_dict = {
        'infra_pipeline': True,
        'infra_runpy': '/tmp/cool',
        'log_pipeline_calls': True,
        'logfile': '/tmp/bummer',
        'logging_ignore_basedir': True,
        'monitoring_script': 'infra.cooler',
        'monitoring_type': 'prod',
    }
    with self._make_logger(config_dict) as logger:
      self.assertTrue(logger.active)
      self.assertTrue(logger._logging)
      self.assertTrue(logger._pipeline)
      self.assertTrue(logger.log_pipeline_calls)
      self.assertEqual(logger._basedir, '/')
      self.assertEqual(logger.logfile, '/tmp/bummer')
      self.assertEqual(logger.infra_runpy, '/tmp/cool')
      self.assertEqual(logger.monitoring_script, 'infra.cooler')
      self.assertEqual(logger.monitoring_type, 'prod')

  def testStartBuild(self):
    config_dict = {
        'infra_pipeline': True,
        'file_logging': False,
    }
    with self._make_logger(config_dict) as logger:
      logger.buildStarted('coconuts', Build())
      self.assertEqual(len(self.called_programs), 1)
      self.assertEqual(self.called_programs[0][0],
                       '/home/chrome-bot/infra/run.py')

  def testStartStep(self):
    config_dict = {
        'infra_pipeline': True,
        'file_logging': False,
    }
    with self._make_logger(config_dict) as logger:
      logger.stepStarted(Build(), Step())
      self.assertEqual(len(self.called_programs), 1)
      self.assertEqual(self.called_programs[0][0],
                       '/home/chrome-bot/infra/run.py')

  def testStopBuild(self):
    config_dict = {
        'infra_pipeline': True,
        'file_logging': False,
    }
    with self._make_logger(config_dict) as logger:
      logger.buildFinished('coconuts', Build(), [0])
      self.assertEqual(len(self.called_programs), 1)
      self.assertEqual(self.called_programs[0][0],
                       '/home/chrome-bot/infra/run.py')

  def testStopStep(self):
    config_dict = {
        'infra_pipeline': True,
        'file_logging': False,
    }
    with self._make_logger(config_dict) as logger:
      logger.stepFinished(Build(), Step(), [0])
      self.assertEqual(len(self.called_programs), 1)
      self.assertEqual(self.called_programs[0][0],
                       '/home/chrome-bot/infra/run.py')


if __name__ == '__main__':
  unittest.main()
