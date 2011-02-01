#!/usr/bin/python
# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

Contains the Native Client specific commands. Based on commands.py"""

from buildbot.process import buildstep
from buildbot.process.properties import WithProperties
from buildbot.steps import shell
from buildbot.steps import trigger
from buildbot.status.builder import FAILURE

from master import chromium_step
from master.factory import commands
from master.log_parser import archive_command
from master.log_parser import process_log

import config


class NativeClientCommands(commands.FactoryCommands):
  """Encapsulates methods to add nacl commands to a buildbot factory."""

  # pylint: disable-msg=W0212
  # (accessing protected member _NaClBase)
  PERF_BASE_URL = config.Master._NaClBase.perf_base_url

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None, options=None, test_target=None):
    if not options:
      options = {}

    if not test_target:
      test_target = target

    commands.FactoryCommands.__init__(self, factory, target, build_dir,
                                      target_platform)

    # Where to point waterfall links for builds and test results.
    self._archive_url = config.Master.archive_url

    # Where the chromium slave scripts are.
    self._chromium_script_dir = self.PathJoin(self._script_dir, 'chromium')
    self._private_script_dir = self.PathJoin(self._script_dir, '..', 'private')
    self._gsutil_dir = self.PathJoin(self._script_dir, '..', '..',
                                     'third_party', 'gsutil')

    self._build_dir = self.PathJoin('build', build_dir)
    self._toolchain_build_dir = self.PathJoin('build', build_dir, 'tools')

    self._cygwin_env = {
      'PATH': (
        r'c:\cygwin\bin;'
        r'c:\cygwin\usr\bin;'
        r'c:\WINDOWS\system32;'
        r'c:\WINDOWS;'
        r'c:\b\depot_tools;'
        r'c:\b\depot_tools\python_bin;'
        r'e:\b\depot_tools;'
        r'e:\b\depot_tools\python_bin;'
      ),
    }
    self._runhooks_env = None
    self._build_compile_name = 'compile'
    self._gyp_build_tool = None
    self._toolchain_build_env = {}
    self._build_env = {}
    self._gyp_build_env = {}

    # Figure out build tool.
    if self._target_platform == 'arm':
      self._toolchain_build_dir = self._build_dir
      self._toolchain_clobber_tool = 'rm -rf ../toolchain ../hg'
      # untrusted
      self._toolchain_build_tool = (
          'UTMAN_DEBUG=true tools/llvm/utman.sh download-trusted &&'
          'UTMAN_DEBUG=true '
          'tools/llvm/utman.sh untrusted_sdk arm-untrusted.tgz &&'
          'chmod a+r arm-untrusted.tgz')
      self._toolchain_sync_tool = ''
      self._toolchain_build_tar_tool = 'echo tar_built_in_for_llvm'
      self._toolchain_build_untar_tool = (
          'mkdir -p toolchain/linux_arm-untrusted &&'
          'cd toolchain/linux_arm-untrusted &&'
          'tar xfz ../../arm-untrusted.tgz')
      # trusted
      self._toolchain_trusted_build_tool = (
          'tools/llvm/trusted-toolchain-creator.sh '
          'trusted_sdk arm-trusted.tgz &&'
          'chmod a+r arm-trusted.tgz')
      self._toolchain_trusted_build_tar_tool = 'echo tar_built_in_for_llvm'
      self._toolchain_trusted_build_untar_tool = (
          'mkdir -p toolchain/linux_arm-trusted &&'
          'cd toolchain/linux_arm-trusted &&'
          'tar xfz ../../arm-trusted.tgz')
    else:
      self._toolchain_clobber_tool = (
        'rm -rf ../scons-out sdk-out sdk ../toolchain SRC BUILD || '
        'echo already_clean')
      if self._target_platform.startswith('win'):
        pwd = '`cygpath -u ${PWD}`'
      else:
        pwd = '`pwd`'
      toolchain_bits = options.get('toolchain_bits', 'multilib')
      if toolchain_bits == '32':
        extra64 = ''
      elif toolchain_bits == '64':
        extra64 = 'GCC_VERSION=4.4.2 CROSSARCH=nacl64 '
      elif toolchain_bits == 'multilib':
        extra64 = 'GCC_VERSION=4.4.3 CROSSARCH=nacl64 '
      else:
        assert False
      if self._target_platform.startswith('win'):
        extract_dir = 'win_x86'
      elif self._target_platform == 'darwin':
        extract_dir = 'mac_x86'
      else:
        extract_dir = 'linux_x86'
      self._toolchain_build_tool = (
        'MAKEINFO=%(pwd)s/makeinfo_dummy '
        'make clean build SDKLOC=%(pwd)s/sdk %(extra64)s') % {
            'pwd': pwd,
            'extra64': extra64,
        }
      self._toolchain_sync_tool = (
        '. ~/.bashrc && '
        'rm -rf SRC && '
        'git clone ssh://git@gitrw.chromium.org:9222/nacl-toolchain.git SRC && '
        'make prepare-git-src'
      )
      self._toolchain_build_tar_tool = (
        'tar cvfz naclsdk.tgz sdk/ &&'
        'chmod a+r naclsdk.tgz')
      self._toolchain_build_untar_tool = (
        'mkdir -p ../toolchain/%(extract_dir)s/.tmp &&'
        'cd ../toolchain/%(extract_dir)s/.tmp &&'
        'tar xfz ../../../tools/naclsdk.tgz &&'
        'mv sdk/nacl-sdk/* ../') % {
            'extract_dir': extract_dir,
        }
      if self._target_platform.startswith('win'):
        cache_config = (
          'GLOBAL_CONFIG_CACHE=/nacl_config_cache '
          'CONFIG_SITE=%(pwd)s/global_config_cache ') % {'pwd': pwd}
        self._toolchain_build_tool = cache_config + self._toolchain_build_tool
        self._toolchain_build_env = self._cygwin_env
        self._toolchain_build_tool = (
          'mkdir ..\\toolchain\\win_x86 && '
          "c:\\cygwin\\bin\\bash -c '%s'" % self._toolchain_build_tool)
        self._toolchain_build_tar_tool = (
          "c:\\cygwin\\bin\\bash -c '%s'" % self._toolchain_build_tar_tool)
        self._toolchain_build_untar_tool = (
          "c:\\cygwin\\bin\\bash -c '%s'" % self._toolchain_build_untar_tool)
        self._toolchain_clobber_tool = (
          "c:\\cygwin\\bin\\bash -c '%s'" % self._toolchain_clobber_tool)
        self._toolchain_sync_tool = (
          "c:\\cygwin\\bin\\bash -c '%s'" % self._toolchain_sync_tool)

    self._build_compile_name = 'scons_compile'
    if 'dbg' in target:
      configuration = 'Debug'
    else:
      configuration = 'Release'
    if self._target_platform.startswith('win'):
      if self._target_platform == 'win32':
        subarch = 'x86'
      else:
        subarch = 'x64'
      gyp_build = (
          'vcvarsall x86 && '
          'devenv.com build\\all.sln /build ' + configuration)
      scons = (
          'vcvarsall ' + subarch + ' && '
          'scons -j 8 DOXYGEN=..\\third_party\\doxygen\\win\\doxygen')
      scons_test = (
          'vcvarsall ' + subarch + ' && '
          'scons DOXYGEN=..\\third_party\\doxygen\\win\\doxygen')
      self._build_env = {
        'PATH': (
          r'c:\WINDOWS\system32;'
          r'c:\WINDOWS;'
          r'c:\b\depot_tools;'
          r'c:\b\depot_tools\python_bin;'
          r'e:\b\depot_tools;'
          r'e:\b\depot_tools\python_bin;'
          r'c:\Program Files\Microsoft Visual Studio 9.0\VC;'
          r'c:\Program Files (x86)\Microsoft Visual Studio 9.0\VC;'
          r'c:\Program Files\Microsoft Visual Studio 9.0\Common7\Tools;'
          r'c:\Program Files (x86)\Microsoft Visual Studio 9.0\Common7\Tools;'
          r'c:\Program Files\Microsoft Visual Studio 8\VC;'
          r'c:\Program Files (x86)\Microsoft Visual Studio 8\VC;'
          r'c:\Program Files\Microsoft Visual Studio 8\Common7\Tools;'
          r'c:\Program Files (x86)\Microsoft Visual Studio 8\Common7\Tools;'
          r'c:\Program Files\Microsoft Visual Studio 9.0'
             r'\Team Tools\Performance Tools;'
          r'c:\Program Files (x86)\Microsoft Visual Studio 9.0'
              r'\Team Tools\Performance Tools;'
          r'c:\Program Files\Microsoft Visual Studio 8'
             r'\Team Tools\Performance Tools;'
          r'c:\Program Files (x86)\Microsoft Visual Studio 8'
              r'\Team Tools\Performance Tools;'
          r'c:\Program Files\Microsoft Visual Studio 9.0'
             r'\Team Tools\Performance Tools;'
          r'c:\Program Files (x86)\Microsoft Visual Studio 9.0'
              r'\Team Tools\Performance Tools;'
        ),
      }
      self._gyp_build_env = self._build_env
      self._clobber_tool = (
          'rd /s /q scons-out & '
          'rd /s /q toolchain & '
          'rd /s /q build\\Debug build\\Release & '
          'rd /s /q build\\Debug-Win32 build\\Release-Win32 & '
          'rd /s /q build\\Debug-x64 build\\Release-x64 & '
          'echo already_clean '
      )
      self._clobber_packages_tool = (
        'c:\\cygwin\\bin\\bash -c ./nacl-clean-all.sh')
      self._clobber_packages_env = self._cygwin_env
    else:
      if self._target_platform == 'darwin':
        gyp_build = ('xcodebuild -project build/all.xcodeproj '
                     '-configuration ' + configuration)
        scons = './scons -j 8 DOXYGEN=../third_party/doxygen/osx/doxygen'
        scons_test = './scons DOXYGEN=../third_party/doxygen/osx/doxygen'
      elif self._target_platform == 'arm':
        gyp_build = 'cd .. ; make -k -j4 V=1 BUILDTYPE=' + configuration
        scons = './scons -j 8 DOXYGEN=../third_party/doxygen/linux/doxygen'
        scons_test = './scons DOXYGEN=../third_party/doxygen/linux/doxygen'
        # For now we will assume a fixed toolchain location on the builders.
        crosstool_prefix = (
            'native_client/toolchain/linux_arm-trusted/arm-2009q3/'
            'bin/arm-none-linux-gnueabi')
        # Setup environment to use arm cross toolchain.
        crosstool_env = {
          'AR': crosstool_prefix + '-ar',
          'AS': crosstool_prefix + '-as',
          'CC': crosstool_prefix + '-gcc',
          'CXX': crosstool_prefix + '-g++',
          'LD': crosstool_prefix + '-ld',
          'RANLIB': crosstool_prefix + '-ranlib',
          'GYP_GENERATORS': 'make',
          'GYP_DEFINES': (
              'target_arch=arm '
              'sysroot=native_client/toolchain/linux_arm-trusted'
              '/arm-2009q3/arm-none-linux-gnueabi/libc '
              'linux_use_tcmalloc=0 '
              'armv7=1 '
              'arm_thumb=1 '
          ),
        }
        self._build_env = crosstool_env
        self._runhooks_env = crosstool_env
        self._gyp_build_env = crosstool_env
      elif self._target_platform == 'linux2':
        gyp_build = ('cd .. && '
                     'make -k -j12 V=1 BUILDTYPE=' + configuration)
        scons = './scons -j 8 DOXYGEN=../third_party/doxygen/linux/doxygen'
        scons_test = './scons DOXYGEN=../third_party/doxygen/linux/doxygen'
      else:
        assert False
      self._clobber_tool = (
          'rm -rf scons-out toolchain compiler hg '
          '../xcodebuild ../sconsbuild ../out '
          'src/third_party/nacl_sdk/arm-newlib')
      self._clobber_packages_tool = './nacl-clean-all.sh'
      self._clobber_packages_env = {}
    self._gyp_build_tool = gyp_build
    self._gyp_test_tool = 'python trusted_test.py'
    if 'dbg' in target:
      self._gyp_test_tool += ' --config Debug'
    else:
      self._gyp_test_tool += ' --config Release'
    self._build_tool = '%s -k --verbose --mode=%s' % (scons, target)
    self._test_tool = '%s -k --verbose --mode=%s' % (scons_test, test_target)

    self._repository_root = ''

    # Create smaller name for the functions and vars to siplify the code below.
    J = self.PathJoin
    s_dir = self._chromium_script_dir

    self._process_dumps_tool = self.PathJoin(self._script_dir,
                                             'process_dumps.py')

    # Scripts in the chromium scripts dir.  This list is sorted by decreasing
    # line length just because it looks pretty.
    self._differential_installer_tool = J(s_dir, 'differential_installer.py')
    self._process_coverage_tool = J(s_dir, 'process_coverage.py')
    self._layout_archive_tool = J(s_dir, 'archive_layout_test_results.py')
    self._crash_handler_tool = J(s_dir, 'run_crash_handler.py')
    self._layout_test_tool = J(s_dir, 'layout_test_wrapper.py')
    self._archive_coverage = J(s_dir, 'archive_coverage.py')
    self._crash_dump_tool = J(s_dir, 'archive_crash_dumps.py')
    self._dom_perf_tool = J(s_dir, 'dom_perf.py')
    self._archive_tool = J(s_dir, 'archive_build.py')
    self._archive_file_tool = J(s_dir, 'archive_file.py')
    self._gsutil_tool = J(self._gsutil_dir, 'gsutil')
    self._sizes_tool = J(s_dir, 'sizes.py')

    # Setup gsutil path.
    self._build_env['GSUTIL'] = self._gsutil_tool

  def GClientRunHooks(self, mode, options=None, timeout=1200):
    self._factory.addStep(shell.ShellCommand,
                          name='gclient_runhooks',
                          description='gclient_runhooks',
                          timeout=timeout,
                          workdir=self._build_dir,
                          env=self._runhooks_env,
                          command=['gclient', 'runhooks', '--force'])

  def AddCompileStep(self, solution, clobber=False, description='compiling',
                     descriptionDone='compile', timeout=1200, mode=None,
                     options=None):
    cmd = self._build_tool

    options = options or {}

    if options.get('scons_prefix'):
      cmd = options['scons_prefix'] + cmd
    if options.get('scons_opts'):
      cmd = cmd + ' ' + options['scons_opts']

    # Tar build result on arm.
    if self._target_platform == 'arm':
      cmd += ' && tar cvfz arm.tgz scons-out/'

    # Tar build result on vista64.
    if self._target_platform == 'win64':
      cmd += '&& set PATH=c:\\cygwin\\bin;%PATH%'
      cmd += '&& tar cvfz vista64.tgz scons-out/'

    if not self._target_platform.startswith('win'):
      cmd = 'bash -c " ' + cmd + ' "'

    toolchain_cmd = self._toolchain_build_tool
    toolchain_sync_cmd = self._toolchain_sync_tool
    toolchain_tar_cmd = self._toolchain_build_tar_tool
    toolchain_untar_cmd = self._toolchain_build_untar_tool
    if options.get('just_trusted'):
      toolchain_cmd = self._toolchain_trusted_build_tool
      toolchain_tar_cmd = self._toolchain_trusted_build_tar_tool
      toolchain_untar_cmd = self._toolchain_trusted_build_untar_tool
    if not self._target_platform.startswith('win'):
      toolchain_cmd = 'bash -c " ' + toolchain_cmd + ' "'
      toolchain_sync_cmd = 'bash -c " ' + toolchain_sync_cmd + ' "'
      toolchain_tar_cmd = 'bash -c " ' + toolchain_tar_cmd + ' "'
      toolchain_untar_cmd = 'bash -c " ' + toolchain_untar_cmd + ' "'

    build_toolchain = options.get('build_toolchain')

    if clobber:
      if build_toolchain:
        self._factory.addStep(shell.ShellCommand,
                              description='clobber_toolchain',
                              timeout=timeout,
                              haltOnFailure=True,
                              workdir=self._toolchain_build_dir,
                              env=self._toolchain_build_env,
                              command=self._toolchain_clobber_tool)
      self._factory.addStep(shell.ShellCommand,
                            description='clobber',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir=self._build_dir,
                            env=self._build_env,
                            command=self._clobber_tool)
    if clobber and options.get('build_packages'):
      self._factory.addStep(shell.ShellCommand,
                            description='clobber_packages',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir='build/native_client_sdk/packages',
                            env=self._clobber_packages_env,
                            command=self._clobber_packages_tool)
    partial_sdk = options.get('partial_sdk')
    if build_toolchain:
      if options.get('git_toolchain'):
        self._factory.addStep(shell.ShellCommand,
                              description='sync_from_git',
                              timeout=timeout,
                              haltOnFailure=True,
                              workdir=self._toolchain_build_dir,
                              env=self._toolchain_build_env,
                              command=toolchain_sync_cmd)
      self._factory.addStep(shell.ShellCommand,
                            description='compile_toolchain',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir=self._toolchain_build_dir,
                            env=self._toolchain_build_env,
                            command=toolchain_cmd)
      self._factory.addStep(shell.ShellCommand,
                            description='tar_toolchain',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir=self._toolchain_build_dir,
                            env=self._toolchain_build_env,
                            command=toolchain_tar_cmd)
      self._factory.addStep(shell.ShellCommand,
                            description='untar_toolchain',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir=self._toolchain_build_dir,
                            env=self._toolchain_build_env,
                            command=toolchain_untar_cmd)
    if partial_sdk and not build_toolchain:
      self._factory.addStep(shell.ShellCommand,
                            name='partial_sdk',
                            description='partial_sdk',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir=self._build_dir,
                            env=self._build_env,
                            command=options['partial_sdk'])
    if self._gyp_build_tool:
      self._factory.addStep(shell.ShellCommand,
                            name='gyp_compile',
                            description='gyp_compile',
                            timeout=timeout,
                            haltOnFailure=False,
                            workdir=self._build_dir,
                            env=self._gyp_build_env,
                            command=self._gyp_build_tool)
      self._factory.addStep(shell.ShellCommand,
                            name='gyp_tests',
                            description='gyp_tests',
                            timeout=timeout,
                            haltOnFailure=False,
                            workdir=self._build_dir,
                            env=self._gyp_build_env,
                            command=self._gyp_test_tool)
    if self._target_platform != 'arm' or not build_toolchain:
      self._factory.addStep(shell.ShellCommand,
                            name=self._build_compile_name,
                            description=self._build_compile_name,
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir=self._build_dir,
                            env=self._build_env,
                            command=cmd)
    if options and options.get('build_packages'):
      if self._target_platform.startswith('win'):
        pack_cmd = 'c:\\cygwin\\bin\\bash -c ./nacl-install-all.sh'
        pack_env = self._cygwin_env
      else:
        pack_cmd = './nacl-install-all.sh'
        pack_env = self._build_env
      self._factory.addStep(shell.ShellCommand,
                            description='build_packages',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir='build/native_client_sdk/packages',
                            env=pack_env,
                            command=pack_cmd)

  def AddBrowserTests(self, clobber=False, options=None,
                      timeout=1200, run_selenium=True):
    """Adds a step archiving samples and installers to run on QA machines."""
    cmd = '%s SILENT=1' % self._test_tool
    if options and options.get('scons_prefix'):
      cmd = options['scons_prefix'] + cmd
    if options and options.get('scons_opts'):
      cmd = cmd + ' ' + options['scons_opts']
    self.AddTestStep(
        shell.ShellCommand,
        test_name='backup_plugin', timeout=1500,
        test_command='%s firefox_install_backup' % cmd,
        workdir='build/native_client',
        env=self._build_env,
        locks=[self.slave_exclusive_lock])
    if self._target_platform in ['arm', 'linux2']:
      self.AddTestStep(
          shell.ShellCommand,
          test_name='start_vncserver', timeout=1500,
          test_command=(
              'vncserver -kill :20 ; '
              'sleep 2 ; '
              'vncserver :20 -geometry 1500x1000 -depth 24 ; '
              'sleep 10'),
          workdir='build/native_client',
          env=self._build_env,
          locks=[self.slave_exclusive_lock])
      gui_prefix = (
        'DISPLAY=localhost:20 '
        'XAUTHORITY=/home/chrome-bot/.Xauthority ')
    else:
      gui_prefix = ''
    self.AddTestStep(
        shell.ShellCommand,
        test_name='chrome_browser_tests', timeout=1500,
        test_command=gui_prefix + '%s chrome_browser_tests' % cmd,
        workdir='build/native_client',
        env=self._build_env,
        locks=[self.slave_exclusive_lock])
    if run_selenium:
      self.AddTestStep(
          shell.ShellCommand,
          test_name='install_plugin', timeout=1500,
          test_command='%s firefox_install' % cmd,
          workdir='build/native_client',
          env=self._build_env,
          locks=[self.slave_exclusive_lock])
      self.AddTestStep(
          shell.ShellCommand,
          test_name='selenium', timeout=1500,
          test_command=gui_prefix + '%s browser_tests' % cmd,
          workdir='build/native_client',
          env=self._build_env,
          locks=[self.slave_exclusive_lock])
      self.AddTestStep(
          shell.ShellCommand,
          test_name='restore_plugin', timeout=1500,
          test_command='%s firefox_install_restore' % cmd,
          workdir='build/native_client',
          env=self._build_env,
          locks=[self.slave_exclusive_lock])
    if self._target_platform in ['arm', 'linux2']:
      self.AddTestStep(
          shell.ShellCommand,
          test_name='stop_vncserver', timeout=1500,
          test_command='vncserver -kill :20',
          workdir='build/native_client',
          env=self._build_env,
          locks=[self.slave_exclusive_lock])

  def AddCoverageTests(self, clobber=False, options=None,
                       timeout=1200):
    """Adds a step that runs coverage tests."""
    cmd = self._test_tool
    if options and options.get('scons_prefix'):
      cmd = options['scons_prefix'] + cmd
    if options and options.get('scons_opts'):
      cmd = cmd + ' ' + options['scons_opts']
    self.AddTestStep(
        shell.ShellCommand,
        test_name='coverage', timeout=1500,
        test_command='%s coverage' % cmd,
        workdir='build/native_client',
        env=self._build_env,
        locks=[self.slave_exclusive_lock])

  def AddTrigger(self, trigger_who):
    # TODO(nsylvain): Switch back waitForFinish to True once all the netbook
    # and arm boards are online.
    self._factory.addStep(trigger.Trigger(schedulerNames=[trigger_who],
                                          waitForFinish=False))

  def AddSizedTests(self, test_size, full_name=None, options=None, timeout=300):
    """Add a build step to run tests of a given size."""
    test_name = '%s_tests' % test_size
    if full_name:
      test_name = full_name
    cmd = '%s %s' % (self._test_tool, test_name)
    if options and options.get('scons_prefix'):
      cmd = options['scons_prefix'] + cmd
    if options and options.get('scons_opts'):
      cmd = cmd + ' ' + options['scons_opts']
    if not self._target_platform.startswith('win'):
      cmd = 'bash -c " ' + cmd + ' "'
    self.AddTestStep(
        shell.ShellCommand,
        test_name=test_name, timeout=timeout,
        test_command=cmd,
        workdir='build/native_client',
        env=self._build_env,
        locks=[self.slave_exclusive_lock])

  def AddUtmanTests(self, platform, options=None, timeout=300):
    """Add a build step to run utman tests."""
    self.AddTestStep(
        shell.ShellCommand,
        test_name='test-' + platform, timeout=timeout,
        test_command='UTMAN_DEBUG=true tools/llvm/utman.sh test-' + platform,
        workdir='build/native_client',
        env=self._build_env,
        locks=[self.slave_exclusive_lock])

  def AddMemcheck(self, options=None):
    """Adds a Memcheck test step."""
    cmd = ('%s platform=x86-64 sdl=none '
           'buildbot=memcheck memcheck_bot_tests') % self._test_tool
    self.AddTestStep(
        shell.ShellCommand,
        test_name='memcheck', timeout=10000,
        test_command=cmd,
        workdir='build/native_client',
        env=self._build_env,
        locks=[self.slave_exclusive_lock])

  def AddThreadSanitizer(self, trusted=False, hybrid=False, race_verifier=False,
                         options=None):
    """Adds a ThreadSanitizer test step."""
    preset_name = 'tsan'
    if trusted:
      preset_name = 'tsan-trusted'
    extra_args = []
    if hybrid:
      extra_args.append('--hybrid')
    # TODO(eugenis): Support per-process logs for forking tests.
    if race_verifier:
      extra_args.append('--log-file=race.log')
    cmd = ('%s platform=x86-64 sdl=none '
           'buildbot=%s run_under_extra_args=%s tsan_bot_tests') % (
               self._test_tool, preset_name, ','.join(extra_args))
    if race_verifier:
      extra_args = ['--race-verifier=race.log']
      cmd2 = ('%s platform=x86-64 sdl=none '
              'buildbot=%s run_under_extra_args=%s tsan_bot_tests') % (
                  self._test_tool, preset_name, ','.join(extra_args))
      cmd = cmd + "; echo -e '\n\n== RaceVerifier 2nd run ==\n\n\'; " + cmd2
    test_name = []
    if trusted:
      test_name.append('trusted')
    else:
      test_name.append('untrusted')
    if hybrid:
      test_name.append('hybrid')
    if race_verifier:
      test_name.append('RV')
    self.AddTestStep(
        shell.ShellCommand,
        test_name='tsan(' + ', '.join(test_name) + ')',
        timeout=20000,
        test_command=cmd,
        workdir='build/native_client',
        env=self._build_env,
        locks=[self.slave_exclusive_lock])

  def DropDoxygen(self):
    """Adds a step to drop doxygen from the tarballs."""
    if self._target_platform.startswith('win'):
      cmd = ('rmdir /q /s ..\\third_party\\doxygen & '
             'rmdir /q /s ..\\doxygen.DEPS & echo nop')
    else:
      cmd = 'rm -rf ../third_party/doxygen ../doxygen.DEPS'
    self._factory.addStep(shell.ShellCommand,
                          name='drop doxygen',
                          timeout=600,
                          command=cmd)

  def AddArchiveCoverage(self, coverage_dir):
    """Adds a step to the factory to archive coverage."""
    url = ('http://gsdview.appspot.com/nativeclient-coverage/'
           'revs/%(got_revision:-other)s/' + coverage_dir + '/html/index.html')

    src = 'native_client/scons-out/%s/coverage' % coverage_dir
    dst_path = ('nativeclient-coverage2/revs/%(got_revision:-other)s/' +
                coverage_dir)
    dst = 'gs://' + dst_path
    index_path = '/html/index.html'
    url = '@@@link@view@http://gsdview.appspot.com/' + dst_path + index_path

    env = self._build_env.copy()
    if self._target_platform.startswith('win'):
      env['GSUTIL'] = r'e:\b\build\scripts\slave\gsutil.bat'
      env['HOME'] = r'c:\Users\chrome-bot'

    cmd = [self._python, '/b/build/scripts/slave/gsutil_cp_dir.py',
           '--message', url, src, dst]
    cmd = WithProperties(' '.join(cmd))
    self._factory.addStep(AnnotatedCommand,
                          name='archive_coverage',
                          timeout=600,
                          haltOnFailure=True,
                          description='archiving coverage',
                          descriptionDone='archived coverage',
                          env=env,
                          command=cmd)

  def AddArchiveBuild(self, src, dst_base, dst, mode='dev', show_url=True):
    """Adds a step to the factory to archive a build."""
    if show_url:
      url = '%s/nacl_archive/%s' %  (self._archive_url, dst_base)
      text = 'download'
    else:
      url = None
      text = None

    full_dst = WithProperties(
        'gs://nativeclient-archive2/%s/%s' % (dst_base, dst))

    cmd = [self._python,
           '/b/build/scripts/command_wrapper/bin/command_wrapper.py',
           '--', self._python, self._gsutil_tool, 'cp', src, full_dst]
    cmd2 = [self._python,
            '/b/build/scripts/command_wrapper/bin/command_wrapper.py',
            '--', self._python, self._gsutil_tool,
            'setacl', 'public-read', full_dst]

    self.AddArchiveStep(data_description='build', base_url=url,
                        link_text=text, command=cmd, command2=cmd2)

  def AddArchiveStep(self, data_description, base_url, link_text, command,
                     command2=None):
    if self._target_platform.startswith('win'):
      env = self._cygwin_env.copy()
      env['PATH'] = r'e:\b\depot_tools;' + r'c:\b\depot_tools;' + env['PATH']
      env['HOME'] = r'c:\Users\chrome-bot'
    else:
      env = self._build_env
    step_name = ('archive_%s' % data_description).replace(' ', '_')
    self._factory.addStep(archive_command.ArchiveCommand,
                          name=step_name,
                          timeout=600,
                          haltOnFailure=True,
                          description='archiving %s' % data_description,
                          descriptionDone='archived %s' % data_description,
                          base_url=base_url,
                          env=env,
                          link_text=link_text,
                          command=command)
    if command2:
      self._factory.addStep(shell.ShellCommand,
                            name='setting_acls',
                            timeout=600,
                            haltOnFailure=True,
                            description='setting_acls',
                            env=env,
                            command=command2)

  def AddTarballStep(self, name, show_url=True):
    """Adds a step to create a release tarball."""

    if self._target_platform.startswith('win'):
      prefix = 'vcvarsall x86 && '
      ext = '.zip'
    else:
      prefix = ''
      ext = '.tgz'

    cmd = ' '.join([prefix, self._python, 'cook_tarball.py',
                    name, self._target])

    self._factory.addStep(shell.ShellCommand,
                          description='cooking_tarball',
                          timeout=1500,
                          workdir='build/native_client/build',
                          env=self._build_env,
                          haltOnFailure=True,
                          command=cmd)
    self.AddArchiveBuild('native_client/build/' + name + ext,
                         'nacl_archive/nacl_tarballs/latest',
                         name + ext)

  def AddExtractBuild(self, url):
    """Adds a step to download and extract a previously archived build."""
    if self._target_platform.startswith('win'):
      env = self._cygwin_env
    else:
      env = self._build_env
    cmd = WithProperties(('curl -L %s -o build.tgz && '
                         'tar xvfz build.tgz --no-same-owner') % url)
    self._factory.addStep(shell.ShellCommand,
                          name='extract_archive',
                          description='extract archive',
                          timeout=600,
                          env=env,
                          haltOnFailure=True,
                          workdir='build/native_client',
                          command=cmd)

  def AddModularBuildStep(self, modular_build_type, timeout=1200):
    self._factory.addStep(shell.ShellCommand,
                          name='modular_build',
                          description='modular_build',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir='build/native_client/tools/modular-build',
                          command='python build_for_buildbot.py %s' %
                            modular_build_type)

  def AddAnnotatedStep(self, command, timeout=1200,
                       workdir='build/native_client', haltOnFailure=True,
                       factory_properties=None):
    factory_properties = factory_properties or {}
    if 'test_name' not in factory_properties:
      test_class = AnnotatedCommand
    else:
      test_name = factory_properties.get('test_name')
      test_class = self.GetPerfStepClass(factory_properties, test_name,
                                         process_log.GraphingLogProcessor,
                                         command_class=AnnotatedCommand)
    self._factory.addStep(test_class,
                          name='annotate',
                          description='annotate',
                          timeout=timeout,
                          haltOnFailure=haltOnFailure,
                          workdir=workdir,
                          command=command)


class AnnotationObserver(buildstep.LogLineObserver):
  """This class knows how to understand annotations."""

  def __init__(self, command):
    buildstep.LogLineObserver.__init__(self)
    self.command = command
    self.links = []

  def outLineReceived(self, line):
    """This is called once with each line of the test log."""
    if line.startswith('@@@link@'):
      self.links.append(line.strip()[8:].split('@'))
    if line.startswith('@@@BUILD_FAILED@@@'):
      self.command.failed(FAILURE)


class AnnotatedCommand(chromium_step.ProcessLogShellStep):
  """Buildbot command that knows how to display annotations."""

  def __init__(self, **kwargs):
    chromium_step.ProcessLogShellStep.__init__(self, **kwargs)
    self.script_observer = AnnotationObserver(self)
    self.addLogObserver('stdio', self.script_observer)

  def createSummary(self, log):
    for link in self.script_observer.links:
      self.addURL(link[0], link[1])
