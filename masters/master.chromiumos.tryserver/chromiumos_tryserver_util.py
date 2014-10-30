# -*- python -*-
# ex: set syntax=python:

# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


class NextSlaveAndBuild(object):
  """Callable BuildBot 'nextSlaveAndBuild' function for ChromeOS try server.

  This function differs from default assignment:
  - It preferentially assigns slaves to builds that explicitly request slaves.
  - It prioritizes higher-strata builders when multiple builders are asking
    for slaves.
  - It prioritizes slaves with fewer builders (more specialized) over slaves
    with more builders.
  """
  def __init__(self, testing_slaves=None):
    """Initializes a new callable object.

    Args:
      testing_slaves (None/list): If not None, a list of slaves not to assign.
    """
    self.testing_slaves = testing_slaves or ()

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

  def __call__(self, slaves, buildrequests):
    """Called by master to determine which job to run and which slave to use.

    Build requests may have a 'slaves_request' property (list of strings),
    established from the try job definition. Such requests allow try jobs to
    request to be run on specific slaves.

    Arguments:
      slaves: A list of available BuilderSlave objects.
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
                     if s.slave.slavename not in self.testing_slaves]

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
