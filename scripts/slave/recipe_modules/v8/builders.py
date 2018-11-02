# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Contains the bulk of the V8 builder configurations so they can be reused
# from multiple recipes.


from collections import defaultdict

from recipe_engine.types import freeze
# pylint: disable=relative-import
from testing import V8Variant


class TestStepConfig(object):
  """Per-step test configuration."""
  def __init__(self, name, shards=1, suffix='', test_args=None, variants=None,
               swarming_dimensions=None, swarming_task_attrs=None):
    """Init per-step test configuration.

    Args:
      name: Test name used for keying testing.TEST_CONFIGS.
      shards: Number of swarming shards, default 1.
      suffix: Optional suffix for test name in UI.
      test_args: Optional list of extra args to the test driver.
      variants: Optional V8Variant object defining the testing variants to use.
      swarming_dimensions: Dict with extra swarming dimensions.
      swarming_task_attrs: Dict with extra swarming task attributes.
    """
    self.name = name
    self.shards = shards
    self._suffix = suffix
    self.test_args = test_args or []
    self.variants = variants
    self.swarming_dimensions = swarming_dimensions or {}
    self.swarming_task_attrs = swarming_task_attrs or {}
    if not suffix and variants:
      # Disambiguate step names if a particular variant is specified and no
      # default suffix is provided.
      self._suffix = str(variants)

  def __str__(self):
    return '%s(%d) %s' % (self.name, self.shards, self.variants)

  @property
  def step_name_suffix(self):
    return ' - %s' % self._suffix if self._suffix else ''

  def pack(self):
    """Returns a serializable version of this object.

    This method is the counterpart to the method below.
    """
    return [
      self.name,
      self.shards,
      self.variants.pack() if self.variants else None,
      self._suffix,
      self.test_args,
      self.swarming_dimensions,
      self.swarming_task_attrs,
    ]

  @staticmethod
  def unpack(packed, swarming_dimensions=None, swarming_task_attrs=None):
    """Constructs a test-step config from a serialized version of this class.

    This method is the counterpart to the method ablve.

    Args:
      packed: An object to unpack as returned by pack() above.
      swarming_dimensions: Default swarming dimensions, flattened into every
          test config. Per-test dimensions will override these defaults.
      swarming_task_attrs: Default swarming attributes, flattened into every
          test config. Per-test attributes will override these defaults.
    """
    return TestStepConfig(
        name=packed[0],
        shards=packed[1],
        variants=V8Variant.unpack(packed[2]) if packed[2] else None,
        suffix=packed[3],
        test_args=packed[4],
        swarming_dimensions=dict((swarming_dimensions or {}), **packed[5]),
        swarming_task_attrs=dict((swarming_task_attrs or {}), **packed[6]),
    )

  @staticmethod
  def from_python_literal(spec):
    """Constructs a test-step config from the V8-side pyl test spec."""
    variant = spec.get('variant')
    return TestStepConfig(
        name=spec['name'],
        swarming_dimensions=spec.get('swarming_dimensions'),
        swarming_task_attrs=spec.get('swarming_task_attrs'),
        shards=spec.get('shards', 1),
        suffix=spec.get('suffix', ''),
        test_args=spec.get('test_args'),
        variants=V8Variant(variant) if variant else None,
    )


