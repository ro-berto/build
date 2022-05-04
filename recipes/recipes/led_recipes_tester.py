# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests a recipe CL by running a chromium builder."""

import attr
import collections
import re

from recipe_engine import post_process

from PB.go.chromium.org.luci.led.job import job as job_pb2

from RECIPE_MODULES.build.attr_utils import (attrib, attrs, cached_property,
                                             enum, sequence)

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'recipe_engine/buildbucket',
    'recipe_engine/cipd',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/futures',
    'recipe_engine/json',
    'recipe_engine/led',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/swarming',
    'depot_tools/gclient',
    'depot_tools/bot_update',
    'depot_tools/tryserver',
]


# If present in a CL description, will override the existing default builders
# with a custom list. Format is expected to be:
# "luci.<project>.<bucket>:<builder>"
# For example: "luci.chromium.try:some-builder"
BUILDER_FOOTER = 'Led-Recipes-Tester-Builder'


@attrs()
class BuilderToTrigger(object):
  # The buildbucket v1 style name of the builder
  name = attrib(str)
  # The key of the CL to use when triggering the builder
  cl_key = attrib(enum(['fast', 'slow']), default='slow')


DEFAULT_BUILDERS = (
    BuilderToTrigger('luci.chromium.try:chromium_presubmit', cl_key='fast'),
    BuilderToTrigger('luci.chromium.try:linux-rel'),
    BuilderToTrigger(
        'luci.chromium.try:win10_chromium_x64_rel_ng', cl_key='fast'),
)


@attrs()
class FilesToIgnore(object):
  # A list of strings containing regex patterns of files to ignore. The patterns
  # will be matched against the repo-root-relative paths of the affected files
  # (e.g. recipes/recipe_modules/chromium_tests_builder_config/trybots.py). The
  # patterns will be implicitly anchored to match the entire relative path.
  patterns = attrib(sequence[str])

  # If any files match `ignore_patterns`, a step will be created with the name
  # `step_name` and the step text will combine `step_text` and the list of
  # excluded files.
  step_name = attrib(str)
  step_text = attrib(str)

  @cached_property
  def regex(self):
    # Create a single pattern that has all of the patterns as options. Surround
    # each individual pattern with parentheses so that the | applies to the
    # whole pattern, not just the boundary characters.
    pattern = '|'.join('({})'.format(p) for p in self.patterns)
    # Anchor the combined pattern so that the whole string must be matched.
    # Parentheses are used so that the anchors apply to the entire combined
    # pattern, not just the first and last options.
    pattern = '^({})$'.format(pattern)
    return re.compile(pattern)


# The builders and trybots files affect specific builders, so when changes only
# affect these files, launching the default set of builders will only provide a
# useful signal in the small percentage of CLs that affect those default
# builders and unnecesarily consume resources and time in the rest of the CLs
DEFAULT_FILES_TO_IGNORE = (FilesToIgnore(
    patterns=[
        'recipes/recipe_modules/chromium_tests_builder_config/{}'.format(r)
        for r in (r'builders/.*\.py', r'trybots\.py')
    ],
    step_name='ignoring per-builder config',
    step_text=('The following affected files are being ignored because they'
               ' contain per-builder config that is unlikely to affect the'
               ' default builders:'),
),)

FILES_TO_ALWAYS_IGNORE = (
    FilesToIgnore(
        patterns=[
            r'(.+/)?recipe_modules/[^/]+/examples/.+',
            r'(.+/)?recipe_modules/[^/]+/tests/.+',
        ],
        step_name='ignoring recipe tests',
        step_text=('The following affected files'
                   ' do not contain production recipe code:'),
    ),
    FilesToIgnore(
        patterns=[r'(.+/)*[A-Z_]*OWNERS'],
        step_name='ignoring OWNERS files',
        step_text=(
            'The following affected files are being ignored because they are'
            ' OWNERS files, which contain repository metadata and are not part'
            ' of the recipes:'),
    ),
    FilesToIgnore(
        patterns=[
            r'(.+/)?recipe_modules/chromium_tests_builder_config/migration/.+',
        ],
        step_name='ignoring src-side config migration files',
        step_text=(
            'The following affected files are being ignored because they are'
            ' used for tracking the migration of builder configs src-side and'
            ' are not part of the recipes:'),
    ))

