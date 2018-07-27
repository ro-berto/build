# Copyright 2016 The LUCI Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.

"""Tests a recipe CL by running a chromium builder."""

from recipe_engine.recipe_api import Property

DEPS = [
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/led',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',

  'depot_tools/gclient',
  'depot_tools/bot_update',
]

PROPERTIES = {
  # This is set by CQ when triggering a job.
  'repo_name': Property(kind=str),
}

DEFAULT_BUILDERS = [
  'luci.chromium.try:linux_chromium_rel_ng',
]

def _checkout_project(api, workdir, gclient_config, patch):
  api.file.ensure_directory(
      '%s checkout' % gclient_config.solutions[0].name, workdir)

  with api.context(cwd=workdir):
    api.bot_update.ensure_checkout(
        patch=patch, gclient_config=gclient_config)

def RunSteps(api, repo_name):
  workdir_base = api.path['cache'].join('builder')
  cl_workdir = workdir_base.join(repo_name)
  client_py_workdir = workdir_base.join('client_py')

  # Check out the repo for the CL, applying the patch.
  cl_config = api.gclient.make_config(repo_name)
  _checkout_project(api, cl_workdir, cl_config, True)

  # Check out the client-py repo, which gives us swarming.py.
  client_py_config = api.gclient.make_config()
  soln = client_py_config.solutions.add()
  soln.name = 'client-py'
  soln.url = 'https://chromium.googlesource.com/infra/luci/client-py'
  _checkout_project(api, client_py_workdir, client_py_config, False)

  triggered_jobs = {}
  for builder in DEFAULT_BUILDERS:
    with api.context(cwd=cl_workdir.join('build')):
      result = (api.
                led('get-builder', builder).
                then('edit-recipe-bundle').
                # Force the job to be experimental, since we don't want it
                # affecting production services.
                then('edit', '-p', '$recipe_engine/runtime={'
                     '"is_experimental":true, "is_luci": true}').
                then('launch')).result

    triggered_jobs[builder] = result['swarming']

  for builder, job in triggered_jobs.items():
    result = None
    try:
      result = api.python(
      'collect %s task' % builder, client_py_workdir.join(
          'client-py', 'swarming.py'), [
              'collect', '-S', job['host_name'], job['task_id'],
              # Needed because these jobs often take >40 minutes, since they're
              # regular tryjobs.
              '--print-status-updates',
              # Don't need task stdout; if the task fails then the user should
              # just look at the task itself.
              '--task-output-stdout=none',
          ])
    finally:
      if result:
        result.presentation.links['Swarming task'] = 'https://%s/task?id=%s' % (
            job['host_name'], job['task_id'])


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(repo_name='build') +
      api.step_data('led launch',
                    stdout=api.json.output({
                      'swarming':{
                          'host_name': 'chromium-swarm.appspot.com',
                          'task_id': 'beeeeeeeee5',
                      }
                    }))
  )

