# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""API for interacting with the siso, experimental build tool."""

import collections

from recipe_engine import recipe_api


class SisoApi(recipe_api.RecipeApi):
  """A module for interacting with siso."""

  def __init__(self, props, **kwargs):
    super().__init__(**kwargs)
    self._props = props
    # Initialization is delayed until ensure_siso.
    self._siso_path = None

  @property
  def enabled(self):
    """True if siso is configured."""
    return self._props.project and self._props.reapi_instance

  def _ensure_siso(self):
    """ensure siso is installed."""

    assert self.enabled, 'siso is not configured'
    self._siso_path = self.m.cipd.ensure_tool(
        'infra_internal/experimental/siso/${platform}',
        self._props.siso_version)

  def run_ninja(self, ninja_command, ninja_env, name, **kwargs):
    """Run the ninja command with siso.

        Args:
          ninja_command: Command used for build.
                     e.g. ['ninja', '-C', 'out/Release'],
          ninja_env: Environment for ninja.
          name: Name of compile step.

        Returns:
          A named tuple with the fields
           - failure_summary: string of the error that occurred during the step.
           - retcode: return code of the step

        Raises:
          - InfraFailure when an unexpected failure occured.
    """
    assert self.enabled, 'siso is not configured'
    self._assert_ninja_command(ninja_command)
    CompileResult = collections.namedtuple('CompileResult',
                                           'failure_summary retcode')

    cmd = [
        self.siso_path,
        'ninja',
        '--project',
        self._props.project,
    ]
    if self._props.reapi_address:
      cmd.extend([
          '--reapi_address',
          self._props.reapi_address,
      ])
    cmd.extend([
        '--reapi_instance',
        self._props.reapi_instance,
    ])
    if self._props.deps_log_bucket:
      cmd.extend([
          '--deps_log_bucket',
          self._props.deps_log_bucket,
      ])
    cmd.extend(['--enable_cloud_logging'])
    if self._props.enable_cloud_trace:
      cmd.extend(['--enable_cloud_trace'])
    if self._props.enable_cloud_profiler:
      cmd.extend(['--enable_cloud_profiler'])
    if self._props.action_salt:
      cmd.extend([
          '--action_salt',
          self._props.action_salt,
      ])
    cmd.extend(ninja_command[1:])
    env = ninja_env or {}
    if len(self._props.experiments) > 0:
      env['SISOEXPERIMENTS'] = ','.join(self._props.experiments)
    try:
      with self.m.context(env=env):
        ninja_step_result = self.m.step(name or 'compile', cmd, **kwargs)
    except self.m.step.StepFailure as ex:
      ninja_step_result = ex.result
      if ninja_step_result.retcode != 1:
        raise self.m.step.InfraFailure(
            ninja_step_result.name, result=ninja_step_result)
      failure_summary = ('(retcode=%d) No failure summary provided.' %
                         ninja_step_result.retcode)
      # TODO(ukai): set better failure summary output as chromium does.
      return CompileResult(
          failure_summary=failure_summary, retcode=ninja_step_result.retcode)
    finally:
      # TODO(ukai): clang crash report?
      # TODO(ukai): upload siso_metrics.json, siso_trace.json?
      pass

  def _assert_ninja_command(self, ninja_command):
    """Check ninja_command runs ninja

    Args:
      ninja_command: a list of command line.
                 e.g. ['ninja', '-C', 'out/Release']
    Returns:
      True if ninja_command runs ninja. False otherwise.
    """
    assert len(ninja_command) > 0, 'ninja_command is empty'
    cmdname = self.m.path.splitext(self.m.path.basename(ninja_command[0]))[0]
    assert cmdname == 'ninja', 'wrong command name'

  @property
  def siso_path(self):
    # TODO(ukai): decide path used in product tree.
    self._ensure_siso()
    return self._siso_path
