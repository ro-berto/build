# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib

from recipe_engine import config_types, recipe_api

from RECIPE_MODULES.build.chromium_tests.steps import ResultDB


class ToolsBuildApi(recipe_api.RecipeApi):

  @property
  def runit_py(self):
    return self.repo_resource('scripts', 'tools', 'runit.py')

  @property
  def slave_utils_args(self):
    """Returns (list): A list of arguments to supply to configure slave_utils
        parameters. See `slave_utils.py`'s AddArgs method.

    TODO(dnj): This function and its invocations should be deprecated in favor
    of using environment variables via "add_slave_utils_kwargs". The script
    invocation path for some of these is just too intertwined to confidently
    apply this via explicit args everywhere.
    """
    return [
        '--slave-utils-gsutil-py-path', self.m.depot_tools.gsutil_py_path,
    ]

  @contextlib.contextmanager
  def gsutil_py_env(self):
    """Augments environment with `slave_utils.py` parameters.
    """
    with self.m.context(env={
        'BUILD_SLAVE_UTILS_GSUTIL_PY_PATH':
        self.m.depot_tools.gsutil_py_path}):
      yield

  def python(self,
             name,
             script,
             args=None,
             venv=None,
             resultdb=None,
             **kwargs):
    """Bootstraps a Python through "tools/build"'s "runit.py".

    This function has the same semantics as the "recipe_engine/python" module's
    __call__ method. It augments the call to run the invoked script through
    "runit.py", which runs the targeted script within the "tools/build"
    Python path environment.

    resultdb is an instance of chromium_tests.steps.ResultDB.
    If resultdb.enable is set to True, then the python script is wrapped
    with ResultSink and result_adapter before execution.
    For more info, find the doc-string of chromium_tests.steps.ResultDB.
    """
    cmd = ['vpython' if venv else 'python']
    if isinstance(venv, config_types.Path):
      cmd += ['-vpython-spec', venv]
    assert isinstance(resultdb,
                      (type(None), ResultDB)), "%s: %s" % (name, resultdb)

    # Replace "script" positional argument with "runit.py".
    cmd.append(self.runit_py)
    cmd.append('--show-path')
    if not venv:
      cmd.append('--with-third-party-lib')
    cmd.extend(['--', 'python', script])
    if args:
      cmd.extend(args)

    if resultdb:
      cmd = resultdb.wrap(self.m, cmd, step_name=name)

    with self.m.context(infra_steps=kwargs.pop('infra_step', None)):
      return self.m.step(name, cmd, **kwargs)