class TestSpec(object):
  """Represents a V8-side test specification with extra tests to run on a
  set of builders.

  The builder set is comprised of the parent builder and all triggered child
  builders.
  """
  def __init__(self):
    self._test_spec = {}

  def update(self, other_test_spec):
    self._test_spec.update(other_test_spec._test_spec)

  def as_properties_dict(self, buildername):
    """Packs a test spec and returns it as a properties dict to be passed to
    another builder.

    This method is the counterpart to the method below.

    Args:
      buildername: The name of the builder to which the property is passed. The
          spec will contain the data for that builder only.
    Returns: A dict to be used to update recipe properties of the triggered
        child builders.
    """
    builder_spec = self._test_spec.get(buildername, {})
    packed_spec = {
      'swarming_dimensions': builder_spec.get('swarming_dimensions', {}),
      'swarming_task_attrs': builder_spec.get('swarming_task_attrs', {}),
      'tests': [t.pack() for t in builder_spec.get('tests', [])],
    }
    if packed_spec['tests']:
      return {'parent_test_spec': packed_spec}
    return {}

  @staticmethod
  def from_properties_dict(properties):
    """Unpacks a test spec provided by another builder via properties.

    This method is the counterpart to the method above.

    Returns: A list of TestStepConfig objects representing extra test.
    """
    # Swarming dimensions and properties are flattened into each test config.
    builder_spec = properties.get('parent_test_spec', {})
    swarming_dimensions = builder_spec.get('swarming_dimensions', {})
    swarming_task_attrs = builder_spec.get('swarming_task_attrs', {})
    return [
      TestStepConfig.unpack(
          packed_spec, swarming_dimensions, swarming_task_attrs)
      for packed_spec in builder_spec.get('tests', [])
    ]

  @staticmethod
  def from_python_literal(full_test_spec, builderset):
    """Constructs a filtered test spec from the raw V8-side pyl.

    Args:
      full_test_spec: Full unfiltered test spec from python literal.
      builderset: Iterable with builder names (comprising the current builder
          and all its triggered testers).
    Returns:
      A test spec dict (buildername->builder spec dict) filtered by the
      builders in the given builderset. The tests in each builder spec are
      defined by TestStepConfig objects.
    """
    result = TestSpec()
    for buildername in builderset:
      builder_spec = full_test_spec.get(buildername)
      if builder_spec:
        result._test_spec[buildername] = {
          'swarming_dimensions': builder_spec.get('swarming_dimensions', {}),
          'swarming_task_attrs': builder_spec.get('swarming_task_attrs', {}),
          'tests': [
            TestStepConfig.from_python_literal(t)
            for t in builder_spec.get('tests', [])
          ],
        }
    return result

  def log_lines(self):
    """Readable representation of this test spec for recipe log lines.

    Returns: List of strings.
    """
    log = []
    for builder, builder_spec in sorted(self._test_spec.iteritems()):
      log.append(builder)
      for test in builder_spec['tests']:
        log.append('  ' + str(test))
    return log

  def get_tests(self, buildername):
    """Get all TestStepConfig objects filtered by `buildername`.

    The swarming dimensions and properties are flattened into each test-step
    config. Per-test dimensions and properties have precedence.
    """
    builder_spec = self._test_spec.get(buildername, {})
    swarming_dimensions = builder_spec.get('swarming_dimensions', {})
    swarming_task_attrs = builder_spec.get('swarming_task_attrs', {})
    # Pack/unpack each test spec in order to flatten the swarming dimensions
    # and properties into each object.
    return [
      TestStepConfig.unpack(
          test_spec.pack(), swarming_dimensions, swarming_task_attrs)
      for test_spec in builder_spec.get('tests', [])
    ]

  def get_all_test_names(self):
    """Get all test names for all tests of all builders."""
    return [
      test.name
      for builder_spec in self._test_spec.values()
      for test in builder_spec.get('tests', [])
    ]


# Empty test spec, usable as null object.
EmptyTestSpec = TestSpec()


BUILDERS = {
####### Waterfall: client.v8
  'client.v8': {
    'builders': {
####### Category: Linux
      'V8 Linux - builder': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        # TODO(machenbach): Get presubmit on swarming. Currently this builder
        # needs to upload a legacy build because of presubmit. It currently
        # uploads anyways because of the triggers_proxy specification.
        'should_upload_build': True,
        'testing': {
          'properties': {
            'triggers': [
              'V8 Linux',
              'V8 Linux - presubmit',
            ],
          },
          'platform': 'linux',
        },
        'binary_size_tracking': {
          'path_pieces_list': [['d8']],
          'category': 'linux32'
        },
        'triggers_proxy': True,
      },
      'V8 Linux - shared': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'testing': {'platform': 'linux'},
        'binary_size_tracking': {
          'path_pieces_list': [['libv8.so']],
          'category': 'linux32'
        },
      },
####### Category: Linux64
      'V8 Linux64 - builder': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'testing': {
          'properties': {
            'triggers': [
              'V8 Linux64',
              'V8 Linux64 - fyi',
            ],
          },
          'platform': 'linux',
        },
        'track_build_dependencies': True,
        'binary_size_tracking': {
          'path_pieces_list': [['d8']],
          'category': 'linux64'
        },
        'triggers_proxy': True,
      },
