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


DEFAULT_BUILDERS = (
    'luci.chromium.try:linux-rel',
    'luci.chromium.try:win10_chromium_x64_rel_ng',
    'luci.chromium.try-beta:linux-rel',
    'luci.chromium.try-beta:win10_chromium_x64_rel_ng',
    'luci.chromium.try-stable:linux-rel',
    'luci.chromium.try-stable:win10_chromium_x64_rel_ng',
    'luci.chromium.try-m80:linux-rel',
    'luci.chromium.try-m80:win10_chromium_x64_rel_ng',
)


@attr.s(frozen=True)
class PathBasedBuilderSet(object):
  builders = attr.ib()
  files = attr.ib()


# Builders that will be tested only if specific files are touched
IOS_PATH_BASED_BUILDERS = PathBasedBuilderSet(
    builders=[
        'luci.chromium.try:ios-simulator',
        'luci.chromium.try-beta:ios-simulator',
        'luci.chromium.try-stable:ios-simulator',
        'luci.chromium.try-m80:ios-simulator',
    ],
    files=[
        'scripts/slave/recipes/ios/try.py',
        'scripts/slave/recipe_modules/ios/api.py',
    ],
)

PATH_BASED_BUILDER_SETS = (IOS_PATH_BASED_BUILDERS,)


# We run the fast CL on Windows to speed up cycle time. Most of the
# recipe functionality is tested by the slow CL on Linux.
FAST_BUILDERS = (
    'luci.chromium.try:win10_chromium_x64_rel_ng',
    'luci.chromium.try-beta:win10_chromium_x64_rel_ng',
    'luci.chromium.try-stable:win10_chromium_x64_rel_ng',
    'luci.chromium.try-m80:win10_chromium_x64_rel_ng',
)

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
            'https://chromium-review.googlesource.com/c/chromium/src/+/2110683',
        'fast':
            'https://chromium-review.googlesource.com/c/chromium/src/+/2110393',
    },
    'luci.chromium.try-stable': {
        'slow':
            'https://chromium-review.googlesource.com/c/chromium/src/+/2067090',
        'fast':
            'https://chromium-review.googlesource.com/c/chromium/src/+/2066664',
    },
    'luci.chromium.try-m80': {
        'slow':
            'https://chromium-review.googlesource.com/c/chromium/src/+/2068245',
        'fast':
            'https://chromium-review.googlesource.com/c/chromium/src/+/2068246',
    },
}


@attr.s(frozen=True)
class RelatedBuilder(object):
  """Type to record a related builder.

  When a footer builder is requested, we will try to run the equivalent
  builder for the release branches. This type is used to record the
  original builder and the bucket variant.
  """
  original_builder = attr.ib()
  bucket = attr.ib()


def _get_recipe(led_builder):
  # Recipe we run probably doesn't change between slices.
  job_slice = led_builder.result['job_slices'][0]
  # TODO(martiniss): Use recipe_cipd_source to determine which repo this recipe
  # lives in. For now we assume the recipe lives in the repo the CL lives in.
  return job_slice['userland']['recipe_name']


def _checkout_project(api, workdir, gclient_config, patch):
  api.file.ensure_directory('%s checkout' % gclient_config.solutions[0].name,
                            workdir)

  with api.context(cwd=workdir):
    api.bot_update.ensure_checkout(patch=patch, gclient_config=gclient_config)


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

  return builder_map


