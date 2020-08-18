# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests a recipe CL by running a chromium builder."""

import attr
import collections
import contextlib

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

from PB.go.chromium.org.luci.led.job import job as job_pb2

DEPS = [
    'recipe_engine/cipd',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/futures',
    'recipe_engine/json',
    'recipe_engine/led',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/swarming',
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
    'luci.chromium.try:chromium_presubmit',
    'luci.chromium.try:linux-rel',
    'luci.chromium.try:win10_chromium_x64_rel_ng',
    'luci.chromium.try-m84:chromium_presubmit',
    'luci.chromium.try-m84:linux-rel',
    'luci.chromium.try-m84:win10_chromium_x64_rel_ng',
    'luci.chromium.try-m85:chromium_presubmit',
    'luci.chromium.try-m85:linux-rel',
    'luci.chromium.try-m85:win10_chromium_x64_rel_ng',
)


@attr.s(frozen=True)
class PathBasedBuilderSet(object):
  builders = attr.ib()
  files = attr.ib()


# Builders that will be tested only if specific files are touched
IOS_PATH_BASED_BUILDERS = PathBasedBuilderSet(
    builders=[
        'luci.chromium.try:ios-simulator',
        'luci.chromium.try-m84:ios-simulator',
        'luci.chromium.try-m85:ios-simulator',
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
    'luci.chromium.try-m84:win10_chromium_x64_rel_ng',
    'luci.chromium.try-m85:win10_chromium_x64_rel_ng',
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
    'luci.chromium.try-m84': {
        'slow':
            'https://chromium-review.googlesource.com/c/chromium/src/+/2204441',
        'fast':
            'https://chromium-review.googlesource.com/c/chromium/src/+/2204425',
    },
    'luci.chromium.try-m85': {
        'slow':
            'https://chromium-review.googlesource.com/c/chromium/src/+/2270351',
        'fast':
            'https://chromium-review.googlesource.com/c/chromium/src/+/2270701',
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
  build_proto = led_builder.result.buildbucket.bbagent_args.build
  try:
    return build_proto.input.properties['recipe']
  except ValueError as ex:  # pragma: no cover
    # If you see this in simulations, it's possible that you are missing a
    # led_get_builder clause.
    raise ValueError("build has no recipe set (%s): %r" % (ex, build_proto))


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


def _test_builder(api, affected_files, affected_recipes, builder, led_builder,
                  recipes_cfg_path, bundle):
  """Try running a builder with the patched recipe.

  Args:
    api - The recipe API object.
    affected_files - The set of files affected by the change.
    affected_recipes - The set of recipes affected by the change.
    builder - The name of the builder to test.
    led_builder - The led job definition for the builder.
    recipes_cfg_path - A Path object identifying the location of the
      recipes.cfg file.
    bundle - A Bundle object that can be applied to an led job to edit
      the recipe bundle.

  Raises:
    InfraFailure if any of the led calls fail.
    StepFailure if the triggered task failed.
  """
  with api.step.nest('test {}'.format(builder)) as presentation:
    cl_key = _get_cl_category_to_trigger(affected_files, affected_recipes,
                                         builder, _get_recipe(led_builder),
                                         recipes_cfg_path)
    if not cl_key:
      presentation.step_text = (
          '\nNot running a tryjob for {!r}. The CL does not affect the '
          '{!r} recipe and the CL does not affect recipes.cfg'.format(
              builder, _get_recipe(led_builder)))
      return

    with api.step.nest('trigger'), api.context(infra_steps=True):
      # FIXME: We should check if the recipe we're testing tests patches to
      # chromium/src. For now just assume this works.
      bucket = builder.split(':', 1)[0]
      cl = CHROMIUM_SRC_TEST_CLS[bucket][cl_key]
      ir = led_builder.then('edit-cr-cl', cl)
      # TODO(gbeaty) Once the recipe engine no longer supports annotations and
      # nest step presentation is reflected in the UI before it's closed, we can
      # just update the nest step's presentation
      step_result = api.step.active_result
      step_result.presentation.links['Test CL ({})'.format(cl_key)] = cl
      presentation.links.update(step_result.presentation.links)

      ir = bundle.apply(ir)
      # We used to set `is_experimental` to true, but the chromium recipe
      # currently uses that to deprioritize swarming tasks, which results in
      # very slow runtimes for the led task. Because this recipe blocks the
      # build.git CQ, we decided the tradeoff to run these edited recipes in
      # production mode instead would be better.
      ir = ir.then('edit', '-exp', 'false')
      ir = ir.then('launch')

      job = ir.launch_result
      presentation.links.update(api.step.active_result.presentation.links)

    with api.swarming.with_server(job.swarming_hostname):
      results = api.swarming.collect(
          'collect',
          [job.task_id],
          # We're launching LUCI builders, so they can be viewed in the Milo UI,
          # which is much better than the stdout, so don't take the time to
          # download the stdout
          task_output_stdout='none')
      for result in results:
        result.analyze()


# TODO(martiniss): make this work if repo_name != 'build'
def RunSteps(api, repo_name):
  with api.context(cwd=api.path['cache'].join('builder')):
    update_result = api.bot_update.ensure_checkout(
        patch=True, gclient_config=api.gclient.set_config(repo_name))

  repo_path = api.path['cache'].join('builder',
                                     update_result.json.output['root'])

  with api.context(cwd=repo_path):
    affected_files = api.tryserver.get_files_affected_by_patch(repo_path)

  builders = _get_builders_to_check(api, affected_files, repo_path)

  led_builders = _get_led_builders(api, builders)
  recipes = set(
      _get_recipe(led_builder) for led_builder in led_builders.values())

  recipes_py_path = api.cipd.ensure_tool(
      'infra/recipe_bundles/chromium.googlesource.com/infra/luci/recipes-py',
      version='refs/heads/master',
      executable_path='recipe_engine/recipes.py')
  recipes_cfg_path = repo_path.join('infra', 'config', 'recipes.cfg')
  affected_recipes = _determine_affected_recipes(
      api, affected_files, recipes, recipes_py_path, recipes_cfg_path)

  # TODO(https://crbug.com/1088020) Switch to using the led module's bundle
  # functionality when it is ready
  class Bundle(object):

    def __init__(self):
      self._future = api.futures.spawn(self._create_bundle)

    @staticmethod
    def _create_bundle():
      # It doesn't matter which builder the led job belongs to, the recipe
      # bundle will be the same, so just bundle it once and apply the hash to
      # each one in the trigger greenlets
      led_job = next(led_builders.itervalues())
      with api.step.nest('bundle recipes'), api.context(
          cwd=repo_path, infra_steps=True):
        led_out = led_job.then('edit-recipe-bundle')
      return led_out.result.user_payload.digest

    def apply(self, led_job):
      return led_job.then('edit', '-rbh', self._future.result())

  bundle = Bundle()

  # Kick off a future to make the swarming client ready to use so that the
  # install appears as a top-level step
  api.futures.spawn_immediate(api.swarming.ensure_client)

  futures = []
  for builder, led_builder in led_builders.iteritems():
    futures.append(
        api.futures.spawn(_test_builder, api, affected_files, affected_recipes,
                          builder, led_builder, recipes_cfg_path, bundle))

  for f in api.futures.wait(futures):
    f.result()


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

  def parse_legacy_buildername(name):
    # TODO: stop using buildbucket v1 buildernames.
    bucket, buildername = name.split(':', 1)
    assert bucket.startswith('luci.')
    project, bucket = bucket[len('luci.'):].split('.', 1)
    return project, bucket, buildername

  def non_existent_builder(name):
    return api.led.mock_get_builder(None, *parse_legacy_buildername(name))

  def led_set_builder_recipe(name, recipe):
    build = job_pb2.Definition()
    build.buildbucket.bbagent_args.build.input.properties['recipe'] = recipe
    return api.led.mock_get_builder(build, *parse_legacy_buildername(name))

  def default_builders():
    # Set the default recipe for all chromium builders
    build = job_pb2.Definition()
    build.buildbucket.bbagent_args.build.input.properties['recipe'] = RECIPE
    return api.led.mock_get_builder(build, 'chromium')

  yield api.test(
      'basic',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      affected_recipes(RECIPE),
      default_builders(),
  )

  yield api.test(
      'expired_tryjob',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      affected_recipes(RECIPE),
      default_builders(),
      # Step has a retcode of 0 in production.
      api.step_data(
          'test luci.chromium.try:linux-rel.collect',
          api.json.output({
              'deadbeef': {
                  'results': {
                      'name': 'test',
                      'state': 'EXPIRED',
                  },
              },
          })),
      api.post_check(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no_jobs_to_run',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      default_builders(),
      api.post_check(post_process.DoesNotRunRE, 'test .*\.trigger'),
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
      default_builders(),
  )

  yield api.test(
      'manual_roll_with_changes',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      affected_files(
          'random/file.py',
          'infra/config/recipes.cfg',
      ),
      default_builders(),
  )

  yield api.test(
      'analyze_missing_json',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      default_builders(),
      api.override_step_data('determine affected recipes', retcode=1),
      api.post_check(post_process.StepException, 'determine affected recipes'),
      api.post_check(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'analyze_failure',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      default_builders(),
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
      default_builders(),
      api.post_check(post_process.DoesNotRun,
                     *[led_get_builder_name(b) for b in DEFAULT_BUILDERS]),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'footer_builder_not_on_all_branches',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(footer_builder='luci.chromium.try:arbitrary-builder'),
      affected_recipes(RECIPE),
      default_builders(),
      non_existent_builder('luci.chromium.try-m84:arbitrary-builder'),
      api.post_check(
          post_process.StepWarning,
          led_get_builder_name('luci.chromium.try-m84:arbitrary-builder')),
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
      default_builders(),
      api.post_check(
          post_process.DoesNotRun,
          *[led_get_builder_name(b) for b in IOS_PATH_BASED_BUILDERS.builders]),
      api.post_check(post_process.DoesNotRunRE, 'test .*\.trigger'),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'ios-recipe-module-change',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      affected_files('scripts/slave/recipe_modules/ios/api.py',),
      affected_recipes('ios/try'),
      default_builders(),
      led_set_builder_recipe('luci.chromium.try:ios-simulator', 'ios/try'),
      led_set_builder_recipe('luci.chromium.try-81:ios-simulator', 'ios/try'),
      led_set_builder_recipe('luci.chromium.try-83:ios-simulator', 'ios/try'),
  )

  yield api.test(
      'ios-try-recipe-change',
      api.properties.tryserver(repo_name='build'),
      gerrit_change(),
      affected_files('scripts/slave/recipes/ios/try.py',),
      affected_recipes('ios/try'),
      default_builders(),
      led_set_builder_recipe('luci.chromium.try:ios-simulator', 'ios/try'),
      led_set_builder_recipe('luci.chromium.try-81:ios-simulator', 'ios/try'),
      led_set_builder_recipe('luci.chromium.try-83:ios-simulator', 'ios/try'),
  )