####### Category: Windows
      'V8 Win32 - builder': {
        'chromium_apply_config': [
          'default_compiler',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'binary_size_tracking': {
          'path_pieces_list': [['d8.exe']],
          'category': 'win32'
        },
        'testing': {
          'properties': {
            'triggers': [
              'V8 Win32',
            ],
          },
          'platform': 'win',
        },
      },
      'V8 Win64': {
        'chromium_apply_config': [
          'default_compiler',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'binary_size_tracking': {
          'path_pieces_list': [['d8.exe']],
          'category': 'win64'
        },
        'testing': {'platform': 'win'},
      },
####### Category: Mac
      'V8 Mac64': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'binary_size_tracking': {
          'path_pieces_list': [['d8']],
          'category': 'mac64'
        },
        'testing': {'platform': 'mac'},
      },
####### Category: FYI
      'V8 Linux64 - gcov coverage': {
        'chromium_apply_config': [
          'clobber', 'gcc', 'goma', 'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'gcov_coverage_folder': 'linux64_gcov_rel',
        'enable_swarming': False,
        'disable_auto_bisect': True,
        'testing': {'platform': 'linux'},
      },
    },
  },
####### Waterfall: client.v8.ports
  'client.v8.ports': {
    'builders': {
####### Category: Arm
      'V8 Arm - builder': {
        'chromium_apply_config': [
            'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
        },
        'binary_size_tracking': {
          'path_pieces_list': [['d8']],
          'category': 'linux_arm32'
        },
        'testing': {
          'properties': {
            'triggers': [
              'V8 Arm',
            ],
          },
          'platform': 'linux',
        },
        'triggers_proxy': True,
      },
      'V8 Android Arm - builder': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'android',
        },
        'binary_size_tracking': {
          'path_pieces_list': [['d8']],
          'category': 'android_arm32'
        },
        'testing': {'platform': 'linux'},
        'triggers_proxy': True,
      },
####### Category: ARM64
      'V8 Android Arm64 - builder': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'android',
        },
        'binary_size_tracking': {
          'path_pieces_list': [['d8']],
          'category': 'android_arm64'
        },
        'testing': {
          'properties': {
            'triggers': [
              'V8 Android Arm64 - N5X',
            ],
          },
          'platform': 'linux',
        },
        'triggers_proxy': True,
      },
    },
  },