def _get_builders_to_check(api, affected_files, repo_path):
  """Get the set of builders to test the recipe change against.

  If the CL has Led-Recipes-Tester-Builder footer in its description,
  then those builders will be the on tested, with branched versions of
  them provisonally included. Otherwise, a default set of builders will
  be tested, with some additional testing of iOS builders if
  iOS-specific recipe files are changed.

  Args:
    api - The recipe API object.
    affected_files - The set of files affected by the change.
    repo_path - A Path object identifying the root of repo the change is
      against.

  Returns:
    An OrderedDict mapping builder name to None or a RelatedBuilder
    instance. If the value is None, the associated builder should exist
    and it will be considered an error if it does not. If the value is
    not None, the associated builder may or may not exist and the value
    identifies the related builder and the alternative bucket that the
    builder was based on.
  """
  cl_footers = api.tryserver.get_footers() or {}
  footer_builders = cl_footers.get(BUILDER_FOOTER)

  if footer_builders is not None:
    return _process_footer_builders(api, footer_builders)

  prefix = str(repo_path) + '/'

  def remove_prefix(f):
    assert f.startswith(prefix)
    return f[len(prefix):]

  affected_files = set(remove_prefix(f) for f in affected_files)
  builders = list(DEFAULT_BUILDERS)
  for builder_set in PATH_BASED_BUILDER_SETS:
    if any(f in affected_files for f in builder_set.files):
      builders.extend(builder_set.builders)
  return collections.OrderedDict.fromkeys(builders)


def _get_led_builders(api, builders):
  """Get the led job definitions for the builders.

  Args:
    api - The recipe API object.
    builders - A mapping that maps the builder name to a RelatedBuilder
      or None. A RelatedBuilder object means that the builder named by
      the key is a provisional builder that may or may not exist but
      we're checking because we think it may exist based off of another
      builder that's been requested. A None value indicates that we
      expect the builder to exist and it is an error if it does not.

  Returns:
    An OrderedDict mapping builder name to the led job definition for
    the builder. Any provisional builders that do not exist will not
    have an entry in the returned dictionary.

  Raises:
    StepFailure if getting the job definition for a builder fails and
    the builder was not a provisional builder.
  """
  led_builders = collections.OrderedDict()

  with api.step.nest('get led builders'):
    for builder, related_builder in builders.iteritems():
      # Nest the led get-builder call because we don't get to control the step
      # name and having the step name identify the buidler we're getting is more
      # helpful than 'led get-builder', 'led get-builder (2)',
      # 'led get-builder (3)', etc.
      with api.step.nest('get ' + builder):
        try:
          led_builders[builder] = api.led('get-builder', builder)
        except api.step.StepFailure as e:
          if related_builder is None:
            raise
          e.result.presentation.status = api.step.WARNING
          e.result.presentation.step_text = (
              '\nNo equivalent to builder {} was found for bucket {}'.format(
                  related_builder.original_builder, related_builder.bucket))

  return led_builders


def _determine_affected_recipes(api, affected_files, recipes, recipes_py_path,
                                recipes_cfg_path):
  """Determine the set of recipes that are affected by the change.

  Args:
    api - The recipe API object.
    affected_files - The set of files affected by the change.
    recipes - The set of recipes that the prospective builders run.
    recipes_py_path - A Path object identifying the location of the
      recipes.py script.
    recipes_cfg_path - A Path object identifying the location of the
      recipes.cfg file.

  Returns:
    A set of the recipes that are affected by the change.

  Raises:
    StepFailure if analyzing the recipes fails.
  """
  cmd = [
      '--package',
      recipes_cfg_path,
      'analyze',
      api.json.input({
          'files': sorted(affected_files),
          'recipes': sorted(recipes),
      }),
      api.json.output(),
  ]

  step_name = 'determine affected recipes'
  result = api.python(
      step_name,
      recipes_py_path,
      cmd,
      ok_ret='any',
      venv=True,
      step_test_data=lambda: api.json.test_api.output({'recipes': []}),
  )

  json = getattr(result, 'json', None)
  json_output = getattr(json, 'output', None)
  if json_output is None:
    result.presentation.status = api.step.EXCEPTION
    result.presentation.step_text = 'Missing json output'
    raise api.step.InfraFailure(step_name, result)

  error = json_output.get('error', None)
  if error:
    result.presentation.logs['error'] = json_output['error']

  invalid_recipes = json_output.get('invalid_recipes', [])
  if invalid_recipes:
    result.presentation.step_text = (
        '\nanalyze reported that the recipes {!r} were invalid. '
        'The associated builders may be incorrectly configured.'.format(
            invalid_recipes))
    result.presentation.logs['invalid recipes'] = invalid_recipes

  if error or invalid_recipes:
    result.presentation.status = api.step.FAILURE
    raise api.step.StepFailure(step_name, result)

  affected_recipes = json_output['recipes']
  result.presentation.logs['recipes'] = '\n'.join(affected_recipes)

  return set(affected_recipes)