# CL to use when testing a recipe which touches chromium source.
# The first level of keys is the bucket of the builder. The second level of keys
# is the type of CL: 'fast' or 'slow', with the value being the CL to use.

# The slow CLs touch `DEPS` which causes analyze to compile and test all
# targets.

# The fast CLs touch `chrome/test/base/interactive_test_utils.cc`, resulting
# in just interactive_ui_tests being built and run. This is a relatively
# fast, but still swarmed w/ multiple shards, test suite. This fast
# verification is used for "upstream-only-changes" on the assumption that no
# upstream code would (should) have variable effects based on WHICH test
# suite is executed, so we just need to pick SOME test suite.
CHROMIUM_SRC_TEST_CLS = {
    'luci.chromium.try': {
        'slow':
            'https://chromium-review.googlesource.com/c/chromium/src/+/1286761',
        'fast':
            'https://chromium-review.googlesource.com/c/chromium/src/+/3299047',
    },
}


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

  return [BuilderToTrigger(builder) for builder in builders]


def _get_builders_to_check(api):
  """Get the set of builders to test the recipe change against.

  If the CL has Led-Recipes-Tester-Builder footer in its description,
  then those builders will be the ones tested, otherwise a default set
  of builders will be the ones tested. In both cases, branched versions
  of the builders will be provisonally included.

  Args:
    * api - The recipe API object.

  Returns:
    A 2-element tuple:
      * A sequence of BuilderToTrigger for the builders that should be
        checked.
      * A list of FilesToIgnore indicating files that should be ignored
        when determining if a recipe is affected.
  """
  files_to_ignore = []

  footer_builders = api.tryserver.get_footer(BUILDER_FOOTER)
  if footer_builders:
    builders = _process_footer_builders(api, footer_builders)
  else:
    builders = DEFAULT_BUILDERS
    files_to_ignore.extend(DEFAULT_FILES_TO_IGNORE)

  files_to_ignore.extend(FILES_TO_ALWAYS_IGNORE)

  return builders, files_to_ignore


def _ignore_affected_files(api, repo_path, affected_files, files_to_ignore):
  """Ignore files for analysis that match a regex.

  Args:
    api - The recipe API object.
    repo_path - The path to the repo root.
    affected_files - The list of files affected by the change.
    files_to_ignore - A list of `FilesToIgnore` that detail the files to
      ignore for analysis.

  Returns:
    The list of affected files with ignored files removed.
  """
  ignored_files = {i: [] for i in files_to_ignore}
  new_affected_files = []

  for f in affected_files:
    rel_path = api.path.relpath(f, repo_path)
    ignored = False
    for i in files_to_ignore:
      if i.regex.match(rel_path):
        ignored_files[i].append(f)
        ignored = True
    if not ignored:
      new_affected_files.append(f)

  for i, files in ignored_files.items():
    if files:
      step_result = api.step(i.step_name, [])
      message = ['\n' + i.step_text]
      message.extend('*   {}'.format(f.replace('*', r'\*').replace('_', r'\_'))
                     for f in sorted(files))
      step_result.presentation.step_text = '\n'.join(message)

  return new_affected_files


