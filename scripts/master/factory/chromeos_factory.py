# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to build the chromium master."""

import os

from buildbot.steps import trigger, shell
from buildbot.process.properties import WithProperties

from master import chromeos_revision_source
from master import chromium_step
from master.factory import chromeos_build_factory

class CbuildbotFactory(object):
  """
  Create a cbuildbot build factory.

  This is designed mainly to utilize build scripts directly hosted in
  crostools.git.

  Attributes:
      type: The type of cbuildbot setup to produce. If none is specified you
          just get the boiler plate code in your factory and you can add
          whatever steps you want to that factory.
      board: What board to build (x86-generic x86-agz etc).
      buildroot: --buildroot to pass to cbuild.
      triagelog: Path to a log file to run triagelog, if it is not defined
          triagelog will not run.
      variant: board variant to pass on to cbuild build type
      params: string of parameters to pass to the cbuildbot type
      timeout: Timeout in seconds for the main command
          (i.e. the type command). Default 9000 seconds.
      crostools_repo: git repo for crostools toolset.
      chromite_repo: git repo for chromite toolset.
      dry_run: Means cbuildbot --debug, or don't push anything (cbuildbot only)
  """
  _default_git_base = 'http://gerrit.chromium.org/gerrit/p/chromiumos'
  _default_crostools = 'ssh://gerrit-int.chromium.org:29419/chromeos/crostools'
  _default_chromite = _default_git_base + '/chromite'

  DEFAULT_CBUILDBOT_TYPE = 'cbuildbot'
  CHROME_CBUILDBOT_TYPE = 'cbuildbot_chrome'

  # Redefining built-in 'type'
  # pylint: disable=W0622
  def __init__(self, type=DEFAULT_CBUILDBOT_TYPE, board='x86-generic',
               buildroot='/b/cbuild', triagelog=None, params='', timeout=9000,
               variant=None, is_master=False, branch='master', old_style=False,
               crostools_repo=_default_crostools,
               chromite_repo=_default_chromite,
               dry_run=False):
    self.buildroot = buildroot
    self.crostools_repo = crostools_repo
    self.chromite_repo = chromite_repo
    self.timeout = timeout
    self.variant = variant
    self.board = board
    self.branch = branch
    self.type = type
    self.is_master = is_master
    self.dry_run = dry_run

    self.f_cbuild = chromeos_build_factory.BuildFactory()
    self.add_boiler_plate_steps()

    if type == 'cbuildbot':
      description_suffix = ''
      if self.is_master:
        description_suffix = 'master'

      self.cbuildbot_type(params, description_suffix=description_suffix)
    elif type == 'cbuild':
      self.cbuild_type(params)
    elif type == 'oneoff':
      self.oneoff_type()

    if triagelog:
      self.add_triagelog_step(triagelog)


  def _branchAtOrAbove(self, version):
    """See if the current branch is at or above some cutoff point.

       This is intended to help with backwards compatibility with older
       branches.

       '0.12.123.456' > '0.12'
       '0.11.123.456' < '0.12'

       Note that this method can break with some version strings out there:
       '0.11.241.B'. In this case, if you don't specify enough detail
       reach the 'B' it's fine. If that's a problem, the method will
       have to be improved.
    """

    # Master is assumed to be past the cut off point.
    if self.branch == 'master':
      return True

    # '0.12.123.456' -> ['0', '12', '123', '456']
    branch_parts = self.branch.split('.')
    version_parts = version.split('.')

    # The first different section tells which is newer
    for b, v in zip(branch_parts, version_parts):
      if int(b) > int(v):
        return True

      if int(b) < int(v):
        return False

    # If all sections matched, see if zip truncated a difference
    return len(branch_parts) >= len(version_parts)

  def _git_clear_and_checkout(self, repo):
    """
    rm -rf and clone the basename of the repo passed without .git

    Args:
      repo: ssh: uri for the repo to be checked out
    """
    git_bin = '/usr/bin/git'
    git_checkout_dir = os.path.basename(repo).replace('.git', '')
    clear_and_clone_cmd = 'rm -rf %s ; sleep 10 ;' % git_checkout_dir
    clear_and_clone_cmd += '%s clone %s;cd %s;' % (git_bin, repo,
                                                   git_checkout_dir)
    #It's possible that branch can be coming from WithProperites set
    #If the branch is master, then even if the branch is empty, it amounts
    #to the same 'git checkout' or 'git checkout master'
    #If self.branch is set to something otherthan master, that means, branch
    #has been passed in and we want to honor the explicitly passed in branch

    clear_and_clone_cmd += '%s checkout ' % git_bin

    if self.branch == 'master':
      # Whitelist top of tree chrome PFQ builds to always use master
      # as the branch checkout, this avoids us trying to clone a SVN
      # revision that is passed to the builder. We are doing this in this
      # fashion to avoid having to write a script that wraps our git call
      # to confirm the hash we are passed. While technically we have access to
      # branch/revision unfortunately the only way it is available is via
      # WithProperties which is only transferred to something usable in a shell
      # step.
      if self.type and (self.CHROME_CBUILDBOT_TYPE == self.type):
        clear_and_clone_cmd += 'master'
      else:
        # If branch is passed by the change source and we are not chrome pfq use
        # use it.
        clear_and_clone_cmd += '%(branch)s'
    else:
      clear_and_clone_cmd += self.branch

    msg = 'Clear and Clone %s' % git_checkout_dir
    self.f_cbuild.addStep(shell.ShellCommand,
                          command=WithProperties(clear_and_clone_cmd),
                          name=msg,
                          description=msg)

  def add_boiler_plate_steps(self):
    """
    Add the following boiler plate steps to the factory.

    * gclient sync of /b
    * clearing of crostools/chromite
    * clean checkout of crostools/chromite
    """
    build_slave_sync = ['gclient', 'sync']
    self.f_cbuild.addStep(shell.ShellCommand,
                          command=build_slave_sync,
                          description='Sync buildbot slave files',
                          workdir='/b',
                          timeout=300)

    self._git_clear_and_checkout(self.chromite_repo)
    self._git_clear_and_checkout(self.crostools_repo)

  def cbuildbot_type(self, params, description_suffix='', haltOnFailure=True):
    """Adds cbuildbot steps for pre flight queue builders.

    Cbuildbot includes the steps for syncing and building pre flight queue
    builders.  This includes both chrome and standard pfq builders.

    Args:
      params:  Extra parameters for cbuildbot.
      description_suffix:  Optional suffix to add to description that shows up
        on dashboard.
      haltOnFailure: To halt build because of failure of cbuildbot step.  Useful
        for setting to False for case of Chrome pfq where multiple cbuildbot
        steps are invoked.
    """
    # Gathers queued commits and drops them for cbuildbot to pick up.
    self.f_cbuild.addStep(chromeos_revision_source.GitRevisionDropper,
                          timeout=self.timeout)

    # Triggered cbuildbots (pfq slaves) have this property set.
    if self.is_master:
      if self.type == self.CHROME_CBUILDBOT_TYPE:
        self.f_cbuild.addStep(
          trigger.Trigger(schedulerNames=['chrome_pre_flight_queue_slaves'],
                          waitForFinish=False))
      else:
        self.f_cbuild.addStep(
          trigger.Trigger(schedulerNames=['pre_flight_queue_slaves'],
                          waitForFinish=False))

    cbuild_cmd = ['chromite/buildbot/cbuildbot',
                  shell.WithProperties("--buildnumber=%(buildnumber)s")]

    if self._branchAtOrAbove('0.12'):
      cbuild_cmd += ['--buildbot']

    if self.dry_run:
      cbuild_cmd += ['--debug']

    cbuild_cmd += ['--buildroot=%s' % self.buildroot]
    cbuild_cmd += [('--revisionfile=%s' %
                   chromeos_revision_source.PFQ_REVISION_FILE)]
    # Below, WithProperties is appended to cbuild_cmd and rendered into a string
    # for each specific build at build-time.  When clobber is None, it renders
    # to an empty string.  When clobber is not None, it renders to the string
    # --clobber.  Note: the :+ after clobber controls this behavior and is not
    # a typo.
    cbuild_cmd.append(WithProperties('%s', 'clobber:+--clobber'))

    name = self.type
    if description_suffix:
      description = '%s_%s' % (name, description_suffix)
    else:
      description = name

    cbuild_cmd += params.split()
    self.f_cbuild.addStep(chromium_step.AnnotatedCommand,
                          command=cbuild_cmd,
                          timeout=self.timeout,
                          name=name,
                          description=description,
                          haltOnFailure=haltOnFailure,
                          usePTY=False)

  def oneoff_type(self):
    """
    Add a step to run /home/chrome-bot/buildbot-oneoff --buildnumber=XXX.
    """
    cmd = ['/home/chrome-bot/buildbot-oneoff',
           shell.WithProperties("--buildnumber=%(buildnumber)s"),
           shell.WithProperties('%(branch)s)')]
    self.f_cbuild.addStep(shell.ShellCommand,
                          command=cmd,
                          timeout=self.timeout,
                          name='one off chromebot',
                          description='one off chromebot')

  def cbuild_type(self, params):
    cbuild_cmd = ['crostools/cbuild',
                  shell.WithProperties("--buildnumber=%(buildnumber)s")]
    cbuild_cmd += ['--board=%s' % self.board,
                   '--buildroot=%s' % self.buildroot]
    # Below, WithProperties is appended to cbuild_cmd and rendered into a string
    # for each specific build at build-time.  When clobber is None, it renders
    # to an empty string.  When clobber is not None, it renders to the string
    # --clobber.  Note: the :+ after clobber controls this behavior and is not
    # a typo.
    cbuild_cmd.append(WithProperties('%s', 'clobber:+--clobber'))
    cbuild_cmd.append(WithProperties('%(branch)s'))
    if self.variant:
      cbuild_cmd.append('--variant=%s' % self.variant)
    cbuild_cmd += params.split()
    self.f_cbuild.addStep(shell.ShellCommand,
                          command=cbuild_cmd,
                          timeout=self.timeout,
                          name='cbuild',
                          description='cbuild')

    logfile = os.path.join(self.buildroot, 'logs/cbuild.log')
    self.add_triagelog_step(logfile)

  def add_triagelog_step(self, logfile):
    """
    Add a step to the boiler plate to run triage log with the
    specified log

    Args:
        logfile: path to the file to run triage log on.
    """
    triagelog_cmd = ['crostools/triagelog', '--nohighlighting', logfile]
    self.f_cbuild.addStep(shell.ShellCommand,
                          command=triagelog_cmd,
                          timeout=900,
                          name='triagelog',
                          description='triagelog')

  def get_factory(self):
    """
    Return the produced factory.

    Returns:
        a buildbot factory object
    """
    return self.f_cbuild


