# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Recipe providing src-side builder config migration functionality.

This recipe is not used on any builder, it is used as part of a PRESUBMIT check
to prevent additional configs from being added to the recipe.
"""
# TODO(crbug.com/868153) Remove this once the builder config migration is
# complete

import attr
import collections
import contextlib
import re
import textwrap

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from RECIPE_MODULES.build import proto_validation
from RECIPE_MODULES.build.chromium import BuilderId

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from PB.recipe_engine import result as result_pb
from PB.recipes.build.chromium import (builder_config_migration as
                                       builder_config_migration_pb)

PYTHON_VERSION_COMPATIBILITY = 'PY3'

PROPERTIES = builder_config_migration_pb.InputProperties

DEPS = [
    'chromium_tests_builder_config',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/step',
]


def RunSteps(api, properties):
  errors = VALIDATORS.validate(properties)
  if errors:
    summary = ['The following errors were found with the input properties:', '']
    summary.extend(errors)
    return result_pb.RawResult(
        status=common_pb.INFRA_FAILURE, summary_markdown='\n'.join(summary))

  handlers_by_operation = {
      'groupings_operation': _groupings_operation,
      'migration_operation': _migration_operation,
  }
  operation = properties.WhichOneof('operation')
  handler = handlers_by_operation[operation]
  return handler(api, getattr(properties, operation))


VALIDATORS = proto_validation.Registry()


@VALIDATORS.register(builder_config_migration_pb.InputProperties)
def _validate_properties(message, ctx):
  operation = message.WhichOneof('operation')
  if operation:
    ctx.validate_field(message, operation)
  else:
    ctx.error('no operation is set')


@VALIDATORS.register(builder_config_migration_pb.GroupingsOperation)
def _validate_groupings_operation(message, ctx):
  ctx.validate_field(message, 'output_path')
  ctx.validate_repeated_field(message, 'builder_group_filters')


@VALIDATORS.register(
    builder_config_migration_pb.GroupingsOperation.BuilderGroupFilter)
def _validate_builder_group_filter(message, ctx):
  ctx.validate_field(message, 'builder_group_regex')


@VALIDATORS.register(builder_config_migration_pb.MigrationOperation)
def _validate_migration_operation(message, ctx):
  ctx.validate_repeated_field(message, 'builders_to_migrate')
  ctx.validate_field(message, 'output_path')


@VALIDATORS.register(
    builder_config_migration_pb.MigrationOperation.BuilderGroupAndName)
def _validate_builder_group_and_name(message, ctx):
  ctx.validate_field(message, 'builder_group')
  ctx.validate_field(message, 'builder')


def _groupings_operation(api, groupings_operation):
  builder_group_filters = []
  for f in reversed(groupings_operation.builder_group_filters):
    regex = re.compile('^{}$'.format(f.builder_group_regex))
    include = not f.exclude
    builder_group_filters.append((regex, include))

  def builder_filter(builder_id):
    builder_group = builder_id.group
    for regex, include in builder_group_filters:
      if regex.match(builder_group):
        return include
    return False

  groupings_by_builder_id = _compute_groupings(api, builder_filter)

  output_path = api.path.abspath(groupings_operation.output_path)

  json = {}
  for b, grouping in groupings_by_builder_id.items():
    json[str(b)] = [str(b2) for b2 in sorted(grouping)]
  output = api.json.dumps(json, indent=2, separators=(',', ': '))

  # Include log during the tests so that the expectation file is easier to
  # review
  api.file.write_text(
      'groupings', output_path, output, include_log=api._test_data.enabled)


class _OutputCollector(object):

  def __init__(self):
    self.lines = []
    self._indent = ''

  @contextlib.contextmanager
  def increase_indent(self, closing_line=None):
    saved = self._indent
    self._indent += ' ' * 4
    yield
    self._indent = saved
    if closing_line is not None:
      self.add_line(closing_line)

  def add_line(self, line):
    self.lines.append(self._indent + line)

  def add_lines(self, lines):
    for l in lines:
      self.add_line(l)


def _failure(summary):
  return result_pb.RawResult(
      status=common_pb.INFRA_FAILURE, summary_markdown=summary)


def _migration_operation(api, migration_operation):
  groupings_by_builder_id = _compute_groupings(api)

  to_migrate = set()
  for b in migration_operation.builders_to_migrate:
    builder_id = chromium.BuilderId.create_for_group(b.builder_group, b.builder)
    grouping = groupings_by_builder_id.get(builder_id)
    if grouping is None:
      return _failure("unknown builder '{}'".format(builder_id))
    to_migrate.update(grouping)

  builder_db = api.chromium_tests_builder_config.builder_db
  try_db = api.chromium_tests_builder_config.try_db

  output = _OutputCollector()

  try:
    for builder_id in sorted(to_migrate):
      output.add_line(str(builder_id))
      with output.increase_indent(''):
        builder_spec = builder_db.get(builder_id)
        if builder_spec is not None:
          output.add_lines(_migrate_builder_spec(builder_id, builder_spec))

        try_spec = try_db.get(builder_id)
        if try_spec is not None:
          output.add_lines(_migrate_try_spec(try_spec))
  except MigrationError as e:
    return _failure(e.summary)

  output_path = api.path.abspath(migration_operation.output_path)
  api.file.write_text('src-side snippets', output_path, '\n'.join(output.lines))


_DEFAULT_BUILDER_SPEC = ctbc.BuilderSpec.create()
_UNSUPPORTED_ATTRS = (
    # Resolve the issues that requires these attributes, then remove all
    # non-default uses
    'set_output_commit',

    # The use of all of these fields should be replaced with the use of
    # the archive module
    'archive_build',
    'gs_bucket',
    'gs_acl',
    'gs_build_name',
    'cf_archive_build',
    'cf_gs_bucket',
    'cf_gs_acl',
    'cf_archive_name',
    'cf_archive_subdir_suffix',
    'bisect_archive_build',
    'bisect_gs_bucket',
    'bisect_gs_extra',
)


class MigrationError(Exception):

  def __init__(self, summary):
    super(MigrationError, self).__init__(summary)
    self.summary = summary


def _migrate_builder_spec(builder_id, builder_spec):
  output = _OutputCollector()

  if builder_spec.execution_mode == ctbc.PROVIDE_TEST_SPEC:
    raise MigrationError(
        "cannot migrate builder '{}' with {} execution_mode".format(
            builder_id, builder_spec.execution_mode))

  invalid_attrs = [
      a for a in _UNSUPPORTED_ATTRS
      if getattr(builder_spec, a) != getattr(_DEFAULT_BUILDER_SPEC, a)
  ]
  if invalid_attrs:
    message = [
        "cannot migrate builder '{}' with the following unsupported attrs:"
        .format(builder_id)
    ]
    for a in invalid_attrs:
      message.append('* {}'.format(a))
    raise MigrationError('\n'.join(message))

  output.add_line('builder_spec = builder_config.builder_spec(')
  with output.increase_indent('),'):
    if builder_spec.execution_mode == ctbc.TEST:
      output.add_line('execution_mode = builder_config.execution_mode.TEST,')

    output.add_line('gclient_config = builder_config.gclient_config(')
    with output.increase_indent('),'):
      output.add_line('config = "{}",'.format(builder_spec.gclient_config))
      if builder_spec.gclient_apply_config:
        output.add_line('apply_configs = [')
        with output.increase_indent('],'):
          for c in builder_spec.gclient_apply_config:
            output.add_line('"{}",'.format(c))

    output.add_line('chromium_config = builder_config.chromium_config(')
    with output.increase_indent('),'):
      output.add_line('config = "{}",'.format(builder_spec.chromium_config))
      if builder_spec.chromium_apply_config:
        output.add_line('apply_configs = [')
        with output.increase_indent('],'):
          for c in builder_spec.chromium_apply_config:
            output.add_line('"{}",'.format(c))
      for k, v in builder_spec.chromium_config_kwargs.items():
        if k == 'BUILD_CONFIG':
          output.add_line(
              'build_config = builder_config.build_config.{},'.format(
                  v.upper()))
        elif k == 'TARGET_ARCH':
          output.add_line('target_arch = builder_config.target_arch.{},'.format(
              v.upper()))
        elif k == 'TARGET_BITS':
          output.add_line('target_bits = {},'.format(v))
        elif k == 'TARGET_PLATFORM':
          output.add_line(
              'target_platform = builder_config.target_platform.{},'.format(
                  v.upper()))
        elif k in ('TARGET_CROS_BOARDS', 'CROS_BOARDS_WITH_QEMU_IMAGES'):
          output.add_line('{} = [,'.format(k.lower()))
          with output.increase_indent('],'):
            for e in v.split(':'):
              output.add_line('"{}",'.format(e))

    if builder_spec.android_config:
      output.add_line('android_config = builder_config.android_config(')
      with output.increase_indent('),'):
        output.add_line('config = "{}",'.format(builder_spec.android_config))
        if builder_spec.android_apply_config:
          output.add_line('apply_configs = [')
          with output.increase_indent('],'):
            for c in builder_spec.android_apply_config:
              output.add_line('"{}",'.format(c))

    if builder_spec.test_results_config:
      output.add_line(
          'test_results_config = builder_config.test_results_config(')
      with output.increase_indent('),'):
        output.add_line('config = "{}",'.format(
            builder_spec.test_results_config))

    if builder_spec.android_version:
      output.add_line('android_version_file = "{}",'.format(
          builder_spec.android_version))

    if builder_spec.clobber:
      output.add_line('clobber = True,')

    if builder_spec.build_gs_bucket:
      output.add_line('build_gs_bucket = "{}",'.format(
          builder_spec.build_gs_bucket))

    if builder_spec.serialize_tests:
      output.add_line('run_tests_serially = True,')

    if builder_spec.perf_isolate_upload:
      output.add_line('perf_isolate_upload = True,')

    if builder_spec.expose_trigger_properties:
      output.add_line('expose_trigger_properties = True,')

    if builder_spec.skylab_gs_bucket:
      output.add_line('skylab_upload_location = '
                      'builder_config.skylab_upload_location(')
      with output.increase_indent('),'):
        output.add_line('gs_bucket = "{}"'.format(
            builder_spec.skylab_gs_bucket))
        if builder_spec.skylab_gs_extra:
          output.add_line('gs_extra = "{}"'.format(
              builder_spec.skylab_gs_extra))

  return output.lines


_DEFAULT_TRY_SPEC = ctbc.TrySpec.create_for_single_mirror(
    'unused-group', 'unused-builder')
_SETTINGS_ATTRS = tuple(
    a.name
    for a in attr.fields(ctbc.TrySpec)
    # There is no default for mirrors, so we don't compare against that.
    # regression_test_selection_recall only has an effect if
    # regression_test_selection is set, so we don't set it in the src snippet
    # unless regression_test_selection is also modified.
    if a.name not in ('mirrors', 'regression_test_selection_recall'))


def _migrate_try_spec(try_spec):
  output = _OutputCollector()

  output.add_line('mirrors = [')
  mirrors = set()
  with output.increase_indent('],'):
    for m in try_spec.mirrors:
      if m.builder_id not in mirrors:
        output.add_line('"ci/{}",'.format(m.builder_id.builder))
        mirrors.add(m.builder_id)
      if m.tester_id and m.tester_id not in mirrors:
        output.add_line('"ci/{}",'.format(m.tester_id.builder))
        mirrors.add(m.tester_id)

  if any(
      getattr(try_spec, a) != getattr(_DEFAULT_TRY_SPEC, a)
      for a in _SETTINGS_ATTRS):
    output.add_line('try_settings = builder_config.try_settings(')
    with output.increase_indent('),'):
      if try_spec.include_all_triggered_testers:
        output.add_line('include_all_triggered_testers = True,')

      if try_spec.is_compile_only:
        output.add_line('is_compile_only = True,')

      if try_spec.analyze_names:
        output.add_line('analyze_names = [')
        with output.increase_indent('],'):
          for n in try_spec.analyze_names:
            output.add_line('"{}",'.format(n))

      if not try_spec.retry_failed_shards:
        output.add_line('retry_failed_shards = False,')

      if not try_spec.retry_without_patch:
        output.add_line('retry_without_patch = False,')

      if try_spec.regression_test_selection != ctbc.NEVER:
        output.add_line('rts_config = builder_config.rts_config(')
        with output.increase_indent('),'):
          output.add_line('condition = builder_config.rts_condition.{},'.format(
              try_spec.regression_test_selection.upper()))
          if (try_spec.regression_test_selection_recall !=
              _DEFAULT_TRY_SPEC.regression_test_selection_recall):
            output.add_line('recall = {},'.format(
                try_spec.regression_test_selection_recall))

  return output.lines


def _compute_groupings(api, builder_filter=None):
  builder_filter = builder_filter or (lambda _: True)

  groupings_by_builder_id = collections.defaultdict(set)

  def check_included(related_ids, step_name):
    included_by_builder_id = {}
    for related_id in related_ids:
      included_by_builder_id[related_id] = builder_filter(related_id)

    included = set(included_by_builder_id.values())
    if len(included) == 1:
      return next(iter(included))

    api.step.empty(
        step_name,
        status=api.step.INFRA_FAILURE,
        log_name='mismatched_inclusion',
        log_text=[
            '{} ignored: {}'.format(builder_id, included)
            for builder_id, included in included_by_builder_id.items()
        ])

  def update_groupings(builder_id, related_ids):
    grouping = groupings_by_builder_id[builder_id]
    grouping.add(builder_id)
    for related_id in related_ids:
      related_grouping = groupings_by_builder_id[related_id]
      related_grouping.add(related_id)
      grouping.update(related_grouping)
      for connected_id in related_grouping:
        groupings_by_builder_id[connected_id] = grouping

  builder_db = api.chromium_tests_builder_config.builder_db
  for builder_id, child_ids in builder_db.builder_graph.items():
    included = check_included([builder_id] + sorted(child_ids),
                              'invalid children for {}'.format(builder_id))
    if included:
      update_groupings(builder_id, child_ids)

  try_db = api.chromium_tests_builder_config.try_db
  for try_id, try_spec in try_db.items():
    mirrored_ids = []
    for mirror in try_spec.mirrors:
      mirrored_ids.append(mirror.builder_id)
      if mirror.tester_id:
        mirrored_ids.append(mirror.tester_id)
    included = check_included(
        mirrored_ids, 'invalid mirroring configuration for {}'.format(try_id))
    if included:
      update_groupings(try_id, mirrored_ids)

  return groupings_by_builder_id


def GenTests(api):
  yield api.test(
      'groupings',
      api.properties(
          groupings_operation={
              'output_path':
                  '/fake/output/path',
              'builder_group_filters': [
                  {
                      'builder_group_regex': r'(tryserver\.)?migration(\..+)?',
                  },
                  {
                      'builder_group_regex': r'migration\.excluded',
                      'exclude': True,
                  },
              ],
          }),
      api.chromium_tests_builder_config.databases(
          ctbc.BuilderDatabase.create({
              'migration.foo': {
                  'foo-builder':
                      ctbc.BuilderSpec.create(),
                  'foo-x-tests':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='foo-builder',
                      ),
                  'foo-y-tests':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='foo-builder',
                      ),
              },
              'migration.bar': {
                  'bar-builder':
                      ctbc.BuilderSpec.create(),
                  'bar-tests':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='bar-builder',
                      ),
              },
              'migration.excluded': {
                  'excluded-builder':
                      ctbc.BuilderSpec.create(),
                  'excluded-tests':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='excluded-builder',
                      ),
              },
              'other': {
                  'other-builder': ctbc.BuilderSpec.create(),
              }
          }),
          ctbc.TryDatabase.create({
              'tryserver.migration.foo': {
                  'foo-try-builder':
                      ctbc.TrySpec.create([
                          ctbc.TryMirror.create(
                              builder_group='migration.foo',
                              buildername='foo-builder',
                              tester='foo-x-tests',
                          ),
                      ]),
              },
              'tryserver.migration.bar': {
                  'bar-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='migration.bar',
                          buildername='bar-builder',
                      ),
              },
          }),
      ),
      api.post_check(post_process.StatusSuccess),
  )

  yield api.test(
      'invalid-children',
      api.properties(
          groupings_operation={
              'output_path':
                  '/fake/output/path',
              'builder_group_filters': [
                  {
                      'builder_group_regex': r'(tryserver\.)?migration(\..+)?',
                  },
                  {
                      'builder_group_regex': r'migration\.excluded',
                      'exclude': True,
                  },
              ],
          }),
      api.chromium_tests_builder_config.databases(
          ctbc.BuilderDatabase.create({
              'migration': {
                  'foo-builder': ctbc.BuilderSpec.create(),
              },
              'migration.excluded': {
                  'foo-tests':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_builder_group='migration',
                          parent_buildername='foo-builder',
                      ),
              },
          }),
          ctbc.TryDatabase.create({}),
      ),
      api.post_check(post_process.MustRun,
                     'invalid children for migration:foo-builder'),
      api.post_check(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'invalid-mirrors',
      api.properties(
          groupings_operation={
              'output_path':
                  '/fake/output/path',
              'builder_group_filters': [
                  {
                      'builder_group_regex': r'(tryserver\.)?migration(\..+)?',
                  },
                  {
                      'builder_group_regex': r'migration\.excluded',
                      'exclude': True,
                  },
              ],
          }),
      api.chromium_tests_builder_config.databases(
          ctbc.BuilderDatabase.create({
              'migration': {
                  'foo-builder': ctbc.BuilderSpec.create(),
              },
              'migration.excluded': {
                  'bar-builder': ctbc.BuilderSpec.create(),
              },
          }),
          ctbc.TryDatabase.create({
              'tryserver.migration': {
                  'try-builder':
                      ctbc.TrySpec.create([
                          BuilderId.create_for_group('migration',
                                                     'foo-builder'),
                          BuilderId.create_for_group('migration.excluded',
                                                     'bar-builder'),
                      ]),
              },
          })),
      api.post_check(
          post_process.MustRun,
          'invalid mirroring configuration for tryserver.migration:try-builder'
      ),
      api.post_check(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  expected_contents = textwrap.dedent("""\
      bar-group:bar-builder
          builder_spec = builder_config.builder_spec(
              gclient_config = builder_config.gclient_config(
                  config = "chromium",
              ),
              chromium_config = builder_config.chromium_config(
                  config = "chromium",
              ),
          ),

      bar-group:bar-tester
          builder_spec = builder_config.builder_spec(
              execution_mode = builder_config.execution_mode.TEST,
              gclient_config = builder_config.gclient_config(
                  config = "chromium",
              ),
              chromium_config = builder_config.chromium_config(
                  config = "chromium",
              ),
          ),

      foo-group:foo-builder
          builder_spec = builder_config.builder_spec(
              gclient_config = builder_config.gclient_config(
                  config = "gclient-config1",
                  apply_configs = [
                      "gclient-config2",
                      "gclient-config3",
                  ],
              ),
              chromium_config = builder_config.chromium_config(
                  config = "chromium-config1",
                  apply_configs = [
                      "chromium-config2",
                      "chromium-config3",
                  ],
                  build_config = builder_config.build_config.RELEASE,
                  target_arch = builder_config.target_arch.ARM,
                  target_bits = 64,
                  target_platform = builder_config.target_platform.CHROMEOS,
                  target_cros_boards = [,
                      "fake-board1",
                      "fake-board2",
                  ],
                  cros_boards_with_qemu_images = [,
                      "fake-board1",
                      "fake-board2",
                  ],
              ),
              android_config = builder_config.android_config(
                  config = "android-config1",
                  apply_configs = [
                      "android-config2",
                      "android-config3",
                  ],
              ),
              test_results_config = builder_config.test_results_config(
                  config = "test-results-config",
              ),
              android_version_file = "//android/version/file",
              clobber = True,
              build_gs_bucket = "build-gs-bucket",
              run_tests_serially = True,
              perf_isolate_upload = True,
              expose_trigger_properties = True,
              skylab_upload_location = builder_config.skylab_upload_location(
                  gs_bucket = "skylab-gs-bucket"
                  gs_extra = "skylab-gs-extra"
              ),
          ),

      foo-group:foo-tester
          builder_spec = builder_config.builder_spec(
              execution_mode = builder_config.execution_mode.TEST,
              gclient_config = builder_config.gclient_config(
                  config = "chromium",
              ),
              chromium_config = builder_config.chromium_config(
                  config = "chromium",
              ),
          ),

      try-group:try-builder
          mirrors = [
              "ci/foo-builder",
              "ci/foo-tester",
              "ci/bar-builder",
          ],
          try_settings = builder_config.try_settings(
              include_all_triggered_testers = True,
              is_compile_only = True,
              analyze_names = [
                  "analyze-name1",
                  "analyze-name2",
              ],
              retry_failed_shards = False,
              retry_without_patch = False,
              rts_config = builder_config.rts_config(
                  condition = builder_config.rts_condition.QUICK_RUN_ONLY,
                  recall = 0.5,
              ),
          ),
      """)

  yield api.test(
      'migration',
      api.properties(
          migration_operation={
              'builders_to_migrate': [{
                  'builder_group': 'foo-group',
                  'builder': 'foo-builder',
              }],
              'output_path': '/fake/output/path',
          }),
      api.chromium_tests_builder_config.databases(
          ctbc.BuilderDatabase.create({
              'foo-group': {
                  # This spec has nonsensical combinations, it provides coverage
                  # of the handling for different fields
                  'foo-builder':
                      ctbc.BuilderSpec.create(
                          gclient_config='gclient-config1',
                          gclient_apply_config=[
                              'gclient-config2',
                              'gclient-config3',
                          ],
                          chromium_config='chromium-config1',
                          chromium_apply_config=[
                              'chromium-config2',
                              'chromium-config3',
                          ],
                          chromium_config_kwargs={
                              'BUILD_CONFIG':
                                  'Release',
                              'TARGET_ARCH':
                                  'arm',
                              'TARGET_BITS':
                                  64,
                              'TARGET_PLATFORM':
                                  'chromeos',
                              'TARGET_CROS_BOARDS':
                                  'fake-board1:fake-board2',
                              'CROS_BOARDS_WITH_QEMU_IMAGES':
                                  'fake-board1:fake-board2',
                          },
                          android_config='android-config1',
                          android_apply_config=[
                              'android-config2',
                              'android-config3',
                          ],
                          test_results_config='test-results-config',
                          android_version='//android/version/file',
                          clobber=True,
                          build_gs_bucket='build-gs-bucket',
                          serialize_tests=True,
                          perf_isolate_upload=True,
                          expose_trigger_properties=True,
                          skylab_gs_bucket='skylab-gs-bucket',
                          skylab_gs_extra='skylab-gs-extra',
                      ),
                  'foo-tester':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='foo-builder',
                          gclient_config='chromium',
                          chromium_config='chromium',
                      ),
              },
              'bar-group': {
                  'bar-builder':
                      ctbc.BuilderSpec.create(
                          gclient_config='chromium',
                          chromium_config='chromium',
                      ),
                  'bar-tester':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='bar-builder',
                          gclient_config='chromium',
                          chromium_config='chromium',
                      ),
              }
          }),
          ctbc.TryDatabase.create({
              'try-group': {
                  'try-builder':
                      ctbc.TrySpec.create(
                          mirrors=[
                              ctbc.TryMirror.create(
                                  builder_group='foo-group',
                                  buildername='foo-builder',
                                  tester='foo-tester',
                              ),
                              ctbc.TryMirror.create(
                                  builder_group='bar-group',
                                  buildername='bar-builder',
                              ),
                          ],
                          include_all_triggered_testers=True,
                          is_compile_only=True,
                          analyze_names=[
                              'analyze-name1',
                              'analyze-name2',
                          ],
                          retry_failed_shards=False,
                          retry_without_patch=False,
                          regression_test_selection=ctbc.QUICK_RUN_ONLY,
                          regression_test_selection_recall=0.5,
                      ),
              },
          }),
      ),
      api.post_check(post_process.StatusSuccess),
      api.post_check(lambda check, steps: \
          check(expected_contents in steps['src-side snippets'].cmd)),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'migration-unknown-builder',
      api.properties(
          migration_operation={
              'builders_to_migrate': [{
                  'builder_group': 'foo-group',
                  'builder': 'foo-builder',
              }],
              'output_path': '/fake/output/path',
          }),
      api.chromium_tests_builder_config.databases(
          ctbc.BuilderDatabase.create({
              'bar-group': {
                  'bar-builder': ctbc.BuilderSpec.create(),
              },
          }),
          ctbc.TryDatabase.create({}),
      ),
      api.post_check(post_process.StatusException),
      api.post_check(post_process.ResultReason,
                     "unknown builder 'foo-group:foo-builder'"),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'migration-provide-test-spec',
      api.properties(
          migration_operation={
              'builders_to_migrate': [{
                  'builder_group': 'foo-group',
                  'builder': 'foo-builder',
              }],
              'output_path': '/fake/output/path',
          }),
      api.chromium_tests_builder_config.databases(
          ctbc.BuilderDatabase.create({
              'foo-group': {
                  'foo-builder':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.PROVIDE_TEST_SPEC),
              }
          }),
          ctbc.TryDatabase.create({}),
      ),
      api.post_check(post_process.StatusException),
      api.post_check(
          post_process.ResultReason,
          ("cannot migrate builder 'foo-group:foo-builder' "
           "with provide-test-spec execution_mode"),
      ),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'migration-unsupported-attrs',
      api.properties(
          migration_operation={
              'builders_to_migrate': [{
                  'builder_group': 'foo-group',
                  'builder': 'foo-builder',
              }],
              'output_path': '/fake/output/path',
          }),
      api.chromium_tests_builder_config.databases(
          ctbc.BuilderDatabase.create({
              'foo-group': {
                  'foo-builder':
                      ctbc.BuilderSpec.create(
                          set_output_commit=False,
                          archive_build=True,
                          gs_bucket='fake-gs-bucket',
                          gs_build_name='fake-gs-build-name',
                          cf_archive_build=True,
                          cf_gs_bucket='fake-cf-gs-bucket',
                          cf_gs_acl='fake-cf-gs-acl',
                          cf_archive_name='fake-cf-archive-name',
                          cf_archive_subdir_suffix='fake-cf-archive-suffix',
                          bisect_archive_build=True,
                          bisect_gs_bucket='fake-bisect-gs-bucket',
                          bisect_gs_extra='fake-bisect-gs-extra',
                      ),
              }
          }),
          ctbc.TryDatabase.create({}),
      ),
      api.post_check(post_process.StatusException),
      api.post_check(
          post_process.ResultReason,
          textwrap.dedent("""\
              cannot migrate builder 'foo-group:foo-builder' with the \
