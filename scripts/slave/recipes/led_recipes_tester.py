# Copyright 2016 The LUCI Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.

"""Tests a recipe CL by running a chromium builder."""

from recipe_engine.recipe_api import Property
from recipe_engine.post_process import Filter

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
  'depot_tools/tryserver',
]


PROPERTIES = {
  # This is set by CQ when triggering a job.
  'repo_name': Property(kind=str),
}


# If present in a CL description, will override the existing default builders
# with a custom list. Format is expected to be "<bucket>.<builder>".
BUILDER_FOOTER = 'Led-Recipes-Tester-Builder'


DEFAULT_BUILDERS = [
  'luci.chromium.try:linux-rel',
  'luci.chromium.try:win10_chromium_x64_rel_ng',
]


# We run the fast CL on Windows to speed up cycle time. Most of the
# recipe functionality is tested by the slow CL on Linux.
FAST_BUILDERS = [
  'luci.chromium.try:win10_chromium_x64_rel_ng',
]


# CL to use when testing a recipe which touches chromium source.
CHROMIUM_SRC_TEST_CLS = {
  # This slow CL touches `DEPS` which causes analyze to compile and test all
  # targets.
  'slow': 'https://chromium-review.googlesource.com/c/chromium/src/+/1286761',
  # This fast CL touches `chrome/test/base/interactive_test_utils.cc`, resulting
  # in just interactive_ui_tests being built and run. This is a relatively fast,
  # but still swarmed w/ multiple shards, test suite. This fast verification is
  # used for "upstream-only-changes" on the assumption that no upstream code
  # would (should) have variable effects based on WHICH test suite is executed,
  # so we just need to pick SOME test suite.
  'fast': 'https://chromium-review.googlesource.com/c/chromium/src/+/1406154',
}


def _checkout_project(api, workdir, gclient_config, patch):
  api.file.ensure_directory(
      '%s checkout' % gclient_config.solutions[0].name, workdir)

  with api.context(cwd=workdir):
    api.bot_update.ensure_checkout(
        patch=patch, gclient_config=gclient_config)


def trigger_cl(api, recipe, repo_path, recipes_py_path, builder):
  """Calculates the chromium testing CL for the current CL.

  Returns None if we shouldn't trigger anything.
  Returns a key in the CHROMIUM_SRC_TEST_CLS dictionary.
  """
  recipes_cfg_path = repo_path.join('infra', 'config', 'recipes.cfg')

  affected_files = api.tryserver.get_files_affected_by_patch(repo_path)
  try:
    analyze_step = api.python(
      'analyze %s' % recipe,
      recipes_py_path, [
        '--package', recipes_cfg_path,
        'analyze',
        api.json.input({
            'files': affected_files,
            'recipes': [recipe],
        }),
        api.json.output()],
      venv=True)
  except api.step.StepFailure:
    analyze_step = api.step.active_result
    if analyze_step.json.output:
      analyze_step.presentation.logs['error'] = (
        analyze_step.json.output['error'])

  if recipe in analyze_step.json.output.get('invalid_recipes', []):
    api.python.failing_step(
        'recipe invalid',
        'analyze reported that the recipe \'%s\' was invalid. Something may'
        ' be wrong with the swarming task this is based on.' % recipe)

  if recipe in analyze_step.json.output['recipes']:
    if builder in FAST_BUILDERS:
      return 'fast'
    return 'slow'

  if str(repo_path.join('infra', 'config', 'recipes.cfg')) in affected_files:
    return 'fast'

  return None