####### Waterfall: client.v8.official
  'client.v8.official': {
    'builders': {
      'V8 Official Arm32': {
        'recipe': 'v8/archive',
        'chromium_apply_config': [
          'arm_hard_float', 'clobber', 'default_compiler',
          'default_target_v8_archive', 'v8_static_library', 'goma',
          'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Official Android Arm32': {
        'recipe': 'v8/archive',
        'chromium_apply_config': [
          'clobber', 'default_compiler', 'default_target_v8_archive',
          'v8_android', 'v8_static_library', 'goma', 'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
          'TARGET_PLATFORM': 'android',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Official Android Arm64': {
        'recipe': 'v8/archive',
        'chromium_apply_config': [
          'clobber', 'default_compiler', 'default_target_v8_archive',
          'v8_android', 'v8_static_library', 'goma', 'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
          'TARGET_PLATFORM': 'android',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Official Linux32': {
        'recipe': 'v8/archive',
        'chromium_apply_config': [
          'clobber', 'clang', 'default_target_v8_archive',
          'v8_static_library', 'goma', 'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Official Linux32 Debug': {
        'recipe': 'v8/archive',
        'chromium_apply_config': [
          'clobber', 'clang', 'default_target_v8_archive',
          'slow_dchecks', 'goma', 'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Official Linux64': {
        'recipe': 'v8/archive',
        'chromium_apply_config': [
          'clobber', 'clang', 'default_target_v8_archive',
          'v8_static_library', 'goma', 'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Official Linux64 Debug': {
        'recipe': 'v8/archive',
        'chromium_apply_config': [
          'clobber', 'clang', 'default_target_v8_archive',
          'slow_dchecks', 'goma', 'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Official Win32': {
        'recipe': 'v8/archive',
        'chromium_apply_config': [
          'clobber', 'clang', 'default_target_v8_archive',
          'v8_static_library', 'goma', 'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'win'},
      },
      'V8 Official Win32 Debug': {
        'recipe': 'v8/archive',
        'chromium_apply_config': [
          'clobber', 'clang', 'default_target_v8_archive',
          'slow_dchecks', 'goma', 'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'win'},
      },
      'V8 Official Win64': {
        'recipe': 'v8/archive',
        'chromium_apply_config': [
          'clobber', 'clang', 'default_target_v8_archive',
          'v8_static_library', 'goma', 'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'win'},
      },
      'V8 Official Win64 Debug': {
        'recipe': 'v8/archive',
        'chromium_apply_config': [
          'clobber', 'clang', 'default_target_v8_archive',
          'slow_dchecks', 'goma', 'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'win'},
      },
      'V8 Official Mac64': {
        'recipe': 'v8/archive',
        'chromium_apply_config': [
          'clobber', 'clang', 'default_target_v8_archive',
          'v8_static_library', 'goma', 'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'mac'},
      },
      'V8 Official Mac64 Debug': {
        'recipe': 'v8/archive',
        'chromium_apply_config': [
          'clobber', 'clang', 'default_target_v8_archive',
          'slow_dchecks', 'goma', 'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'mac'},
      },
    },
  },
####### Waterfall: tryserver.v8
  'tryserver.v8': {
    'builders': {
      'v8_linux64_sanitizer_coverage_rel': {
        'gclient_apply_config': ['llvm_compiler_rt'],
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'sanitizer_coverage_folder': 'linux64',
        'testing': {
          'properties': {
            'build_config': 'Release'
          },
          'platform': 'linux',
        },
      },
    },
  },
}


BUILDERS = freeze(BUILDERS)

def flatten_configs():
  # TODO(machenbach): Temporary code to migrate to flattened builder configs.
  # Clean up the config above and remove this after testing in prod.
  flattened_builders = {}
  for _, master_config in BUILDERS.iteritems():
      builders = master_config['builders']
      for buildername, bot_config in builders.iteritems():
        assert buildername not in flattened_builders, buildername
        flattened_builders[buildername] = bot_config
  return freeze(flattened_builders)

FLATTENED_BUILDERS = flatten_configs()



def iter_builders(recipe='v8'):
  """Iterates tuples of (mastername, builders, buildername, bot_config).

  Args:
    recipe: Limits iteration to a specific recipe (default: v8).
  """
  for mastername, master_config in BUILDERS.iteritems():
    builders = master_config['builders']
    for buildername, bot_config in builders.iteritems():
      if bot_config.get('recipe', 'v8') != recipe:
        continue
      yield mastername, builders, buildername, bot_config


# Map from mastername to map from buildername to its parent if specified.
# The parent is encoded as a tuple of (buildername, bot_config).
# This is used for simulation only. Prod data might have additional
# parent-child relationships from runtime properties. Those are only simulated
# here with the "testing" dict, but data might not be accurate.
PARENT_MAP = {}
def fill_parent_map():
  for _, _, builder, bot_config in iter_builders():
    # Simulated dynamically defined triggers.
    for triggered in bot_config.get('testing', {}).get('properties', {}).get(
        'triggers', []):
      PARENT_MAP[triggered] = (builder, bot_config)

fill_parent_map()
