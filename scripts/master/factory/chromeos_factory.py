# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to build the chromium master."""

import os

from buildbot.steps import trigger, shell
from buildbot.process.properties import WithProperties

from master import chromeos_revision_source
from master.factory import chromeos_commands
from master.factory import chromeos_build_factory
from master.factory import gclient_factory
from master.factory.build_factory import BuildFactory

import config


class ChromeOSFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the chromium master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform

  def __init__(self, build_dir, target_platform=None, target_arch=None,
               official_build=None):

    self._official_build = official_build
    if official_build is not None:
      # Official build's buildspec
      # pylint: disable=E1101
      url = '%s/%s' % (
          config.Master.git_server_url, official_build)
    else:
      # pylint: disable=E1101
      url = config.Master.chromeos_url

    # XXX: changed so it all lands in the same namespace
    #main = gclient_factory.GClientSolution(url, name='chromeos')
    main = gclient_factory.GClientSolution(url, name='chromiumos')
    deps_list = [main]
    gclient_factory.GClientFactory.__init__(self, build_dir, deps_list,
                                            target_platform=target_platform)
    self._target_arch = target_arch

  def ChromeOSFactory(
      self, identifier, target='Release', clobber=False, tests=None,
      steps=None, mode=None, slave_type='BuilderTester', options=None,
      compile_timeout=1200, build_url=None, factory_properties=None,
      custom_deps_list=None):
    # Defaults which are mutable objects
    steps = steps or ['platform']
    tests = tests or []
    factory_properties = factory_properties or {}

    # Add any custom deps.
    self._solutions[0].custom_deps_list = custom_deps_list or []
    # Create the spec for the solutions
    gclient_spec = self.BuildGClientSpec(tests)
    # Set gclient_timeout to deal with large git syncs
    factory_properties['gclient_timeout'] = 600
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               factory_properties=factory_properties,
                               delay_compile_step=True,
                               sudo_for_remove=True)

    # Get the factory command object to create new steps to the factory.
    chromeos_cmd_obj = chromeos_commands.ChromeOSCommands(
        factory=factory,
        identifier=identifier,
        target=target,
        build_dir=self._build_dir,
        target_platform=self._target_platform,
        official_build=self._official_build)

    # Ensures that we clean up a previous fail of a temporary commit from a
    # previous run.
    if 'pre_flight_queue' in steps:
      chromeos_cmd_obj.AddChromeOSPreFlightStep('clean',
          clobber, mode=mode, options=options, timeout=compile_timeout)

    # Do straight cbuild
    if 'cbuild' in steps:
      chromeos_cmd_obj.AddcbuildStep(
          clobber, mode=mode, options=options, timeout=compile_timeout,
          base_url=factory_properties.get('archive_url'))

    # TODO(sosa) - Remove steps once we switch to cbuildbot. 
    chromeos_cmd_obj.AddChromeOSCrosUtilsStep()

    chromeos_cmd_obj.AddChromeOSRepoUpdateStep(clobber, mode=mode,
                                               options=options,
                                               timeout=compile_timeout)

    # Add official overlay step if needed
    if 'overlay_official' in steps:
      chromeos_cmd_obj.AddOverlayOfficialStep(
          clobber, mode=mode, options=options, timeout=compile_timeout)

    # Add the compile steps if needed.
    if (slave_type == 'BuilderTester' or slave_type == 'Builder' or
        slave_type == 'Trybot'):

      if 'publish_repo' in steps:
        chromeos_cmd_obj.AddChromeOSPublishRepoStep(
            clobber, mode=mode, options=options, timeout=compile_timeout)
      if 'make_chroot' in steps:
        chromeos_cmd_obj.AddChromeOSMakeChrootStep(
            clobber, mode=mode, options=options, timeout=compile_timeout+1800)

      # Optionally restore built packages.
      if 'cache' in steps:
        chromeos_cmd_obj.AddRestorePackages(options=options)

      if 'make_chroot' in steps:
        chromeos_cmd_obj.AddChromeOSSetupBoardStep(
            clobber, mode=mode, options=options, timeout=compile_timeout)

    # Everyone currently needs copy config step
    # This has to happen after the chroot step because a file gets dropped in
    # there.
    chromeos_cmd_obj.AddChromeOSCopyConfigStep(
        clobber, mode=mode, options=options, timeout=compile_timeout)

    # Temporarily marks new changes as stable.
    if 'pre_flight_queue' in steps:
      chromeos_cmd_obj.AddChromeOSPreFlightStep('commit',
          clobber, mode=mode, options=options, timeout=compile_timeout)

    if (slave_type == 'BuilderTester' or slave_type == 'Builder' or
        slave_type == 'Trybot'):

      if 'platform' in steps:
        chromeos_cmd_obj.AddChromeOSPackagesStep(
            clobber, mode=mode, options=options, timeout=compile_timeout+2000)
      if 'kernel' in steps:
        chromeos_cmd_obj.AddChromeOSKernelStep(
            clobber, mode=mode, options=options, timeout=compile_timeout)
      if 'image' in steps:
        chromeos_cmd_obj.AddChromeOSImageStep(
            clobber, mode=mode, options=options, timeout=compile_timeout)

    # Add test steps if needed.
    chromeos_cmd_obj.AddChromeOSTestSteps(
        tests, clobber, mode=mode, options=options, timeout=compile_timeout)
    # Archive the full output directory if the machine is a builder.
    if slave_type == 'Builder':
      chromeos_cmd_obj.AddZipBuild()

    # Download the full output directory if the machine is a tester.
    if slave_type == 'Tester':
      chromeos_cmd_obj.AddExtractBuild(build_url)

    # Optionally cache built packages.
    if 'cache' in steps:
      chromeos_cmd_obj.AddCachePackages(options=options)

    # Add this cbuild link step.
    if factory_properties.get('download_link'):
      chromeos_cmd_obj.AddcbuildDownloadLinkStep(
          base_url=factory_properties.get('archive_url'))

    # Add this cbuild triagelink step.
    if factory_properties.get('triagelog_link'):
      chromeos_cmd_obj.AddcbuildTriageLogLinkStep(
          base_url=factory_properties.get('archive_url'))

    # Add this archive build step.
    if factory_properties.get('archive_build'):
      chromeos_cmd_obj.AddArchiveBuild(
          base_url=factory_properties.get('archive_url'),
          keep_max=factory_properties.get('archive_max', 0),
          gsutil_archive=factory_properties.get('gsutil_archive', ''),
          options=options)

    # Pushes temporary stable chagnes to git repo.
    # TODO(sosa) - Move to master bot once logic is complete to have it control
    # this step.
    if 'pre_flight_queue' in steps:
      chromeos_cmd_obj.AddChromeOSPreFlightStep('push',
          clobber, mode=mode, options=options, timeout=compile_timeout)

    # Do we need to trigger the Build Verification Test slave?
    if 'bvt' in steps:
      factory.addStep(trigger.Trigger(schedulerNames=['x86_full_bvt'],
                                      waitForFinish=False,
                                      set_properties={'main_buildnumber':
                                          WithProperties("%(buildnumber)s")}))

    # Revert official overlay if needed
    if 'overlay_official' in steps:
      chromeos_cmd_obj.AddRevertOfficialStep(
          clobber, mode=mode, options=options, timeout=compile_timeout)

    if 'note_success' in steps:
      chromeos_cmd_obj.AddNoteSuccess(options=options)

    return factory

  def BuildVerificationTestFactory(self):
    """Create a BuildFactory to run a build verification test slave."""
    factory = BuildFactory({})
    cmd_obj = chromeos_commands.ChromeOSCommands(factory,
                                                 'chromeos-x86-bvt',
                                                 'Release', '',
                                                 self._target_platform)
    cmd_obj.AddUpdateScriptStep()
    cmd_obj.AddBuildVerificationTestStep()
    return factory


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
      crosutils_repo: git repo for crosutils toolset.
  """

  # type is aliasing builtin.
  # pylint: disable=W0622
  def __init__(self, type=None, board='x86-generic', buildroot='/b/cbuild',
               triagelog=None, params='', timeout=9000, variant=None,
               is_master=False,
               crostools_repo='ssh://git@gitrw.chromium.org:9222/crostools',
               crosutils_repo='ssh://git@gitrw.chromium.org:9222/crosutils'):
    self.buildroot = buildroot
    self.crostools_repo = crostools_repo
    self.crosutils_repo = crosutils_repo
    self.timeout = timeout
    self.variant = variant
    self.board = board
    self.f_cbuild = chromeos_build_factory.BuildFactory()
    self.add_boiler_plate_steps()
    self.is_master = is_master

    if type == 'cbuildbot':
      self.cbuildbot_type(params)
    elif type == 'cbuild':
      self.cbuild_type(params)
    elif type == 'oneoff':
      self.oneoff_type()

    if triagelog:
      self.add_triagelog_step(triagelog)

  def _git_clear_and_checkout(self, repo):
    """
    rm -rf and clone the basename of the repo passed without .git

    Args:
      repo: ssh: uri for the repo to be checked out
    """
    git_checkout_dir = os.path.basename(repo).replace('.git', '')
    clear_and_clone_cmd = 'rm -rf %s ; sleep 10 ;' % git_checkout_dir
    clear_and_clone_cmd += '/usr/bin/git clone %s' % repo
    msg = 'Clear and Clone %s' % git_checkout_dir
    self.f_cbuild.addStep(shell.ShellCommand,
                          command=clear_and_clone_cmd,
                          name=msg,
                          description=msg)

  def add_boiler_plate_steps(self):
    """
    Add the following boiler plate steps to the factory.

    * gclient sync of /b
    * clearing of crostools/crosutils
    * clean checkout of crostools/crosutils
    """
    build_slave_sync = ['gclient', 'sync']
    self.f_cbuild.addStep(shell.ShellCommand,
                          command=build_slave_sync,
                          description='Sync buildbot slave files',
                          workdir='/b',
                          timeout=300)

    self._git_clear_and_checkout(self.crosutils_repo)
    self._git_clear_and_checkout(self.crostools_repo)

  def cbuildbot_type(self, params):
    # Gathers queued commits and drops them for cbuildbot to pick up.
    self.f_cbuild.addStep(chromeos_revision_source.GitRevisionDropper,
                          timeout=self.timeout)

    # Triggered cbuildbots (pfq slaves) have this property set.
    if self.is_master:
      self.f_cbuild.addStep(
          trigger.Trigger(schedulerNames=['pre_flight_queue_slaves'],
                          waitForFinish=False))

    cbuild_cmd = ['crosutils/bin/cbuildbot',
                  shell.WithProperties("--buildnumber=%(buildnumber)s")]
    cbuild_cmd += ['--buildroot=%s' % self.buildroot]
    cbuild_cmd += [('--revisionfile=%s' %
                   chromeos_revision_source.PFQ_REVISION_FILE)]
    clobber_string = WithProperties('%s', 'clobber:+--clobber')
    if clobber_string:
      cbuild_cmd.append(clobber_string)

    cbuild_cmd += params.split()
    self.f_cbuild.addStep(shell.ShellCommand,
                          command=cbuild_cmd,
                          timeout=self.timeout,
                          name='cbuildbot',
                          description='cbuildbot',
                          haltOnFailure=True)

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
