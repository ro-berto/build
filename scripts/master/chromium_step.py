# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Subclasses of various slave command classes."""

import copy
import re
import time

from twisted.python import log

from buildbot import interfaces, util
from buildbot.process import buildstep
from buildbot.process.properties import WithProperties
from buildbot.status import builder
from buildbot.steps import shell
from buildbot.steps import source


def change_to_revision(c):
  """Handle revision == None or any invalid value."""
  try:
    return int(str(c.revision).split('@')[-1])
  except (ValueError, TypeError):
    return 0


class GClient(source.Source):
  """Check out a source tree using gclient."""

  name = 'update'

  def __init__(self, svnurl=None, rm_timeout=None, gclient_spec=None, env=None,
               sudo_for_remove=False, gclient_deps=None, gclient_nohooks=False,
               no_gclient_branch=False, gclient_transitive=False,
               primary_repo=None, gclient_jobs=None, **kwargs):
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
    self.args['gclient_nohooks'] = gclient_nohooks
    self.args['no_gclient_branch'] = no_gclient_branch
    self.args['gclient_transitive'] = gclient_transitive
    self.args['primary_repo'] = primary_repo or ''
    self.args['gclient_jobs'] = gclient_jobs

  def computeSourceRevision(self, changes):
    """Finds the latest revision number from the changeset that have
    triggered the build.

    This is a hook method provided by the parent source.Source class and
    default implementation in source.Source returns None. Return value of this
    method is be used to set 'revsion' argument value for startVC() method."""
    if not changes:
      return None
    # Change revision numbers can be invalid, for a try job for instance.
    # TODO(maruel): Make this work for git hash.
    lastChange = max([change_to_revision(c) for c in changes])
    return lastChange

  def startVC(self, branch, revision, patch):
    warnings = []
    args = copy.copy(self.args)
    wk_revision = revision
    try:
      # parent_wk_revision might be set, but empty.
      if self.getProperty('parent_wk_revision'):
        wk_revision = self.getProperty('parent_wk_revision')
    except KeyError:
      pass
    nacl_revision = revision
    try:
      # parent_nacl_revision might be set, but empty.
      if self.getProperty('parent_got_nacl_revision'):
        nacl_revision = self.getProperty('parent_got_nacl_revision')
    except KeyError:
      pass
    try:
      # parent_cr_revision might be set, but empty.
      if self.getProperty('parent_cr_revision'):
        revision = 'src@' + self.getProperty('parent_cr_revision')
    except KeyError:
      pass
    self.setProperty('primary_repo', args['primary_repo'], 'Source')
    args['revision'] = revision
    args['branch'] = branch
    if args.get('gclient_spec'):
      args['gclient_spec'] = args['gclient_spec'].replace(
          '$$WK_REV$$', str(wk_revision or ''))
      args['gclient_spec'] = args['gclient_spec'].replace(
          '$$NACL_REV$$', str(nacl_revision or ''))
    if patch:
      args['patch'] = patch
    elif args.get('patch') is None:
      del args['patch']
    cmd = buildstep.LoggedRemoteCommand('gclient', args)
    self.startCommand(cmd, warnings)

  def describe(self, done=False):
    """Tries to append the revision number to the description."""
    description = source.Source.describe(self, done)
    self.appendChromeRevision(description)
    self.appendWebKitRevision(description)
    self.appendNaClRevision(description)
    self.appendV8Revision(description)
    return description

  def appendChromeRevision(self, description):
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
      # TODO: Right now, 'no_gclient_branch' is a euphemism for 'git', but we
      # probably ought to be explicit about this switch.
      if not self.args['no_gclient_branch']:
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

  def appendNaClRevision(self, description):
    """Tries to append the NaCl revision to the given description."""
    nacl_revision = None
    try:
      nacl_revision = self.getProperty('got_nacl_revision')
    except KeyError:
      pass
    if nacl_revision:
      nacl_revision = 'nacl r%s' % nacl_revision
      # Only append revision if it's not already there.
      if not nacl_revision in description:
        description.append(nacl_revision)

  def appendV8Revision(self, description):
    """Tries to append the V8 revision to the given description."""
    v8_revision = None
    try:
      v8_revision = self.getProperty('got_v8_revision')
    except KeyError:
      pass
    if v8_revision:
      v8_revision = 'v8 r%s' % v8_revision
      # Only append revision if it's not already there.
      if not v8_revision in description:
        description.append(v8_revision)

  def commandComplete(self, cmd):
    """Handles status updates from buildbot slave when the step is done.

    As a result 'got_revision', 'got_webkit_revision', 'got_nacl_revision' as
    well as 'got_v8_revision' properties will be set, though either may be None
    if it couldn't be found.
    """
    source.Source.commandComplete(self, cmd)
    primary_repo = self.args.get('primary_repo', '')
    primary_revision_key = 'got_' + primary_repo + 'revision'
    if cmd.updates.has_key(primary_revision_key):
      got_revision = cmd.updates[primary_revision_key][-1]
      if got_revision:
        self.setProperty('got_revision', str(got_revision), 'Source')
    if cmd.updates.has_key('got_webkit_revision'):
      got_webkit_revision = cmd.updates['got_webkit_revision'][-1]
      if got_webkit_revision:
        self.setProperty('got_webkit_revision', str(got_webkit_revision),
                         'Source')
    if cmd.updates.has_key('got_nacl_revision'):
      got_nacl_revision = cmd.updates['got_nacl_revision'][-1]
      if got_nacl_revision:
        self.setProperty('got_nacl_revision', str(got_nacl_revision),
                         'Source')
    if cmd.updates.has_key('got_v8_revision'):
      got_v8_revision = cmd.updates['got_v8_revision'][-1]
      if got_v8_revision:
        self.setProperty('got_v8_revision', str(got_v8_revision),
                         'Source')


