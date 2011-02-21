#!/usr/bin/python
# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

Contains the Native Client Ports specific commands. Based on commands.py"""

from buildbot.process.properties import WithProperties
from buildbot.steps import shell

from master.factory import commands
from master.log_parser import archive_command

import config

class NativeClientPortsCommands(commands.FactoryCommands):
  """Encapsulates methods to add nacl commands to a buildbot factory."""

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None):

    commands.FactoryCommands.__init__(self, factory, target, build_dir,
                                      target_platform)

    # Where to point waterfall links for builds and test results.
    self._archive_url = config.Master.archive_url

    # Where the chromium slave scripts are.
    self._chromium_script_dir = self.PathJoin(self._script_dir, 'chromium')
    self._private_script_dir = self.PathJoin(self._script_dir, '..', 'private')

    self._build_dir = self.PathJoin('build', build_dir)

    self._cygwin_env = {
      'PATH': (
        'c:\\cygwin\\bin;'
        'c:\\cygwin\\usr\\bin;'
        'c:\\WINDOWS\\system32;'
        'c:\\WINDOWS;'
        'e:\\b\depot_tools;'
      ),
    }
    self._runhooks_env = None
    self._build_compile_name = 'compile'
    self._gyp_build_tool = None
    self._build_env = {}
    self._repository_root = ''
    if target_platform.startswith('win'):
      self._build_env['PATH'] = (
          r'c:\cygwin\bin;'
          r'c:\native_client_sdk\third_party\cygwin\bin;'
          r'c:\WINDOWS\system32;'
          r'c:\WINDOWS;'
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
      )

    # Create smaller name for the functions and vars to siplify the code below.
    J = self.PathJoin
    s_dir = self._chromium_script_dir

    self._process_dumps_tool = self.PathJoin(self._script_dir,
                                             'process_dumps.py')

    # Scripts in the chromium scripts dir.  This list is sorted by decreasing
    # line length just because it looks pretty.
    self._differential_installer_tool = J(s_dir,  'differential_installer.py')
    self._process_coverage_tool = J(s_dir, 'process_coverage.py')
    self._layout_archive_tool = J(s_dir, 'archive_layout_test_results.py')
    self._crash_handler_tool = J(s_dir, 'run_crash_handler.py')
    self._layout_test_tool = J(s_dir, 'layout_test_wrapper.py')
    self._archive_coverage = J(s_dir, 'archive_coverage.py')
    self._crash_dump_tool = J(s_dir, 'archive_crash_dumps.py')
    self._dom_perf_tool = J(s_dir, 'dom_perf.py')
    self._archive_tool = J(s_dir, 'archive_build.py')
    self._archive_file_tool = J(s_dir, 'archive_file.py')
    self._sizes_tool = J(s_dir, 'sizes.py')

    if self._target_platform.startswith('win'):
      self.script_prefix = 'set PWD=&& '
      self.script_suffix = '.cmd'
    else:
      self.script_prefix = './'
      self.script_suffix = '.sh'

  def AddSdkSetup(self):
    download_script = 'build_tools/buildbot_sdk_setup.py'
    if self._target_platform.startswith('win'):
      download_script = 'python.bat ' + download_script
    self._factory.addStep(shell.ShellCommand,
                          description='setup-sdk',
                          timeout=1500,
                          workdir='build/src',
                          env=self._build_env,
                          haltOnFailure=True,
                          command=download_script)

  def AddCompileStep(self, solution, clobber=False, description='compiling',
                     descriptionDone='compile', timeout=1200, mode=None,
                     options=None):
    if clobber:
      clean_script = '%sbuildbot_cleanup_packages%s' % (
          self.script_prefix, self.script_suffix)
      self._factory.addStep(shell.ShellCommand,
                            description='cleanup-packages',
                            timeout=1500,
                            workdir='build/src/build_tools',
                            env=self._build_env,
                            haltOnFailure=True,
                            command=clean_script)
    build_script = '%sbuildbot_build_packages%s' % (
        self.script_prefix, self.script_suffix)
    self._factory.addStep(shell.ShellCommand,
                          description='build-packages',
                          timeout=1500,
                          workdir='build/src/build_tools',
                          env=self._build_env,
                          haltOnFailure=True,
                          command=build_script)

  def AddArchiveBuild(self, src, dst_base, dst,
                      data_description='build', mode='dev', show_url=True):
    """Adds a step to the factory to archive a build."""
    if show_url:
      url = '%s/%s' %  (self._archive_url, dst_base)
      text = 'download'
    else:
      url = None
      text = None

    cmd = [self._python, self._archive_file_tool,
           '--source', src,
           '--target', WithProperties('%s/%s' % (dst_base, dst))]

    if 'Ports' in self._target:
      cmd.append('--force-ssh')

    self.AddArchiveStep(data_description=data_description, base_url=url,
                        link_text=text, command=cmd)

  def AddArchiveStep(self, data_description, base_url, link_text, command):
    if self._target_platform.startswith('win'):
      env = self._cygwin_env.copy()
      env['PATH'] = r'e:\b\depot_tools;' + env['PATH']
    else:
      env = self._build_env
    step_name = ('archive_%s' % data_description).replace(' ', '_')
    self._factory.addStep(archive_command.ArchiveCommand,
                          name=step_name,
                          timeout=600,
                          description='archiving %s' % data_description,
                          descriptionDone='archived %s' % data_description,
                          base_url=base_url,
                          env=env,
                          link_text=link_text,
                          command=command)

  def AddTarballStep(self):
    """Adds a step to create a release tarball."""

    cmd = ' '.join([self._python, 'src/build_tools/generate_installers.py'])
    if self._target_platform.startswith('win'):
      cmd = 'vcvarsall x86 && ' + cmd
    self._factory.addStep(shell.ShellCommand,
                          description='cooking_tarball',
                          timeout=1500,
                          workdir='build',
                          env=self._build_env,
                          haltOnFailure=True,
                          command=cmd)

  def AddExtractBuild(self, url, factory_properties=None):
    """Adds a step to download and extract a previously archived build."""
    factory_properties = factory_properties or {}
    # TODO(bradnelson): make this work places besides linux.
    cmd = ('curl %s -o build.tgz && '
           'tar xfvz build.tgz') % url
    self._factory.addStep(shell.ShellCommand,
                          name='extract archive',
                          timeout=600,
                          workdir='build/native_client',
                          command=cmd)