# TODO(martiniss): make this work if repo_name != 'build'
def RunSteps(api, repo_name):
  workdir_base = api.path['cache']
  cl_workdir = workdir_base.join(repo_name)
  client_py_workdir = workdir_base.join('client_py')
  recipes_dir = workdir_base.join('recipe_engine')

  # Needed to run `recipes.py analyze`.
  recipes_config = api.gclient.make_config('recipes_py')
  _checkout_project(api, recipes_dir, recipes_config, False)
  recipes_dir = recipes_dir.join('infra', 'recipes-py')

  # Check out the repo for the CL, applying the patch.
  cl_config = api.gclient.make_config(repo_name)
  _checkout_project(api, cl_workdir, cl_config, True)

  triggered_jobs = {}

  cl_footers = api.tryserver.get_footers() or {}
  builders = cl_footers.get(BUILDER_FOOTER, DEFAULT_BUILDERS)
  # We don't currently check anything about the list of builders to trigger.
  # This is because the only existing builder which runs this recipe uses a
  # service account which is only allowed to trigger jobs in the
  # luci.chromium.try bucket. That builder is not in that bucket, so there's no
  # possibility for running a tryjob on itself.

  for builder in builders:
    with api.step.nest('analyze+launch '+builder):
      with api.context(cwd=cl_workdir.join('build')):
        # intermediate result
        ir = api.led('get-builder', builder)
        # Recipe we run probably doesn't change between slices.
        job_slice = ir.result['job_slices'][0]
        # TODO(martiniss): Use recipe_cipd_source to determine which repo this
        # recipe lives in. For now we assume the recipe lives in the repo the CL
        # lives in.
        recipe = job_slice['userland']['recipe_name']

        # FIXME: If we collect all the recipes-to-run up front, we can do
        # a single analysis pass, instead of one per builder.
        cl = trigger_cl(
            api, recipe, cl_workdir.join(repo_name),
            recipes_dir.join('recipes.py'), builder)
        if not cl:
          result = api.python.succeeding_step(
              'not running a tryjob for %s' % recipe,
              '`recipes.py analyze` indicates this recipe is not affected by '
              'the files changed by the CL, and the CL does not affect '
              'recipes.cfg')
          continue

        # FIXME: We should check if the recipe we're testing tests patches to
        # chromium/src. For now just assume this works.
        ir = ir.then('edit-cr-cl', CHROMIUM_SRC_TEST_CLS[cl])
        preso = api.step.active_result.presentation
        preso.step_text += 'Using %s testing CL' % cl
        preso.links['Test CL'] = CHROMIUM_SRC_TEST_CLS[cl]

        result = (
          ir.then('edit-recipe-bundle').
          # We used to set `is_experimental` to true, but the chromium recipe
          # currently uses that to deprioritize swarming tasks, which results in
          # very slow runtimes for the led task. Because this recipe blocks the
          # build.git CQ, we decided the tradeoff to run these edited recipes in
          # production mode instead would be better.
          then('edit', '-exp', 'false').
          then('launch')).result

        triggered_jobs[builder] = result['swarming']

  if not triggered_jobs:
    api.python.succeeding_step('exiting', 'no tryjobs to run, exiting')
    return

  # Check out the client-py repo, which gives us swarming.py.
  client_py_config = api.gclient.make_config()
  soln = client_py_config.solutions.add()
  soln.name = 'client-py'
  soln.url = 'https://chromium.googlesource.com/infra/luci/client-py'
  _checkout_project(api, client_py_workdir, client_py_config, False)

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
  RECIPE = 'foo_recipe'

  def gerrit_change(footer_builder=None):
    message = 'nothing important'
    parse_description_json = {}
    if footer_builder:
      message = '{}: {}'.format(BUILDER_FOOTER, footer_builder)
      parse_description_json = {BUILDER_FOOTER: [footer_builder]}

    t = api.override_step_data(
        'gerrit changes',
        api.json.output([{
            'revisions': {
                1: {
                    '_number': 12,
                    'commit': {
                        'message': message,
                    }
                }
            }
        }]))
    t += api.override_step_data('parse description',
                                api.json.output(parse_description_json))
    return t

  def prefix(name):
    return 'analyze+launch {}.'.format(name)

  def led_get_builder(name):
    return api.step_data(
        prefix(name) + 'led get-builder',
        stdout=api.json.output({
            'job_slices': [{
                'userland': {
                    'recipe_name': RECIPE,
                },
            }],
        }))

  def test_builder(name,
                   recipe_affected=True,
                   affected_files=None,
                   task_id='task0'):
    t = led_get_builder(name)

    affected_files = affected_files or []
    if affected_files:
      t += api.override_step_data(
          prefix(name) + 'git diff to analyze patch',
          stdout=api.raw_io.output('\n'.join(affected_files)))

    t += api.step_data(
        '{}analyze {}'.format(prefix(name), RECIPE),
        api.json.output({
            'recipes': ([RECIPE] if recipe_affected else []),
        }))

    if recipe_affected or 'infra/config/recipes.cfg' in affected_files:
      t += api.step_data(
          prefix(name) + 'led launch',
          stdout=api.json.output({
              'swarming': {
                  'host_name': 'chromium-swarm.appspot.com',
                  'task_id': task_id,
              }
          }))

    return t

  def default_builders(**kwargs):
    t = api.empty_test_data()
    for i, b in enumerate(DEFAULT_BUILDERS):
      t += test_builder(b, task_id='task{}'.format(i), **kwargs)
    return t

  yield api.test(
      'basic',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      default_builders(),
  )

  yield api.test(
      'no_jobs_to_run',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      default_builders(recipe_affected=False),
      api.post_process(Filter('exiting')),
  )

  yield api.test(
      'recipe_roller',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      default_builders(
          recipe_affected=False,
          affected_files=[
              'random/file.py',
              'infra/config/recipes.cfg',
          ]),
  )

  yield api.test(
      'manual_roll_with_changes',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      default_builders(affected_files=[
          'random/file.py',
          'infra/config/recipes.cfg',
      ]),
  )

  yield api.test(
      'analyze_failure',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      led_get_builder('luci.chromium.try:linux-rel'),
      api.step_data(
          prefix('luci.chromium.try:linux-rel') + 'analyze foo_recipe',
          api.json.output({
              'error': 'Bad analyze!!!!',
              'invalid_recipes': [RECIPE],
          }),
          retcode=1),
      api.post_process(
          Filter(prefix('luci.chromium.try:linux-rel') + 'recipe invalid')),
  )

  yield api.test(
      'custom_builder',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(footer_builder='arbitrary.blah'),
      test_builder('arbitrary.blah'),
      api.post_process(Filter(prefix('arbitrary.blah') + 'led get-builder')),
  )