def _get_cl_category_to_trigger(affected_files, affected_recipes, builder,
                                recipe, recipes_cfg_path):
  """Calculates the chromium testing CL for the current CL.

  Args:
    affected_files - The set of files affected by the CL.
    affected_recipes - The set of recipes affected by the CL.
    builder - The name of the builder to get the CL category for.
    recipe - The recipe of the builder.
    recipes_cfg_path - A Path object identifying the location of the
      recipes.cfg file.

  Returns:
    None if nothing should be triggered. A CL category for indexing
    into CHROMIUM_SRC_TEST_CLS to get the CL to trigger.
  """
  if recipe in affected_recipes:
    if builder in FAST_BUILDERS:
      return 'fast'
    return 'slow'

  if str(recipes_cfg_path) in affected_files:
    return 'fast'

  return None


def _trigger_builders(api, affected_files, affected_recipes, led_builders,
                      cl_workdir, recipes_cfg_path):
  """Trigger led jobs for builders that are affected by the change.

  Args:
    api - The recipe API object.
    affected_files - The set of files affected by the change.
    affected_recipes - The set of recipes affected by the change.
    led_builders - A mapping that maps builder name to the led job
      definition for the builder.
    cl_workdir - A Path object identifying the root of the repo
      checkout.
    recipes_cfg_path - A Path object identifying the location of the
      recipes.cfg file.

  Returns:
    An OrderedDict mapping builder name to the swarming task ID for the
    triggered led job. Depending on the affected files/recipes, it may
    be determined that some of the builders don't need to be run, the
    returned dictionary contains keys only for those builders that are
    run.

  Raises:
    StepFailure if any of the led calls fail.
  """
  triggered_jobs = collections.OrderedDict()

  for builder, led_builder in led_builders.iteritems():
    with api.context(cwd=cl_workdir.join('build')):
      trigger_name = 'trigger {}'.format(builder)
      cl_key = _get_cl_category_to_trigger(affected_files, affected_recipes,
                                           builder, _get_recipe(led_builder),
                                           recipes_cfg_path)
      if not cl_key:
        result = api.step(trigger_name, [])
        result.presentation.step_text = (
            '\nNot running a tryjob for {!r}. The CL does not affect the '
            '{!r} recipe and the CL does not affect recipes.cfg'.format(
                builder, _get_recipe(led_builder)))
        continue

      with api.step.nest(trigger_name):
        # FIXME: We should check if the recipe we're testing tests patches to
        # chromium/src. For now just assume this works.
        bucket = builder.split(':', 1)[0]
        cl = CHROMIUM_SRC_TEST_CLS[bucket][cl_key]
        ir = led_builder.then('edit-cr-cl', cl)
        preso = api.step.active_result.presentation
        preso.step_text += 'Using %s testing CL' % cl_key
        preso.links['Test CL'] = cl

        # ir - intermediate result
        ir = ir.then('edit-recipe-bundle')
        # We used to set `is_experimental` to true, but the chromium recipe
        # currently uses that to deprioritize swarming tasks, which results in
        # very slow runtimes for the led task. Because this recipe blocks the
        # build.git CQ, we decided the tradeoff to run these edited recipes in
        # production mode instead would be better.
        ir = ir.then('edit', '-exp', 'false')
        ir = ir.then('launch')
        result = ir.result

        triggered_jobs[builder] = result['swarming']

  return triggered_jobs


