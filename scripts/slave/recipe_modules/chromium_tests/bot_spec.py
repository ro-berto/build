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

BUILDER = 'builder'
TESTER = 'tester'
BUILDER_TESTER = 'builder_tester'
# The type of a bot that is never actually executed, it is only used as the
# tester in a trybot-mirror configuration so that src-side information can be
# specified providing different test configurations
DUMMY_TESTER = 'dummy_tester'

BUILDER_TYPES = (BUILDER, BUILDER_TESTER)
TESTER_TYPES = (TESTER, BUILDER_TESTER)


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

    bot_type = kwargs.get('bot_type', BUILDER_TESTER)
    if bot_type == DUMMY_TESTER:
      # DUMMY_TESTER bots should never be executed, so most fields are invalid
      # The testing field is a dict; one of the keys overrides the location of
      # the src-side spec, which is the point of DUMMY_TESTER bots, so it is
      # valid to set
      invalid_attrs = get_filtered_attrs(*[
          a for a in attr.fields_dict(cls) if a not in ('bot_type', 'testing')
      ])
      assert not invalid_attrs, (
          "The following fields are ignored when 'bot_type' is {!r}: {}".format(
              DUMMY_TESTER, invalid_attrs))

    elif bot_type not in BUILDER_TYPES:
      invalid_attrs = get_filtered_attrs('compile_targets')
      assert not invalid_attrs, (
          "The following fields are ignored unless 'bot_type' is one of {}: {}"
          .format(BUILDER_TYPES, invalid_attrs))

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
    if self.bot_type == TESTER:
      assert self.parent_buildername is not None, (
          'Tester-only bot must specify a parent builder')

    if self.parent_mastername:
      assert self.parent_buildername, ("'parent_buildername' must be provided "
                                       "when 'parent_mastername' is set")

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

  # The type of the bot
  bot_type = enum_attrib([BUILDER, TESTER, BUILDER_TESTER, DUMMY_TESTER],
                         default=BUILDER_TESTER)

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
  # The keyword arguments used when setting the config for the gclient recipe
  # module
  gclient_config_kwargs = mapping_attrib(str, default={})
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
  # A dictionary used for component builds: builds where Chromium should should
  # be built and tested with a patch for one of Chromium's dependency projects
  # e.g. v8
  # The dictionary should contain 2 keys:
  #  name - The name of the dependency in the gclient solution that the patch
  #    should be applied to
  #  rev_str - A %-format string that the component revision will be applied to
  #    compute the revision
  set_component_rev = mapping_attrib(str, str, default={})

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

  # A bool controlling whether tests should be disabled
  disable_tests = attrib(bool, default=False)
  # Specs for tests to be run for this builder
  test_specs = sequence_attrib(TestSpec, default=())
  # A bool controlling whether swarming tests should be run serially
  # If not True, requests for test tasks are issued to swarming in parallel
  # Running tests in serial can be useful if you have limited hardware capacity
  serialize_tests = attrib(bool, default=False)

  # A path relative to chromium.c.source_side_spec_dir containing the
  # information describing the tests to be run for this builder
  source_side_spec_file = attrib(str, default=None)
  # A dictionary describing the tests to be run for this builder - has the same
  # format as the value of a single builder's entry in one of the *.json files
  # under //testing/buildbot of chromium/src
  source_side_spec = mapping_attrib(str, default=None)
  # A dictionary describing the tests to be run for this builder's master - has
  # the same format as one of the *.json files under //testing/buildbot of
  # chromium/src
  downstream_spec = mapping_attrib(str, default=None)

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
