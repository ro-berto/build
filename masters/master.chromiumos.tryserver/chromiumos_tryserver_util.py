# -*- python -*-
# ex: set syntax=python:

# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import urllib

from common import chromium_utils


def is_general_pre_cq_builder(cbb_name):
  return cbb_name == 'pre-cq-group'


def is_pre_cq_builder(cbb_name):
  return (
      is_general_pre_cq_builder(cbb_name) or
      cbb_name.endswith('-pre-cq'))


# Load all of Chromite's 'cbuildbot' config targets.
configs = chromium_utils.GetCBuildbotConfigs()

# Load builder sets from the 'cbuildbot' config.
cbb_builders = set(cfg['name'] for cfg in configs)
etc_builders = set(['etc'])
all_builders = cbb_builders.union(etc_builders)
precq_builders = set(filter(is_pre_cq_builder, all_builders))


class TestingSlavePool(object):

  def __init__(self, testing_slaves=None):
    self.testing_slaves = set(testing_slaves or ())

  def is_testing_slave(self, slavename):
    return slavename in self.testing_slaves

  def cros_slave_name(self, slavename):
    """BuildBot Jinja2 template function to style our slave groups into pools.

    This function is called by our customized 'buildslaves.html' template. Given
    a slave name, it returns the name to display for that slave.
    """
    if self.is_testing_slave(slavename):
      return '%s (Testing)' % (slavename,)
    return slavename


def cros_builder_links(builders):
  """BuildBot Jinja2 template function to style our slave groups into pools.

  This function is called by our customized 'buildslaves.html' template. It is
  evaluated for each slave, receiving 'builders', a list containing template
  information for each builder attached to that slave.

  This function accepts and returns a list containing entries:
    {'name': <name>, 'link': <link>}

  Each entry is then used by the templating engine to populate that slave's
  builder table cell. This function analyzes the list of builders for a
  given slave and optionally returns a modified set of links to render.

  This function summarizes known sets of builders, replacing individual builder
  names/links with concise builder pool names/links.
  """
  builder_names = set(s['name'] for s in builders)

  if builder_names == all_builders:
    builders = [{'link': 'builders', 'name': 'General'}]
  elif builder_names == precq_builders:
    query = '&'.join('builder=%s' % (urllib.quote(n),)
                     for n in precq_builders)
    builders = [{'link': 'builders?%s' % (query,), 'name': 'Pre-CQ'}]
  return builders


class NextSlaveAndBuild(object):
  """Callable BuildBot 'nextSlaveAndBuild' function for ChromeOS try server.

  This function differs from default assignment:
  - It preferentially assigns slaves to builds that explicitly request slaves.
  - It prioritizes higher-strata builders when multiple builders are asking
    for slaves.
  - It prioritizes slaves with fewer builders (more specialized) over slaves
    with more builders.
  """

  def __init__(self, testing_slave_pool=None):
    """Initializes a new callable object.

    Args:
      testing_slave_pool (None/TestingSlavePool): If not None, the pool of
          testing slaves.
    """
    self.testing_slave_pool = testing_slave_pool or TestingSlavePool()

  @staticmethod
  def get_buildrequest_category(br):
    """Returns (str): the category of builder associated with a build request.
    """
    builder = br.master.status.getBuilder(br.buildername)
    if not builder:
      return None
    return builder.category

  # Paraphrased from 'buildbot.status.web.slaves.content()'.
  @staticmethod
  def get_slave_builders(slave, br):
    """Returns (list): The names (str) of builders assigned to a slave.
    """
    builders = []
    for bname in br.master.status.getBuilderNames():
      b = br.master.status.getBuilder(bname)
      for bs in b.getSlaves():
        if bs.getName() == slave.slavename:
          builders.append(b)
    return builders

  def is_testing_slave(self, slave):
    """Returns: True if 'slave' is a testing slave.

    Args:
      slave (BuildSlave): The build slave to test.
    """
    return self.testing_slave_pool.is_testing_slave(slave.slavename)

  def __call__(self, slaves, buildrequests):
    """Called by master to determine which job to run and which slave to use.

    Build requests may have a 'slaves_request' property (list of strings),
    established from the try job definition. Such requests allow try jobs to
    request to be run on specific slaves.

    Arguments:
      slaves: A list of candidate SlaveBuilder objects.
      buildrequests: A list of pending BuildRequest objects.

    Returns:
      A (slave, buildrequest) tuple containing the buildrequest to run and
      the slave to run it on.
    """
    # We need to return back a BuilderSlave object, so map slave names to
    # BuilderSlave objects.
    slave_dict = dict((bs.slave.slavename, bs) for bs in slaves)

    # Service builds with explicit slave requests first. A build requesting a
    # specific set of slaves will only be scheduled on those slaves.
    remaining = []
    for br in buildrequests:
      slaves_request = br.properties.getProperty('slaves_request', None)
      if not slaves_request:
        remaining.append(br)
        continue

      # If a list of slaves are requested, the order of the list is the order
      # of preference.
      for slave_name in slaves_request:
        s = slave_dict.get(slave_name)
        if s:
          return s, br

    # Service builds based on priority. We will use a builder's 'category' as
    # its priority, which also mirrors waterfall ordering.
    #
    # Note: Python sort is stable, so this will preserve the relative order of
    # build requests that share a category.
    remaining.sort(key=self.get_buildrequest_category)

    # Get a list of available slaves. We'll sort ascendingly by number of
    # attached builders with the intention of using more-specialized (fewer
    # attached builders) slaves before using generic ones.
    normal_slaves = [s for s in slaves
                     if not self.is_testing_slave(s.slave)]

    for br in remaining:
      builder = br.master.status.getBuilder(br.buildername)
      normal_slaves.sort(key=lambda s:
          len(self.get_slave_builders(s.slave, br)))

      # Iterate through slaves and choose the appropriate one.
      for s in normal_slaves:
        for builder_slave in builder.getSlaves():
          if s.slave.slavename == builder_slave.getName():
            return s, br
    return None, None
