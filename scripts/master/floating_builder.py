# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from datetime import datetime

from twisted.python import log
from twisted.internet import reactor


class FloatingSet(object):
  """A set describing available primary/floating slaves."""
  def __init__(self):
    self._primary = set()
    self._floating = set()

  def AddPrimary(self, *s):
    self._primary.update(s)

  def AddFloating(self, *s):
    self._floating.update(s)

  def NextSlaveFunc(self, grace_period):
    """Returns a NextSlaveFunc that uses the contents of this set."""
    return _FloatingNextSlaveFunc(self, grace_period)

  def Get(self):
    return (sorted(self._primary), sorted(self._floating))

  def __str__(self):
    return '%s > %s' % (
        ', '.join(sorted(self._primary)),
        ', '.join(sorted(self._floating)))


class PokeBuilderTimer(object):
  def __init__(self, botmaster, buildername):
    self.botmaster = botmaster
    self.buildername = buildername
    self.delayed_call = None

  def cancel(self):
    if self.delayed_call is not None:
      self.delayed_call.cancel()
      self.delayed_call = None

  def reset(self, delta):
    if self.delayed_call is not None:
      current_delta = (datetime.fromtimestamp(self.delayed_call.getTime()) -
                       _get_now())
      if delta < current_delta:
        self.delayed_call.reset(delta.total_seconds())
      return

    # Schedule a new call
    self.delayed_call = reactor.callLater(
        delta.total_seconds(),
        self._poke,
    )

  def _poke(self):
    self.delayed_call = None
    log.msg('Poking builds for builder [%s]' % (self.buildername,))
    self.botmaster.maybeStartBuildsForBuilder(self.buildername)


