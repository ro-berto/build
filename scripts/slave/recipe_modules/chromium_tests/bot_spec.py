# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr
from attr import converters, validators
import collections
import itertools

from recipe_engine.types import FrozenDict, freeze

from . import steps

from RECIPE_MODULES.build.attr_utils import (attrib, attrs, cached_property,
                                             enum_attrib, mapping_attrib,
                                             sequence_attrib)
from RECIPE_MODULES.build import chromium

COMPILE_AND_TEST = 'compile/test'
TEST = 'test'
# The type of a bot that is never actually executed, it is only used as the
# tester in a trybot-mirror configuration so that src-side information can be
# specified providing different test configurations
PROVIDE_TEST_SPEC = 'provide-test-spec'


@attrs()
class TestSpec(object):

  test_type = attrib(type)
  args = sequence_attrib(default=())
  kwargs = mapping_attrib(default={})

  @classmethod
  def create(cls, test_type, *args, **kwargs):
    return cls(test_type, args=args, kwargs=kwargs)

  def get_test(self):
    return self.test_type(*self.args, **self.kwargs)


@attrs()
class BotSpec(object):
  """An immutable specification for a bot.

  This type provides a means of specifying all of the input values for
  the bot with the following benefits:
    * All available fields and their default values are declared and
      documented in one place
    * Typos are caught at the time a spec is instantiated
    * Validation is performed to ensure that values are of approriate
      type and that combinations make sense

  If another recipe/recipe module needs to add its own information, it
  should define a subclass of this type and declare fields for its
  additional information.
  """

  @classmethod
  def normalize(cls, spec):
    if isinstance(spec, cls):
      return spec
    return cls.create(**spec)

  @classmethod
  def create(cls, **kwargs):
    """Create a BotSpec.

    Arguments:
      kwargs - Values to initialize the BotSpec.

    Returns:
      A new BotSpec instance with fields set to the values passed in kwargs and
      all other fields set to their defaults.
    """
    def get_filtered_attrs(*attributes):
      return [a for a in attributes if a in kwargs]

    execution_mode = kwargs.get('execution_mode', COMPILE_AND_TEST)

    if execution_mode == PROVIDE_TEST_SPEC:
      # Builders with execution mode PROVIDE_TEST_SPEC should never be executed,
      # so most fields are invalid
      # The source_side_spec_file field overrides the location of the src-side
      # spec, which is the point of PROVIDE_TEST_SPEC, so it is valid to set
      invalid_attrs = get_filtered_attrs(*[
          a for a in attr.fields_dict(cls)
          if a not in ('execution_mode', 'source_side_spec_file')
      ])
      assert not invalid_attrs, (
          "The following fields are ignored when 'execution_mode' is {!r}: {}"
          .format(PROVIDE_TEST_SPEC, invalid_attrs))

    elif execution_mode != COMPILE_AND_TEST:
      invalid_attrs = get_filtered_attrs('compile_targets')
      assert not invalid_attrs, (
          "The following fields are ignored unless 'execution_mode' is {!r}: {}"
          .format(COMPILE_AND_TEST, invalid_attrs))

    if not kwargs.get('archive_build'):
      invalid_attrs = get_filtered_attrs('gs_bucket', 'gs_acl', 'gs_build_name')
      assert not invalid_attrs, (
          'The following fields are ignored unless '
          "'archive_build' is set to True: {}".format(invalid_attrs))

    if not kwargs.get('cf_archive_build'):
      invalid_attrs = get_filtered_attrs('cf_gs_bucket', 'cf_archive_name',
                                         'cf_gs_acl',
                                         'cf_archive_subdir_suffix')
      assert not invalid_attrs, (
          'The following fields are ignored unless '
          "'cf_archive_build' is set to True: {}".format(invalid_attrs))

    if not kwargs.get('bisect_archive_build'):
      invalid_attrs = get_filtered_attrs('bisect_gs_bucket', 'bisect_gs_extra')
      assert not invalid_attrs, (
          'The following fields are ignored unless '
          "'bisect_archive_build' is set to True: {}".format(invalid_attrs))

    return cls(**kwargs)

  def __attrs_post_init__(self):
    if self.execution_mode == TEST:
      assert self.parent_buildername is not None, (
          'Test-only builder must specify a parent builder')
    elif self.execution_mode == COMPILE_AND_TEST:
      assert self.parent_buildername is None, (
          'Non-test-only builder must not specify a parent builder')
      assert self.parent_mastername is None, (
          'Non-test-only builder must not specify parent master name')

    if self.archive_build:
      assert self.gs_bucket, (
          "'gs_bucket' must be provided when 'archive_build' is True")

    if self.cf_archive_build:
      assert self.cf_gs_bucket, (
          "'cf_gs_bucket' must be provided when 'cf_archive_build' is True")

    if self.bisect_archive_build:
      assert self.bisect_gs_bucket, ("'bisect_gs_bucket' must be provided when "
                                     "'bisect_archive_build' is True")

  # The LUCI project that the builder belongs to
  luci_project = attrib(str, default='chromium')

  # The execution mode of the builder
  # COMPILE_AND_TEST - Compile targets and optionally run tests and/or trigger
  #     a tester
  # TEST - Run tests, requires a parent builder, some ancestor must have
  #     COMPILE_AND_TEST execution mode
  # PROVIDE_TEST_SPEC - Cannot actually be executed, can only be specified as a
  #     tester in a trybot's mirror in order to provide an additional test spec
  #     to read
  execution_mode = enum_attrib([COMPILE_AND_TEST, TEST, PROVIDE_TEST_SPEC],
                               default=COMPILE_AND_TEST)

  # An optional mastername of the bot's parent builder - if parent_buildername
  # is provided and parent_mastername is not, the parent's mastername is the
  # same as the bot associated with this spec
  parent_mastername = attrib(str, default=None)
  # An optional buildername of the bot's parent builder
  parent_buildername = attrib(str, default=None)

  # The name of the config to use for the chromium recipe module
  chromium_config = attrib(str, default=None)
  # The names of additional configs to apply for the chromium recipe module
  chromium_apply_config = sequence_attrib(str, default=())
  # The keyword arguments used when setting the config for the chromium recipe
  # module
  chromium_config_kwargs = mapping_attrib(str, default={})
  # The name of the config to use for the chromium_tests recipe module
  chromium_tests_config = attrib(str, default='chromium')
  # The name of additional configs to apply for the chromium_tests recipe module
  chromium_tests_apply_config = sequence_attrib(str, default=())
  # The name of the config to use for the gclient recipe module
  gclient_config = attrib(str, default=None)
  # The names of additional configs to apply for the gclient recipe module
  gclient_apply_config = sequence_attrib(str, default=())
  # The name of the config to use for the android recipe module
  android_config = attrib(str, default=None)
  # The names of additional configs to apply for the android recipe module
  android_apply_config = sequence_attrib(str, default=())
  # The name of the config to use for the test_results recipe module
  test_results_config = attrib(str, default=None)

  # URL to override the isolate server to use
  isolate_server = attrib(str, default=None)
  # Override for the default priority used when creating swarming tasks
  swarming_default_priority = attrib(int, default=None)
  # Dimensions to apply to all created swarming tasks
  swarming_dimensions = mapping_attrib(str, default={})
  # URL to override the swarming server to use
  swarming_server = attrib(str, default=None)

  # A path relative to the checkout to a file containing the Chrome version
  # information for Android
  android_version = attrib(str, default=None)

  # A bool controlling whether have bot_update perform a clobber of any
  # pre-existing build outputs
  clobber = attrib(bool, default=False)

  # The names of targets to compile
  compile_targets = sequence_attrib(str, default=())

  # Name of a Google Storage bucket to use when using the legacy package
  # transfer where build outputs are uploaded to Google Storage and then
  # downloaded by the tester
  # This must be set for builders with the BUILDER bot type that trigger testers
  # that will run non-isolated tests
  build_gs_bucket = attrib(str, default=None)
  # A bool controlling whether the legacy package transfer mechanism should be
  # used for all tests, even those that are isolated
  # Don't use this unless you know what you're doing, there's little reason to
  # use this for new builders
  enable_package_transfer = attrib(bool, default=False)

  # Specs for tests to be run for this builder
  test_specs = sequence_attrib(TestSpec, default=())
  # A bool controlling whether swarming tests should be run serially
  # If not True, requests for test tasks are issued to swarming in parallel
  # Running tests in serial can be useful if you have limited hardware capacity
  serialize_tests = attrib(bool, default=False)

  # A path relative to chromium.c.source_side_spec_dir containing the
  # information describing the tests to be run for this builder
  source_side_spec_file = attrib(str, default=None)

  # A bool controlling whether an isolate is uploaded to the perf dashboard
  perf_isolate_upload = attrib(bool, default=False)

  # A bool controlling whether to archive the build outputs
  archive_build = attrib(bool, default=None)
  # The bucket to archive the build to
  # Must be provided when archive_build is True
  # Cannot be provided when archive_build is not True
  gs_bucket = attrib(str, default=None)
  # The ACL to apply to the archived build
  # Cannot be provided when archive_build is not True
  gs_acl = attrib(str, default=None)
  # The build name to apply to the archived build
  # cannot be provided when archive_build is not True
  gs_build_name = attrib(str, default=None)

  # A bool controlling whether to archive the build outputs for Clusterfuzz
  cf_archive_build = attrib(bool, default=False)
  # The bucket to archive the build to
  # Must be provided when cf_archive_build is True
  # Cannot be provided when cf_archive_build is not True
  cf_gs_bucket = attrib(str, default=None)
  # The ACL to apply to the archived build
  # Cannot be provided when cf_archive_build is not True
  cf_gs_acl = attrib(str, default=None)
  # The prefix to apply to the archived build
  # Cannot be provided when cf_archive_build is not True
  # TODO(gbeaty) Rename this to cf_archive_prefix
  cf_archive_name = attrib(str, default=None)
  # Suffix to apply to the subdirectory within the bucket the archived is
  # uploaded to
  # Cannot be provided when cf_archive_build is not True
  cf_archive_subdir_suffix = attrib(str, default='')

  # A bool indicating whether the build should be archived for bisection
  bisect_archive_build = attrib(bool, default=False)
  # The bucket to archive the build to
  # Must be provided when bisect_archive_build is True
  # Cannot be provided when bisect_archive_build is not True
  bisect_gs_bucket = attrib(str, default=None)
  # Additional URL components to add to the Google Storage URL for bisection
  # archiving
  # Cannot be provided when bisect_archive_build is not True
  bisect_gs_extra = attrib(str, default=None)

  # The platform of the builder (e.g. 'linux'), used when running simulation
  # tests
  # Normally the platform is provided by the platform recipe module, but during
  # simulation tests we need to tell the platform recipe module what platform
  # the builder would be run on
  # For acceptable values, see
  # https://source.chromium.org/chromium/infra/infra/+/master:recipes-py/recipe_modules/platform/test_api.py?q=symbol:name
  simulation_platform = attrib(str, default=None)

  def evolve(self, **kwargs):
    """Create a new BotSpec with updated values.

    Arguments:
      kwargs - Updated values for fields.

    Returns:
      A new BotSpec where the fields specified in kwargs have been overridden
      and all other fields are kept the same.
    """
    return attr.evolve(self, **kwargs)

  def extend(self, **kwargs):
    """Create a new BotSpec extending the values of sequence fields.

    Arguments:
      kwargs - Additional values for fields. The value of each keyword must be
        an iterable object.

    Returns:
      A new BotSpec where the fields specified in kwargs have been updated with
      the concatenation of the existing value for the field (or an empty
      iterable if the existing value is None) with the value provided in kwargs.
    """
    for k, v in kwargs.iteritems():
      current = getattr(self, k)
      kwargs[k] = itertools.chain(current, v)
    return self.evolve(**kwargs)
