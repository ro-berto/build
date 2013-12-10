# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A StatusReceiver module to send mail under certain conditions.

A very simple subclass of MailNotifier, with the ability to decide whether or
not to email based on the failure state of individual steps.

Similar to ChromiumNotifier, but sane.
"""

from buildbot import interfaces
from buildbot.status.builder import SUCCESS, FAILURE
from buildbot.status.mail import MailNotifier


# Singleton objects used as values for |watch_mode|.
BUILDERS = object()
CATEGORIES = object()


class StepNotifier(MailNotifier):
  """This is a status notifier which can selectively mail for certain steps."""

  def __init__(self, watch_mode, interesting_steps, boring_steps=None,
               **kwargs):
    """
    @type  watch_mode: either BUILDERS or CATEGORIES
    @param watch_mode: A singleton object denoting whether this class is
                       watching steps keyed by builder name or by category.

    @type  interesting_steps: mapping of strings to lists of strings.
    @param interesting_steps: Keys are either builder names or categories;
                              values are lists of steps which we care about.
                              The key '*' (wildcard) means 'all builders'.
                              The value ['*'] (wildcard) means 'all steps'.
                              All keys (other than wildcard) must be present in
                              either |builders| or |categories| (in kwargs).
                              Required since otherwise this class has no point.

    @type  boring_steps: mapping of strings to lists of strings.
    @param boring_steps: Keys are either builder names or categories;
                         values are lists of steps which we do not care about.
                         The key '*' (wildcard) means 'all builders'.
                         The value ['*'] (wildcard) means 'all steps'.
                         All keys (other than wildcard) must be present in
                         either |builders| or |categories| (in kwargs).
                         Boring steps override interesting steps.
    """
    self.watch_mode = watch_mode
    self.interesting_steps = interesting_steps
    self.boring_steps = boring_steps or {}

    # Pass through the keys in interesting/boring steps to the appropriate list
    # in the parent class.
    if any((arg in ('builders', 'categores') for arg in kwargs)):
      raise interfaces.ParameterError(
          'Please do not specify |builders| or |categories| in StepNotifier.')
    keys = set(self.interesting_steps) + set(self.boring_steps)
    keys.pop('*')
    if self.watch_mode is BUILDERS:
      kwargs['builders'] = list(keys)
    elif self.watch_mode is CATEGORIES:
      kwargs['categories'] = list(keys)
    else:
      raise interfaces.ParameterError(
          'Please specify either BUILDERS or CATEGORIES for |watch_mode|.')
    # Don't use super because MailNotifier is an old-style class.
    MailNotifier.__init__(self, **kwargs)

  def _isInterestingBuilder(self, builder):
    """Determines if we care about a builder.

    We care about a builder if:
    * we care about steps on all (wildcard) builders
    * we care about steps on the builder with this name
    * we care about steps on any of this builder's categories
    """
    if '*' in self.categories:
      self.watched.append(builder)
      return True

    if builder.name in (self.builders or []):
      self.watched.append(builder)
      return True

    if any([cat in (self.categories or [])
        for cat in builder.category.split('|')]):
      self.watched.append(builder)
      return True

    return False

  def builderAdded(self, name, builder):
    """Called as a hook when a builder attaches to the master.

    We subscribe to events from the builder if we find it interesting.
    """
    if self._isInterestingBuilder(builder):
      return self  # subscribe to this builder
    return None

  def isMailNeeded(self, build, _results):
    """Called by buildFinished to determine if we should send mail."""

    builder = build.getBuilder()

    if not self._isInterestingBuilder(builder):
      # We should never be here (we shouldn't be subscribed) but just in case.
      return False

    watched_steps = set(self.interesting_steps.get('*'))
    if self.watch_mode is BUILDERS:
      watched_steps |= (set(self.interesting_steps.get(builder.name)) -
                        set(self.boring_steps.get(builder.name)))
    else:
      for category in builder.category.split('|'):
        watched_steps |= (set(self.interesting_steps.get(category)) -
                          set(self.boring_steps.get(category)))
    watched_steps -= set(self.boring_steps.get('*'))

    for step in build.getSteps():
      if step.getName() not in watched_steps:
        continue
      result = step.getResults()[0]

      if self.mode == "passing" and result == SUCCESS:
        return True
      if self.mode == "warnings" and result != SUCCESS:
        return True
      if self.mode == "failing" and result == FAILURE:
        return True
      # TODO(agable): Handle 'problem' and 'change' on a step-by-step level.
      if self.mode == "problem":
        prev = build.getPreviousBuild()
        if result == FAILURE and (prev and prev.getResults() != FAILURE):
          return True
      if self.mode == "change":
        prev = build.getPreviousBuild()
        if not prev or prev.getResults() != result:
          return True

    return False
