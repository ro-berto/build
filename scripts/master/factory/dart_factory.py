#!/usr/bin/python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to generate a Dart-specific BuildFactory.

Based on gclient_factory.py.
"""

from buildbot.process.buildstep import RemoteShellCommand
from buildbot.changes import svnpoller

from master.factory import dart_commands
from master.factory import gclient_factory
from master import master_utils

import config

dartium_url = config.Master.dart_bleeding + '/deps/dartium.deps'
dartium_trunk_url = config.Master.dart_trunk + '/deps/dartium.deps'

# We set these paths relative to the dart root, the scripts need to
# fix these to be absolute if they don't run from there.
linux_env =  {'BUILDBOT_JAVA_HOME': 'third_party/java/linux/j2sdk'}
windows_env = {'BUILDBOT_JAVA_HOME': 'third_party\\java\\windows\\j2sdk',
               'LOGONSERVER': '\\\\AD1'}

dart_revision_url = "http://code.google.com/p/dart/source/detail?r=%s"

def AddGeneralGClientProperties(factory_properties=None):
  """Adds the general gclient options to ensure we get the correct revisions"""
  # Make sure that pulled in projects have the right revision based on date.
  factory_properties['gclient_transitive'] = True
  # Don't set branch part on the --revision flag - we don't use standard
  # chromium layout and hence this is doing the wrong thing.
  factory_properties['no_gclient_branch'] = True

class DartFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the dart master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform

  # A map used to skip dependencies when a test is not run.
  # The map key is the test name. The map value is an array containing the
  # dependencies that are not needed when this test is not run.
  NEEDED_COMPONENTS = {
  }

  NEEDED_COMPONENTS_INTERNAL = {
  }

  if config.Master.trunk_internal_url:
    CUSTOM_DEPS_JAVA = ('dart/third_party/java',
                        config.Master.trunk_internal_url +
                        '/third_party/openjdk')
    # Fix broken ubuntu OpenJDK by importing windows TZ files
    CUSTOM_TZ = ('dart/third_party/java/linux/j2sdk/jre/lib/zi',
                 config.Master.trunk_internal_url +
                 '/third_party/openjdk/windows/j2sdk/jre/lib/zi')

  def __init__(self, build_dir, target_platform=None, trunk=False):
    solutions = []
    self.target_platform = target_platform
    deps_file = '/deps/all.deps'
    dart_url = config.Master.dart_bleeding + deps_file
    # If this is trunk use the deps file from there instead.
    if trunk:
      dart_url = config.Master.dart_trunk + deps_file
    custom_deps_list = []

    if config.Master.trunk_internal_url:
      custom_deps_list.append(self.CUSTOM_DEPS_JAVA)
      custom_deps_list.append(self.CUSTOM_TZ)

    main = gclient_factory.GClientSolution(
        dart_url,
        needed_components=self.NEEDED_COMPONENTS,
        custom_deps_list = custom_deps_list)
    solutions.append(main)

    gclient_factory.GClientFactory.__init__(self, build_dir, solutions,
                                            target_platform=target_platform)

  def DartFactory(self, target='Release', clobber=False, tests=None,
                  slave_type='BuilderTester', options=None,
                  compile_timeout=1200, build_url=None,
                  factory_properties=None, env=None):
    factory_properties = factory_properties or {}
    AddGeneralGClientProperties(factory_properties)
    tests = tests or []
    gclient_spec = self.BuildGClientSpec(tests)
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               factory_properties=factory_properties)
    # Get the factory command object to create new steps to the factory.
    dart_cmd_obj = dart_commands.DartCommands(factory,
                                              target,
                                              self._build_dir,
                                              self._target_platform,
                                              env=env)

    # We must always add the MaybeClobberStep, since this factory is
    # created at master start, but the choice of clobber or not may be
    # chosen at runtime (e.g. check the 'clobber' box).
    dart_cmd_obj.AddMaybeClobberStep(clobber, options=options)

    # Add the compile step if needed.
    if slave_type in ['BuilderTester', 'Builder', 'Trybot']:
      dart_cmd_obj.AddCompileStep(options=options,
                                  timeout=compile_timeout)

    # Add all the tests.
    if slave_type in ['BuilderTester', 'Trybot', 'Tester']:
      dart_cmd_obj.AddTests(options=options)

    return factory

  def DartAnnotatedFactory(self, python_script,
                           target='Release', tests=None,
                           timeout=1200, factory_properties=None,
                           env=None):
    factory_properties = factory_properties or {}
    AddGeneralGClientProperties(factory_properties)
    tests = tests or []
    # Create the spec for the solutions
    gclient_spec = self.BuildGClientSpec(tests)
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               factory_properties=factory_properties)
    # Get the factory command object to create new steps to the factory.
    dart_cmd_obj = dart_commands.DartCommands(factory,
                                              target,
                                              self._build_dir,
                                              self._target_platform,
                                              env=env)
    dart_cmd_obj.AddAnnotatedSteps(python_script, timeout=timeout)
    return factory

def monkey_patch_remoteshell():
  # Hack to increase timeout for steps, dart2js debug checked mode takes more
  # than 8 hours.
  RemoteShellCommand.__init__.im_func.func_defaults = (None,
                                                       1,
                                                       1,
                                                       1200,
                                                       48*60*60, {},
                                                       'slave-config',
                                                       True)

def DartTreeFileSplitter(path):
  pieces = path.split('/')
  if pieces[0] == 'trunk':
    return ('trunk', '/'.join(pieces[1:]))
  elif pieces[0] == 'branches':
    return ('/'.join(pieces[0:2]),
            '/'.join(pieces[2:]))
  else:
    return None

def get_builders_from_variants(variants, slaves, slave_lock):
  builders = []
  for v in variants:
    builders.append({
       'name': v['name'],
       'builddir': v['name'],
       'factory': v['factory_builder'],
       'slavenames': slaves.GetSlavesName(builder=v['name']),
       'category': v['category'],
       'locks': [slave_lock],
       'auto_reboot': False,
    })
  return builders

def get_builders_from_factories(factories, slaves, auto_reboot):
  builders = []
  for f in factories:
    builders.append({
        'name': f[0],
        'slavenames': slaves.GetSlavesName(builder=f[0]),
        'builddir': f[0],
        'factory': f[2],
        'category': '%s' % f[1],
        # Don't enable auto_reboot for people testing locally.
        'auto_reboot': auto_reboot,
    })
  return builders

def get_slaves(builders):
  # The 'slaves' list defines the set of allowable buildslaves. List all the
  # slaves registered to a builder. Remove dupes.
  return master_utils.AutoSetupSlaves(builders, config.Master.GetBotPassword())

def get_svn_poller():
  # Polls config.Master.dart_url for changes
  return svnpoller.SVNPoller(svnurl=config.Master.dart_url,
                             split_file=DartTreeFileSplitter,
                             pollinterval=10,
                             revlinktmpl=dart_revision_url)

def get_web_statuses(public_html, templates, master_port, master_port_alt):
  statuses = []
  statuses.append(master_utils.CreateWebStatus(master_port,
                                               allowForce=True,
                                               public_html=public_html,
                                               templates=templates))
  statuses.append(
      master_utils.CreateWebStatus(master_port_alt, allowForce=False))
  return statuses

