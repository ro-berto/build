# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Subclasses of various slave command classes."""

import copy

from buildbot.steps import source
from buildbot.process import buildstep
from buildbot.steps import shell
from buildbot.status import builder


class GClient(source.Source):
  """Check out a source tree using gclient."""

  name = 'gclient'

  def __init__(self, svnurl=None, rm_timeout=None, gclient_spec=None, env=None,
               sudo_for_remove=False, gclient_deps=None, **kwargs):
    source.Source.__init__(self, **kwargs)
    if env:
      self.args['env'] = env.copy()
    self.args['rm_timeout'] = rm_timeout
    self.args['svnurl'] = svnurl
    self.args['sudo_for_remove'] = sudo_for_remove
    # linux doesn't handle spaces in command line args properly so remove them.
    # This doesn't matter for the format of the DEPS file.
    self.args['gclient_spec'] = gclient_spec.replace(' ', '')
    self.args['gclient_deps'] = gclient_deps

  def computeSourceRevision(self, changes):
    """Finds the latest revision number from the changeset that have
    triggered the build.

    This is a hook method provided by the parent source.Source class and
    default implementation in source.Source returns None. Return value of this
    method is be used to set 'revsion' argument value for startVC() method."""
    if not changes:
      return None
    def GrabRevision(c):
      """Handle revision == None or any invalid value."""
      try:
        return int(c.revision)
      except TypeError:
        return 0
    # Change revision numbers can be invalid, for a try job for instance.
    lastChange = max([GrabRevision(c) for c in changes])
    return lastChange

  def startVC(self, branch, revision, patch):
    warnings = []
    args = copy.copy(self.args)
    args['revision'] = revision
    args['branch'] = branch
    if patch:
      args['patch'] = patch
    elif args.get('patch') is None:
      del args['patch']
    cmd = buildstep.LoggedRemoteCommand('gclient', args)
    self.startCommand(cmd, warnings)

  def describe(self, done=False):
    """Tries to append the revision number to the description."""
    description = source.Source.describe(self, done)
    self.appendRevision(description)
    self.appendWebKitRevision(description)
    return description

  def appendRevision(self, description):
    """Tries to append the Chromium revision to the given description."""
    revision = None
    try:
      revision = self.getProperty('got_revision')
    except KeyError:
      # 'got_revision' doesn't exist yet, check 'revision'
      try:
        revision = self.getProperty('revision')
      except KeyError:
        pass  # neither exist, go on without revision
    if revision:
      revision = 'r%s' % revision
      # Only append revision if it's not already there.
      if not revision in description:
        description.append(revision)

  def appendWebKitRevision(self, description):
    """Tries to append the WebKit revision to the given description."""
    webkit_revision = None
    try:
      webkit_revision = self.getProperty('got_webkit_revision')
    except KeyError:
      pass
    if webkit_revision:
      webkit_revision = 'webkit r%s' % webkit_revision
      # Only append revision if it's not already there.
      if not webkit_revision in description:
        description.append(webkit_revision)

  def commandComplete(self, cmd):
    """Handles status updates from buildbot slave when the step is done.

    As a result both 'got_revision' and 'got_webkit_revision' properties will
    be set, though either may be None if it couldn't be found.
    """
    source.Source.commandComplete(self, cmd)
    if cmd.updates.has_key('got_webkit_revision'):
      got_webkit_revision = cmd.updates['got_webkit_revision'][-1]
      if got_webkit_revision:
        self.setProperty('got_webkit_revision', str(got_webkit_revision),
                         'Source')


class ProcessLogShellStep(shell.ShellCommand):
  """ Step that can process log files.

    Delegates actual processing to log_processor, which is a subclass of
    process_log.PerformanceLogParser.

    Sample usage:
    # construct class that will have no-arg constructor.
    log_processor_class = chromium_utils.PartiallyInitialize(
        process_log.GraphingPageCyclerLogProcessor,
        report_link='http://host:8010/report.html,
        output_dir='~/www')
    # We are partially constructing Step because the step final
    # initialization is done by BuildBot.
    step = chromium_utils.PartiallyInitialize(
        chromium_step.ProcessLogShellStep,
        log_processor_class)

  """
  def  __init__(self, log_processor_class=None, *args, **kwargs):
    """
    Args:
      log_processor_class: subclass of
        process_log.PerformanceLogProcessor that will be initialized and
        invoked once command was successfully completed.
    """
    self._result_text = []
    self._log_processor = None
    # If log_processor_class is not None, it should be a class.  Create an
    # instance of it.
    if log_processor_class:
      self._log_processor = log_processor_class()
    shell.ShellCommand.__init__(self, *args, **kwargs)

  def start(self):
    """Overridden shell.ShellCommand.start method.

    Adds a link for the activity that points to report ULR.
    """
    self._CreateReportLinkIfNeccessary()
    shell.ShellCommand.start(self)

  def _GetRevision(self):
    """Returns the revision number for the build.

    Result is the revision number of the latest change that went in
    while doing gclient sync. Tries 'got_revision' (from log parsing)
    then tries 'revision' (usually from forced build). If neither are
    found, will return -1 instead.
    """
    revision = None
    try:
      revision = self.build.getProperty('got_revision')
    except KeyError:
      pass  # 'got_revision' doesn't exist (yet)
    if not revision:
      try:
        revision = self.build.getProperty('revision')
      except KeyError:
        pass  # neither exist
    if not revision:
      revision = -1
    return revision

  def commandComplete(self, cmd):
    """Callback implementation that will use log process to parse 'stdio' data.
    """
    if self._log_processor:
      self._result_text = self._log_processor.Process(
          self._GetRevision(), self.getLog('stdio').getText())

  def getText(self, cmd, results):
    text_list = self.describe(True)
    if self._result_text:
      self._result_text.insert(0, '<div class="BuildResultInfo">')
      self._result_text.append('</div>')
      text_list = text_list + self._result_text
    return text_list

  def evaluateCommand(self, cmd):
    shell_result = shell.ShellCommand.evaluateCommand(self, cmd)
    log_result = None
    if self._log_processor and 'evaluateCommand' in dir(self._log_processor):
      log_result = self._log_processor.evaluateCommand(cmd)
    if shell_result is builder.FAILURE or log_result is builder.FAILURE:
      return builder.FAILURE
    if shell_result is builder.WARNINGS or log_result is builder.WARNINGS:
      return builder.WARNINGS
    return builder.SUCCESS

  def _CreateReportLinkIfNeccessary(self):
    if self._log_processor and self._log_processor.ReportLink():
      self.addURL('results', "%s" % self._log_processor.ReportLink())
