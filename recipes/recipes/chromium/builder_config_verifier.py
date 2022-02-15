# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Checks src-side builder configs against the recipe config objects.

Once migration of all specs to src is complete, this recipe will be
irrelevant.
"""

import attr
import difflib

from google.protobuf import json_format

from recipe_engine import post_process
from recipe_engine.engine_types import thaw

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from RECIPE_MODULES.build import proto_validation
from RECIPE_MODULES.build.chromium import BuilderId

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from PB.recipe_engine import result as result_pb
from PB.recipes.build.chromium import (builder_config_verifier as
                                       builder_config_verifier_pb)
from PB.recipe_modules.build.chromium_tests_builder_config import (properties as
                                                                   properties_pb
                                                                  )
PYTHON_VERSION_COMPATIBILITY = "PY3"

PROPERTIES = builder_config_verifier_pb.InputProperties

DEPS = [
    'chromium_tests_builder_config',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/git',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/futures',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]


def RunSteps(api, properties):
  api.tryserver.require_is_tryserver()

  errors = VALIDATORS.validate(properties)
  if errors:
    return _result(
        status=common_pb.INFRA_FAILURE,
        elements=errors,
        header='The following errors were found with the input properties:')

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

  return _verify_builder_configs(api, repo_path,
                                 properties.builder_config_directory)


VALIDATORS = proto_validation.Registry()


@VALIDATORS.register(builder_config_verifier_pb.InputProperties)
def _validate_properties(message, ctx):
  ctx.validate_field(message, 'builder_config_directory')


def _result(status, header, elements):
  summary = [header, '']
  summary.extend('* {}'.format(e) for e in elements)
  return result_pb.RawResult(status=status, summary_markdown='\n'.join(summary))


def _verify_builder_configs(api, repo_path, builder_config_directory):
  with api.step.nest('determine affected properties files'):
    with api.context(cwd=repo_path):
      affected_files = api.tryserver.get_files_affected_by_patch('')

    paths = api.file.glob_paths(
        'find builder properties files',
        repo_path,
        '{}/*/*/properties.json'.format(builder_config_directory),
        include_hidden=True)
    properties_files = set(api.path.relpath(p, repo_path) for p in paths)

    with api.context(cwd=repo_path.join(builder_config_directory)):
      # Lists the files known to git at HEAD
      result = api.git(
          'ls-tree',
          '-r',
          'HEAD',
          '--name-only',
          stdout=api.raw_io.output_text(add_output_log=True))
    files_at_head = set('{}/{}'.format(builder_config_directory, f)
                        for f in result.stdout.strip().splitlines())

  futures = []
  for f in sorted(affected_files):
    if f not in properties_files:
      continue

    builder = f.rsplit('/', 2)[1]

    futures.append(
        api.futures.spawn_immediate(
            _verify_builder_config,
            api,
            repo_path,
            files_at_head,
            f,
            builder,
            __name=f))

  api.futures.wait(futures)

  failures = [f.name for f in futures if not f.result()]
  if failures:
    return _result(
        status=common_pb.FAILURE,
        elements=failures,
        header='Could not verify the following files:')


_CTBC_PROPERTY = '$build/chromium_tests_builder_config'


def _verify_builder_config(api, repo_path, files_at_head, f, builder):
  with api.step.nest('verify {}'.format(f)) as presentation:

    def success(message):
      presentation.step_text = '\n' + message
      return True

    def failure(message):
      presentation.status = api.step.FAILURE
      presentation.step_text = '\n' + message
      return False

    properties = api.file.read_json(
        'read file at CL', repo_path.join(f), test_data={}, include_log=True)
    if _CTBC_PROPERTY not in properties:
      return success('{} is not set, nothing to verify'.format(_CTBC_PROPERTY))

    if f in files_at_head:
      result = api.git(
          'cat-file',
          'HEAD:{}'.format(f),
          '--textconv',
          name='read file at HEAD',
          stdout=api.raw_io.output_text(),
      )
      result.presentation.logs[f.rsplit('/', 1)[-1]] = result.stdout
      prev_properties = api.json.loads(result.stdout)

      builder_config_property = properties[_CTBC_PROPERTY]
      prev_builder_config_property = prev_properties.get(_CTBC_PROPERTY)
      if builder_config_property == prev_builder_config_property:
        return success(
            '{} is unchanged, nothing to verify'.format(_CTBC_PROPERTY))

    if 'builder_group' not in properties:
      return failure("builder_group property is not set, can't verify")

    builder_id = BuilderId.create_for_group(properties['builder_group'],
                                            builder)

    ctbc_api = api.chromium_tests_builder_config
    try:
      recipe_config = ctbc.BuilderConfig.lookup(
          builder_id, ctbc_api.builder_db, ctbc_api.try_db, use_try_db=True)
    except ctbc.BuilderConfigException:
      return success('no recipe config exists, nothing to verify')

    ctbc_properties = properties_pb.InputProperties()
    json_format.ParseDict(properties[_CTBC_PROPERTY], ctbc_properties)
    src_side_config = ctbc.proto.convert_builder_config(
        ctbc_properties.builder_config)

    diff = _compare_builder_configs(api, recipe_config, src_side_config)
    if diff:
      presentation.logs['diff'] = diff
      return failure("builder configs differ, see 'diff' log for details")

    return success('src-side config matches recipe config')


def _compare_builder_configs(api, recipe_config, src_side_config):
  """Compare recipe and src-side configs for equivalence.

  There are some differences that need to be massaged between recipe
  configs and src-side configs:
  1. The builder DB will be the entire static DB for recipe configs
    whereas it will only contain the relevant entries for src-side
    configs
  2. include_all_triggered_testers is not part of the proto since it
    will already be reflected in the entries being added by the src-side
    generator, in both cases, builder_ids_in_scope_for_testing will
    already reflect whether or not it was set
  3. simulation_platform is not part of the proto since it's only used
    in recipe tests

  A comparison can be performed directly between BuilderConfig objects,
  but removing the irrelevant fields from the diff would involve
  repetition, so instead convert the configs to a representative json
  format and compare that.

  Args:
    recipe_config: The BuilderConfig obtained from the static DBs.
    src_side_config: The BuilderConfig obtained from the properties
      file.

  Returns:
    A list of strings with the differences between the representative
    json if they differ. Otherwise, None.
  """

  def default_json_conversion(obj):
    # BuilderId is used as keys in BuilderDatabase, but keys in json can't be
    # arbitrary objects, so convert it to strings to match how they'll be
    # presented for BuilderDatabase
    if isinstance(obj, BuilderId):
      return str(obj)

    if attr.has(obj):
      # Don't recurse, otherwise other attrs types will get converted to dicts
      # and we won't be given the opportunity to make type-specific tweaks to
      # child objects.
      d = attr.asdict(obj, recurse=False)

      # Logically, the DB is just a mapping of builder ID to spec; the
      # builders_by_group field is redundant with the _db field, so just present
      # it as a dict mapping ID to spec. Keys in json can't be arbitrary objects
      # (and the json module use the default callback for dict keys), so convert
      # the keys to strings.
      if isinstance(obj, ctbc.BuilderDatabase):
        return {
            str(builder_id): builder_spec
            for builder_id, builder_spec in d['_db'].items()
        }

      # include_all_triggered_testers will already be reflected in
      # builder_ids_in_scope_for_testing and it doesn't appear in the proto, so
      # set it to False so that it doesn't impact comparison
      if isinstance(obj, ctbc.BuilderConfig):
        d.pop('include_all_triggered_testers', None)
        # Make sure unordered collections are sorted for comparison
        d['builder_ids'] = sorted(d['builder_ids'])
        d['mirroring_try_builders'] = sorted(d['mirroring_try_builders'])
        # Use the effective value for builder_ids_in_scope_for_testing rather
        # than the private field
        d['builder_ids_in_scope_for_testing'] = sorted(
            obj.builder_ids_in_scope_for_testing)
        del d['_builder_ids_in_scope_for_testing']
        return d

      if isinstance(obj, ctbc.BuilderSpec):
        # Simulation platform is only used for running recipe tests, it doesn't
        # appear in the proto
        d.pop('simulation_platform', None)
        return d

      return d  # pragma: no cover

    # FrozenDict is not JSON serializable, so thaw it out
    thawed = thaw(obj)
    if thawed is not obj:
      return thawed

    raise TypeError(
        '{!r} is not JSON serializable'.format(obj))  # pragma: no cover

  def convert_to_json(builder_config):
    return api.json.dumps(
        builder_config, indent=2, default=default_json_conversion).splitlines()

  def normalize_recipe_config(builder_config):
    builder_db = builder_config.builder_db
    builders_by_group = {}
    for i in builder_config.builder_ids_in_scope_for_testing:
      builder_spec = builder_db[i]
      # Recipe configs can omit the parent builder group, which is treated as
      # the same builder group as the associated builder
      if (builder_spec.parent_buildername and
          not builder_spec.parent_builder_group):
        builder_spec = attr.evolve(builder_spec, parent_builder_group=i.group)
      builders_by_group.setdefault(i.group, {})[i.builder] = builder_spec
    return attr.evolve(
        builder_config,
        builder_db=ctbc.BuilderDatabase.create(builders_by_group))

  recipe_config_json = convert_to_json(normalize_recipe_config(recipe_config))
  src_side_config_json = convert_to_json(src_side_config)

  return list(
      difflib.unified_diff(
          recipe_config_json,
          src_side_config_json,
          fromfile='recipe builder config',
          tofile='src-side builder config',
          n=max(len(recipe_config_json), len(src_side_config_json)),
      ))


def GenTests(api):

  def properties(**kwargs):
    return api.properties(builder_config_verifier_pb.InputProperties(**kwargs))

  def affected_file(f):
    return api.tryserver.get_files_affected_by_patch(
        [f],
        step_name=(
            'determine affected properties files.git diff to analyze patch'))

  def properties_file(builder_config_directory,
                      f,
                      patched_content=None,
                      content_at_head=None,
                      affected=True):
    assert f.startswith(builder_config_directory + '/')
    t = properties(builder_config_directory=builder_config_directory)
    t += api.override_step_data(
        'determine affected properties files.find builder properties files',
        api.file.glob_paths([f]))
    if affected:
      t += affected_file(f)
    if patched_content is not None:
      t += api.override_step_data('verify {}.read file at CL'.format(f),
                                  api.file.read_text(patched_content))
    if content_at_head is not None:
      relative_f = f[len(builder_config_directory) + 1:]
      t += api.override_step_data(
          'determine affected properties files.git ls-tree',
          api.raw_io.stream_output_text('{}\n'.format(relative_f)))
      t += api.override_step_data(
          'verify {}.read file at HEAD'.format(f),
          api.raw_io.stream_output_text(content_at_head))
    return t

  def dumps(obj):
    return api.json.dumps(obj, indent=2)

  def check_verify(check,
                   steps,
                   step_name,
                   status='SUCCESS',
                   step_text=None,
                   has_log=None):
    if check('step {} was run'.format(step_name), step_name in steps):
      step = steps[step_name]
      if check('step {} has expected status'.format(step_name),
               step.status == status):
        if step_text is not None:
          message = 'step_text for step {} contains expected string'.format(
              step_name)
          check(message, step_text in step.step_text)
        if has_log is not None:
          check('step {} has log {}'.format(step_name, has_log),
                has_log in step.logs)

  def build_failure_result(check, steps, *files):
    return post_process.ResultReason(
        check, steps,
        '\n* '.join(['Could not verify the following files:\n'] + list(files)))

  yield api.test(
      'non-properties-file',
      api.buildbucket.try_build(),
      properties(builder_config_directory='props-files'),
      affected_file('foo/bar/non-properties-file'),
      api.post_check(post_process.DoesNotRun,
                     'verify foo/bar/non-properties-file'),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'unaffected-properties-files',
      api.buildbucket.try_build(),
      properties_file(
          'props-files',
          'props-files/bucket/unchanged/properties.json',
          affected=False),
      api.post_check(post_process.DoesNotRun,
                     'verify props-files/bucket/unchanged/properties.json'),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'properties-file-without-builder-config',
      api.buildbucket.try_build(),
      properties_file(
          'props-files',
          'props-files/bucket/no-builder-config/properties.json',
          patched_content=api.json.dumps('{}')),
      api.post_check(
          check_verify,
          'verify props-files/bucket/no-builder-config/properties.json',
          step_text=('$build/chromium_tests_builder_config is not set,'
                     ' nothing to verify')),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'unchanged-builder-config',
      api.buildbucket.try_build(),
      properties_file(
          'props-files',
          'props-files/bucket/same-builder-config/properties.json',
          # We only evaluate it if its changed and there's a recipe config to
          # compare against, so it doesn't need to be valid
          patched_content=dumps({
              '$build/chromium_tests_builder_config': {
                  'foo': 'bar',
              },
          }),
          content_at_head=dumps({
              '$build/chromium_tests_builder_config': {
                  'foo': 'bar',
              },
          }),
      ),
      api.post_check(
          check_verify,
          'verify props-files/bucket/same-builder-config/properties.json',
          step_text=('$build/chromium_tests_builder_config is unchanged,'
                     ' nothing to verify')),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'changed-builder-config-no-builder-group',
      api.buildbucket.try_build(),
      properties_file(
          'props-files',
          'props-files/bucket/no-builder-group/properties.json',
          # We only evaluate it if its changed and there's a recipe config to
          # compare against, so it doesn't need to be valid
          patched_content=dumps({
              '$build/chromium_tests_builder_config': {
                  'foo': 'bar',
              },
          }),
      ),
      api.post_check(
          check_verify,
          'verify props-files/bucket/no-builder-group/properties.json',
          status='FAILURE',
          step_text="builder_group property is not set, can't verify"),
      api.post_check(post_process.StatusFailure),
      api.post_check(build_failure_result,
                     'props-files/bucket/no-builder-group/properties.json'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'changed-builder-config-without-recipe-config',
      api.buildbucket.try_build(),
      properties_file(
          'props-files',
          'props-files/bucket/no-recipe-config/properties.json',
          # We only evaluate it if its changed and there's a recipe config to
          # compare against, so it doesn't need to be valid
          patched_content=dumps({
              '$build/chromium_tests_builder_config': {
                  'foo': 'bar',
              },
              'builder_group': 'fake-group',
          }),
      ),
      api.chromium_tests_builder_config.builder_db(
          ctbc.BuilderDatabase.create({})),
      api.post_check(
          check_verify,
          'verify props-files/bucket/no-recipe-config/properties.json',
          step_text='no recipe config exists, nothing to verify'),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  example_spec = ctbc.BuilderSpec.create(
      chromium_config='chromium',
      gclient_config='chromium',
  )

  ctbc_api = api.chromium_tests_builder_config

  ctbc_prop = (
      ctbc_api.properties_builder_for_ci_builder(
          bucket='bucket',
          builder='matching-config',
          builder_group='fake-group',
          builder_spec=example_spec,
      ).with_tester(
          builder='matching-config-tester',
          builder_group='fake-group',
      ).build())

  yield api.test(
      'changed-builder-config-matching-recipe-config',
      api.buildbucket.try_build(),
      properties_file(
          'props-files',
          'props-files/bucket/matching-config/properties.json',
          patched_content=dumps({
              '$build/chromium_tests_builder_config':
                  json_format.MessageToDict(ctbc_prop),
              'builder_group':
                  'fake-group',
          }),
      ),
      api.chromium_tests_builder_config.builder_db(
          ctbc.BuilderDatabase.create({
              'fake-group': {
                  'matching-config':
                      attr.evolve(example_spec, simulation_platform='linux'),
                  'matching-config-tester':
                      attr.evolve(
                          example_spec,
                          execution_mode=ctbc.TEST,
                          parent_buildername='matching-config',
                      ),
              },
              # The recipe config will have the entire builder DB, so this
              # ensures that the verification accounts for that
              'unrelated-group': {
                  'unrelated-builder': example_spec,
              },
          })),
      api.post_check(
          check_verify,
          'verify props-files/bucket/matching-config/properties.json',
          step_text='src-side config matches recipe config'),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  ctbc_prop = (
      ctbc_api.properties_builder_for_ci_builder(
          bucket='bucket',
          builder='not-matching-config',
          builder_group='fake-group',
          builder_spec=example_spec,
      ).build())

  yield api.test(
      'changed-builder-config-not-matching-recipe-config',
      api.buildbucket.try_build(),
      properties_file(
          'props-files',
          'props-files/bucket/not-matching-config/properties.json',
          # We only evaluate it if its changed and there's a recipe config
          # to compare against, so it doesn't need to be valid
          patched_content=dumps({
              '$build/chromium_tests_builder_config':
                  json_format.MessageToDict(ctbc_prop),
              'builder_group':
                  'fake-group',
          }),
      ),
      api.chromium_tests_builder_config.builder_db(
          ctbc.BuilderDatabase.create({
              'fake-group': {
                  'not-matching-config':
                      ctbc.BuilderSpec.create(
                          chromium_config='not-chromium',
                          chromium_config_kwargs={
                              'TARGET_PLATFORM': 'mac',
                              'TARGET_BITS': 32,
                          },
                          gclient_config='not-chromium',
                          gclient_apply_config=['foo', 'bar'],
                      ),
              }
          })),
      api.post_check(
          check_verify,
          'verify props-files/bucket/not-matching-config/properties.json',
          status='FAILURE',
          step_text="builder configs differ, see 'diff' log for details",
          has_log='diff'),
      api.post_check(build_failure_result,
                     'props-files/bucket/not-matching-config/properties.json'),
      # Keep just the verify step so that we can see when the diff changes
      api.post_process(
          post_process.Filter(
              'verify props-files/bucket/not-matching-config/properties.json')),
  )

  # Must appear last since it drops expectations
  def invalid_properties(*errors):
    test_data = api.post_check(post_process.StatusException)
    test_data += api.post_check(
        post_process.ResultReasonRE,
        '^The following errors were found with the input properties')
    for error in errors:
      test_data += api.post_check(post_process.ResultReasonRE, error)
    test_data += api.post_process(post_process.DropExpectation)
    return test_data

  yield api.test(
      'builder-config-dir-not-set',
      api.buildbucket.try_build(),
      invalid_properties('builder_config_directory is not set'),
  )
