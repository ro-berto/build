# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A class to mail the try bot results.
"""

try:
  # Create a block to work around evil sys.modules manipulation in
  # email/__init__.py that triggers pylint false positives.
  # pylint: disable=E0611,F0401
  from email.MIMEMultipart import MIMEMultipart
  from email.MIMEText import MIMEText
  from email.Utils import formatdate
except ImportError:
  raise

from buildbot.status import mail
from buildbot.status.builder import SUCCESS, WARNINGS, SKIPPED
from twisted.internet import defer
from twisted.python import log

from master import build_utils
# TODO(maruel): Remove me.
from master.try_job_stamp import TryJobStamp


class TryMailNotifier(mail.MailNotifier):
  def __init__(self, reply_to=None, **kwargs):
    mail.MailNotifier.__init__(self, **kwargs)
    self.reply_to = reply_to

  def buildMessage(self, name, build, results):
    """Send an email about the result. Send it as a nice HTML message."""
    log.msg('Building try job email')
    try:
      # 0.7.x
      projectName = self.master_status.getProjectName()
    except AttributeError:
      # 0.8.x
      projectName = self.master_status.getTitle()

    if isinstance(build, list):
      # buildbot 0.8.4p1
      build = build[0]
    job_stamp = build.getSourceStamp()
    build_url = self.master_status.getURLForThing(build)
    waterfall_url = self.master_status.getBuildbotURL()
    # TODO(maruel): TryJobStamp is being deleted.
    if (isinstance(job_stamp, TryJobStamp) and
        (results == SKIPPED or job_stamp.canceled)):
      status_text_html = ("Incomplete try due to another try being submitted "
                          "with same name.")
      res = "incomplete"
    elif results == SUCCESS:
      status_text_html = "You are awesome! Try succeeded!"
      res = "success"
    elif results == WARNINGS:
      status_text_html = "Try Had Warnings"
      res = "warnings"
    else:
      status_text_html = (
          'TRY FAILED<p>'
          '<strong>If you think the try slave is broken (it happens!) or tests '
          'are flaky, please REPLY to this email, don\'t ask on irc, mailing '
          'list or IM.</strong><br>'
          'Please use "rich text" replies so the links aren\'t lost.<br>'
          'It is possible that you get no reply, don\'t worry, the reply '
          'address isn\'t a blackhole.'
          '<p>'
          'Thanks!')
      res = "failure"

    info = {
        'result': res,
        'projectName': projectName,
        'builder': name,
        'reason': build.getReason(),
        'revision': job_stamp.revision,
        'timestamp': getattr(job_stamp, "timestamp", "")
    }
    subject = self.subject % info
    first_line = (
        "try %(result)s for %(reason)s on %(builder)s @ r%(revision)s" % info)

    html_params = {
        'subject': subject,
        'first_line': first_line,
        'waterfall_url': waterfall_url,
        'status_text_html': status_text_html,
        'build_url': build_url,
        'slave': build.getSlavename(),
    }

    # Generate a HTML table looking like the waterfall.
    # WARNING: Gmail ignores embedded CSS style unless it's inline.
    html_content = (
"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>%(subject)s</title>
</head>
<body style="font-family: Verdana, Cursor; font-size: 10px;">
  %(first_line)s<p>
  <a href="%(waterfall_url)s">%(waterfall_url)s</a><p>
  %(status_text_html)s<p>
  <a href="%(build_url)s">%(build_url)s</a><br>
  slave: %(slave)s<br>
    """) % html_params

    html_content += build_utils.EmailableBuildTable(build, waterfall_url)
    html_content += """<br>
FAQ: <a href="http://sites.google.com/a/chromium.org/dev/developers/testing/try-server-usage">
http://sites.google.com/a/chromium.org/dev/developers/testing/try-server-usage</a><br>
</body>
</html>
"""

    m = MIMEMultipart()
    m.attach(MIMEText(html_content, 'html', 'iso-8859-1'))
    m['Date'] = formatdate(localtime=True)
    m['Subject'] = subject
    m['From'] = self.fromaddr
    if self.reply_to:
      m['Reply-To'] = self.reply_to
    # now, who is this message going to?
    dl = []
    recipients = self.extraRecipients[:]
    if self.sendToInterestedUsers and self.lookup:
      for u in build.getInterestedUsers():
        d = defer.maybeDeferred(self.lookup.getAddress, u)
        d.addCallback(recipients.append)
        dl.append(d)
    d = defer.DeferredList(dl)
    d.addCallback(self._gotRecipients, recipients, m)
    return d
