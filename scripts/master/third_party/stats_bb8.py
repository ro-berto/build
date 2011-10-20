import urllib

from buildbot.status import builder
from buildbot.status.web.base import HtmlResource

class StatsBuilderStatusResource(HtmlResource):
  def __init__(self, builder_status):
    HtmlResource.__init__(self)
    self.builder_status = builder_status

  def getBuilderVariables(self, cxt):
    # 1. build time over 300 builds or average 5 weeks
    # 2. pie chart, success failures
    # 3. pie chart, which steps fails the most
    # 4. 1 graph per step showing last 300 builds timing, or average 5 weeks.
    # click on a graph makes it go bigger.
    buildTimes = []
    stepTimes = {}
    numberOfSuccess = 0
    numberOfFailures = 0
    failingSteps = {}

    build = self.builder_status.getBuild(-1) or self.builder_status.getBuild(-2)

    while build and numberOfSuccess + numberOfFailures < 300:
      if not build.isFinished():
        build = build.getPreviousBuild()
        continue

      if build.getResults() == builder.SUCCESS or \
         build.getResults() == builder.WARNINGS:
        (start, end) = build.getTimes()
        buildTimes.append(end-start)
        numberOfSuccess += 1
      else:
        numberOfFailures += 1

      for step in build.getSteps():
        stepName = step.getName().translate(None, '- /[]{}():')
        stepTime = stepTimes.setdefault(stepName, [])
        failCount = failingSteps.setdefault(stepName, 0)
        (result, output) = step.getResults()
        if result == builder.SUCCESS or result == builder.WARNINGS:
          (start, end) = step.getTimes()
          elapsed = end - start
          stepTime.append(elapsed)
        if result == builder.FAILURE:
          failingSteps[stepName] = failCount + 1

      build = build.getPreviousBuild()

    # Iteration was latest->earliest; reverse data
    buildTimes.reverse()
    for v in stepTimes.itervalues():
      v.reverse()

    slowest = reduce(max, [ reduce(max, t, 0) for t in stepTimes.values() ], 0)
    timeRange = slowest + 1
    yTicks = '[%s]' % ', '.join(["{v:%d}" % i for i in range(timeRange+1)])

    cxt['builder_status'] = self.builder_status
    cxt['buildTimes'] = [ float(i) / 60.0 for i in buildTimes ]
    cxt['failingSteps'] = failingSteps
    cxt['stepTimes'] = stepTimes
    cxt['numberOfSuccess'] = numberOfSuccess
    cxt['numberOfFailures'] = numberOfFailures
    cxt['yTicks'] = yTicks
    cxt['timeRange'] = timeRange
    cxt['colorMap'] = { 'compile': 1, 'update': 1 };

  def content(self, request, cxt):
    self.getBuilderVariables(cxt)
    templates = request.site.buildbot_service.templates
    template = templates.get_template("builder_stats.html")
    return template.render(cxt)


class StatsStatusResource(HtmlResource):
  def __init__(self, allowForce=True, css=None):
    HtmlResource.__init__(self)

    self.status = None
    self.control = None
    self.changemaster = None
    self.allowForce = allowForce
    self.css = css

  def getMainVariables(self, status, cxt):
    builderNames = []
    builderTimes = []
    builderFailures = []

    for builderName in status.getBuilderNames():
      builderNames.append(builderName)
      builderObj = status.getBuilder(builderName)

      # Get the latest build.  If it's still in progress, it will be skipped.
      build = builderObj.getBuild(-1) or builderObj.getBuild(-2)

      goodCount = 0
      badCount = 0
      buildTimes = []

      while build and goodCount + badCount < 50:
        if not build.isFinished():
          build = build.getPreviousBuild()
          continue
        if (build.getResults() == builder.SUCCESS or
            build.getResults() == builder.WARNINGS):
          (start, end) = build.getTimes()
          buildTimes.append(end - start)
          goodCount += 1
        else:
          badCount += 1
        build = build.getPreviousBuild()

      # Get the average time per build in minutes
      avg = float(sum(buildTimes)) / float(max(len(buildTimes), 1))
      builderTimes.append(avg / 60.0)

      # Get the proportion of failed builds.
      avg = float(badCount) / float(max(goodCount + badCount, 1))
      builderFailures.append(avg)

    cxt['builderNames'] = builderNames
    cxt['builderTimes'] = builderTimes
    cxt['builderFailures'] = builderFailures

  def content(self, request, cxt):
    self.getMainVariables(self.getStatus(request), cxt)
    templates = request.site.buildbot_service.templates
    template = templates.get_template("stats.html")
    return template.render(cxt)

  def getChild(self, path, req):
    return StatsBuilderStatusResource(self.getStatus(req).getBuilder(path))