following unsupported attrs:
              * set_output_commit
              * archive_build
              * gs_bucket
              * gs_build_name
              * cf_archive_build
              * cf_gs_bucket
              * cf_gs_acl
              * cf_archive_name
              * cf_archive_subdir_suffix
              * bisect_archive_build
              * bisect_gs_bucket
              * bisect_gs_extra""")),
      api.post_process(post_process.DropExpectation),
  )

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
      'no-operation',
      invalid_properties('no operation is set'),
  )

  yield api.test(
      'bad-groupings-operation',
      api.properties(groupings_operation={}),
      invalid_properties(
          r'groupings_operation\.output_path is not set',
          r'groupings_operation\.builder_group_filters is empty'),
  )

  yield api.test(
      'bad-builder-group-filter',
      api.properties(groupings_operation={
          'builder_group_filters': [{}],
      }),
      invalid_properties((r'groupings_operation\.builder_group_filters\[0\]'
                          r'\.builder_group_regex is not set')),
  )

  yield api.test(
      'bad-migration-operation',
      api.properties(migration_operation={}),
      invalid_properties(r'migration_operation\.builders_to_migrate is empty',
                         r'migration_operation\.output_path is not set'),
  )

  yield api.test(
      'bad-builder-to-migrate',
      api.properties(migration_operation={
          'builders_to_migrate': [{}],
      }),
      invalid_properties(
          (r'migration_operation\.builders_to_migrate\[0\]'
           r'\.builder_group is not set'),
          r'migration_operation\.builders_to_migrate\[0\]\.builder is not set'),
  )
