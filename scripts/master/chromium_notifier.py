# Copyright (c) 2006-2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A StatusReceiver module to mail someone when a step warns/fails.

Since the behavior is very similar to the MainNotifier, we simply inherit from
it and also reuse some of its methods to send emails.
"""

import time
import urllib
try:
  # Create a block to work around evil sys.modules manipulation in
  # email/__init__.py that triggers pylint false positives.
  # pylint: disable=E0611
  from email.MIMEMultipart import MIMEMultipart
  from email.MIMEText import MIMEText
  from email.Utils import formatdate
except ImportError:
  raise

from buildbot.status.builder import SUCCESS, FAILURE
from buildbot.status.mail import MailNotifier
from twisted.internet import defer
from twisted.python import log

from build_sheriffs import BuildSheriffs
import build_utils


# TODO(chase): Notifier doesn't send email on step exception, only on step
#              warnings and failures.  Email on exceptions would be really
#              nice to have.
class ChromiumNotifier(MailNotifier):
  """This is a status notifier which closes the tree upon failures.

  See builder.interfaces.IStatusReceiver to have more information about the
  parameters type."""

  _CATEGORY_SPLITTER = '|'
  _MINIMUM_DELAY_BETWEEN_ALERT = 600  # 10 minutes in seconds

  def __init__(self, reply_to=None, categories_steps=None,
      exclusions=None, forgiving_steps=None, status_header=None,
      send_to_sheriffs=False, **kwargs):
    """Constructor with following specific arguments (on top of base class').

    @type categories_steps: Dictionary of category string mapped to a list of
                            step strings.
    @param categories_steps: For each category name we can specify the steps we
                             want to check for success to keep the tree opened.
                             An empty list of steps means that we simply check
                             for results == FAILURE to close the tree. Defaults
                             to None for the dictionary, which means all
                             categories, and the empty string category can be
                             used to say all builders.

    @type exclusions: Dictionary of strings to arrays of strings.
    @param exclusions: The key is a builder name for which we want to ignore a
                       series of step names set as the value in the form of an
                       array of strings. Defaults to None.

    @type forgiving_steps: List of strings.
    @param forgiving_steps: The list of steps for which a failure email should
                            NOT be sent to the blame list.

    @type status_header: String.
    @param status_header: Formatted header used in mail message.

    @type send_to_sheriffs: Boolean.
    @param send_to_sheriffs: If true, build sheriffs are copied on emails.
    """
    # Change the default.
    kwargs.setdefault('sendToInterestedUsers', False)
    MailNotifier.__init__(self, **kwargs)

    self.reply_to = reply_to
    self.categories_steps = categories_steps
    self.exclusions = exclusions or {}
    self.forgiving_steps = forgiving_steps or []
    self.status_header = status_header
    assert self.status_header
    self.send_to_sheriffs = send_to_sheriffs
    self._last_time_mail_sent = None

  def isInterestingBuilder(self, builder_status):
    """Confirm if we are interested in this builder."""
    builder_name = builder_status.getName()
    if builder_name in self.exclusions and not self.exclusions[builder_name]:
      return False
    if not self.categories_steps or '' in self.categories_steps:
      # We don't filter per step.
      return True

    if not builder_status.category:
      return False
    # We hack categories here. This should use a different builder attribute.
    for category in builder_status.category.split(self._CATEGORY_SPLITTER):
      if category in self.categories_steps:
        return True
    return False

  def isInterestingStep(self, build_status, step_status, results):
    """Watch all steps that don't end in success."""
    return results[0] != SUCCESS

  def builderAdded(self, builder_name, builder_status):
    """Only subscribe to builders we are interested in.

    @type name:    string
    @type builder: L{buildbot.status.builder.BuilderStatus} which implements
                   L{buildbot.interfaces.IBuilderStatus}
    """
    if self.isInterestingBuilder(builder_status):
      return self  # subscribe to this builder

  def buildStarted(self, builder_name, build_status):
    """A build has started allowing us to register for stepFinished.

    @type builder_name: string
    @type build_status: L{buildbot.status.builder.BuildStatus} which implements
                        L{buildbot.interfaces.IBuildStatus}
    """
    if self.isInterestingBuilder(build_status.getBuilder()):
      return self

  def buildFinished(self, builder_name, build_status, results):
    """Must be overloaded to avoid the base class sending email."""
    pass

  def stepFinished(self, build_status, step_status, results):
    """A build step has just finished.

    @type builder_status: L{buildbot.status.builder.BuildStatus}
    @type step_status:    L{buildbot.status.builder.BuildStepStatus}
    @type results: tuple described at
                   L{buildbot.interfaces.IBuildStepStatus.getResults}
    """

    if not self.isInterestingStep(build_status, step_status, results):
      return

    builder_status = build_status.getBuilder()
    builder_name = builder_status.getName()
    steps_text = step_status.getText()
    if builder_name in self.exclusions:
      for step_text in steps_text:
        # TODO(maruel): This is wrong. We should use step_status.getName().
        if step_text in self.exclusions[builder_name]:
          return

    if not self.categories_steps:
      # No filtering on steps.
      return self.buildMessage(builder_name, build_status, results, steps_text)

    # Now get all the steps we must check for this builder.
    steps_to_check = []
    for category in builder_status.category.split(self._CATEGORY_SPLITTER):
      if category in self.categories_steps:
        steps_to_check += self.categories_steps[category]
    if '' in self.categories_steps:
      steps_to_check += self.categories_steps['']

    for step_text in steps_text:
      if step_text in steps_to_check:
        return self.buildMessage(builder_name, build_status, results,
                                 [step_text])

  def getFinishedMessage(self, dummy, builder_name, build_status, steps_text):
    """Called after being done sending the email."""
    return defer.succeed(0)

  def shouldBlameCommitters(self, steps_text):
    for step_text in steps_text:
      if step_text not in self.forgiving_steps:
        return True
    return False

  def buildMessage(self, builder_name, build_status, results, steps_text):
    """Send an email about the tree closing.

    Don't attach the patch as MailNotifier.buildMessage do.

    @type builder_name: string
    @type build_status: L{buildbot.status.builder.BuildStatus}
    @type steps_text: list of string
    """
    log.msg('About to email')
    if (self._last_time_mail_sent and self._last_time_mail_sent >
        time.time() - self._MINIMUM_DELAY_BETWEEN_ALERT):
      # Rate limit tree alerts.
      return
    self._last_time_mail_sent = time.time()

    blame_interested_users = self.shouldBlameCommitters(steps_text)
    project_name = self.master_status.getProjectName()
    revisions_list = build_utils.getAllRevisions(build_status)
    build_url = self.master_status.getURLForThing(build_status)
    waterfall_url = self.master_status.getBuildbotURL()
    status_text = self.status_header % {
        'builder': builder_name,
        'steps': ', '.join(steps_text)
    }
    blame_list = ','.join(build_status.getResponsibleUsers())
    revisions_string = ''
    latest_revision = 0
    if revisions_list:
      revisions_string = ', '.join([str(rev) for rev in revisions_list])
      latest_revision = max([rev for rev in revisions_list])
    if results[0] == FAILURE:
      result = 'failure'
    else:
      result = 'warning'

    # Generate a HTML table looking like the waterfall.
    # WARNING: Gmail ignores embedded CSS style. I don't know how to fix that so
    # meanwhile, I just won't embedded the CSS style.
    html_content = (
"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>%s</title>
</head>
<body>
  <a href="%s">%s</a><p>
  %s<p>
  <a href="%s">%s</a><p>
  Revision: %s<br>
""" % (status_text, waterfall_url, waterfall_url, status_text, build_url,
       build_url, revisions_string))

    # Only include the blame list if relevant.
    if blame_interested_users:
      html_content += "  Blame list: %s<p>\n" % blame_list

    html_content += build_utils.EmailableBuildTable(build_status, waterfall_url)
    html_content += "<p>"
    # Add the change list descriptions. getChanges() returns a tuple of
    # buildbot.changes.changes.Change
    for change in build_status.getChanges():
      html_content += change.asHTML()
    html_content += "</body>\n</html>"

    # Simpler text content for non-html aware clients.
    text_content = (
"""%s

%s

%swaterfall?builder=%s

--=>  %s  <=--

Revision: %s
Blame list: %s

Buildbot waterfall: http://build.chromium.org/
""" % (status_text,
       build_url,
       urllib.quote(waterfall_url, '/:'),
       urllib.quote(builder_name),
       status_text,
       revisions_string,
       blame_list))

    m = MIMEMultipart('alternative')
    # The HTML message, is best and preferred.
    m.attach(MIMEText(text_content, 'plain', 'iso-8859-1'))
    m.attach(MIMEText(html_content, 'html', 'iso-8859-1'))

    m['Date'] = formatdate(localtime=True)
    m['Subject'] = self.subject % {
        'result': result,
        'projectName': project_name,
        'builder': builder_name,
        'reason': build_status.getReason(),
        'revision': str(latest_revision),
    }
    m['From'] = self.fromaddr
    if self.reply_to:
      m['Reply-To'] = self.reply_to

    recipients = list(self.extraRecipients[:])
    if self.send_to_sheriffs:
      recipients.extend(BuildSheriffs.GetSheriffs())
    dl = []
    if self.sendToInterestedUsers and self.lookup and blame_interested_users:
        for u in build_status.getInterestedUsers():
          d = defer.maybeDeferred(self.lookup.getAddress, u)
          d.addCallback(recipients.append)
          dl.append(d)
    defered_object = defer.DeferredList(dl)
    defered_object.addCallback(self._gotRecipients, recipients, m)
    defered_object.addCallback(self.getFinishedMessage, builder_name,
                               build_status, steps_text)
    return defered_object
