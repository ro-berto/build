# Copyright (c) 2006-2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Mixed bag of anything."""

import re

from twisted.python import log
from buildbot.status.web.base import IBox


def getAllRevisions(build):
  """Helper method to extract all revisions associated to a build.

  Args:
    build: The build we want to extract the revisions of.

  Returns:
    A list of revision numbers.
  """
  source_stamp = build.getSourceStamp()
  if source_stamp and source_stamp.changes:
    return [change.revision for change in source_stamp.changes]


def getLatestRevision(build):
  """Helper method to extract the latest revision associated to a build.

  Args:
    build: The build we want to extract the latest revision of.

  Returns:
    The latest revision of that build, or None, if none.
  """
  revisions = getAllRevisions(build)
  if revisions:
    return max(revisions)


def SplitPath(projects, path):
  """Common method to split SVN path into branch and filename sections.

  Since we have multiple projects, we announce project name as a branch
  so that schedulers can be configured to kick off builds based on project
  names.

  Args:
    projects: array containing modules we are interested in. It should
      be mapping to first directory of the change file.
    path: Base SVN path we will be polling.

  More details can be found at:
    http://buildbot.net/repos/release/docs/buildbot.html#SVNPoller.
  """
  pieces = path.split('/')
  if pieces[0] in projects:
    # announce project name as a branch
    branch = pieces.pop(0)
    return (branch, '/'.join(pieces))
  # not in projects, ignore
  return None


# Extracted from
# http://src.chromium.org/svn/trunk/tools/buildbot/master.chromium/public_html/buildbot.css
DEFAULT_STYLES = {
  'BuildStep': '',
  'start': ('color: #666666; background-color: #fffc6c;'
            'border-color: #C5C56D;'),
  'success': ('color: #FFFFFF; background-color: #8fdf5f; '
              'border-color: #4F8530;'),
  'failure': ('color: #FFFFFF; background-color: #e98080; '
              'border-color: #A77272;'),
  'warnings': ('color: #FFFFFF; background-color: #ffc343; '
               'border-color: #C29D46;'),
  'exception': ('color: #FFFFFF; background-color: #e0b0ff; '
                'border-color: #ACA0B3;'),
  'offline': ('color: #FFFFFF; background-color: #e0b0ff; '
              'border-color: #ACA0B3;'),
}

def EmailableBuildTable(build_status, waterfall_url, styles=None):
  """Convert a build_status into a html table that can be sent by email.

  That means the CSS style must be inline."""
  class DummyObject(object):
    pass

  def GenBox(item):
    """Generates a box for one build step."""
    # Fix the url root.
    box_text = IBox(item).getBox(request).td(align='center').replace(
                   'href="builders/',
                   'href="' + waterfall_url + 'builders/')
    # Convert CSS classes to inline style.
    match = re.search(r"class=\"([^\"]*)\"", box_text)
    if match:
      css_class_text = match.group(1)
      css_classes = css_class_text.split()
      not_found = [c for c in css_classes if c not in styles]
      css_classes = [c for c in css_classes if c in styles]
      if len(not_found):
        log.msg('CSS classes couldn\'t be converted in inline style in '
                'email: %s' % str(not_found))
      inline_styles = ' '.join([styles[c] for c in css_classes])
      box_text = box_text.replace('class="%s"' % css_class_text,
                                  'style="%s"' % inline_styles)
    else:
      log.msg('Couldn\'t find the class attribute')
    return '<tr>%s</tr>\n' % box_text

  styles = styles or DEFAULT_STYLES
  request = DummyObject()
  request.prepath = None

  # With a hack to fix the url root.
  build_boxes = [GenBox(build_status)]
  build_boxes.extend([GenBox(step) for step in build_status.getSteps()
                      if step.isStarted() and step.getText()])
  table_content = ''.join(build_boxes)
  return (('<table style="border-spacing: 1px 1px; font-weight: bold; '
           'padding: 3px 0px 3px 0px; text-align: center;">\n') +
          table_content +
          '</table>\n')
