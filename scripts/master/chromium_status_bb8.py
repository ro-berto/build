# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for buildbot.status module modifications. """

import urllib

import buildbot
import buildbot.util
import buildbot.status.web.base as base
import buildbot.status.web.console as console
import buildbot.status.web.waterfall as waterfall
import buildbot.status.builder as statusbuilder

from twisted.python import log
from twisted.python import components
from twisted.web import html
from zope.interface import declarations

# pylint: disable=F0401
import jinja2
import urllib

from master.third_party import stats_bb8 as stats

def _ShortRev(rev):
  """A simplified version of the default 'shortrev' macro used in some jinja
  templates.  This version isn't actually used for template processing; rather,
  it's used to shorten revision names in the waterfall view, which doesn't make
  much use of jinja templates."""

  shortrev = rev[:12]
  if len(shortrev) < len(rev):
    shortrev += '...'
  return shortrev


class BuildBox(waterfall.BuildBox):
  """Build the yellow starting-build box for a waterfall column.

  This subclass adds the builder's name to the box.  It's otherwise identical
  to the parent class, apart from naming syntax.
  """
  def getBox(self, req):
    b = self.original
    number = b.getNumber()
    url = base.path_to_build(req, b)
    reason = b.getReason()
    if reason:
      text = (('%s<br><a href="%s">Build %d</a><br>%s')
              % (b.getBuilder().getName(), url, number, html.escape(reason)))
    else:
      text = ('%s<br><a href="%s">Build %d</a>'
              % (b.getBuilder().getName(), url, number))
    color = "yellow"
    class_ = "start"
    if b.isFinished() and not b.getSteps():
      # the steps have been pruned, so there won't be any indication
      # of whether it succeeded or failed. Color the box red or green
      # to show its status
      color = b.getColor()
      class_ = base.build_get_class(b)
    return base.Box([text], color=color, class_="BuildStep " + class_)

# First unregister ICurrentBox registered by waterfall.py.
# We won't be able to unregister it without messing with ALLOW_DUPLICATES
# in twisted.python.components. Instead, work directly with adapter to
# remove the component:
origInterface = statusbuilder.BuildStatus
origInterface = declarations.implementedBy(origInterface)
registry = components.getRegistry()
registry.register([origInterface], base.IBox, '', None)
components.registerAdapter(BuildBox, statusbuilder.BuildStatus, base.IBox)


class ChromiumStepBox(waterfall.StepBox):
  """Apply _ShortRev to the revision numbers in 'update' status boxes."""

  def getBox(self, req):
    text = self.original.getText()
    if len(text) > 1 and (text[0] == 'update' or text[0] == 'updating'):
      text[1] = _ShortRev(text[1])
    return waterfall.StepBox.getBox(self, req)

origInterface = statusbuilder.BuildStepStatus
origInterface = declarations.implementedBy(origInterface)
registry = components.getRegistry()
registry.register([origInterface], base.IBox, '', None)
components.registerAdapter(ChromiumStepBox,
                           statusbuilder.BuildStepStatus,
                           base.IBox)


class ChromiumChangeBox(buildbot.status.web.changes.ChangeBox):
  """Apply _ShortRev to the change boxes in the left-hand column."""

  def getBox(self, req):
    url = req.childLink("../changes/%d" % self.original.number)
    template = \
        req.site.buildbot_service.templates.get_template("change_macros.html")
    who = '@'.join(self.original.getShortAuthor().split('@')[0:2])
    revision = _ShortRev(self.original.revision)
    text = template.module.box_contents(url=url,
                                        who=who,
                                        pageTitle=self.original.comments,
                                        revision=revision)
    return base.Box([text], class_="Change")

origInterface = buildbot.changes.changes.Change
origInterface = declarations.implementedBy(origInterface)
registry = components.getRegistry()
registry.register([origInterface], base.IBox, '', None)
components.registerAdapter(ChromiumChangeBox,
                           buildbot.changes.changes.Change,
                           base.IBox)


