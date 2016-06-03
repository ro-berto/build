# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master.factory import annotator_commands
from master.factory import commands
from master.factory.build_factory import BuildFactory


def RemoteRunFactory(active_master, repository, recipe,
                     revision='origin/master', factory_properties=None,
                     timeout=1200, max_time=2400):
  """Returns buildbot build factory which runs recipes using recipe engine's
  remote_run command.

  |active_master| is config_bootstrap.Master's subclass from master's
  master_site_config.py .

  |repository| is the URL of repository containing recipe to run.

  |recipe| is the name of the recipe to run.

  |revision| is the revision to use for repo checkout (by default we use latest
  revision).

  |factory_properties| is a dictionary of default build properties.

  |timeout| refers to the maximum number of seconds a build should be allowed
  to run without output. After no output for |timeout| seconds, the build is
  forcibly killed.

  |max_time| refers to the maximum number of seconds a build should be allowed
  to run, regardless of output. After |max_time| seconds, the build is
  forcibly killed.
  """
  factory_properties = factory_properties or {}

  factory = BuildFactory(build_inherit_factory_properties=False)
  factory.properties.update(factory_properties, 'RemoteRunFactory')
  cmd_obj = annotator_commands.AnnotatorCommands(
      factory, active_master=active_master)

  runner = cmd_obj.PathJoin(cmd_obj.script_dir, 'remote_run.py')
  cmd = [
      cmd_obj.python, '-u', runner,
      '--repository', repository,
      '--revision', revision,
      '--recipe', recipe,
  ]
  cmd = cmd_obj.AddB64GzBuildProperties(cmd)
  cmd = cmd_obj.AddB64GzFactoryProperties(factory_properties, cmd)

  cmd_obj.AddAnnotatedScript(cmd, timeout=timeout, max_time=max_time)

  return factory
