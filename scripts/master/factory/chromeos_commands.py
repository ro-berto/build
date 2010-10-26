# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory."""

import os

from buildbot.steps import shell
from buildbot.process.properties import WithProperties

from master.factory import commands
from master.log_parser import archive_command


def BoardName(options):
  if options.get('lasercats_variant'):
    return '%s_%s' % (options['lasercats_board'],
                      options['lasercats_variant'])
  else:
    return options['lasercats_board']


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
    # TODO(scottz): don't hard-code script path, but _private_script_dir above
    # doesn't work because workdir is not the default value.
    cmd = ['/b/build/scripts/private/chromeos_dev_config.sh', self._identifier]
    self._factory.addStep(shell.ShellCommand,
                          name='configure build',
                          description='configure build',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

  # 5 hour timeout
  def AddcbuildStep(self, clobber=False, mode=None, options=None,
                    timeout=18000, base_url=None):
    # XXX: If I can ever figure out how to symlink cbuild.log to a buildbot
    # viewable/accessible URL, I can turn -v off and add this link here to
    # the full log and let the main log just be a summary.
    cmd = ['/b/build/scripts/crostools/cbuild', '-v', '--clean', '--chromeos',
           '--buildroot=../../../..',
           WithProperties("--buildnumber=%(buildnumber)s")]

    self._factory.addStep(shell.ShellCommand,
                          name='cbuild',
                          description='cbuild',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

  def AddcbuildDownloadLinkStep(self, options=None, base_url=None):
    """Adds a step to the factory to archive a build."""
    cmd = ['sudo']
    self._factory.addStep(shell.ShellCommand,
                          name='Download Link',
                          description='Download Link',
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)


  def AddcbuildTriageLogLinkStep(self, timeout=120, options=None,
                                 base_url=None):
    """Adds a step to the factory to archive a build."""
    cmd = ['sudo']
    self._factory.addStep(shell.ShellCommand,
                          name='Error Summary',
                          description='Error Summary',
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

  def AddChromeOSMakeRepoStep(self, clobber=False, mode=None, options=None,
                             timeout=1200):
    cmd = ['./make_local_repo.sh',
           '--mirror=http://chromeos-deb.corp.google.com/ubuntu',
           '--suite=karmic']
    self._factory.addStep(shell.ShellCommand,
                          name='update local repo',
                          description='update local repo',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

  def AddChromeOSPublishRepoStep(self, clobber=False, mode=None, options=None,
                            timeout=1200):

    cmd = ['scp', '-r', 'db', 'dists', 'pool',
           'chrome-web.corp.google.com:/home/chrome-bot/www/packages']
    self._factory.addStep(shell.ShellCommand,
                          name='publish local repo',
                          description='publish local repo',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir='build/chromeos/repo/apt',
                          command=cmd)

  def AddChromeOSMakeChrootStep(self, clobber=False, mode=None, options=None,
                                timeout=3000):
    if options and options.get('lasercats'):
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
                         WithProperties('%s', 'clobber:+--replace'))]
      if options.get('lasercats_fast'):
        cmd += [options.get('lasercats_fast')]
    else:
      cmd = ['./make_chroot.sh', '--replace', '--nousepkg']
    self._factory.addStep(shell.ShellCommand,
                          name='update chroot',
                          description='update chroot',
                          timeout=3000,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

  def AddChromeOSSetupBoardStep(self, clobber=False, mode=None, options=None,
                                timeout=1200):
    if options and options.get('lasercats'):
      if options.get('lasercats_variant'):
        variant = ' --variant %s' % options['lasercats_variant']
      else:
        variant = ''
      cmd = self._enter_chroot + [
          './setup_board --force --board %s' % options.get('lasercats_board') +
          variant,
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

    if options and options.get('lasercats'):
      pass
    else:
      cmd = self._enter_chroot + ['rm -f ../build/x86/local_packages/*']
      self._factory.addStep(shell.ShellCommand,
                            name='clean local packages',
                            description='clean local packages',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir=self._build_dir,
                            command=cmd)

    if options and options.get('lasercats'):
      if options.get('lasercats_fast'):
        fast = ' ' + options.get('lasercats_fast')
      else:
        fast = ''
      buildbot_base_cmd = ('./build_packages --showoutput --retries 3 '
                           '--chromefromsource --board ')
      cmd = self._enter_chroot + [
            buildbot_base_cmd,
            BoardName(options) +
            ' ' + options.get('lasercats_jobs', '') +
            ' ' + options.get('lasercats_chromebase', '') +
            ' ' + options.get('lasercats_extra', '') +
            ' ' + options.get('lasercats_autotest', '') +
            fast
      ]
    else:
      cmd = self._enter_chroot + ['./build_platform_packages.sh']
    self._factory.addStep(shell.ShellCommand,
                          name='build packages',
                          description='build packages',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

  def AddChromeOSKernelStep(self, clobber=False, mode=None, options=None,
                            timeout=1200):

    cmd = self._enter_chroot + ['./build_kernel.sh']
    self._factory.addStep(shell.ShellCommand,
                          name='build kernel',
                          description='build kernel',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

  def AddChromeOSImageStep(self, clobber=False, mode=None, options=None,
                            timeout=1200):

    if options and options.get('lasercats'):
      pass
    else:
      cmd = self._enter_chroot + ['sudo rm -rf ../build/images/*']
      self._factory.addStep(shell.ShellCommand,
                            name='clean image',
                            description='clean image',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir=self._build_dir,
                            command=cmd)

    if options and options.get('lasercats'):
      if options.get('lasercats_fast'):
        fast = ' ' + options.get('lasercats_fast')
      else:
        fast = ''
      cmd = self._enter_chroot + [
            './build_image --replace --board ' + BoardName(options) + fast
      ]
    else:
      cmd = self._enter_chroot + ['./build_image.sh']
    self._factory.addStep(shell.ShellCommand,
                          name='build image',
                          description='build image',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)


  def AddChromeOSFactoryInstallStep(self, clobber=False, mode=None,
                                    options=None, timeout=1200):
    board = BoardName(options)
    cmd = self._enter_chroot + [
        './image_to_usb.sh ',
        '--factory_install',
        '-y',
        ' --force_copy',
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

      cmd = self._enter_chroot + [
          './cros_run_unit_tests --board ' + BoardName(options)]
      self._factory.addStep(shell.ShellCommand,
                            name='run tests',
                            description='run tests',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir=self._build_dir,
                            command=cmd)

  def AddChromeOSPreFlightStep(self, command, clobber=False, mode=None,
                                options=None, timeout=300):
    """Adds pre-flight steps for the slaves"""

    if command == 'clean':
      cmd = self._enter_chroot + [
            './cros_mark_as_stable clean']

      self._factory.addStep(shell.ShellCommand,
                            name='preflight clean',
                            description='preflight clean',
                            timeout=timeout,
                            haltOnFailure=False,
                            workdir=self._build_dir,
                            command=cmd)
    elif command == 'commit':
      cmd = self._enter_chroot + [
            './cros_mark_all_as_stable --board %s' % BoardName(options)]

      self._factory.addStep(shell.ShellCommand,
                            name='preflight all commit',
                            description='preflight all commit',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir=self._build_dir,
                            command=cmd)
    elif command == 'push':
      cmd = self._enter_chroot + [
        './cros_mark_as_stable --push_options "--bypass-hooks -f" push']

      self._factory.addStep(shell.ShellCommand,
                            name='preflight push',
                            description='preflight push',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir=self._build_dir,
                            command=cmd)


  def AddArchiveStep(self, data_description, base_url, link_text, command):
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
          '/b/build/scripts/gsd_generate_index/gsd_generate_index.py',
        '--gsutil', '/b/build/scripts/slave/gsutil',
    ]
    if options and options.get('lasercats'):
      cmd += ['' + options.get('lasercats_testmod', ''),
              '' + options.get('lasercats_factory1', ''),
              '' + options.get('lasercats_factory2', ''),
              '--board', BoardName(options)]
    self.AddArchiveStep(data_description='build', base_url=url,
                        link_text=text, command=cmd)

  def AddOverlayOfficialStep(self, clobber=False, mode=None, options=None,
                             timeout=1200):
    cmd = ['./overlay_official.sh']
    self._factory.addStep(shell.ShellCommand,
                          name='overlay official repo',
                          description='overlay official repo',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=self.PathJoin('build', 'official/scripts'),
                          command=cmd)

  def AddRevertOfficialStep(self, clobber=False, mode=None, options=None,
                            timeout=1200):
    cmd = ['gclient', 'revert']
    self._factory.addStep(shell.ShellCommand,
                          name='revert official overlay',
                          description='revert official overlay',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

  def AddNoteSuccess(self, options=None):
    board = BoardName(options)
    cmd = ['./save_pinned_deps',
           '--commit',
           '--substitute',
           '--depfile',
           board + '/build-full.gclient']
    self._factory.addStep(shell.ShellCommand,
                          name='save_pinned_deps',
                          description='save_pinned_deps',
                          timeout=300,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

  def AddCachePackages(self, options):
    cmd = ['sudo', 'chmod', 'a+rwx', '../../chroot/var/lib/portage/pkgs']
    self._factory.addStep(shell.ShellCommand,
                          name='access host packages',
                          description='access host packages',
                          timeout=1200,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)

    board = BoardName(options)
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
    board = BoardName(options)
    cmd = ['sudo', 'mkdir', '-p', '../../chroot/build/%s/packages' % board]
    self._factory.addStep(shell.ShellCommand,
                          name='mkdir board packages',
                          description='mkdir board packages',
                          timeout=1200,
                          haltOnFailure=True,
                          workdir=self._build_dir,
                          command=cmd)
    board = BoardName(options)
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