class ChromeCbuildbotFactory(CbuildbotFactory):
  """
  Create a cbuildbot build factory for chrome.

  Attributes:
      board: What board to build (x86-generic x86-agz etc).
      buildroot: --buildroot to pass to cbuild.
      params: string of parameters to pass to the cbuildbot type
      timeout: Timeout in seconds for the main command
          (i.e. the type command). Default 9000 seconds.
      is_master: Whether or not this pfq manages others.
      chrome_rev_stages:  Array of strings designating chrome rev steps to run
        in cbuildbot tot, latest_release, etc.
      crostools_repo: git repo for crostools toolset.
      chromite_repo: git repo for chromite toolset.
      dry_run: Means cbuildbot --debug, or don't push anything (cbuildbot only)
  """
  def __init__(self, buildroot='/b/cbuild', params='', timeout=9000,
               is_master=False, branch='master', chrome_rev_stages=None,
               crostools_repo=CbuildbotFactory._default_crostools,
               chromite_repo=CbuildbotFactory._default_chromite,
               dry_run=False):
    CbuildbotFactory.__init__(self, type=CbuildbotFactory.CHROME_CBUILDBOT_TYPE,
                              board=None,
                              buildroot=buildroot, is_master=is_master,
                              crostools_repo=crostools_repo,
                              chromite_repo=chromite_repo,
                              dry_run=dry_run)
    # TODO(sosa): Remove legacy support.
    if chrome_rev_stages:
      for chrome_rev in chrome_rev_stages:
        bot_params = '--chrome_rev=%s %s' % (chrome_rev, params)
        self.cbuildbot_type(bot_params, description_suffix=chrome_rev,
                            haltOnFailure=False)
    else:
      self.cbuildbot_type(params, haltOnFailure=False)
