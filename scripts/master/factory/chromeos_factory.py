# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to build the chromium master."""

import os

from buildbot.steps import trigger, shell
from buildbot.process.properties import Property, WithProperties

from master import chromium_step
from master.factory import build_factory
from master.factory import chromeos_build_factory

class CbuildbotFactory(object):
  """
  Create a cbuildbot build factory.

  This is designed mainly to utilize build scripts directly hosted in
  chromite.git.

  Attributes:
      buildroot: --buildroot to pass to cbuild.
      params: string of parameters to pass to the cbuildbot type
      timeout: Timeout in seconds for the main command
          (i.e. the type command). Default 9000 seconds.
      crostools_repo: git repo for crostools toolset.
      chromite_repo: git repo for chromite toolset.
      trigger_name: Name of the trigger to fire after starting.
      dry_run: Means cbuildbot --debug, or don't push anything (cbuildbot only)
      factory: a factory with pre-existing steps to extend rather than start
          fresh.  Allows composing.
      pass_revision: to pass the chrome revision desired into the build.
      chromite_patch: a url and ref pair (dict) to patch the checked out
          chromite. Fits well with a single change from a codereview, to use
          on one or more builders for realistic testing, or experiments.
  """
  _default_git_base = 'http://git.chromium.org/chromiumos'
  _default_crostools = 'ssh://gerrit-int.chromium.org:29419/chromeos/crostools'
  _default_chromite = _default_git_base + '/chromite.git'

  def __init__(self, params, buildroot='/b/cbuild', timeout=9000,
               trigger_name=None, branch='master',
               crostools_repo=_default_crostools,
               chromite_repo=_default_chromite, dry_run=False, chrome_root=None,
               factory=None, pass_revision=False, slave_manager=True,
               chromite_patch=None, trybot=False, sleep_sync=None):
    self.buildroot = buildroot
    self.crostools_repo = crostools_repo
    self.chromite_repo = chromite_repo
    self.chromite_patch = chromite_patch
    if chromite_patch:
      assert ('url' in chromite_patch and 'ref' in chromite_patch)

    self.timeout = timeout
    self.branch = branch
    self.trigger_name = trigger_name
    self.dry_run = dry_run
    self.chrome_root = chrome_root
    self.slave_manager = slave_manager
    self.trybot = trybot
    self.sleep_sync = sleep_sync

    if factory:
      self.f_cbuild = factory
    elif pass_revision:
      self.f_cbuild = build_factory.BuildFactory()
    else:
      self.f_cbuild = chromeos_build_factory.BuildFactory()

    self.add_bootstrap_steps()
    self.add_cbuildbot_step(params, pass_revision)

  def _git_clear_and_checkout(self, repo, patch=None):
    """rm -rf and clone the basename of the repo passed without .git

    Args:
      repo: ssh: uri for the repo to be checked out
      patch: object with url and ref to patch on top
    """
    git_bin = '/usr/bin/git'
    git_checkout_dir = os.path.basename(repo).replace('.git', '')
    clear_and_clone_cmd = 'rm -rf %s' % git_checkout_dir
    clear_and_clone_cmd += ' && %s clone %s' % (git_bin, repo)
    clear_and_clone_cmd += ' && cd %s' % git_checkout_dir

    # We ignore branches coming from buildbot triggers and rely on those in the
    # config.  This is because buildbot branch names do not match up with
    # cros builds.
    clear_and_clone_cmd += ' && %s checkout %s' % (git_bin, self.branch)
    msg = 'Clear and Clone %s' % git_checkout_dir
    if patch:
      clear_and_clone_cmd += (' && %s pull %s %s' %
                              (git_bin, patch['url'], patch['ref']))
      msg = 'Clear, Clone and Patch %s' % git_checkout_dir

    self.f_cbuild.addStep(shell.ShellCommand,
                          command=clear_and_clone_cmd,
                          name=msg,
                          description=msg,
                          haltOnFailure=True)

  def add_bootstrap_steps(self):
    """Bootstraps Chromium OS Build by syncing pre-requisite repositories.

    * gclient sync of /b
    * clearing of chromite[& crostools]
    * clean checkout of chromite[& crostools]
    """
    if self.slave_manager:
      build_slave_sync = ['gclient', 'sync', '--delete_unversioned_trees']
      self.f_cbuild.addStep(shell.ShellCommand,
                            command=build_slave_sync,
                            name='update_scripts',
                            description='Sync buildbot slave files',
                            workdir='/b',
                            timeout=300)

    if self.sleep_sync:
      # We run a script from the script checkout above.
      fuzz_start = ['python', 'scripts/slave/random_delay.py',
                    '--max=%g' % self.sleep_sync,]
      self.f_cbuild.addStep(shell.ShellCommand,
                            command=fuzz_start,
                            name='random_delay',
                            description='Delay start of build',
                            workdir='/b/build',
                            timeout=int(self.sleep_sync) + 10)

    self._git_clear_and_checkout(self.chromite_repo, self.chromite_patch)
    if self.crostools_repo:
      self._git_clear_and_checkout(self.crostools_repo)

  def add_cbuildbot_step(self, params, pass_revision=False):
    """Adds cbuildbot step for Chromium OS builds.

    Cbuildbot includes all steps for building any Chromium OS config.

    Args:
      params:  Extra parameters for cbuildbot.
      pass_revision: To pass the chrome revision desired into the build.
    """
    cmd = ['chromite/buildbot/cbuildbot',
           shell.WithProperties('--buildnumber=%(buildnumber)s'),
           '--buildroot=%s' % self.buildroot]

    if self.trybot:
      cmd.append(Property('extra_args'))
    else:
      cmd += ['--buildbot']

    if self.dry_run:
      cmd += ['--debug']

    if self.chrome_root:
      cmd.append('--chrome_root=%s' % self.chrome_root)

    # Add properties from buildbot as necessary.
    cmd.append(WithProperties('%s', 'clobber:+--clobber'))
    if pass_revision:
      cmd.append(shell.WithProperties('--chrome_version=%(revision)s'))

    # Add additional parameters.
    cmd += params.split()

    # Trigger other slaves that should be run along with this builder.
    if self.trigger_name:
      self.f_cbuild.addStep(trigger.Trigger(schedulerNames=[self.trigger_name],
                                            waitForFinish=False))
      description = 'cbuildbot_master'
    else:
      description = 'cbuildbot'

    self.f_cbuild.addStep(chromium_step.AnnotatedCommand,
                          command=cmd,
                          timeout=self.timeout,
                          name='cbuildbot',
                          description=description,
                          usePTY=False)

  def get_factory(self):
    """Returns the produced factory."""
    return self.f_cbuild
