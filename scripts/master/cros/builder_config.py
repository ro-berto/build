# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility classes to define and coordinate CrOS Chromite builder display.
"""

from collections import OrderedDict, namedtuple

from common.cros_chromite import ChromiteTarget, SlaveType


class _AnnotatedCallable(object):
  """Annotated callable that has a friendly string message for
  config/expectation dumps."""

  def __init__(self, func, doc):
    self._func = func
    self._doc = doc

  def __repr__(self):
    return self._doc

  def __call__(self, *args, **kwargs):
    return self._func(*args, **kwargs)


# BuildBot builder 'collapseRequests' callable that always returns True.
# (See http://docs.buildbot.net/latest/manual/customization.html)
AlwaysCollapseFunc = _AnnotatedCallable(
    lambda _builder, _req1, _req2: True,
    '<Always Collapse>')


class BuilderConfig(object):
  """Represents the presentation of a Chromite builder on a waterfall.

  Note that every property here is potentially derivable from the Chromite
  configuration. Information stored in this class should be examined in detail
  and, as appropriate, moved into Chromite.
  """

  # Default set of class base properties. Subclasses can override these to
  # affect behavior.
  CLOSER = False
  FLOATING = None
  UNIQUE = False
  COLLAPSE = True
  MASTER_BUILDER_NAME = None
  SLAVE_TYPE = SlaveType.BAREMETAL
  SLAVE_CLASS = None

  def __init__(self, config):
    """Initializes a new configuration.

    Args:
      config (ChromiteTarget): The underlying Chromite configuration object.
    """
    self.config = config

  def __str__(self):
    return '%s/%s' % (self.config.name, self.config.category)

  def __cmp__(self, other):
    assert isinstance(other, BuilderConfig)
    return cmp(self._CmpTuple(), other._CmpTuple())

  def _CmpTuple(self):
    """Returns (tuple): A comparable tuple to determine waterfall ordering."""
    return (self.ordinal, not self.config.is_master, self.is_experimental,
            self.config.name)

  @property
  def closer(self):
    """Returns (bool): Whether or not this builder is a tree closer."""
    return self.CLOSER

  @property
  def slave_type(self):
    """Returns (str): A SlaveType enumeration value."""
    return self.SLAVE_TYPE

  @property
  def slave_class(self):
    """Returns (str): The slave class for this enumeration, or None."""
    return self.SLAVE_CLASS

  @property
  def unique(self):
    """Returns (bool): Whether BuildBot should enforce singleton locks."""
    return self.UNIQUE

  @property
  def collapse(self):
    """Returns (bool): Whether BuildBot should collapse multiple builds.

    This will be passed to the 'collapseRequests' builder property, and can
    either be True, False, or a lambda function (see
    http://docs.buildbot.net/latest/manual/customization.html).
    """
    return self.COLLAPSE

  @property
  def floating(self):
    """Returns (bool): Whether this builder should have a floating backup slave.
    """
    return self.FLOATING

  @property
  def ordinal(self):
    """Returns (int): This builder's ordinal (sort order).

    This BuilderConfig class' ordinal. This is determined by its position in the
    CONFIG_MAP.
    """
    result = ORDINALS.get(self.config.category)
    if result is None:
      return ORDINALS.get(None)
    return result

  @property
  def builder_name(self):
    """Returns (str): The waterfall builder name for this configuration."""
    if self.config.get('buildbot_waterfall_name'):
      return self.config['buildbot_waterfall_name']
    if self.config.is_master:
      builder_name = self.MASTER_BUILDER_NAME or self._GetBuilderName()
    else:
      builder_name = self._GetBuilderName()
    return str(builder_name)

  @property
  def is_experimental(self):
    """Returns (bool): If this builder is experimental."""
    return not (self.config.is_master or self.config.get('important'))

  def _GetBuilderName(self):
    """Returns (str): Returns the generated builder name.

    Unless overloaded, the builder name will default to the target configuration
    name.
    """
    return self.config.name


class PreCqLauncherBuilderConfig(BuilderConfig):
  """BuilderConfig for the Pre-CQ launcher target."""

  UNIQUE = True
  CLOSER = True
  SLAVE_TYPE = SlaveType.VM

  def _GetBuilderName(self):
    return 'Pre-CQ Launcher'


class PaladinBuilderConfig(BuilderConfig):
  """BuilderConfig for Paladin launcher targets."""

  UNIQUE = True
  FLOATING = 'paladin'
  MASTER_BUILDER_NAME = 'CQ master'

  def _GetBuilderName(self):
    return '%s paladin' % (self.config.base,)


class IncrementalBuilderConfig(BuilderConfig):
  """BuilderConfig for Incremental launcher targets."""

  CLOSER = True
  COLLAPSE = AlwaysCollapseFunc

  def _GetBuilderName(self):
    return '%s incremental' % (self.config.base,)


class FirmwareBuilderConfig(BuilderConfig):
  """BuilderConfig for Firmware launcher targets."""

  def _GetBuilderName(self):
    return '%s firmware' % (self.config.base,)


class PfqBuilderConfig(BuilderConfig):
  """BuilderConfig for PFQ launcher targets."""

  MASTER_BUILDER_NAME = 'Chrome PFQ master'

  def _GetBuilderName(self):
    if self.config.suffix == 'chrome-pfq':
      project = 'chrome'
    elif self.config.suffix == 'chromium-pfq':
      project = 'chromium'
    else:
      raise ValueError("Unknown PFQ builder sufifx: %s" % (self.config.suffix,))
    return '%s %s PFQ' % (self.config.base, project)


class CanaryBuilderConfig(BuilderConfig):
  """BuilderConfig for canary launcher targets."""

  MASTER_BUILDER_NAME = 'Canary master'

  def _GetBuilderName(self):
    return '%s canary' % (self.config.base,)


class SdkBuilderConfig(BuilderConfig):
  """BuilderConfig for SDK launcher targets."""

  SLAVE_TYPE = SlaveType.GCE
  COLLAPSE = AlwaysCollapseFunc

  def _GetBuilderName(self):
    # Return 'major/minor' (end of toolchain name).
    return '%s sdk' % (self.config.base,)


class ToolchainBuilderConfig(BuilderConfig):
  """BuilderConfig for toolchain launcher targets.

  Toolchain builders leverage a declared slave class to share slaves between
  them.
  """

  SLAVE_CLASS = 'toolchain'

  def _GetBuilderName(self):
    # Expected toolchain names are:
    # - internal-toolchain-VERSION (base='internal', suffix='toolchain-VERSION')
    # - toolchain-VERSION (base='', suffix='toolchain-VERSION')
    frags = self.config.suffix.split('-')
    assert len(frags) == 2, (
        "Unsupported toolchain suffix: %s" % (self.config.suffix,))
    if self.config.name:
      return '%s %s (%s)' % (frags[0], frags[1], self.config.base)
    return '%s %s' % (frags[0], frags[1])


# Map of cbuildbot target type to configuration class.
#
# This is an ordered dictionary. The order of items corresponds to the
# config type's order on the waterfall.
#
# Any configuration type not mapped should default to the 'None' value.
CONFIG_MAP = OrderedDict((
    (ChromiteTarget.PRE_CQ_LAUNCHER, PreCqLauncherBuilderConfig),
    (ChromiteTarget.PALADIN, PaladinBuilderConfig),
    (ChromiteTarget.INCREMENTAL, IncrementalBuilderConfig),
    (ChromiteTarget.FIRMWARE, FirmwareBuilderConfig),
    (ChromiteTarget.PFQ, PfqBuilderConfig),
    (ChromiteTarget.CANARY, CanaryBuilderConfig),
    (ChromiteTarget.SDK, SdkBuilderConfig),
    (ChromiteTarget.TOOLCHAIN, ToolchainBuilderConfig),
    (None, BuilderConfig),
))

# Determine ordinals for each BuilderTarget type.
_config_map_keys = CONFIG_MAP.keys()
ORDINALS = dict((k, _config_map_keys.index(k))
                for k in CONFIG_MAP.iterkeys())


def GetBuilderConfig(target):
  """Returns (BuilderConfig): a typed BuilderConfig instance for a target.

  Args:
    target (ChromiteTarget): The Chromite target to configure.
  """
  return CONFIG_MAP.get(target.category, CONFIG_MAP[None])(target)


def GetBuilderConfigs(targets):
  """Returns (OrderedDict): BuilderConfig instances for a set of targets.

  Args:
    targets (list): A list of ChromiteTarget instances to generate
        BuilderConfigs for.
  """
  configs = [GetBuilderConfig(t)
             for t in targets.itervalues()]
  configs.sort()
  return OrderedDict((c.config.name, c) for c in configs)
