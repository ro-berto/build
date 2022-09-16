# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import contextlib
import re

import attr

from recipe_engine import recipe_api

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from RECIPE_MODULES.build import proto_validation
from RECIPE_MODULES.build import chromium

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from PB.recipe_engine import result as result_pb

from PB.recipe_modules.build.chromium_tests_builder_config_migration import (
    properties as properties_pb)

_VALIDATORS = proto_validation.Registry()


@_VALIDATORS.register(properties_pb.InputProperties)
def _validate_properties(message, ctx):
  operation = message.WhichOneof('operation')
  if operation:
    ctx.validate_field(message, operation)
  else:
    ctx.error('no operation is set')


@_VALIDATORS.register(properties_pb.GroupingsOperation)
def _validate_groupings_operation(message, ctx):
  ctx.validate_field(message, 'output_path')
  ctx.validate_repeated_field(message, 'builder_group_filters')


@_VALIDATORS.register(properties_pb.GroupingsOperation.BuilderGroupFilter)
def _validate_builder_group_filter(message, ctx):
  ctx.validate_field(message, 'builder_group_regex')


@_VALIDATORS.register(properties_pb.MigrationOperation)
def _validate_migration_operation(message, ctx):
  ctx.validate_repeated_field(message, 'builders_to_migrate')
  ctx.validate_field(message, 'output_path')


@_VALIDATORS.register(properties_pb.MigrationOperation.BuilderGroupAndName)
def _validate_builder_group_and_name(message, ctx):
  ctx.validate_field(message, 'builder_group')
  ctx.validate_field(message, 'builder')


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


class _Grouping(object):

  def __init__(self):
    self.builder_ids = set()
    self.blockers = set()

  def merge(self, other):
    self.builder_ids.update(other.builder_ids)
    self.blockers.update(other.blockers)


def _failure(summary):
  return result_pb.RawResult(
      status=common_pb.INFRA_FAILURE, summary_markdown=summary)


_NON_EXISTENT_BUILDERS = tuple(
    chromium.BuilderId.create_for_group(group, builder)
    for (group, builder) in (
        # Test value
        ('non.existent', 'non-existent-builder'),))

_DEFAULT_BUILDER_SPEC = ctbc.BuilderSpec.create()
_UNSUPPORTED_ATTRS = (
    # The use of all of these fields should be replaced with the use of
    # the archive module
    'bisect_archive_build',
    'bisect_gs_bucket',
    'bisect_gs_extra',
)


def _builder_spec_migration_blocker(builder_id, builder_spec):
  if builder_id in _NON_EXISTENT_BUILDERS:
    return "builder '{}' does not exist".format(builder_id)

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
    return '\n'.join(message)

  return None


def _migrate_builder_spec(builder_spec):
  output = _OutputCollector()

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
          output.add_line('{} = ['.format(k.lower()))
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

    if builder_spec.cf_archive_build:
      output.add_line('clusterfuzz_archive = '
                      'builder_config.clusterfuzz_archive(')
      with output.increase_indent('),'):
        output.add_line('gs_bucket = "{}",'.format(builder_spec.cf_gs_bucket))
        if builder_spec.cf_gs_acl:
          output.add_line('gs_acl = "{}",'.format(builder_spec.cf_gs_acl))
        output.add_line('archive_name_prefix = "{}",'.format(
            builder_spec.cf_archive_name))
        if builder_spec.cf_archive_subdir_suffix:
          output.add_line('archive_subdir = "{}",'.format(
              builder_spec.cf_archive_subdir_suffix))

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


def _migrate_try_spec(builder_id, try_spec):
  output = _OutputCollector()

  mirrors = []
  for m in try_spec.mirrors:
    if m.builder_id != builder_id and m.builder_id not in mirrors:
      mirrors.append(m.builder_id)
    if m.tester_id and m.tester_id != builder_id and m.tester_id not in mirrors:
      mirrors.append(m.tester_id)

  if mirrors:
    output.add_line('mirrors = [')
    with output.increase_indent('],'):
      for m in mirrors:
        output.add_line('"ci/{}",'.format(m.builder))

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


