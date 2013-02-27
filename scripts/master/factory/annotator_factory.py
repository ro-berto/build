# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to generate and manage a factory to be passed to a
builder dictionary as the 'factory' member, for each builder in c['builders'].

Specifically creates a basic factory that will execute an arbirary annotator
script.
"""

from master.factory import annotator_commands
from master.factory.build_factory import BuildFactory


class AnnotatorFactory(object):
  """Encapsulates data and methods common to all annotators."""

  def __init__(self):
    self._factory_properties = None

  def BaseFactory(self, build_properties=None, factory_properties=None):
    self._factory_properties = factory_properties
    factory = BuildFactory(build_properties)
    cmd_obj = annotator_commands.AnnotatorCommands(factory)
    cmd_obj.AddAnnotatedScript(factory_properties)
    return factory