class BuilderStatus(object):
  # Order in asceding severity.
  BUILD_STATUS_ORDERING = [
      builder.SUCCESS,
      builder.WARNINGS,
      builder.FAILURE,
      builder.EXCEPTION,
  ]

  @classmethod
  def combine(cls, a, b):
    """Combine two status, favoring the more severe."""
    if a not in cls.BUILD_STATUS_ORDERING:
      return b
    if b not in cls.BUILD_STATUS_ORDERING:
      return a
    a_rank = cls.BUILD_STATUS_ORDERING.index(a)
    b_rank = cls.BUILD_STATUS_ORDERING.index(b)
    pick = max(a_rank, b_rank)
    return cls.BUILD_STATUS_ORDERING[pick]


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
    try:
      repo = self.build.getProperty('primary_repository')
      if not repo:
        repo = ''
    except KeyError:
      repo = ''
    revision = None
    try:
      revision = self.build.getProperty('got_' + repo + 'revision')
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

  def _GetWebkitRevision(self):
    """Returns the webkit revision number for the build.
    """
    try:
      return self.build.getProperty('got_webkit_revision')
    except KeyError:
      return None

  def _GetBuildProperty(self):
    """Returns a dict with the channel and version."""
    build_properties = {}
    try:
      channel = self.build.getProperty('channel')
      if channel:
        build_properties.setdefault('channel', channel)
    except KeyError:
      pass  # 'channel' doesn't exist.
    try:
      version = self.build.getProperty('version')
      if version:
        build_properties.setdefault('version', version)
    except KeyError:
      pass  # 'version' doesn't exist.
    return build_properties

  def commandComplete(self, cmd):
    """Callback implementation that will use log process to parse 'stdio' data.
    """
    if self._log_processor:
      self._result_text = self._log_processor.Process(
          self._GetRevision(), self.getLog('stdio').getText(),
          self._GetBuildProperty(), webkit_revision=self._GetWebkitRevision())

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
    return BuilderStatus.combine(shell_result, log_result)

  def _CreateReportLinkIfNeccessary(self):
    if self._log_processor and self._log_processor.ReportLink():
      self.addURL('results', "%s" % self._log_processor.ReportLink())