class _FloatingNextSlaveFunc(object):
  """
  This object, when used as a Builder's 'nextSlave' function, allows a strata-
  based preferential treatment to be assigned to a Builder's Slaves.

  The 'nextSlave' function is called on a scheduled build when an associated
  slave becomes available, either coming online or finishing an existing build.
  These events are used as stimulus to enable the primary builder(s) to pick
  up builds when appropriate.

  1) If a Primary is available, the build will be assigned to them.
  2) If a Primary builder is busy or is still within its grace period for
    unavailability, no slave will be assigned in anticipation of the
    'nextSlave' being re-invoked once the builder returns (1). If the grace
    period expires, we "poke" the master to call 'nextSlave', at which point
    the build will fall through to a lower strata.
  3) If a Primary slave is offline past its grace period, the build will be
    assigned to a Floating slave.

  Args:
    fs (FloatingSet): The set of available primary/floating slaves.
    grace_period: (timedelta) The amount of time that a slave can be offline
        before builds fall through to a lower strata.
  """

  def __init__(self, fs, grace_period):
    self._primary, self._floating = fs.Get()
    self._fs = fs
    self._grace_period = grace_period
    self._slave_seen_times = {}
    self._poke_builder_timers = {}
    self.verbose = False

  def __repr__(self):
    return '%s(%s)' % (type(self).__name__, self._fs)

  def __call__(self, builder, slave_builders):
    """Main 'nextSlave' invocation point.

    When this is called, we are given the following information:
    - The Builder
    - A set of 'SlaveBuilder' instances that are available and ready for
      assignment (slave_builders).
    - The total set of ONLINE 'SlaveBuilder' instances associated with
      'builder' (builder.slaves)
    - The set of all slaves configured for Builder (via
      '_get_all_slave_status')

    We compile that into a stateful awareness and use it as a decision point.
    Based on the slave availability and grace period, we will either:
    (1) Return a slave immediately to claim this build. We do this if:
      (1a) There was a "primary" build slave available, or
      (1b) We are outside of all of the grace periods for the primary slaves,
           and there is a floating builder available.
    (2) Return 'None' (delaying the build) in anticipation of primary/floating
        availability.

    If we go with (2), we will schedule a 'poke' timer to stimulate a future
    'nextSlave' call, since BuildBot only checks for builds on explicit slave
    availability edges. This covers the case where floating builders are
    available, but aren't enlisted because we're within the grace period. In
    this case, we need to re-evaluate slaves after the grace period expires,
    but actual slave state won't haev changed, so no new slave availabilty edge
    will have occurred.
    """
    self._debug("Calling [%s] with builder=[%s], slaves=[%s]",
                self, builder, slave_builders)
    self._cancel_builder_timer(builder)

    # Get the set of all 'SlaveStatus' assigned to this Builder (idle, busy,
    # and offline).
    slave_status_map = dict(
        (slave_status.name, slave_status)
        for slave_status in self._get_all_slave_status(builder)
    )

    # Record the names of the slaves that were proposed.
    proposed_slave_builder_map = {}
    for slave_builder in slave_builders:
      proposed_slave_builder_map[slave_builder.slave.slavename] = slave_builder

    # Calculate the oldest a slave can be before we assume something's wrong.
    now = _get_now()
    grace_threshold = (now - self._grace_period)

    # Record the last time we've seen any of these slaves online.
    online_slave_builders = set()
    for slave_builder in builder.slaves:
      build_slave = slave_builder.slave
      if build_slave is None:
        continue
      self._record_slave_seen_time(build_slave, now)
      online_slave_builders.add(build_slave.slavename)

    self._debug('Online proposed slaves: [%s]',
                slave_builders)

    # Are there any primary slaves that are proposed? If so, use it
    within_grace_period = []
    some_primary_were_busy = False
    wait_delta = None
    for slave_name in self._primary:
      self._debug('Considering primary slave [%s]', slave_name)

      # Was this slave proposed to 'nextSlave'?
      slave_builder = proposed_slave_builder_map.get(slave_name)
      if slave_builder is not None:
        # Yes. Use it!
        self._debug('Slave [%s] is available', slave_name)
        return slave_builder

      # Is this slave online? If so, we won't consider floating candiates.
      if slave_name in online_slave_builders:
        # The slave is online, but is not proposed (BUSY); add it to the
        # desired slaves list.
        self._debug('Slave [%s] is online but BUSY.', slave_name)
        within_grace_period.append(slave_name)
        some_primary_were_busy = True
        continue

      # Get the 'SlaveStatus' object for this slave
      slave_status = slave_status_map.get(slave_name)
      if slave_status is None:
        continue

      # The slave is offline. Is this slave within the grace period?
      last_seen = self._get_latest_seen_time(slave_status)
      if last_seen < grace_threshold:
        # No, the slave is older than our grace period.
        self._debug('Slave [%s] is OFFLINE and outside grace period '
                    '(%s < %s).', slave_name, last_seen, grace_threshold)
        continue

      # This slave is within its grace threshold. Add it to the list of
      # desired slaves from this set and update our wait delta in case we
      # have to poke.
      #
      # We track the longest grace period delta, since after this point if
      # no slaves have taken the build we would otherwise hang.
      self._debug('Slave %r is OFFLINE but within grace period '
                  '(%s >= %s).', slave_name, last_seen, grace_threshold)
      within_grace_period.append(slave_name)
      slave_wait_delta = (self._grace_period - (now - last_seen))
      if (wait_delta is None) or (slave_wait_delta > wait_delta):
        wait_delta = slave_wait_delta

    # We've looped through all primary slaves, and none of them were available.
    # Were some within the grace period?
    if not within_grace_period:
      # We're outside of our grace period. Are there floating slaves that we
      # can use?
      for slave_name in self._floating:
        slave_builder = proposed_slave_builder_map.get(slave_name)
        if slave_builder is not None:
          # Yes. Use it!
          self._debug('Slave [%s] is available', slave_name)
          return slave_builder

      self._debug('No slaves are available; returning None')
      return None

    # We're going to return 'None' to wait for a primary slave. If all of
    # the slaves that we're anticipating are offline, schedule a 'poke'
    # after the last candidate has exceeded its grace period to allow the
    # build to go to lower strata.
    log.msg('Returning None in anticipation of unavailable primary slaves. '
            'Please disregard the following BuildBot `nextSlave` '
            'error: %s' % (within_grace_period,))

    if (not some_primary_were_busy) and (wait_delta is not None):
      self._debug('Scheduling ping for [%s] in [%s]',
                  builder.name, wait_delta)
      self._schedule_builder_timer(builder, wait_delta)
    return None

  def _debug(self, fmt, *args):
    if not self.verbose:
      return
    log.msg(fmt % args)

  @staticmethod
  def _get_all_slave_status(builder):
    # Try using the builder's BuilderStatus object to get a list of all slaves
    if builder.builder_status is not None:
      return builder.builder_status.getSlaves()

    # Satisfy with the list of currently-connected slaves
    return [slave_builder.slave.slave_status
            for slave_builder in builder.slaves]

  def _get_latest_seen_time(self, slave_status):
    times = []

    # Add all of the registered connect times
    times += [datetime.fromtimestamp(connect_time)
              for connect_time in slave_status.connect_times]

    # Add the time of the slave's last message
    times.append(datetime.fromtimestamp(slave_status.lastMessageReceived()))

    # Add the last time we've seen the slave in our 'nextSlave' function
    last_seen_time = self._slave_seen_times.get(slave_status.name)
    if last_seen_time is not None:
      times.append(last_seen_time)

    if not times:
      return None
    return max(times)

  def _record_slave_seen_time(self, build_slave, now):
    self._slave_seen_times[build_slave.slavename] = now

  def _schedule_builder_timer(self, builder, delta):
    poke_builder_timer = self._poke_builder_timers.get(builder.name)
    if poke_builder_timer is None:
      poke_builder_timer = PokeBuilderTimer(
          builder.botmaster,
          builder.name,
      )
      self._poke_builder_timers[builder.name] = poke_builder_timer
    poke_builder_timer.reset(delta)

  def _cancel_builder_timer(self, builder):
    poke_builder_timer = self._poke_builder_timers.get(builder.name)
    if poke_builder_timer is None:
      return
    poke_builder_timer.cancel()


def _get_now():
  """Returns (datetime.datetime): The current time.

  This exists so it can be overridden by mocks in unit tests.
  """
  return datetime.now()
