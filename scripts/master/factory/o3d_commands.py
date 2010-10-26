# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This adds O3D specific commands. This is based on commands.py."""

from buildbot.steps import shell

from master.factory import commands
from master.log_parser import process_log


class O3DCommands(commands.FactoryCommands):
  """Encapsulates methods to add o3d commands to a buildbot factory."""

  def __init__(self, factory=None, identifier=None, target=None,
               build_dir=None, target_platform=None):

    commands.FactoryCommands.__init__(self, factory, identifier,
                                      target, build_dir, target_platform)
    # Where the chromium slave scripts are.
    self._chromium_script_dir = self.PathJoin(self._script_dir, 'chromium')
    self._o3d_script_dir = self.PathJoin(self._script_dir, 'o3d')
    self._private_script_dir = self.PathJoin(self._script_dir, '..', 'private')

    # For O3D project the code is at the root of the build directory.
    self._repository_root = ''

    J = self.PathJoin

    # Tool which prepares the test package.
    self._prepare_archive_command = J(self._o3d_script_dir,
                                      'prepare_selenium_tests.py')
    # Tool for archiving a single file.
    self._archive_file_tool = J(self._chromium_script_dir, 'archive_file.py')
    # Tool for uploading build archive to server.
    self._upload_zip_build_tool = J(self._o3d_script_dir, 'upload_build.py')
    # Tool which unpacks the test archive.
    self._unpack_archive_command = J(self._o3d_script_dir,
                                     'unpack_test_archive.py')
    if self._target_platform == 'linux2':
      self._unit_tests_env = {'LD_LIBRARY_PATH':
                              'out/Debug:third_party/glew/files/lib'}
    else:
      self._unit_tests_env = None
    # Command which runs Selenium tests.
    if self._target_platform == 'win32':
      base_test_dir = r'C:\auto\o3d\o3d'
      self._lab_tests_command = J(base_test_dir, r'tests\lab\run_lab_test.py')
      self._unit_tests_command = J(base_test_dir, 'build', self._target,
                                   'unit_tests.exe')
      self._unit_tests_local_command = r'o3d\build\Debug\unit_tests.exe'
    elif self._target_platform == 'darwin':
      base_test_dir = '/Users/testing/auto/o3d'
      self._lab_tests_command = J(base_test_dir, 'o3d/tests/lab',
                                  'run_lab_test.py')
      self._unit_tests_command = J(base_test_dir, 'xcodebuild', self._target,
                                   'unit_tests')
      self._unit_tests_local_command = 'xcodebuild/Debug/unit_tests'
    else:
      base_test_dir = '/home/testing/auto/o3d'
      self._lab_tests_command = J(base_test_dir, 'o3d/tests/lab',
                                  'run_lab_test.py')
      self._unit_tests_command = J(base_test_dir, 'out', self._target,
                                   'unit_tests')
      self._unit_tests_local_command = (
          'vncserver :32 ; '
          'DISPLAY=localhost:32 '
          'out/Debug/unit_tests')

    # Unit-tests which test performance of O3D.
    self._performance_test_command = J('o3d-internal', 'tests',
                                       'lab_automation',
                                       'performance_test.py')
    # Use hermetic python.
    if self._target_platform == 'win32':
      self._python = r'python_slave'
      self._lab_python = r'C:\Python26\python'
    else:
      self._python = self._lab_python = 'python'

  def PatchDEPS(self, mode, options=None, timeout=1200):
    if self._target_platform == 'win32':
      cmd = ['copy', '/Y', 'o3d\\DEPS_gyp', 'o3d\\DEPS']
    else:
      cmd = ['cp', 'o3d/DEPS_gyp', 'o3d/DEPS']
    self._factory.addStep(shell.ShellCommand,
                          description='patch deps',
                          timeout=timeout,
                          workdir='build',
                          command=cmd)

  def GClientUpdate(self, mode, options=None, timeout=1200):
    self._factory.addStep(shell.ShellCommand,
                          description='update again',
                          timeout=timeout,
                          workdir='build',
                          command=['gclient', 'update'])

  def GClientRunHooks(self, mode, options=None, timeout=1200, env=None):
    self._factory.addStep(shell.ShellCommand,
                          description='gclient runhooks',
                          timeout=timeout,
                          workdir='build',
                          env=env,
                          command=['gclient', 'runhooks', '--force'])

  def AddCompileStep(self, solution, clobber=False, description='compiling',
                     descriptionDone='compile', timeout=1200, mode=None,
                     options=None):
    if self._target_platform == 'win32':
      clobber_cmd = [(
          'rd /s /q o3d\\build\\Debug & '
          'rd /s /q o3d\\build\\Release & echo nop')]
    elif self._target_platform == 'darwin':
      clobber_cmd = 'rm -rf xcodebuild ; echo nop'
    else:
      clobber_cmd = 'rm -rf out sconsbuild ; echo nop'

    self._factory.addStep(shell.ShellCommand,
                          description='clobber',
                          timeout=timeout,
                          workdir='build',
                          command=clobber_cmd)

    if self._target_platform == 'darwin':
      cmd = ['xcodebuild', '-project', 'o3d/build/o3d.xcodeproj',
             '-configuration', self._target]
      env = {}
    elif self._target_platform == 'linux2':
      cmd = 'make -k V=1 BUILDTYPE=' + self._target
      env = {}
    elif self._target_platform == 'win32':
      cmd = ['devenv.com', 'o3d/build/o3d.sln', '/build', self._target]
      env = {
        'DXSDK_DIR':
           '$(SolutionDir)/../../o3d-internal/'
           'third_party/directx/v9_18_944_0_partial/files',
        'PATH':
           ';'.join([
             'c:\\b\\depot_tools',
             'c:\\b\\depot_tools\\python_bin',
             'C:\\WINDOWS\\system32',
             'C:\\WINDOWS\\system32\\WBEM',
             'c:\\Program Files\\Microsoft Visual Studio 8\\Common7\\IDE',
           ]),
      }
    else:
      assert False

    self._factory.addStep(shell.ShellCommand,
                          description='compile',
                          timeout=timeout,
                          workdir='build',
                          haltOnFailure=True,
                          flunkOnFailure=True,
                          env=env,
                          command=cmd)

  def AddArchiveTestPackageStep(self, out_dir, timeout=120):
    """Adds a step archiving tests and related resources for running in lab."""
    cmd = [self._python, self._prepare_archive_command,
           '.', out_dir]

    self._factory.addStep(shell.ShellCommand,
                          description='prepare test package',
                          timeout=timeout,
                          command=cmd)

  def AddUnpackTestArchiveStep(self, builder, timeout=120):
    """Adds a step that unpacks the test archive."""
    cmd = [self._python, self._unpack_archive_command, '--builder', builder]

    self._factory.addStep(shell.ShellCommand,
                          description='unpack test archive',
                          haltOnFailure=True,
                          flunkOnFailure=True,
                          timeout=timeout,
                          command=cmd)

  def AddUnitTestsStep(self, slave_type, timeout=60):
    if slave_type == 'Tester':
      cmd = self._unit_tests_command
    else:
      cmd = self._unit_tests_local_command
    env = self._unit_tests_env

    self._factory.addStep(shell.ShellCommand,
                          description='unit tests',
                          flunkOnFailure=True,
                          timeout=timeout,
                          env=env,
                          command=cmd)

  def AddQATestStep(self, timeout=7200):
    """Runs lab tests."""
    cmd = [self._lab_python, self._lab_tests_command]

    self._factory.addStep(shell.ShellCommand,
                          description='selenium tests',
                          flunkOnFailure=False,
                          warnOnFailure=True,
                          timeout=timeout,
                          command=cmd)

  def AddPerformanceTestStep(self, browser, factory_properties=None,
                             tests=None):
    """Runs the performance tests.

    Note: O3D must be installed on the machine beforing running this method.

    Args:
      factory_properties: list of properties for test specified in master.cfg.
      tests: list of test methods of PerformanceTestCase to run.
      browser: Selenium name of browser to run tests with.
    """
    factory_properties = factory_properties or {}

    # Log processor.
    c = self.GetPerfStepClass(factory_properties, 'performance',
                              process_log.GraphingLogProcessor)

    test_arg = ''
    for test in tests:
      test_arg += test + ','

    cmd = [self._python, self._performance_test_command,
           '--tests', test_arg,
           '--browser', browser,
           ]

    self.AddTestStep(c, browser + ' performance tests.', cmd)

  def AddUploadZipBuild(self):
    cmd = [self._python, self._upload_zip_build_tool]
    self._factory.addStep(shell.ShellCommand,
                          description='upload zipped build',
                          timeout=300,
                          workdir='build',
                          command=cmd)
