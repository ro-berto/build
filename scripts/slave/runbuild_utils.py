#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=C0323

"""Utility routines for the buildrunner (runbuild.py)."""

import os
import json
import sys

from common import chromium_utils


class LogClass(chromium_utils.RunCommandFilter):
  """Collection of methods to log via annotator or logfile."""

  def __init__(self, outstream):
    self.outstream = outstream
    chromium_utils.RunCommandFilter.__init__(self)

  def log_to_file_internal(self, chunk):
    print >>self.outstream, chunk,

  # for use with Buildbot callback updates
  def log_to_file(self, data):
    if 'stdout' in data:
      self.log_to_file_internal(data['stdout'])
    if 'header' in data:
      self.log_to_file_internal(data['header'] + '\n')

    if 'elapsed' in data:
      print >>sys.stderr, '(took %.2fs)' % float(data['elapsed'])

  # for use with RunCommand's filter_obj
  def FilterLine(self, data):
    self.log_to_file_internal(data)
    return None

  def FilterDone(self, data):
    self.log_to_file_internal(data + '\n')
    return None


def Execute(commands, step_regex, step_reject, annotate, log):
  """Given a list of shell commands, execute them sequentially.

  A command is specified as a hash with name, command, workdir, quoted_workdir,
  quoted_command, and env. quoted_workdir and _command are suitably
  shell-escaped. step_regex will filter steps by the supplied regex, while
  step_reject will reject steps based on the supplied regex. annotate will turn
  on annotator-compatible annotations per step. log is a stream to write the
  output of each command's execution.

  If any command returns with a nonzero return code, execution is aborted.

  Returns the number of successfully executed commands and whether execution was
  aborted early or not.
  """
  commands_executed = 0
  for command in commands:
    if step_regex:
      if not step_regex.search(command['name']):
        if not annotate:
          print >>sys.stderr, 'skipping step: ' + command['name']
        continue

    if step_reject:
      if step_reject.search(command['name']):
        if not annotate:
          print >>sys.stderr, 'skipping step: ' + command['name']
          continue

    if not annotate:
      print >>sys.stderr, 'running step: %s' % command['name']
    else:
      print '@@@BUILD_STEP %s@@@' % command['name']

    print >>log, '(in %s): %s' % (command['quoted_workdir'],
                                  command['quoted_command'])

    mydir = os.getcwd()
    myenv = os.environ
    os.chdir(command['workdir'])

    # python docs says this might cause leaks on FreeBSD/OSX
    for envar in command['env']:
      os.environ[envar] = command['env'][envar]

    mylogger = LogClass(log)

    ret = chromium_utils.RunCommand(command['command'],
                                    filter_obj=mylogger,
                                    print_cmd=False)
    os.chdir(mydir)
    os.environ = myenv
    commands_executed += 1
    if ret != 0:
      return commands_executed, True
  return commands_executed, False


def PropertiesToJSON(props):
  """Output a set of properties in JSON format."""
  propdict = props.asDict()
  cleandict = {}
  for k in propdict:
    cleandict[k] = propdict[k][0]

  return json.dumps(cleandict)