def _collect_triggered_jobs(api, triggered_jobs, client_py_workdir):
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
          'collect %s task' % builder,
          client_py_workdir.join('client-py', 'swarming.py'),
          [
              'collect',
              '-S',
              job['host_name'],
              job['task_id'],
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

  repo_path = cl_workdir.join(repo_name)
  with api.context(cwd=repo_path):
    affected_files = api.tryserver.get_files_affected_by_patch(repo_path)

  builders = _get_builders_to_check(api, affected_files, repo_path)

  led_builders = _get_led_builders(api, builders)
  recipes = set(
      _get_recipe(led_builder) for led_builder in led_builders.values())

  recipes_py_path = recipes_dir.join('recipes.py')
  recipes_cfg_path = repo_path.join('infra', 'config', 'recipes.cfg')
  affected_recipes = _determine_affected_recipes(
      api, affected_files, recipes, recipes_py_path, recipes_cfg_path)

  # We don't currently check anything about the list of builders to trigger.
  # This is because the only existing builder which runs this recipe uses a
  # service account which is only allowed to trigger jobs in the
  # luci.chromium.try bucket. That builder is not in that bucket, so there's no
  # possibility for running a tryjob on itself.
  triggered_jobs = _trigger_builders(api, affected_files, affected_recipes,
                                     led_builders, cl_workdir, recipes_cfg_path)

  if not triggered_jobs:
    api.python.succeeding_step('exiting', 'no tryjobs to run, exiting')
    return

  _collect_triggered_jobs(api, triggered_jobs, client_py_workdir)


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

  def affected_files(*affected_files):
    return api.override_step_data(
        'git diff to analyze patch',
        stdout=api.raw_io.output('\n'.join(affected_files)))

  def affected_recipes(*affected_recipes):
    return api.step_data('determine affected recipes',
                         api.json.output({
                             'recipes': affected_recipes,
                         }))

  def led_get_builder_name(name):
    return 'get led builders.get {}.led get-builder'.format(name)

  def led_get_builder(name, recipe=RECIPE):
    return api.step_data(
        led_get_builder_name(name),
        stdout=api.json.output({
            'job_slices': [{
                'userland': {
                    'recipe_name': recipe,
                },
            }],
        }))

  def led_launch_name(name):
    return 'trigger {}.led launch'.format(name)

  def led_launch(name, task_id='task0'):
    return api.step_data(
        led_launch_name(name),
        stdout=api.json.output({
            'swarming': {
                'host_name': 'chromium-swarm.appspot.com',
                'task_id': task_id,
            }
        }))

  def default_builders(launch):
    t = api.empty_test_data()
    for i, b in enumerate(DEFAULT_BUILDERS):
      t += led_get_builder(b)
      if launch:
        t += led_launch(b, task_id='task{}'.format(i))
    return t

  yield api.test(
      'basic',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      affected_recipes(RECIPE),
      default_builders(launch=True),
  )

  yield api.test(
      'no_jobs_to_run',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      default_builders(launch=False),
      api.post_check(post_process.MustRun, 'exiting'),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'recipe_roller',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      affected_files(
          'random/file.py',
          'infra/config/recipes.cfg',
      ),
      default_builders(launch=True),
  )

  yield api.test(
      'manual_roll_with_changes',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      affected_files(
          'random/file.py',
          'infra/config/recipes.cfg',
      ),
      default_builders(launch=True),
  )

  yield api.test(
      'analyze_missing_json',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      default_builders(launch=False),
      api.override_step_data('determine affected recipes', retcode=1),
      api.post_check(post_process.StepException, 'determine affected recipes'),
      api.post_check(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'analyze_failure',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      default_builders(launch=False),
      api.step_data(
          'determine affected recipes',
          api.json.output({
              'error': 'Bad analyze!!!!',
              'invalid_recipes': [RECIPE],
          }),
          retcode=1),
      api.post_check(post_process.StepFailure, 'determine affected recipes'),
      api.post_check(
          lambda check, steps: \
          check(RECIPE in
                steps['determine affected recipes'].logs['invalid recipes'])
      ),
      api.post_check(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
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
      affected_recipes(RECIPE),
      led_get_builder('luci.chromium.try:arbitrary-builder'),
      led_launch('luci.chromium.try:arbitrary-builder'),
      led_get_builder('luci.chromium.try-beta:arbitrary-builder'),
      led_launch('luci.chromium.try-beta:arbitrary-builder'),
      led_get_builder('luci.chromium.try-stable:arbitrary-builder'),
      led_launch('luci.chromium.try-stable:arbitrary-builder'),
      led_get_builder('luci.chromium.try-m80:arbitrary-builder'),
      led_launch('luci.chromium.try-m80:arbitrary-builder'),
      api.post_check(post_process.DoesNotRun,
                     *[led_get_builder_name(b) for b in DEFAULT_BUILDERS]),
      api.post_process(post_process.DropExpectation),
  )

  def non_existent_builder(name):
    return api.step_data(led_get_builder_name(name), retcode=1)

  yield api.test(
      'footer_builder_not_on_all_branches',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(footer_builder='luci.chromium.try:arbitrary-builder'),
      affected_recipes(RECIPE),
      led_get_builder('luci.chromium.try:arbitrary-builder'),
      led_launch('luci.chromium.try:arbitrary-builder'),
      led_get_builder('luci.chromium.try-beta:arbitrary-builder'),
      led_launch('luci.chromium.try-beta:arbitrary-builder'),
      non_existent_builder('luci.chromium.try-stable:arbitrary-builder'),
      non_existent_builder('luci.chromium.try-m80:arbitrary-builder'),
      api.post_check(
          post_process.StepWarning,
          led_get_builder_name('luci.chromium.try-stable:arbitrary-builder')),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'footer_builder_does_not_exist',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(footer_builder='luci.chromium.try:arbitrary-builder'),
      non_existent_builder('luci.chromium.try:arbitrary-builder'),
      api.post_check(
          post_process.StepFailure,
          led_get_builder_name('luci.chromium.try:arbitrary-builder')),
      api.post_check(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'cl_indirectly_affects_ios',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      affected_recipes(),
      default_builders(launch=False),
      api.post_check(
          post_process.DoesNotRun,
          *[led_get_builder_name(b) for b in IOS_PATH_BASED_BUILDERS.builders]),
      api.post_check(post_process.MustRun, 'exiting'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'ios-recipe-module-change',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      affected_files('scripts/slave/recipe_modules/ios/api.py',),
      affected_recipes('ios/try'),
      default_builders(launch=False),
      led_get_builder('luci.chromium.try:ios-simulator', recipe='ios/try'),
      led_launch('luci.chromium.try:ios-simulator', task_id='task0'),
      led_get_builder('luci.chromium.try-beta:ios-simulator', recipe='ios/try'),
      led_launch('luci.chromium.try-beta:ios-simulator', task_id='task1'),
      led_get_builder(
          'luci.chromium.try-stable:ios-simulator', recipe='ios/try'),
      led_launch('luci.chromium.try-stable:ios-simulator', task_id='task2'),
      led_get_builder('luci.chromium.try-m80:ios-simulator', recipe='ios/try'),
      led_launch('luci.chromium.try-m80:ios-simulator', task_id='task3'),
  )

  yield api.test(
      'ios-try-recipe-change',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      affected_files('scripts/slave/recipes/ios/try.py',),
      affected_recipes('ios/try'),
      default_builders(launch=False),
      led_get_builder('luci.chromium.try:ios-simulator', recipe='ios/try'),
      led_launch('luci.chromium.try:ios-simulator', task_id='task0'),
      led_get_builder('luci.chromium.try-beta:ios-simulator', recipe='ios/try'),
      led_launch('luci.chromium.try-beta:ios-simulator', task_id='task1'),
      led_get_builder(
          'luci.chromium.try-stable:ios-simulator', recipe='ios/try'),
      led_launch('luci.chromium.try-stable:ios-simulator', task_id='task2'),
      led_get_builder('luci.chromium.try-m80:ios-simulator', recipe='ios/try'),
      led_launch('luci.chromium.try-m80:ios-simulator', task_id='task3'),
  )