class AnnotationObserver(buildstep.LogLineObserver):
  """This class knows how to understand annotations.

  Here are a list of the currently supported annotations:

  @@@BUILD_STEP <stepname>@@@
  Add a new step <stepname>. End the current step, marking with last available
  status.

  @@@STEP_LINK@<label>@<url>@@@
  Add a link with label <label> linking to <url> to the current stage.

  @@@STEP_WARNINGS@@@
  Mark the current step as having warnings (oragnge).

  @@@STEP_FAILURE@@@
  Mark the current step as having failed (red).

  @@@STEP_EXCEPTION@@@
  Mark the current step as having exceptions (magenta).

  @@@STEP_LOG_LINE@<label>@<line>@@@
  Add a log line to a log named <label>. Multiple lines can be added.

  @@@STEP_LOG_END@<label>@@@
  Finalizes a log added by STEP_LOG_LINE and calls addCompleteLog().

  @@@STEP_CLEAR@@@
  Reset the text description of the current step.

  @@@STEP_SUMMARY_CLEAR@@@
  Reset the text summary of the current step.

  @@@STEP_TEXT@<msg>@@@
  Append <msg> to the current step text.

  @@@STEP_SUMMARY_TEXT@<msg>@@@
  Append <msg> to the step summary (appears on top of the waterfall).

  @@@HALT_ON_FAILURE@@@
  Halt if exception or failure steps are encountered (default is not).

  @@@HONOR_ZERO_RETURN_CODE@@@
  Honor the return code being zero (success), even if steps have other results.

  Deprecated annotations:
  TODO(bradnelson): drop these when all users have been tracked down.

  @@@BUILD_WARNINGS@@@
  Equivalent to @@@STEP_WARNINGS@@@

  @@@BUILD_FAILED@@@
  Equivalent to @@@STEP_FAILURE@@@

  @@@BUILD_EXCEPTION@@@
  Equivalent to @@@STEP_EXCEPTION@@@

  @@@link@<label>@<url>@@@
  Equivalent to @@@STEP_LINK@<label>@<url>@@@
  """

  def __init__(self, command=None, *args, **kwargs):
    buildstep.LogLineObserver.__init__(self, *args, **kwargs)
    self.annotated_logs = {}
    self.command = command
    self.sections = []
    self.annotate_status = builder.SUCCESS
    self.halt_on_failure = False
    self.honor_zero_return_code = False

  def initialSection(self):
    if self.sections:
      return
    # Add a log section for output before the first section heading.
    preamble = self.command.addLog('preamble')
    self.sections.append({
        'name': 'preamble',
        'step': self.command.step_status.getBuild().steps[-1],
        'log': preamble,
        'status': builder.SUCCESS,
        'links': [],
        'step_summary_text': [],
        'step_text': [],
        'started': util.now(),
    })

  def fixupLast(self, status=None):
    # Potentially start initial section here, as initial section might have
    # no output at all.
    self.initialSection()

    last = self.sections[-1]
    # Update status if set as an argument.
    if status is not None:
      last['status'] = status
    # Final update of text.
    self.updateText()
    # Add timing info.
    last['ended'] = last.get('ended', util.now())
    started = last['started']
    ended = last['ended']
    msg = '\n\n' + '-' * 80 + '\n'
    msg += '\n'.join([
        'started: %s' % time.ctime(started),
        'ended: %s' % time.ctime(ended),
        'duration: %s' % util.formatInterval(ended - started),
        '',  # So we get a final \n
    ])
    last['log'].addHeader(msg)
    # Change status (unless handling the preamble).
    if len(self.sections) != 1:
      last['step'].stepFinished(last['status'])
    # Finish log.
    last['log'].finish()

  def errLineReceived(self, line):
    self.handleOutputLine(line)

  def outLineReceived(self, line):
    self.handleOutputLine(line)

  # Override logChunk to intercept headers and to prevent more than one line's
  # worth of data from being processed in a chunk, so we can direct incomplete
  # chunks to the right sub-log (so we get output promptly and completely).
  def logChunk(self, build, step, logmsg, channel, text):
    for line in text.splitlines(True):
      if channel == interfaces.LOG_CHANNEL_STDOUT:
        self.outReceived(line)
      elif channel == interfaces.LOG_CHANNEL_STDERR:
        self.errReceived(line)
      elif channel == interfaces.LOG_CHANNEL_HEADER:
        self.headerReceived(line)

  def outReceived(self, data):
    buildstep.LogLineObserver.outReceived(self, data)
    if self.sections:
      self.sections[-1]['log'].addStdout(data)

  def errReceived(self, data):
    buildstep.LogLineObserver.errReceived(self, data)
    if self.sections:
      self.sections[-1]['log'].addStderr(data)

  def headerReceived(self, data):
    if self.sections:
      if self.sections[-1]['log'].finished:
        # Silently discard message when a log is marked as finished.
        # TODO(maruel): Fix race condition?
        log.msg(
            'Received data unexpectedly on a finished build step log: %r' %
            data)
      else:
        self.sections[-1]['log'].addHeader(data)

  def updateStepStatus(self, status):
    """Update current step status and annotation status based on a new event."""
    self.annotate_status = BuilderStatus.combine(self.annotate_status, status)
    last = self.sections[-1]
    last['status'] = BuilderStatus.combine(last['status'], status)
    if self.halt_on_failure and last['status'] in [
        builder.FAILURE, builder.EXCEPTION]:
      self.fixupLast()
      self.command.finished(last['status'])

  def updateText(self):
    # Don't update the main phase's text.
    if len(self.sections) == 1:
      return

    last = self.sections[-1]

    # Reflect step status in text2.
    if last['status'] == builder.EXCEPTION:
      result = ['exception', last['name']]
    elif last['status'] == builder.FAILURE:
      result = ['failed', last['name']]
    else:
      result = []

    last['step'].setText([last['name']] + last['step_text'])
    last['step'].setText2(result + last['step_summary_text'])

  def handleOutputLine(self, line):
    """This is called once with each line of the test log."""
    # Add \n if not there, which seems to be the case for log lines from
    # windows agents, but not others.
    if not line.endswith('\n'):
      line += '\n'
    # Handle initial setup here, as step_status might not exist yet at init.
    self.initialSection()

    # Support: @@@STEP_LOG_LINE@<label>@<line>@@@ (add log to step)
    # Appends a line to the log's array. When STEP_LOG_END is called,
    # that will finalize the log and call addCompleteLog().
    m = re.match('^@@@STEP_LOG_LINE@(.*)@(.*)@@@', line)
    if m:
      log_label = m.group(1)
      log_line = m.group(2)
      if log_label in self.annotated_logs:
        self.annotated_logs[log_label] += [log_line]
      else:
        self.annotated_logs[log_label] = [log_line]

    # Support: @@@STEP_LOG_END@<label>@<line>@@@ (finalizes log to step)
    m = re.match('^@@@STEP_LOG_END@(.*)@@@', line)
    if m:
      log_label = m.group(1)
      if log_label in self.annotated_logs:
        log_text = '\n'.join(self.annotated_logs[log_label])
      else:
        log_text = ''
      self.command.addCompleteLog(log_label, log_text)

    # Support: @@@STEP_LINK@<name>@<url>@@@ (emit link)
    # Also support depreceated @@@link@<name>@<url>@@@
    m = re.match('^@@@STEP_LINK@(.*)@(.*)@@@', line)
    if not m:
      m = re.match('^@@@link@(.*)@(.*)@@@', line)
    if m:
      link_label = m.group(1)
      link_url = m.group(2)
      self.sections[-1]['links'].append((link_label, link_url))
      self.sections[-1]['step'].addURL(link_label, link_url)
    # Support: @@@STEP_WARNINGS@@@ (warn on a stage)
    # Also support deprecated @@@BUILD_WARNINGS@@@
    if (line.startswith('@@@STEP_WARNINGS@@@') or
        line.startswith('@@@BUILD_WARNINGS@@@')):
      self.updateStepStatus(builder.WARNINGS)
    # Support: @@@STEP_FAILURE@@@ (fail a stage)
    # Also support deprecated @@@BUILD_FAILED@@@
    if (line.startswith('@@@STEP_FAILURE@@@') or
        line.startswith('@@@BUILD_FAILED@@@')):
      self.updateStepStatus(builder.FAILURE)
    # Support: @@@STEP_EXCEPTION@@@ (exception on a stage)
    # Also support deprecated @@@BUILD_FAILED@@@
    if (line.startswith('@@@STEP_EXCEPTION@@@') or
        line.startswith('@@@BUILD_EXCEPTION@@@')):
      self.updateStepStatus(builder.EXCEPTION)
    # Support: @@@HALT_ON_FAILURE@@@ (halt if a step fails immediately)
    if line.startswith('@@@HALT_ON_FAILURE@@@'):
      self.halt_on_failure = True
    # Support: @@@HONOR_ZERO_RETURN_CODE@@@ (succeed on 0 return, even if some
    #     steps have failed)
    if line.startswith('@@@HONOR_ZERO_RETURN_CODE@@@'):
      self.honor_zero_return_code = True
    # Support: @@@STEP_CLEAR@@@ (reset step description)
    if line.startswith('@@@STEP_CLEAR@@@'):
      self.sections[-1]['step_text'] = []
      self.updateText()
    # Support: @@@STEP_SUMMARY_CLEAR@@@ (reset step summary)
    if line.startswith('@@@STEP_SUMMARY_CLEAR@@@'):
      self.sections[-1]['step_summary_text'] = []
      self.updateText()
    # Support: @@@STEP_TEXT@<msg>@@@
    m = re.match('^@@@STEP_TEXT@(.*)@@@', line)
    if m:
      self.sections[-1]['step_text'].append(m.group(1))
      self.updateText()
    # Support: @@@STEP_SUMMARY_TEXT@<msg>@@@
    m = re.match('^@@@STEP_SUMMARY_TEXT@(.*)@@@', line)
    if m:
      self.sections[-1]['step_summary_text'].append(m.group(1))
      self.updateText()
    # Support: @@@BUILD_STEP <step_name>@@@ (start a new section)
    m = re.match('^@@@BUILD_STEP (.*)@@@', line)
    if m:
      step_name = m.group(1)
      # Ignore duplicate consecutive step labels (for robustness).
      if step_name != self.sections[-1]['name']:
        # Finish up last section.
        self.fixupLast()
        # Add new one.
        step = self.command.step_status.getBuild().addStepWithName(step_name)
        step.stepStarted()
        step.setText([step_name])
        stdio = step.addLog('stdio')
        self.sections.append({
            'name': step_name,
            'step': step,
            'log': stdio,
            'status': builder.SUCCESS,
            'links': [],
            'step_summary_text': [],
            'step_text': [],
            'started': util.now(),
        })

  def handleReturnCode(self, return_code):
    # Treat all non-zero return codes as failure.
    # We could have a special return code for warnings/exceptions, however,
    # this might conflict with some existing use of a return code.
    # Besides, applications can always intercept return codes and emit
    # STEP_* tags.
    if return_code == 0:
      self.fixupLast()
      if self.honor_zero_return_code:
        self.annotate_status = builder.SUCCESS
    else:
      self.annotate_status = builder.FAILURE
      self.fixupLast(builder.FAILURE)