def _get_led_builders(api, builders):
  """Get the led job definitions for the builders.

  Args:
    api - The recipe API object.
    builders - A sequence of BuilderToTrigger.

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
    for builder in builders:
      # Nest the led get-builder call because we don't get to control the step
      # name and having the step name identify the buidler we're getting is more
      # helpful than 'led get-builder', 'led get-builder (2)',
      # 'led get-builder (3)', etc.
      with api.step.nest('get ' + builder.name):
        # By default, the priority of the tasks will be increased by 10, but
        # since this builder runs as part of CQ for the recipe repos, we want
        # the builds to run at regular priority
        led_builders[builder.name] = api.led('get-builder', '-adjust-priority',
                                             '0', builder.name)

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
      'vpython',
      recipes_py_path,
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
  result = api.step(
      step_name,
      cmd,
      ok_ret='any',
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
    return builder.cl_key

  if str(recipes_cfg_path) in affected_files:
    return 'fast'

  return None


def _test_builder(api, affected_files, affected_recipes, builder, led_builder,
                  recipes_cfg_path):
  """Try running a builder with the patched recipe.

  Args:
    api - The recipe API object.
    presentation - The step presentation for the top-level step for the
      builder.
    affected_files - The set of files affected by the change.
    affected_recipes - The set of recipes affected by the change.
    builder - The name of the builder to test.
    led_builder - The led job definition for the builder. It must
      already have had its recipe bundle modified.
    recipes_cfg_path - A Path object identifying the location of the
      recipes.cfg file.

  Raises:
    InfraFailure if any of the led calls fail.
    StepFailure if the triggered task failed.
  """
  with api.step.nest('test {}'.format(builder.name)) as presentation:
    cl_key = _get_cl_category_to_trigger(affected_files, affected_recipes,
                                         builder, _get_recipe(led_builder),
                                         recipes_cfg_path)
    if not cl_key:
      presentation.step_text = (
          '\nNot running a tryjob for {!r}. The CL does not affect the '
          '{!r} recipe and the CL does not affect recipes.cfg'.format(
              builder.name, _get_recipe(led_builder)))
      return

    with api.step.nest('trigger'), api.context(infra_steps=True):
      # FIXME: We should check if the recipe we're testing tests patches to
      # chromium/src. For now just assume this works.
      bucket = builder.name.split(':', 1)[0]
      cl = CHROMIUM_SRC_TEST_CLS[bucket][cl_key]
      ir = led_builder.then('edit-cr-cl', cl)
      # TODO(gbeaty) Once the recipe engine no longer supports annotations and
      # nest step presentation is reflected in the UI before it's closed, we can
      # just update the nest step's presentation
      step_result = api.step.active_result
      step_result.presentation.links['Test CL ({})'.format(cl_key)] = cl
      presentation.links.update(step_result.presentation.links)

      # We used to set `is_experimental` to true, but the chromium recipe
      # currently uses that to deprioritize swarming tasks, which results in
      # very slow runtimes for the led task. Because this recipe blocks the
      # build.git CQ, we decided the tradeoff to run these edited recipes in
      # production mode instead would be better.
      ir = ir.then('edit', '-exp', 'false')
      ir = ir.then('launch', '-resultdb', 'on')

      job = ir.launch_result
      presentation.links['Swarming task'] = job.swarming_task_url

    results = api.swarming.collect(
        'collect',
        [job.task_id],
        # We're launching LUCI builders, so they can be viewed in the Milo UI,
        # which is much better than the stdout, so don't take the time to
        # download the stdout
        task_output_stdout='none')
    for result in results:
      result.analyze()


def RunSteps(api):
  gclient_config = api.gclient.make_config()
  s = gclient_config.solutions.add()
  s.url = api.tryserver.gerrit_change_repo_url
  s.name = s.url.rsplit('/', 1)[-1]
  gclient_config.got_revision_mapping[s.name] = 'got_revision'

  with api.context(cwd=api.path['cache'].join('builder')):
    update_result = api.bot_update.ensure_checkout(
        patch=True, gclient_config=gclient_config)

  repo_path = api.path['cache'].join('builder',
                                     update_result.json.output['root'])

  with api.context(cwd=repo_path):
    affected_files = api.tryserver.get_files_affected_by_patch(repo_path)

  builders_to_trigger, files_to_ignore = _get_builders_to_check(api)

  affected_files = _ignore_affected_files(api, repo_path, affected_files,
                                          files_to_ignore)
  if not affected_files:
    result = api.step('all affected files ignored', [])
    result.presentation.step_text = (
        'all affected files have been ignored, there is nothing to test')
    return

  led_builders = _get_led_builders(api, builders_to_trigger)
  recipes = set(
      _get_recipe(led_builder) for led_builder in led_builders.values())

  recipes_py_path = api.cipd.ensure_tool(
      'infra/recipe_bundles/chromium.googlesource.com/infra/luci/recipes-py',
      version='refs/heads/main',
      executable_path='recipe_engine/recipes.py')
  recipes_cfg_path = repo_path.join('infra', 'config', 'recipes.cfg')
  affected_recipes = _determine_affected_recipes(
      api, affected_files, recipes, recipes_py_path, recipes_cfg_path)

  api.swarming.ensure_client()

  futures = []
  for builder in builders_to_trigger:
    # Edit the recipe bundle in the main greenlet so that it is serialized to
    # avoid the concurrency issues of edit-recipe-bundle.
    #
    # TODO(crbug.com/1088020) If edit-recipe-bundle is made concurrency safe, it
    # can be done in the _test_builder call. If a solution is added that
    # performs the bundle once and has the same bootstrap support as
    # edit-recipe-bundle, switch to that.
    with api.step.nest('edit recipe bundle for {}'.format(builder.name)):
      with api.context(cwd=repo_path):
        led_builder = led_builders[builder.name]
        led_builder = led_builder.then('edit-recipe-bundle')
    futures.append(
        api.futures.spawn_immediate(_test_builder, api, affected_files,
                                    affected_recipes, builder, led_builder,
                                    recipes_cfg_path))

  for f in api.futures.wait(futures):
    f.result()


def GenTests(api):
  RECIPE = 'foo_recipe'

  def gerrit_change(footer_builder=None):
    patch_set = 12
    t = api.buildbucket.try_build(
        git_repo='https://chromium.googlesource.com/foo/bar/baz',
        change_number=456789,
        patch_set=patch_set)

    message = 'nothing important'
    parse_description_json = {}
    if footer_builder:
      message = '{}: {}'.format(BUILDER_FOOTER, footer_builder)
      parse_description_json = {BUILDER_FOOTER: [footer_builder]}

    t += api.override_step_data(
        'gerrit changes',
        api.json.output([{
            'revisions': {
                1: {
                    '_number': patch_set,
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

  def led_job(recipe):
    job = job_pb2.Definition()
    build = job.buildbucket.bbagent_args.build
    build.input.properties['recipe'] = recipe
    build.infra.swarming.priority = 40
    return job

  def default_builders():
    return api.led.mock_get_builder(led_job(RECIPE))

  def affected_recipes_input_files(steps):
    json_input = steps['determine affected recipes'].cmd[-2]
    return api.json.loads(json_input)['files']

  def affected_recipes_input_files_does_not_contain(check, steps, *rel_paths):
    input_files = affected_recipes_input_files(steps)
    for rel_path in rel_paths:
      path = str(api.path['cache'].join('builder', 'baz', *rel_path.split('/')))
      check(path not in input_files)

  def affected_recipes_input_files_contains(check, steps, *rel_paths):
    input_files = affected_recipes_input_files(steps)
    for rel_path in rel_paths:
      path = str(api.path['cache'].join('builder', 'baz', *rel_path.split('/')))
      check(path in input_files)

  yield api.test(
      'basic',
      gerrit_change(),
      affected_recipes(RECIPE),
      default_builders(),
  )

  def builder_config_path(p):
    return 'recipes/recipe_modules/chromium_tests_builder_config/{}'.format(p)

  yield api.test(
      'per_builder_config_ignored',
      gerrit_change(),
      affected_recipes(RECIPE),
      affected_files(
          'recipes/foo.py',
          builder_config_path('builders/__init__.py'),
          builder_config_path('builders/chromium.py'),
          builder_config_path('trybots.py'),
      ),
      default_builders(),
      api.post_check(post_process.MustRun, 'ignoring per-builder config'),
      api.post_check(post_process.StepTextContains,
                     'ignoring per-builder config', [r'\_\_init\_\_.py']),
      api.post_check(affected_recipes_input_files_does_not_contain,
                     builder_config_path('builders/__init__.py'),
                     builder_config_path('builders/chromium.py'),
                     builder_config_path('trybots.py')),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'recipe_test_ignored',
      gerrit_change(),
      affected_recipes(RECIPE),
      affected_files(
          'recipes/foo.py',
          'recipes/recipe_modules/chromium_swarming/examples/full.py',
          builder_config_path('tests/builders.py'),
      ),
      default_builders(),
      api.post_check(post_process.MustRun, 'ignoring recipe tests'),
      api.post_check(
          affected_recipes_input_files_does_not_contain,
          'recipes/recipe_modules/chromium_swarming/examples/full.py',
          builder_config_path('tests/builders.py')),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'owners_files_ignored',
      gerrit_change(),
      affected_recipes(RECIPE),
      affected_files(
          'recipes/foo.py',
          builder_config_path('OWNERS'),
          'recipes/recipe_modules/chromium_tests/CHROMIUM_TESTS_OWNERS',
      ),
      default_builders(),
      api.post_check(post_process.MustRun, 'ignoring OWNERS files'),
      api.post_check(
          affected_recipes_input_files_does_not_contain,
          builder_config_path('OWNERS'),
          'recipes/recipe_modules/chromium_tests/CHROMIUM_TESTS_OWNERS'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'src_side_migration_files_ignored',
      gerrit_change(),
      affected_recipes(RECIPE),
      affected_files(
          'recipes/foo.py',
          builder_config_path('migration/chromium.json'),
      ),
      default_builders(),
      api.post_check(post_process.MustRun,
                     'ignoring src-side config migration files'),
      api.post_check(affected_recipes_input_files_does_not_contain,
                     builder_config_path('migration/chromium.json')),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'all_affected_files_are_ignored',
      gerrit_change(),
      affected_files(builder_config_path('builders/__init__.py')),
      api.post_check(post_process.MustRun, 'all affected files ignored'),
      api.post_check(post_process.DoesNotRun, 'determine affected recipes'),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'expired_tryjob',
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
      gerrit_change(),
      default_builders(),
      api.post_check(post_process.DoesNotRunRE, 'test .*\.trigger'),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'recipe_roller',
      gerrit_change(),
      affected_files(
          'random/file.py',
          'infra/config/recipes.cfg',
      ),
      default_builders(),
  )

  yield api.test(
      'manual_roll_with_changes',
      gerrit_change(),
      affected_files(
          'random/file.py',
          'infra/config/recipes.cfg',
      ),
      default_builders(),
  )

  yield api.test(
      'analyze_missing_json',
      gerrit_change(),
      default_builders(),
      api.override_step_data('determine affected recipes', retcode=1),
      api.post_check(post_process.StepException, 'determine affected recipes'),
      api.post_check(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'analyze_failure',
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
      gerrit_change(footer_builder='luci.chromium.try:arbitrary-builder'),
      affected_recipes(RECIPE),
      default_builders(),
      api.post_check(post_process.DoesNotRun,
                     *[led_get_builder_name(b) for b in DEFAULT_BUILDERS]),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'per_builder_config_not_ignored_for_footer_builders',
      gerrit_change(footer_builder='luci.chromium.try:arbitrary-builder'),
      affected_recipes(RECIPE),
      affected_files(
          builder_config_path('builders/chromium.py'),
          builder_config_path('trybots.py')),
      default_builders(),
      api.post_check(post_process.DoesNotRun, 'ignoring builder config'),
      api.post_check(affected_recipes_input_files_contains,
                     builder_config_path('builders/chromium.py'),
                     builder_config_path('trybots.py')),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'footer_builder_does_not_exist',
      gerrit_change(footer_builder='luci.chromium.try:arbitrary-builder'),
      non_existent_builder('luci.chromium.try:arbitrary-builder'),
      api.post_check(
          post_process.StepFailure,
          led_get_builder_name('luci.chromium.try:arbitrary-builder')),
      api.post_check(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