class HorizontalOneBoxPerBuilder(base.HtmlResource):
  """This shows a table with one cell per build. The color of the cell is
  the state of the most recently completed build. If there is a build in
  progress, the ETA is shown in table cell. The table cell links to the page
  for that builder. They are layed out, you guessed it, horizontally.

  builder=: show only builds for this builder. Multiple builder= arguments
            can be used to see builds from any builder in the set. If no
            builder= is given, shows them all.
  """

  # pylint: disable=W0221
  def content(self, request, cxt):
    status = self.getStatus(request)
    builders = request.args.get("builder", status.getBuilderNames())
    cxt_builders = []
    for builder_name in builders:
      try:
        builder_status = status.getBuilder(builder_name)
      except KeyError:
        log.msg('status.getBuilder(%r) failed' % builder_name)
        continue
      classname = base.ITopBox(builder_status).getBox(request).class_
      title = builder_name
      url = (base.path_to_root(request) + "waterfall?builder=" +
              urllib.quote(builder_name, safe=''))
      cxt_builders.append({'outcome': classname,
                           'name': title,
                           'url': url })
    cxt['builders'] = cxt_builders
    templates = request.site.buildbot_service.templates
    template = templates.get_template("horizontal_one_box_per_build.html")
    data = template.render(cxt)
    return data


class WaterfallStatusResource(waterfall.WaterfallStatusResource):
  """Don't serve up waterfall pages for builds older than the threshold."""

  # pylint: disable=W0221
  def content(self, request, cxt):
    cutoff = buildbot.util.now() - (60 * 60 * 24 * 2)
    last_time = int(request.args.get('last_time', [0])[0])
    if (last_time and
        last_time < cutoff and
        not request.args.get('force', [False])[0]):
      return """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Buildbot Waterfall Error</title></head>
  <body><p>To prevent DOS of the waterfall, heavy requests like this
are blocked. If you know what you are doing, ask a Chromium trooper
how to bypass the protection.</p></body></html>
"""
    # pylint: disable=E1121
    return waterfall.WaterfallStatusResource.content(self, request, cxt)


class ConsoleStatusResource(console.ConsoleStatusResource):
  """Class that overrides default behavior of console.ConsoleStatusResource."""

  def displayPage(self, *args, **kwargs):
    """Strip the 'who' parameter down to a valid e-mail address."""
    result = console.ConsoleStatusResource.displayPage(self, *args, **kwargs)
    for revision in result['revisions']:
      if 'who' not in revision:
        continue
      revision['who'] = '@'.join(revision['who'].split('@')[0:2])
    return result


def SetupChromiumPages(webstatus):
  """Add customizations to default web reporting."""

  def _tick_filter(n, stride):
    n = ((n / stride) + 1) * stride
    return filter(lambda x: x % (n/stride) == 0, range(n+1))

  webstatus.templates.filters.update(
      { 'longrev': lambda x, y: jinja2.escape(unicode(x)),
        'numstrip': lambda x: jinja2.escape(unicode(x.lstrip('0123456789'))),
        'quote': urllib.quote,
        'max': lambda x: reduce(max, x, 0),
        'average': lambda x: float(sum(x)) / float(max(len(x), 1)),
        'ticks': lambda x: ["{v:%d}" % y for y in _tick_filter(x, 12)],
        'fixname': lambda x: x.translate(None, ' -():') })

  webstatus.putChild("stats", stats.StatsStatusResource())
  webstatus.putChild("waterfall", WaterfallStatusResource())
  webstatus.putChild("console", ConsoleStatusResource(
      orderByTime=webstatus.orderConsoleByTime))
  webstatus.putChild("grid", ConsoleStatusResource())
  webstatus.putChild("tgrid", ConsoleStatusResource())
  webstatus.putChild("horizontal_one_box_per_builder",
                     HorizontalOneBoxPerBuilder())
  return webstatus
