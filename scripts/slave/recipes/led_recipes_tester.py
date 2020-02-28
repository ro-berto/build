# Copyright 2016 The LUCI Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.

"""Tests a recipe CL by running a chromium builder."""

import attr
import collections

from recipe_engine import post_process
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
    'luci.chromium.try-beta:linux-rel',
    'luci.chromium.try-beta:win10_chromium_x64_rel_ng',
    'luci.chromium.try-stable:linux-rel',
    'luci.chromium.try-stable:win10_chromium_x64_rel_ng',
]


# We run the fast CL on Windows to speed up cycle time. Most of the
# recipe functionality is tested by the slow CL on Linux.
FAST_BUILDERS = [
    'luci.chromium.try:win10_chromium_x64_rel_ng',
    'luci.chromium.try-beta:win10_chromium_x64_rel_ng',
    'luci.chromium.try-stable:win10_chromium_x64_rel_ng',
]

# CL to use when testing a recipe which touches chromium source.
# The first level of keys is the bucket of the builder. The second level of keys
# is the type of CL: 'fast' or 'slow', with the value being the CL to use.
CHROMIUM_SRC_TEST_CLS = {
    # The slow CLs touch `DEPS` which causes analyze to compile and test all
    # targets.

    # The fast CLs touch `chrome/test/base/interactive_test_utils.cc`, resulting
    # in just interactive_ui_tests being built and run. This is a relatively
    # fast, but still swarmed w/ multiple shards, test suite. This fast
    # verification is used for "upstream-only-changes" on the assumption that no
    # upstream code would (should) have variable effects based on WHICH test
    # suite is executed, so we just need to pick SOME test suite.
    'luci.chromium.try': {
        'slow':
            'https://chromium-review.googlesource.com/c/chromium/src/+/1286761',
        'fast':
            'https://chromium-review.googlesource.com/c/chromium/src/+/1406154',
    },
    'luci.chromium.try-beta': {
        'slow':
            'https://chromium-review.googlesource.com/c/chromium/src/+/2067090',
        'fast':
            'https://chromium-review.googlesource.com/c/chromium/src/+/2066664',
    },
    'luci.chromium.try-stable': {
        'slow':
            'https://chromium-review.googlesource.com/c/chromium/src/+/2068245',
        'fast':
            'https://chromium-review.googlesource.com/c/chromium/src/+/2068246',
    },
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


@attr.s(frozen=True)
class RelatedBuilder(object):
  """Type to record a related builder.

  When a footer builder is requested, we will try to run the equivalent
  builder for the release branches. This type is used to record the
  original builder and the bucket variant.
  """
  original_builder = attr.ib()
  bucket = attr.ib()


def _process_footer_builders(api, builders):
  bad_builders = sorted(b for b in builders if ':' not in b)
  if bad_builders:
    step_name = 'bad builders'
    result = api.step(step_name, [])
    result.presentation.status = api.step.FAILURE
    result.presentation.step_text = ''.join(['\n  ' + b for b in bad_builders])
    raise api.step.StepFailure(step_name, result)
  buckets = set(b.split(':', 1)[0] for b in builders)
  unknown_buckets = set(b for b in buckets if b not in CHROMIUM_SRC_TEST_CLS)
  if unknown_buckets:
    step_name = 'unknown buckets'
    result = api.step(step_name, [])
    result.presentation.status = api.step.FAILURE
    result.presentation.step_text = ''.join(
        ['\n  ' + b for b in sorted(unknown_buckets)])
    raise api.step.StepFailure(step_name, result)

  builder_map = collections.OrderedDict.fromkeys(builders)
  # For each builder, add an entry for the version of the builder in each
  # branch, with a RelatedBuilder indicating what it was computed from
  for builder in builders:
    name = builder.split(':', 1)[1]
    for bucket in CHROMIUM_SRC_TEST_CLS:
      builder_map.setdefault('{}:{}'.format(bucket, name),
                             RelatedBuilder(builder, bucket))

  return builder_map.items()


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

  cl_footers = api.tryserver.get_footers() or {}
  builders = cl_footers.get(BUILDER_FOOTER)

  # builders needs to be in the form of tuples:
  # (builder (str), related_builder (RelatedBuilder or None))
  if builders is None:
    builders = [(b, None) for b in DEFAULT_BUILDERS]
  else:
    builders = _process_footer_builders(api, builders)


  # We don't currently check anything about the list of builders to trigger.
  # This is because the only existing builder which runs this recipe uses a
  # service account which is only allowed to trigger jobs in the
  # luci.chromium.try bucket. That builder is not in that bucket, so there's no
  # possibility for running a tryjob on itself.
  triggered_jobs = {}

  for builder, related_builder in builders:
    with api.step.nest('analyze+launch ' + builder) as presentation:
      with api.context(cwd=cl_workdir.join('build')):
        try:
          # intermediate result
          ir = api.led('get-builder', builder)
        except api.step.StepFailure:
          if related_builder is None:
            raise
          presentation.status = api.step.SUCCESS
          presentation.step_text = (
              '\nNo equivalent to builder {} was found for bucket {}'.format(
                  related_builder.original_builder, related_builder.bucket))
          continue
        # Recipe we run probably doesn't change between slices.
        job_slice = ir.result['job_slices'][0]
        # TODO(martiniss): Use recipe_cipd_source to determine which repo this
        # recipe lives in. For now we assume the recipe lives in the repo the CL
        # lives in.
        recipe = job_slice['userland']['recipe_name']

        # FIXME: If we collect all the recipes-to-run up front, we can do
        # a single analysis pass, instead of one per builder.
        cl_key = trigger_cl(api, recipe, cl_workdir.join(repo_name),
                            recipes_dir.join('recipes.py'), builder)
        if not cl_key:
          result = api.python.succeeding_step(
              'not running a tryjob for %s' % recipe,
              '`recipes.py analyze` indicates this recipe is not affected by '
              'the files changed by the CL, and the CL does not affect '
              'recipes.cfg')
          continue

        # FIXME: We should check if the recipe we're testing tests patches to
        # chromium/src. For now just assume this works.
        bucket = builder.split(':', 1)[0]
        cl = CHROMIUM_SRC_TEST_CLS[bucket][cl_key]
        ir = ir.then('edit-cr-cl', cl)
        preso = api.step.active_result.presentation
        preso.step_text += 'Using %s testing CL' % cl_key
        preso.links['Test CL'] = cl

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

  def builder_step_name(builder, sub_step=None):
    name = 'analyze+launch {}'.format(builder)
    if sub_step:
      name = '{}.{}'.format(name, sub_step)
    return name

  def led_get_builder(name):
    return api.step_data(
        builder_step_name(name, 'led get-builder'),
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
          builder_step_name(name, 'git diff to analyze patch'),
          stdout=api.raw_io.output('\n'.join(affected_files)))

    t += api.step_data(
        builder_step_name(name, 'analyze {}'.format(RECIPE)),
        api.json.output({
            'recipes': ([RECIPE] if recipe_affected else []),
        }))

    if recipe_affected or 'infra/config/recipes.cfg' in affected_files:
      t += api.step_data(
          builder_step_name(name, 'led launch'),
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
      api.post_process(post_process.Filter('exiting')),
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
          builder_step_name('luci.chromium.try:linux-rel',
                            'analyze {}'.format(RECIPE)),
          api.json.output({
              'error': 'Bad analyze!!!!',
              'invalid_recipes': [RECIPE],
          }),
          retcode=1),
      api.post_process(
          post_process.Filter(
              builder_step_name('luci.chromium.try:linux-rel',
                                'recipe invalid'))),
  )

  def step_text_lines(step):
    return [l.strip() for l in step.step_text.split('<br/>')]

  yield api.test(
      'footer_builder_with_invalid_format',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(footer_builder='bad-builder'),
      api.post_check(post_process.StepFailure, 'bad builders'),
      api.post_check(
          lambda check, steps: \
          check('bad-builder' in step_text_lines(steps['bad builders']))
      ),
      api.post_check(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'footer_builder_with_unknown_bucket',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(footer_builder='arbitrary-bucket:arbitrary-builder'),
      api.post_check(post_process.StepFailure, 'unknown buckets'),
      api.post_check(
          lambda check, steps: \
          check('arbitrary-bucket' in step_text_lines(steps['unknown buckets']))
      ),
      api.post_check(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'footer_builder',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(footer_builder='luci.chromium.try:arbitrary-builder'),
      test_builder('luci.chromium.try:arbitrary-builder'),
      test_builder('luci.chromium.try-beta:arbitrary-builder'),
      test_builder('luci.chromium.try-stable:arbitrary-builder'),
      api.post_check(post_process.DoesNotRun,
                     *[builder_step_name(b) for b in DEFAULT_BUILDERS]),
      api.post_process(post_process.DropExpectation),
  )

  def non_existent_builder(name):
    return api.step_data(
        builder_step_name(name, 'led get-builder'),
        retcode=1,
    )

  yield api.test(
      'footer_builder_not_on_all_branches',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(footer_builder='luci.chromium.try:arbitrary-builder'),
      test_builder('luci.chromium.try:arbitrary-builder'),
      test_builder('luci.chromium.try-beta:arbitrary-builder'),
      non_existent_builder('luci.chromium.try-stable:arbitrary-builder'),
      api.post_check(
          post_process.StepSuccess,
          builder_step_name('luci.chromium.try-stable:arbitrary-builder')),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'footer_builder_does_not_exist',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(footer_builder='luci.chromium.try:arbitrary-builder'),
      non_existent_builder('luci.chromium.try:arbitrary-builder'),
      api.post_check(post_process.StepFailure,
                     builder_step_name('luci.chromium.try:arbitrary-builder')),
      api.post_check(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
