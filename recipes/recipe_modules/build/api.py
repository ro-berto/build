# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib

from recipe_engine import config_types, recipe_api

from RECIPE_MODULES.build.chromium_tests.steps import ResultDB


class ToolsBuildApi(recipe_api.RecipeApi):

  @property
  def bot_utils_args(self):
    """Returns (list): A list of arguments to supply to configure bot_utils
        parameters. See `bot_utils.py`'s AddArgs method.

    TODO(dnj): This function and its invocations should be deprecated in favor
    of using environment variables via "add_bot_utils_kwargs". The script
    invocation path for some of these is just too intertwined to confidently
    apply this via explicit args everywhere.
    """
    return [
        '--bot-utils-gsutil-py-path',
        self.m.depot_tools.gsutil_py_path,
    ]

  @contextlib.contextmanager
  def scripts_pythonpath(self):
    """Context manager to add the //scripts directory to PYTHONPATH."""
    with self.m.context(env_prefixes={
        'PYTHONPATH': [self.repo_resource('scripts')],
    }):
      yield

  @contextlib.contextmanager
  def recipes_pythonpath(self):
    """Context manager to add the //recipes directory to PYTHONPATH."""
    # Some of the modules in //recipes import modules from the //scripts
    # directory
    with self.scripts_pythonpath():
      with self.m.context(env_prefixes={
          'PYTHONPATH': [self.repo_resource('recipes')],
      }):
        yield

  def python(self,
             name,
             script,
             args=None,
             venv=None,
             resultdb=None,
             **kwargs):
    """Runs a python script with PYTHONPATH set to find common modules.

    This function has the same semantics as the "recipe_engine/python"
    module's __call__ method. It augments the call to add the //scripts
    and //recipes directory to PYTHONPATH.

    resultdb is an instance of chromium_tests.steps.ResultDB. If
    resultdb.enable is set to True, then the python script is wrapped
    with ResultSink and result_adapter before execution. For more info,
    find the doc-string of chromium_tests.steps.ResultDB.
    """
    cmd = ['vpython' if venv else 'python']
    if isinstance(venv, config_types.Path):
      cmd += ['-vpython-spec', venv]
    assert isinstance(resultdb,
                      (type(None), ResultDB)), "%s: %s" % (name, resultdb)

    cmd.append(script)
    if args:
      cmd.extend(args)

    if resultdb:
      cmd = resultdb.wrap(self.m, cmd, step_name=name)

    with self.recipes_pythonpath():
      # The same module will sometimes be imported via the root directory or via
      # the scripts/recipes directory, so include the root python path as well.
      # When migrating away from using build.python, the scripts should be
      # updated to instead import using the PYTHONPATH set using the
      # scripts_pythonpath or recipes_pythonpath instead so that common modules
      # can only be imported from a single path.
      with self.m.context(env_prefixes={
          'PYTHONPATH': [self.repo_resource()],
      }):
        with self.m.context(infra_steps=kwargs.pop('infra_step', None)):
          return self.m.step(name, cmd, **kwargs)