class ChromiumTestsBuilderConfigMigrationApi(recipe_api.RecipeApi):

  def __call__(self, properties, builder_db, try_db):
    errors = _VALIDATORS.validate(properties)
    if errors:
      summary = [
          'The following errors were found with the input properties:',
          '',
      ]
      summary.extend(errors)
      return result_pb.RawResult(
          status=common_pb.INFRA_FAILURE, summary_markdown='\n'.join(summary))

    handlers_by_operation = {
        'groupings_operation': self._groupings_operation,
        'migration_operation': self._migration_operation,
    }
    operation = properties.WhichOneof('operation')
    handler = handlers_by_operation[operation]
    return handler(getattr(properties, operation), builder_db, try_db)

  def _groupings_operation(self, groupings_operation, builder_db, try_db):
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

    groupings_by_builder_id = self._compute_groupings(builder_db, try_db,
                                                      builder_filter)

    output_path = self.m.path.abspath(groupings_operation.output_path)

    json = {}
    for b, grouping in groupings_by_builder_id.items():
      grouping_json = {
          'builders': [str(b2) for b2 in sorted(grouping.builder_ids)],
      }
      if grouping.blockers:
        grouping_json['blockers'] = sorted(grouping.blockers)
      json[str(b)] = grouping_json
    output = self.m.json.dumps(json, indent=2, separators=(',', ': '))

    # Include log during the tests so that the expectation file is easier to
    # review
    self.m.file.write_text(
        'groupings', output_path, output, include_log=self._test_data.enabled)

  def _migration_operation(self, migration_operation, builder_db, try_db):
    groupings_by_builder_id = self._compute_groupings(builder_db, try_db)

    to_migrate = set()
    for b in migration_operation.builders_to_migrate:
      builder_id = chromium.BuilderId.create_for_group(b.builder_group,
                                                       b.builder)
      grouping = groupings_by_builder_id.get(builder_id)
      if grouping is None:
        return _failure("unknown builder '{}'".format(builder_id))
      if grouping.blockers:
        return _failure(
            "The grouping for '{}'"
            " cannot be migrated for the following reasons:{}".format(
                builder_id,
                "".join("\n  {}".format(b) for b in sorted(grouping.blockers))))
      to_migrate.update(grouping.builder_ids)

    output = _OutputCollector()

    for builder_id in sorted(to_migrate):
      output.add_line(str(builder_id))
      with output.increase_indent(''):
        builder_spec = builder_db.get(builder_id)
        if builder_spec is not None:
          output.add_lines(_migrate_builder_spec(builder_spec))

        try_spec = try_db.get(builder_id)
        if try_spec is not None:
          output.add_lines(_migrate_try_spec(builder_id, try_spec))

    output_path = self.m.path.abspath(migration_operation.output_path)
    self.m.file.write_text('src-side snippets', output_path,
                           '\n'.join(output.lines))

  def _compute_groupings(self, builder_db, try_db, builder_filter=None):
    builder_filter = builder_filter or (lambda _: True)

    groupings_by_builder_id = collections.defaultdict(_Grouping)

    def check_included(related_ids, step_name):
      included_by_builder_id = {}
      for related_id in related_ids:
        included_by_builder_id[related_id] = builder_filter(related_id)

      included = set(included_by_builder_id.values())
      if len(included) == 1:
        return next(iter(included))

      self.m.step.empty(
          step_name,
          status=self.m.step.INFRA_FAILURE,
          log_name='mismatched_inclusion',
          log_text=[
              '{} ignored: {}'.format(builder_id, included)
              for builder_id, included in included_by_builder_id.items()
          ])

    def update_groupings(builder_id, related_ids, blocker=None):
      grouping = groupings_by_builder_id[builder_id]
      grouping.builder_ids.add(builder_id)
      if blocker is not None:
        grouping.blockers.add(blocker)
      for related_id in related_ids:
        related_grouping = groupings_by_builder_id[related_id]
        related_grouping.builder_ids.add(related_id)
        grouping.merge(related_grouping)
        for connected_id in related_grouping.builder_ids:
          groupings_by_builder_id[connected_id] = grouping

    for builder_id, child_ids in builder_db.builder_graph.items():
      included = check_included([builder_id] + sorted(child_ids),
                                'invalid children for {}'.format(builder_id))
      builder_spec = builder_db[builder_id]
      blocker = _builder_spec_migration_blocker(builder_id, builder_spec)
      if included:
        update_groupings(builder_id, child_ids, blocker)

    for try_id, try_spec in try_db.items():
      mirrored_ids = []
      for mirror in try_spec.mirrors:
        mirrored_ids.append(mirror.builder_id)
        if mirror.tester_id:
          mirrored_ids.append(mirror.tester_id)
      included = check_included(
          [try_id] + mirrored_ids,
          'invalid mirroring configuration for {}'.format(try_id))
      if included:
        update_groupings(try_id, mirrored_ids)

    return groupings_by_builder_id