class AnnotatedCommand(ProcessLogShellStep):
  """Buildbot command that knows how to display annotations."""

  def __init__(self, *args, **kwargs):
    # Inject standard tags into the environment.
    env = {
        'BUILDBOT_BLAMELIST': WithProperties('%(blamelist:-[])s'),
        'BUILDBOT_BRANCH': WithProperties('%(branch:-None)s'),
        'BUILDBOT_BUILDERNAME': WithProperties('%(buildername:-None)s'),
        'BUILDBOT_BUILDNUMBER': WithProperties('%(buildnumber:-None)s'),
        'BUILDBOT_CLOBBER': WithProperties('%(clobber:+1)s'),
        'BUILDBOT_GOT_REVISION': WithProperties('%(got_revision:-None)s'),
        'BUILDBOT_REVISION': WithProperties('%(revision:-None)s'),
        'BUILDBOT_SCHEDULER': WithProperties('%(scheduler:-None)s'),
        'BUILDBOT_SLAVENAME': WithProperties('%(slavename:-None)s'),
    }
    # Apply the passed in environment on top.
    old_env = kwargs.get('env')
    if not old_env:
      old_env = {}
    env.update(old_env)
    # Change passed in args (ok as a copy is made internally).
    kwargs['env'] = env

    ProcessLogShellStep.__init__(self, *args, **kwargs)
    self.script_observer = AnnotationObserver(self)
    self.addLogObserver('stdio', self.script_observer)

  def interrupt(self, reason):
    self.script_observer.fixupLast(builder.EXCEPTION)
    return ProcessLogShellStep.interrupt(self, reason)

  def evaluateCommand(self, cmd):
    observer_result = self.script_observer.annotate_status
    # Check if ProcessLogShellStep detected a failure or warning also.
    log_processor_result = ProcessLogShellStep.evaluateCommand(self, cmd)
    return BuilderStatus.combine(observer_result, log_processor_result)

  def commandComplete(self, cmd):
    self.script_observer.handleReturnCode(cmd.rc)
    return ProcessLogShellStep.commandComplete(self, cmd)
