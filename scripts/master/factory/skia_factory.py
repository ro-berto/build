#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the Skia master BuildFactory's.

Based on gclient_factory.py and adds Skia-specific steps."""

from master.factory import gclient_factory
from master.factory import skia_commands

import config

class SkiaFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the Skia master.cfg files."""

  def __init__(self, build_dir, target_platform=None):
    main = gclient_factory.GClientSolution(config.Master.skia_url + 'trunk',
                                           name='Skia')
    self.target_platform = target_platform

    custom_deps_list = [main]

    gclient_factory.GClientFactory.__init__(self, build_dir, custom_deps_list,
                                            target_platform=target_platform)

  def SkiaFactory(self, target='release', clobber=False, tests=None,
                  mode=None, slave_type='BuilderTester', options=None,
                  compile_timeout=1200, build_url=None, project=None,
                  factory_properties=None, target_arch=None):
    factory = self.BaseFactory(factory_properties=factory_properties)

    skia_cmd_obj = skia_commands.SkiaCommands(factory, target, '',
                                              self.target_platform,
                                              target_arch)

    skia_cmd_obj.AddBuild()

    return factory
