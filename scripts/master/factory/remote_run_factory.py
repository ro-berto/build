# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from master.factory import annotator_commands
from master.factory import commands
from master.factory.build_factory import BuildFactory


# TODO(nodir): restore timeout=1200, https://crbug.com/593891
def RemoteRunFactory(active_master, repository, recipe,
                     revision=None, factory_properties=None,
                     timeout=2400, max_time=None, triggers=None):
  """Returns buildbot build factory which runs recipes using recipe engine's
  remote_run command.

  |active_master| is config_bootstrap.Master's subclass from master's
  master_site_config.py .

  |repository| is the URL of repository containing recipe to run.

  |recipe| is the name of the recipe to run.

  |revision| is the revision to use for repo checkout (by default we use latest
  revision). Must be a commit hash or a fully-qualified ref.

  |factory_properties| is a dictionary of default build properties.

  |timeout| refers to the maximum number of seconds a build should be allowed
  to run without output. After no output for |timeout| seconds, the build is
  forcibly killed.

  |max_time| refers to the maximum number of seconds a build should be allowed
  to run, regardless of output. After |max_time| seconds, the build is
  forcibly killed.

  |triggers| is a list of builders on the same master to trigger
  after the build.
  """
  revision = revision or 'refs/heads/master'
  if isinstance(revision, basestring):
    assert re.match('^([a-z0-9]{40}|refs/.+)$', revision)

  factory_properties = factory_properties or {}

  # This is useful e.g. for botmap updater to easily extract info about builder.
  factory_properties.update({
    'recipe': recipe,
    'recipe_repository': repository,
  })

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

  for t in triggers or []:
    factory.addStep(commands.CreateTriggerStep(
        t, trigger_copy_properties=['swarm_hashes']))

  return factory
