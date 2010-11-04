# Copyright (c) 2006-2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory."""

import os

from buildbot.steps import shell
from buildbot.process.properties import WithProperties

from master.factory import commands
from master.log_parser import archive_command


class ChromeOSCommands(commands.FactoryCommands):
  """Encapsulates methods to add ChromeOS commands to a buildbot factory."""

  def __init__(self, factory=None, identifier=None, target=None,
               build_dir=None, target_platform=None, target_arch=None,
               official_build=False):

    commands.FactoryCommands.__init__(self, factory, identifier,
                                      target, build_dir, target_platform)

    # Where the chromium slave scripts are.
    self._chromium_script_dir = self.PathJoin(self._script_dir, 'chromium')
    self._private_script_dir = self.PathJoin(self._script_dir, '..', 'private')
    self._build_tool = '/bin/bash'
    self._build_dir = self.PathJoin('build', build_dir)
    self._target_arch = target_arch
    self._official_build = official_build

    # If official build, change enter_chroot command line
    self._enter_chroot = ['./enter_chroot.sh']
    self._enter_chroot += ['--build_number',
                           WithProperties("%(buildnumber)s")]
    self._archive_build = ['./archive_build.sh',
                           '--build_number',
                           WithProperties("%(buildnumber)s")]

    if self._official_build:
      self._enter_chroot += ['--official_build']
      self._archive_build += ['--official_build']

    self._enter_chroot += ['--']

  def AddChromeOSRepoUpdateStep(self, clobber=False, mode=None, options=None,
                                timeout=2400):
    cmd = ['crosutils/bin/cros_repo_sync_all']
    # chromiumos set up by master.cfg.
    cmd += ['--buildroot=%s' % 'chromiumos']
    if clobber:
      cmd += ['--clobber']
    else:
      cmd.append(WithProperties('%s', 'clobber:+--clobber'))

    self._factory.addStep(shell.ShellCommand,
                          command=cmd,
                          name='Repo Sync',
                          description='Repo Sync',
                          haltOnFailure=True,
                          timeout=timeout)

  def AddChromeOSCrosUtilsStep(self,
      crosutils_repo='ssh://git@gitrw.chromium.org:9222/crosutils'):
    # Done in slave directory.
    git_checkout_dir = os.path.basename(crosutils_repo)
    clear_and_clone_cmd = 'rm -rf %s ; sleep 10 ;' % git_checkout_dir
    clear_and_clone_cmd += '/usr/bin/git clone %s' % crosutils_repo
    msg = 'Clear and Clone %s' % git_checkout_dir
    self._factory.addStep(shell.ShellCommand,
                          command=clear_and_clone_cmd,
                          name=msg,
                          description=msg)

  def AddChromeOSCopyConfigStep(self, clobber=False, mode=None, options=None,
                            timeout=1200):
    # TODO: don't hard-code script path, but _private_script_dir above doesn't
    # seem to be working...
    cmd = ['/b/scripts/private/chromeos_dev_config.sh', self._identifier]
    self._factory.addStep(shell.ShellCommand,
                          name='configure build',
                          description='configure build',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

  @staticmethod
  def BoardName(options):
    if options.get('lasercats_variant'):
      return '%s_%s' % (options['lasercats_board'],
                        options['lasercats_variant'])
    else:
      return options['lasercats_board']

  def AddChromeOSMakeChrootStep(self, clobber=False, mode=None, options=None,
                                timeout=3000):
    # Temporary workaround to use local mirror (and avoid blocked ftp sites).
    setup_cmd = 'cp ~/thirdpartymirrors ../third_party/portage/profiles'
    self._factory.addStep(shell.ShellCommand,
                          name='setup mirrors',
                          description='setup mirrors',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=setup_cmd)
    cmd = ['./make_chroot',
           options.get('lasercats_replace',
                       WithProperties('%s', 'clobber:+--replace')),
           options.get('lasercats_fast', '')
    ]
    self._factory.addStep(shell.ShellCommand,
                          name='update chroot',
                          description='update chroot',
                          timeout=3000,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

  def AddChromeOSSetupBoardStep(self, clobber=False, mode=None, options=None,
                                timeout=1200):
    if options.get('lasercats_variant'):
      variant = '--variant %s' % options['lasercats_variant']
    else:
      variant = ''
    cmd = self._enter_chroot + [
        './setup_board',
        '--force',
        '--board=%s' % options.get('lasercats_board'),
        variant
    ]
    self._factory.addStep(shell.ShellCommand,
                          name='setup board',
                          description='setup board',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

  def AddChromeOSPackagesStep(self, clobber=False, mode=None, options=None,
                              timeout=1200):

    cmd = self._enter_chroot + [
        './build_packages',
        '--showoutput',
        '--retries 3',
        '--chromefromsource',
        '--board=%s' % self.BoardName(options),
        options.get('lasercats_jobs', ''),
        options.get('lasercats_chromebase', ''),
        options.get('lasercats_extra', ''),
        options.get('lasercats_autotest', ''),
        options.get('lasercats_fast', '')
    ]

    self._factory.addStep(shell.ShellCommand,
                          name='build packages',
                          description='build packages',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

  def AddChromeOSImageStep(self, clobber=False, mode=None, options=None,
                           timeout=1200):
    cmd = self._enter_chroot + [
        './build_image',
        '--replace',
        '--board=%s' % self.BoardName(options),
        options.get('lasercats_fast', '')
    ]
    self._factory.addStep(shell.ShellCommand,
                          name='build image',
                          description='build image',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

  def AddChromeOSFactoryInstallStep(self, clobber=False, mode=None,
                                    options=None, timeout=1200):
    board = self.BoardName(options)
    cmd = self._enter_chroot + [
        './image_to_usb.sh',
        '--factory_install',
        '-y',
        '--force_copy',
        '--from=../build/images/%s/foo/' % board,
        '-i chromiumos_base_image.bin',
        '--to=../build/images/%s/foo/chromiumos_factory_install_image.bin' %
            board,
    ]
    self._factory.addStep(shell.ShellCommand,
                          name='factory image',
                          description='factory image',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

  def AddChromeOSTestSteps(self, tests, clobber=False, mode=None, options=None,
                          timeout=1200):
    if 'platform' in tests:
      unittest_cmd = self._enter_chroot + [
          './cros_run_unit_tests',
          '--board=%s' % self.BoardName(options)
      ]
      self._factory.addStep(shell.ShellCommand,
                            name='run tests',
                            description='run tests',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir=self._build_dir,
                            command=unittest_cmd)

    if 'target' in tests:
      image_cmd = self._enter_chroot + [
          './image_to_vm.sh',
          ' --board=%s' % self.BoardName(options),
          ' --test_image',
          ' --full',
          ' --vdisk_size=6074',
          ' --statefulfs_size=3072'
      ]

      test_cmd = ['bin/cros_run_vm_test',
          '--board=%s' % self.BoardName(options),
          '--no_graphics',
          '--test_case=suite_Smoke'
      ]

      self._factory.addStep(shell.ShellCommand,
                            name='create qemu image',
                            description='create qemu image',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir=self._build_dir,
                            command=image_cmd)

      self._factory.addStep(shell.ShellCommand,
                            name='run smoke bvt',
                            description='run smoke bvt',
                            timeout=timeout+2000,
                            haltOnFailure=True,
                            workdir=self._build_dir,
                            command=test_cmd)

  def _AddArchiveStep(self, data_description, base_url, link_text, command):
    step_name = ('archive_%s' % data_description).replace(' ', '_')
    self._factory.addStep(archive_command.ArchiveCommand,
                          name=step_name,
                          timeout=1200,
                          haltOnFailure=True,
                          description='archiving %s' % data_description,
                          descriptionDone='archived %s' % data_description,
                          base_url=base_url,
                          link_text=link_text,
                          index_suffix='/_index.html',
                          workdir=self._build_dir,
                          command=command)

  def AddArchiveBuild(self, base_url=None, keep_max=0, gsutil_archive='',
                      options=None):
    """Adds a step to the factory to archive a build."""
    if base_url:
      url = base_url + '/' + self._identifier
      text = 'download'
    else:
      url = None
      text = None

    # TODO: Currently, --to is based on a known config for the buildbot
    # slaves storing their build results locally.  When we can store the
    # results on chrome-web (after open source release), this needs
    # refactoring.
    cmd = self._archive_build + [
        '--to', '/var/www/archive/' + self._identifier,
        '--keep_max', str(keep_max),
        '--acl', '/home/chrome-bot/slave_archive_acl',
        '--gsutil_archive', gsutil_archive,
        '--gsd_gen_index',
          '/b/scripts/gsd_generate_index/gsd_generate_index.py',
        '--gsutil', '/b/scripts/slave/gsutil',
        '--prebuilt_upload',
    ]
    cmd += [
        options.get('lasercats_testmod', ''),
        options.get('lasercats_factory1', ''),
        options.get('lasercats_factory2', ''),
        '--board=%s' % self.BoardName(options)
    ]
    self._AddArchiveStep(data_description='build', base_url=url,
                        link_text=text, command=cmd)

  def AddCachePackages(self, options):
    cmd = ['sudo', 'chmod', 'a+rwx', '../../chroot/var/lib/portage/pkgs']
    self._factory.addStep(shell.ShellCommand,
                          name='access host packages',
                          description='access host packages',
                          timeout=1200,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

    board = self.BoardName(options)
    board_cache_dir = '/var/buildbot-package-cache/%s' % board
    host_cache_dir = '/var/buildbot-package-cache/host'
    # create cache dirs
    cmd = ['sudo', 'mkdir', '-p', board_cache_dir, host_cache_dir]
    self._factory.addStep(shell.ShellCommand,
                          name='Create cache dirs',
                          description='Create host and board cache dirs',
                          timeout=100,
                          haltOnFailure=True,
                          command=cmd)

    # Cache host packages.
    cmd = ['sudo', 'rsync', '-avz', '../../chroot/var/lib/portage/pkgs/',
           host_cache_dir]
    self._factory.addStep(shell.ShellCommand,
                          name='cache host packages',
                          description='cache host packages',
                          timeout=1200,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

    # Cache board packages.
    cmd = ['sudo', 'rsync', '-avz', '../../chroot/build/%s/packages/' % board,
           board_cache_dir]
    self._factory.addStep(shell.ShellCommand,
                          name='cache board packages',
                          description='cache board packages',
                          timeout=1200,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

  def AddRestorePackages(self, options):
    cmd = ['sudo', 'chmod', 'a+rwx', '../../chroot/var/lib/portage/pkgs']
    self._factory.addStep(shell.ShellCommand,
                          name='access host packages',
                          description='access host packages',
                          timeout=1200,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)
    # Restore host packages.
    cmd = ['sudo', 'rsync', '-avz',
           '/var/buildbot-package-cache/host/',
           '../../chroot/var/lib/portage/pkgs']
    self._factory.addStep(shell.ShellCommand,
                          name='restore host packages',
                          description='restore host packages',
                          timeout=1200,
                          haltOnFailure=False,
                          workdir=self._build_dir,
                          command=cmd)

    # Restore board packages.
    board = self.BoardName(options)
    cmd = ['sudo', 'mkdir', '-p', '../../chroot/build/%s/packages' % board]
    self._factory.addStep(shell.ShellCommand,
                          name='mkdir board packages',
                          description='mkdir board packages',
                          timeout=1200,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)
    board = self.BoardName(options)
    cmd = ['sudo', 'chown', '-R', 'chrome-bot:chrome-bot', '../../chroot/build']
    self._factory.addStep(shell.ShellCommand,
                          name='chown board packages',
                          description='chown board packages',
                          timeout=1200,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)
    cmd = ['sudo', 'rsync', '-avz',
           '/var/buildbot-package-cache/%s/' % board,
           '../../chroot/build/%s/packages' % board]
    self._factory.addStep(shell.ShellCommand,
                          name='restore board packages',
                          description='restore board packages',
                          timeout=1200,
                          haltOnFailure=False,
                          workdir=self._build_dir,
                          command=cmd)

  def AddBuildVerificationTestStep(self, clobber=False, mode=None, options=None,
                                   timeout=5400):
    # Add step to execute wait for bvt script, timeout is set at 1.5hrs,
    # imaging + bvt should average around an hour, 30 mins for padding.
    cmd = [self._private_script_dir + '/wait_for_bvt.sh',
           WithProperties("%(main_buildnumber)s")]

    self._factory.addStep(LinkShellCommand,
                          name='bvt',
                          description='bvt',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          link_text='dashboard',
                          base_url='http://cautotest/results/dashboard/',
                          command=cmd)


class LinkShellCommand(shell.ShellCommand):
  """Basic ShellCommand with support for adding a link for display."""

  def __init__(self, **kwargs):
    shell.ShellCommand.__init__(self, **kwargs)
    self.base_url = kwargs['base_url']
    self.link_text = kwargs['link_text']

  def createSummary(self, log):
    if (self.base_url and self.link_text):
      self.addURL(self.link_text, self.base_url)
