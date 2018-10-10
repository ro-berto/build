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

  def __call__(self, shards):
    return TestStepConfig(self.name, shards, self._suffix, self.test_args,
                          self.variants)

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


# Top-level test configs for convenience.
Benchmarks = TestStepConfig('benchmarks')
D8Testing = TestStepConfig('d8testing')
D8TestingRandomGC = TestStepConfig('d8testing_random_gc')
Fuzz = TestStepConfig('jsfunfuzz')
GCMole = TestStepConfig('gcmole')
Mjsunit = TestStepConfig('mjsunit')
MjsunitSPFrameAccess = TestStepConfig('mjsunit_sp_frame_access')
Mozilla = TestStepConfig('mozilla')
NumFuzz = TestStepConfig('numfuzz')
OptimizeForSize = TestStepConfig('optimize_for_size')
Presubmit = TestStepConfig('presubmit')
Test262 = TestStepConfig('test262')
Test262Variants = TestStepConfig('test262_variants')
Unittests = TestStepConfig('unittests')
V8Initializers = TestStepConfig('v8initializers')
V8Testing = TestStepConfig('v8testing')
Webkit = TestStepConfig('webkit')


def with_test_args(suffix, test_args, tests, variants=None, dimensions=None):
  """Wrapper that runs a list of tests with additional arguments."""
  return [
    TestStepConfig(t.name, t.shards, suffix, test_args, variants, dimensions)
    for t in tests
  ]

def with_variant(tests, variant):
  """Convenience wrapper. As above, but to run tests with specific variant."""
  return with_test_args(variant, None, tests, variants=V8Variant(variant))

def with_extra_variants(tests):
  """Convenience wrapper. As above, but to run tests with the 'extra' variant
  set.
  """
  return with_variant(tests, 'extra')

def with_dimensions(suffix, tests, dimensions):
  """Convenience wrapper. As above, but overriding swarming dimensions."""
  return with_test_args(suffix, None, tests, dimensions=dimensions)


SWARMING_FYI_TASK_ATTRS = {
  'expiration': 4 * 60 * 60,
  'hard_timeout': 60 * 60,
  'priority': 35,
}

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
          'platform': 'linux',
        },
        'binary_size_tracking': {
          'path_pieces_list': [['d8']],
          'category': 'linux32'
        },
        'triggers': [
          'V8 Linux',
          'V8 Linux - presubmit',
        ],
        'triggers_proxy': True,
      },
      'V8 Linux - debug builder': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux - debug',
          'V8 Linux - gc stress',
        ],
      },
      'V8 Linux - nosnap builder': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux - nosnap',
        ],
      },
      'V8 Linux - nosnap debug builder': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux - nosnap - debug',
        ],
      },
      'V8 Linux - presubmit': {
        'enable_swarming': False,
        'tests': [Presubmit],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux': {
        'tests': [
          V8Initializers,
          V8Testing,
          OptimizeForSize,
          Benchmarks,
          Test262Variants(2),
          Mozilla,
          MjsunitSPFrameAccess,
          GCMole,
        ] + with_test_args(
            'isolates',
            ['--isolates'],
            [V8Testing],
        ) + with_test_args(
            'nosse3',
            ['--extra-flags',
             '--noenable-sse3 --noenable-ssse3 --noenable-sse4-1 --noenable-avx'
            ],
            [V8Testing, Mozilla],
        ) + with_test_args(
            'nosse4',
            ['--extra-flags', '--noenable-sse4-1 --noenable-avx'],
            [V8Testing, Mozilla],
        ) + with_extra_variants(
            [V8Testing, Mozilla, Test262Variants, Benchmarks]),
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'cpu': 'x86-64-avx2',
        },
      },
      'V8 Linux - debug': {
        'tests': [
          V8Testing(3),
          OptimizeForSize,
          Benchmarks,
          Test262Variants(6),
          Mozilla,
          MjsunitSPFrameAccess,
        ] + with_test_args(
            'isolates',
            ['--isolates'],
            [V8Testing(4)],
        ) + with_test_args(
            'nosse3',
            ['--extra-flags',
             '--noenable-sse3 --noenable-ssse3 --noenable-sse4-1 --noenable-avx'
            ],
            [V8Testing(3), Test262, Mozilla],
        ) + with_test_args(
            'nosse4',
            ['--extra-flags', '--noenable-sse4-1 --noenable-avx'],
            [V8Testing(3), Test262, Mozilla],
        ) + with_extra_variants(
            [V8Testing, Mozilla, Test262Variants(2), Benchmarks]),
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'cpu': 'x86-64-avx2',
        },
      },
      'V8 Linux - shared': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'shared_library', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [V8Testing, Test262, Mozilla],
        'testing': {'platform': 'linux'},
        'binary_size_tracking': {
          'path_pieces_list': [['libv8.so']],
          'category': 'linux32'
        },
      },
      'V8 Linux - nosnap': {
        'tests': [
          V8Testing(3),
          Test262(2),
          Mozilla,
        ],
        'variants': V8Variant('default'),
        'testing': {'platform': 'linux'},
        'swarming_task_attrs': SWARMING_FYI_TASK_ATTRS,
      },
      'V8 Linux - nosnap - debug': {
        'tests': [V8Testing(12)],
        'variants': V8Variant('default'),
        'testing': {'platform': 'linux'},
        'swarming_task_attrs': SWARMING_FYI_TASK_ATTRS,
      },
      'V8 Linux - interpreted regexp': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'enable_swarming': False,
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
        'swarming_task_attrs': SWARMING_FYI_TASK_ATTRS,
      },
      'V8 Linux - noi18n - debug': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'tests': [V8Testing, Mozilla, Test262],
        'variants': V8Variant('default'),
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - verify csa': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - embedded builtins': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - embedded builtins - debug': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'tests': [V8Testing(3)],
        'testing': {'platform': 'linux'},
      },
####### Category: Linux64
      'V8 Linux64 - builder': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'testing': {'platform': 'linux'},
        'track_build_dependencies': True,
        'binary_size_tracking': {
          'path_pieces_list': [['d8']],
          'category': 'linux64'
        },
        'triggers': [
          'V8 Linux64',
          'V8 Linux64 - fyi',
        ],
        'triggers_proxy': True,
      },
      'V8 Linux64 - debug builder': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Fuzzer',
          'V8 Linux64 - debug',
          'V8 Linux64 - debug - fyi',
        ],
      },
      'V8 Linux64 - custom snapshot - debug builder': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux64 - custom snapshot - debug',
          'V8 Linux64 GC Stress - custom snapshot',
        ],
      },
      'V8 Linux64': {
        'tests': [
          V8Initializers,
          V8Testing,
          OptimizeForSize,
          Test262Variants(2),
          Mozilla,
          MjsunitSPFrameAccess,
          Benchmarks,
        ] + with_test_args(
            'noavx',
            ['--extra-flags', '--noenable-avx'],
            [V8Testing, Test262, Mozilla],
        ) + with_extra_variants([
          V8Testing, Mozilla, Test262Variants, Benchmarks]),
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'cpu': 'x86-64-avx2',
        },
      },
      'V8 Linux64 - debug': {
        'tests': [
          V8Testing(2),
          OptimizeForSize,
          Test262Variants(5),
          Mozilla,
          MjsunitSPFrameAccess,
          Benchmarks,
        ] + with_test_args(
            'noavx',
            ['--extra-flags', '--noenable-avx'],
            [V8Testing(2), Test262, Mozilla],
        ) + with_extra_variants([
          V8Testing, Mozilla, Test262Variants(2), Benchmarks]),
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'cpu': 'x86-64-avx2',
        },
      },
      'V8 Linux64 - internal snapshot': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - custom snapshot - debug': {
        'v8_apply_config': ['no_harness'],
        'tests': [Mjsunit],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - verify csa': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - debug - header includes': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'testing': {'platform': 'linux'},
      },
####### Category: Jumbo
      'V8 Linux64 Jumbo': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 Jumbo - debug': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 Jumbo - limited': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 Jumbo - limited - debug': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'testing': {'platform': 'linux'},
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
        'testing': {'platform': 'win'},
        'triggers': [
          'V8 Win32',
        ],
      },
      'V8 Win32 - debug builder': {
        'chromium_apply_config': [
          'default_compiler',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'testing': {'platform': 'win'},
        'triggers': [
          'V8 Win32 - debug',
        ],
      },
      'V8 Win32': {
        'tests': [V8Testing, Test262, Mozilla],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        },
      },
      'V8 Win32 - nosnap - shared': {
        'chromium_apply_config': [
          'default_compiler',
          'goma',
          'shared_library',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [V8Testing(2)],
        'variants': V8Variant('default'),
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'win'},
      },
      'V8 Win32 - debug': {
        'tests': [
          V8Testing(5),
          Test262,
          Mozilla,
        ],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
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
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
        },
        'binary_size_tracking': {
          'path_pieces_list': [['d8.exe']],
          'category': 'win64'
        },
        'tests': [
          V8Testing,
          Test262,
          Mozilla,
        ] + with_extra_variants([V8Testing]),
        'testing': {'platform': 'win'},
      },
      'V8 Win64 - debug': {
        'chromium_apply_config': [
          'default_compiler',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
        },
        'tests': [
          V8Testing(4),
          Test262,
          Mozilla,
        ] + with_extra_variants([V8Testing(3)]),
        'testing': {'platform': 'win'},
      },
      'V8 Win64 - msvc': {
        'chromium_apply_config': [
          'default_compiler',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
        },
        'tests': [
          V8Testing,
          Test262,
          Mozilla,
        ],
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
        'tests': [
          V8Testing,
          Test262,
          Mozilla,
        ] + with_extra_variants([V8Testing]),
        'swarming_dimensions': {
          'os': 'Mac-10.13',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'mac'},
      },
      'V8 Mac64 - debug': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'tests': [
          V8Testing(3),
          Test262,
          Mozilla,
        ] + with_extra_variants([V8Testing]),
        'swarming_dimensions': {
          'os': 'Mac-10.13',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'mac'},
      },
####### Category: Misc
      'V8 Fuzzer': {
        'tests': [Fuzz],
        'testing': {'platform': 'linux'},
        'swarming_task_attrs': SWARMING_FYI_TASK_ATTRS,
      },
      'V8 Linux - gc stress': {
        'v8_apply_config': ['gc_stress'],
        'tests': [D8Testing(5)],
        'testing': {'platform': 'linux'},
      },
      'V8 Mac64 GC Stress': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'tests': [D8Testing(4)],
        'swarming_dimensions': {
          'os': 'Mac-10.13',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'mac'},
      },
      'V8 Linux64 GC Stress - custom snapshot': {
        'v8_apply_config': ['gc_stress', 'no_harness'],
        'tests': [Mjsunit(3)],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux gcc 4.8': {
        'chromium_apply_config': ['gcc', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 gcc 4.8 - debug': {
        'chromium_apply_config': ['gcc', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 ASAN': {
        'chromium_apply_config': ['clang', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [
          V8Testing(2),
          Test262Variants(5),
        ] + with_extra_variants([V8Testing]),
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 TSAN - builder': {
        'chromium_apply_config': ['clang', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'triggers': [
          'V8 Linux64 TSAN',
          'V8 Linux64 TSAN - concurrent marking',
          'V8 Linux64 TSAN - isolates',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 TSAN': {
        'tests': [
          V8Testing(5),
          Test262(3),
          Mozilla,
          Benchmarks,
        ] + with_extra_variants([V8Testing(3)]),
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 TSAN - concurrent marking': {
        'v8_apply_config': ['stress_incremental_marking'],
        'tests': [
          V8Testing(4),
          Test262(4),
          Mozilla,
          Benchmarks,
        ],
        'testing': {'platform': 'linux'},
        'swarming_task_attrs': SWARMING_FYI_TASK_ATTRS,
      },
      'V8 Linux64 TSAN - isolates': {
        'v8_apply_config': ['isolates'],
        'tests': [
          V8Testing(5),
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim - MSAN': {
        'chromium_apply_config': [
          'clang',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [
          V8Testing(4),
          Test262(2),
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - cfi': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [
          V8Testing,
          OptimizeForSize,
          Benchmarks,
          Test262,
          Mozilla,
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 UBSan': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 UBSanVptr': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'V8 Mac64 ASAN': {
        'chromium_apply_config': ['clang', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [V8Testing(5)],
        'swarming_dimensions': {
          'os': 'Mac-10.13',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'mac'},
      },
      'V8 Win64 ASAN': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [V8Testing(5)],
        'swarming_dimensions': {
          'os': 'Windows-10',
        },
        'testing': {'platform': 'win'},
      },
####### Category: FYI
      'V8 Fuchsia': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'fuchsia',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Fuchsia - debug': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'fuchsia',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - fyi': {
        'testing': {'platform': 'linux'},
        'swarming_task_attrs': SWARMING_FYI_TASK_ATTRS,
      },
      'V8 Linux64 - debug - fyi': {
        'testing': {'platform': 'linux'},
        'swarming_task_attrs': SWARMING_FYI_TASK_ATTRS,
      },
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
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - vtunejit': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - predictable': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'enable_swarming': False,
        'tests': [D8Testing, Benchmarks, Mozilla],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - full debug': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'enable_swarming': False,
        'tests': [V8Testing],
        'variants': V8Variant('default'),
        'testing': {'platform': 'linux'},
      },
    },
  },
####### Waterfall: client.v8.clusterfuzz
  'client.v8.clusterfuzz': {
    'builders': {
      'V8 Clusterfuzz Linux64 - release builder': {
        'chromium_apply_config': [
          'clang',
          'goma',
          'mb',
          'default_target_v8_clusterfuzz',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8',
        'triggers': [
          'V8 NumFuzz',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Clusterfuzz Linux64 - debug builder': {
        'chromium_apply_config': [
          'clang',
          'goma',
          'mb',
          'default_target_v8_clusterfuzz',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8',
        'triggers': [
          'V8 NumFuzz - debug',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Clusterfuzz Linux64 - nosnap release builder': {
        'chromium_apply_config': [
          'clang',
          'goma',
          'mb',
          'default_target_v8_clusterfuzz',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 NumFuzz - nosnap',
        ],
      },
      'V8 Clusterfuzz Linux64 - nosnap debug builder': {
        'chromium_apply_config': [
          'clang',
          'goma',
          'mb',
          'default_target_v8_clusterfuzz',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 NumFuzz - nosnap debug',
        ],
      },
      'V8 Clusterfuzz Linux64 ASAN no inline - release builder': {
        'chromium_apply_config': [
          'clang',
          'goma',
          'mb',
          'clobber',
          'default_target_v8_clusterfuzz',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-asan-no-inline',
        'testing': {'platform': 'linux'},
      },
      'V8 Clusterfuzz Linux64 ASAN - debug builder': {
        'chromium_apply_config': [
          'clang',
          'clobber',
          'default_target_v8_clusterfuzz',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-asan',
        'testing': {'platform': 'linux'},
      },
      'V8 Clusterfuzz Linux64 ASAN arm64 - debug builder': {
        'chromium_apply_config': [
          'clang',
          'clobber',
          'default_target_v8_clusterfuzz',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-arm64-asan',
        'testing': {'platform': 'linux'},
      },
      'V8 Clusterfuzz Linux ASAN arm - debug builder': {
        'chromium_apply_config': [
          'clang',
          'clobber',
          'default_target_v8_clusterfuzz',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-arm-asan',
        'testing': {'platform': 'linux'},
      },
      'V8 Clusterfuzz Linux64 CFI - release builder': {
        'chromium_apply_config': [
          'clang',
          'default_target_v8_clusterfuzz',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-cfi',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-cfi',
        'testing': {'platform': 'linux'},
      },
      'V8 Clusterfuzz Linux MSAN no origins': {
        'chromium_apply_config': [
          'clang',
          'default_target_v8_clusterfuzz',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-msan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-msan-no-origins',
        'testing': {'platform': 'linux'},
      },
      'V8 Clusterfuzz Linux MSAN chained origins': {
        'chromium_apply_config': [
          'clang',
          'default_target_v8_clusterfuzz',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-msan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-msan-chained-origins',
        'testing': {'platform': 'linux'},
      },
      'V8 Clusterfuzz Linux64 TSAN - release builder': {
        'chromium_apply_config': [
          'default_compiler',
          'goma',
          'default_target_v8_clusterfuzz',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'triggers': [
          'V8 NumFuzz - TSAN',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Clusterfuzz Linux64 UBSanVptr - release builder': {
        'chromium_apply_config': [
          'default_compiler',
          'goma',
          'default_target_v8_clusterfuzz',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-ubsan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-ubsan-vptr',
        'testing': {'platform': 'linux'},
      },
      'V8 Clusterfuzz Mac64 ASAN - release builder': {
        'chromium_apply_config': [
          'default_compiler',
          'goma',
          'default_target_v8_clusterfuzz',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-asan',
        'testing': {'platform': 'mac'},
      },
      'V8 Clusterfuzz Mac64 ASAN - debug builder': {
        'chromium_apply_config': [
          'default_compiler',
          'goma',
          'default_target_v8_clusterfuzz',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-asan',
        'testing': {'platform': 'mac'},
      },
      'V8 Clusterfuzz Win64 ASAN - release builder': {
        'chromium_apply_config': [
          'default_compiler',
          'goma',
          'default_target_v8_clusterfuzz',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'cf_archive_build': True,
        'cf_archive_bitness': 64,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-asan',
        'testing': {'platform': 'win'},
      },
      'V8 Clusterfuzz Win64 ASAN - debug builder': {
        'chromium_apply_config': [
          'default_compiler',
          'goma',
          'default_target_v8_clusterfuzz',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'cf_archive_build': True,
        'cf_archive_bitness': 64,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-asan',
        'testing': {'platform': 'win'},
      },
      'V8 NumFuzz': {
        'tests': with_test_args(
            'deopt',
            [
              '--total-timeout-sec=2100', # 35 minutes
              '--stress-deopt=1',
            ],
            [NumFuzz],
        ),
        'testing': {'platform': 'linux'},
        'swarming_task_attrs': SWARMING_FYI_TASK_ATTRS,
      },
      'V8 NumFuzz - debug': {
        'tests': [D8TestingRandomGC] + with_test_args(
            'marking',
            [
              '--total-timeout-sec=2100', # 35 minutes
              '--stress-marking=1',
            ],
            [NumFuzz(2)],
        ) + with_test_args(
            'scavenge',
            [
              '--total-timeout-sec=2100', # 35 minutes
              '--stress-scavenge=1',
            ],
            [NumFuzz],
        ) + with_test_args(
            'threads',
            [
              '--total-timeout-sec=2100', # 35 minutes
              '--stress-thread-pool-size=1',
            ],
            [NumFuzz],
        ) + with_test_args(
            'delay',
            [
              '--total-timeout-sec=2100', # 35 minutes
              '--stress-delay-tasks=1',
            ],
            [NumFuzz],
        ) + with_test_args(
            'combined',
            [
              '--total-timeout-sec=2100', # 35 minutes
              '--stress-deopt=2',
              '--stress-compaction=2',
              '--stress-gc=4',
              '--stress-marking=4',
              '--stress-scavenge=4',
              '--stress-thread-pool-size=2',
            ],
            [NumFuzz(3)],
        ) + with_test_args(
            'endurance',
            [
              '--total-timeout-sec=1200', # 20 minutes
              '--combine-tests',
              '--combine-min=30',
              '--combine-max=50',
              '--stress-deopt=2',
              '--stress-compaction=2',
              '--stress-gc=6',
              '--stress-marking=6',
              '--stress-scavenge=4',
              '--stress-thread-pool-size=1',
            ],
            [NumFuzz],
        ) + with_test_args(
            'deopt',
            [
              '--total-timeout-sec=2100', # 35 minutes
              '--stress-deopt=1',
            ],
            [NumFuzz(2)],
        ),
        'testing': {'platform': 'linux'},
        'swarming_task_attrs': SWARMING_FYI_TASK_ATTRS,
      },
      'V8 NumFuzz - TSAN': {
        'tests': [D8TestingRandomGC(2)] + with_test_args(
            'marking',
            [
              '--total-timeout-sec=2100', # 35 minutes
              '--stress-marking=1',
            ],
            [NumFuzz],
        ) + with_test_args(
            'scavenge',
            [
              '--total-timeout-sec=2100', # 35 minutes
              '--stress-scavenge=1',
            ],
            [NumFuzz],
        ) + with_test_args(
            'threads',
            [
              '--total-timeout-sec=2100', # 35 minutes
              '--stress-thread-pool-size=1',
            ],
            [NumFuzz],
        ) + with_test_args(
            'delay',
            [
              '--total-timeout-sec=2100', # 35 minutes
              '--stress-delay-tasks=1',
            ],
            [NumFuzz],
        ) + with_test_args(
            'combined',
            [
              '--total-timeout-sec=2100', # 35 minutes
              '--stress-deopt=2',
              '--stress-compaction=2',
              '--stress-gc=4',
              '--stress-marking=4',
              '--stress-scavenge=4',
              '--stress-thread-pool-size=2',
            ],
            [NumFuzz(4)],
        ) + with_test_args(
            'endurance',
            [
              '--total-timeout-sec=1200', # 20 minutes
              '--combine-tests',
              '--combine-min=10',
              '--combine-max=30',
              '--stress-compaction=2',
              '--stress-gc=6',
              '--stress-marking=6',
              '--stress-scavenge=4',
              '--stress-thread-pool-size=1',
            ],
            [NumFuzz],
        ),
        'testing': {'platform': 'linux'},
        'swarming_task_attrs': SWARMING_FYI_TASK_ATTRS,
      },
      'V8 NumFuzz - nosnap': {
        'tests': with_test_args(
            'interrupt-budget',
            [
              '--total-timeout-sec=2100', # 35 minutes
              '--stress-interrupt-budget=10',
              '--stress-deopt=5',
            ],
            [NumFuzz],
        ),
        'testing': {'platform': 'linux'},
        'swarming_task_attrs': SWARMING_FYI_TASK_ATTRS,
      },
      'V8 NumFuzz - nosnap debug': {
        'tests': with_test_args(
            'interrupt-budget',
            [
              '--total-timeout-sec=2100', # 35 minutes
              '--stress-interrupt-budget=10',
              '--stress-deopt=5',
            ],
            [NumFuzz],
        ),
        'testing': {'platform': 'linux'},
        'swarming_task_attrs': SWARMING_FYI_TASK_ATTRS,
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
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Arm',
        ],
        'triggers_proxy': True,
      },
      'V8 Arm - debug builder': {
        'chromium_apply_config': [
            'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
        },
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Arm - debug',
          'V8 Arm GC Stress',
        ],
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
      'V8 Arm': {
        'tests': [
          V8Testing(2),
          Benchmarks,
          OptimizeForSize,
        ] + with_dimensions(
            'ODROID',
            [V8Testing(2), Benchmarks, OptimizeForSize],
            {
              'cpu': 'armv7l-32-ODROID-XU4',
              'cores': '8',
              'os': 'Ubuntu-16.04',
            },
        ),
        'swarming_task_attrs': {
          'hard_timeout': 90 * 60,
          'expiration': 6 * 60 * 60,
        },
        'swarming_dimensions': {
          'cpu': 'armv7l',
          'cores': '2',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Arm - debug': {
        'v8_apply_config': ['verify_heap_skip_remembered_set'],
        'tests': [
          V8Testing(3),
          OptimizeForSize(2),
        ] + with_dimensions(
            'ODROID',
            [V8Testing(3), OptimizeForSize(2)],
            {
              'cpu': 'armv7l-32-ODROID-XU4',
              'cores': '8',
              'os': 'Ubuntu-16.04',
            },
        ),
        'variants': V8Variant('default'),
        'swarming_task_attrs': {
          'hard_timeout': 60 * 60,
          'expiration': 6 * 60 * 60,
        },
        'swarming_dimensions': {
          'cpu': 'armv7l',
          'cores': '2',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Arm GC Stress': {
        'v8_apply_config': ['gc_stress', 'verify_heap_skip_remembered_set'],
        'tests': [D8Testing(3)] + with_dimensions(
            'ODROID',
            [D8Testing(3)],
            {
              'cpu': 'armv7l-32-ODROID-XU4',
              'cores': '8',
              'os': 'Ubuntu-16.04',
            },
        ),
        'variants': V8Variant('default'),
        'swarming_task_attrs': {
          'hard_timeout': 2 * 60 * 60,
          'expiration': 6 * 60 * 60,
        },
        'swarming_dimensions': {
          'cpu': 'armv7l',
          'cores': '2',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm - sim': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [
          V8Testing(4),
          Test262,
          Mozilla,
          MjsunitSPFrameAccess,
        ] + with_test_args(
            'armv8-a',
            ['--extra-flags', '--enable-armv8'],
            [V8Testing(4), Test262, Mozilla],
        ) + with_test_args(
            'novfp3',
            ['--novfp3'],
            [V8Testing(4), Test262, Mozilla],
        ) + with_extra_variants([V8Testing]),
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm - sim - debug': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'tests': [
          V8Testing(7),
          Test262,
          Mozilla,
          MjsunitSPFrameAccess,
        ] + with_test_args(
            'armv8-a',
            ['--extra-flags', '--enable-armv8'],
            [V8Testing(7), Test262, Mozilla],
        ) + with_test_args(
            'novfp3',
            ['--novfp3'],
            [V8Testing(7), Test262, Mozilla],
            V8Variant('default'),
        ) + with_extra_variants([V8Testing(3)]),
        'testing': {'platform': 'linux'},
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
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Android Arm64 - N5X',
        ],
        'triggers_proxy': True,
      },
      'V8 Android Arm64 - N5X': {
        'tests': [
          V8Testing(3),
          Test262(5),
          Mozilla,
        ],
        'variants': V8Variant('default'),
        'swarming_dimensions': {
          'device_os': 'MMB29Q',
          'device_type': 'bullhead',
          'os': 'Android',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [
          V8Testing(3),
          Test262,
          Mozilla,
          MjsunitSPFrameAccess,
        ] + with_extra_variants([V8Testing]),
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim - debug': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'tests': [
          V8Testing(10),
          Test262,
          Mozilla,
          MjsunitSPFrameAccess,
        ] + with_extra_variants([V8Testing(4)]),
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim - gc stress': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_apply_config': ['gc_stress', 'verify_heap_skip_remembered_set'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
        'swarming_task_attrs': {
          'expiration': 4 * 60 * 60,
          'hard_timeout': 2 * 60 * 60,
          'priority': 35,
        },
        'tests': [D8Testing(5)],
        'testing': {'platform': 'linux'},
      },
####### Category: MIPS
      'V8 Mips - builder': {
        'chromium_apply_config': ['default_compiler', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'mips',
        },
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Mips - big endian - nosnap',
        ],
      },
      'V8 Mips - big endian - nosnap': {
        'tests': [V8Testing(2)],
        'variants': V8Variant('default'),
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Debian-8.7',
          'cpu': 'mips-32',
        },
        'swarming_task_attrs': {
          'expiration': 5 * 60 * 60,
          'hard_timeout': 5 * 60 * 60,
        },
      },
      'V8 Linux - mipsel - sim - builder': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux - mipsel - sim',
        ],
      },
      'V8 Linux - mips64el - sim - builder': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux - mips64el - sim',
        ],
      },
      'V8 Linux - mipsel - sim': {
        'tests': [V8Testing(4), Test262],
        'testing': {'platform': 'linux'},
        'swarming_task_attrs': SWARMING_FYI_TASK_ATTRS,
      },
      'V8 Linux - mips64el - sim': {
        'tests': [V8Testing(4), Test262],
        'testing': {'platform': 'linux'},
        'swarming_task_attrs': SWARMING_FYI_TASK_ATTRS,
      },
####### Category: IBM
      'V8 Linux - ppc64 - sim': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [V8Testing(3)],
        'testing': {'platform': 'linux'},
        'swarming_task_attrs': SWARMING_FYI_TASK_ATTRS,
      },
      'V8 Linux - s390x - sim': {
        'chromium_apply_config': [
          'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'tests': [V8Testing(3)],
        'testing': {'platform': 'linux'},
        'swarming_task_attrs': SWARMING_FYI_TASK_ATTRS,
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
      'v8_linux_nodcheck_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_linux_nodcheck_rel_ng_triggered',
            ],
          },
          'platform': 'linux',
        },
      },
      'v8_linux_dbg_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Debug',
            'triggers': [
              'v8_linux_dbg_ng_triggered',
            ],
          },
          'platform': 'linux',
        },
      },
      'v8_linux_embedded_builtins_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_linux_embedded_builtins_rel_ng_triggered',
            ],
          },
          'platform': 'linux',
        },
      },
      'v8_linux_noi18n_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_linux_noi18n_rel_ng_triggered',
            ],
          },
          'platform': 'linux',
        },
      },
      'v8_linux_nosnap_rel': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
          },
          'platform': 'linux',
        },
      },
      'v8_linux_nosnap_dbg': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Debug',
          },
          'platform': 'linux',
        },
      },
      'v8_linux_gcc_compile_rel': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
          },
          'platform': 'linux',
        },
      },
      'v8_linux_gcc_rel': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
          },
          'platform': 'linux',
        },
      },
      'v8_linux_shared_compile_rel': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
          },
          'platform': 'linux',
        },
      },
      'v8_linux64_dbg_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Debug',
            'triggers': [
              'v8_linux64_dbg_ng_triggered',
            ],
          },
          'platform': 'linux',
        },
      },
      'v8_linux64_gcc_compile_dbg': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Debug',
          },
          'platform': 'linux',
        },
      },
      'v8_linux64_header_includes_dbg': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Debug',
          },
          'platform': 'linux',
        },
      },
      'v8_linux64_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_linux64_rel_ng_triggered',
            ],
          },
          'platform': 'linux',
        },
      },
      'v8_linux64_fyi_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_linux64_fyi_rel_ng_triggered',
            ],
          },
          'platform': 'linux',
        },
      },
      'v8_linux64_verify_csa_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_linux64_verify_csa_rel_ng_triggered',
            ],
          },
          'platform': 'linux',
        },
      },
      'v8_linux_gc_stress_dbg': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Debug',
          },
          'platform': 'linux',
        },
      },
      'v8_linux64_asan_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_linux64_asan_rel_ng_triggered',
            ],
          },
          'platform': 'linux',
        },
      },
      'v8_linux64_cfi_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_linux64_cfi_rel_ng_triggered',
            ],
          },
          'platform': 'linux',
        },
      },
      'v8_linux64_jumbo_compile_rel': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
          },
          'platform': 'linux',
        },
      },
      'v8_linux64_jumbo_limited_compile_rel': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
          },
          'platform': 'linux',
        },
      },
      'v8_linux64_msan_rel': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
          },
          'platform': 'linux',
        },
      },
      'v8_linux64_tsan_rel': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
          },
          'platform': 'linux',
        },
      },
      'v8_linux64_ubsan_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_linux64_ubsan_rel_ng_triggered',
            ],
          },
          'platform': 'linux',
        },
      },
      'v8_linux64_sanitizer_coverage_rel': {
        'gclient_apply_config': ['llvm_compiler_rt'],
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'sanitizer_coverage_folder': 'linux64',
        'tests': [
          V8Testing(3),
        ],
        'testing': {
          'properties': {
            'build_config': 'Release',
          },
          'platform': 'linux',
        },
      },
      'v8_win_dbg': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Debug',
          },
          'platform': 'win',
        },
      },
      'v8_win_compile_dbg': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Debug',
          },
          'platform': 'win',
        },
      },
      'v8_win_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_win_rel_ng_triggered',
            ],
          },
          'platform': 'win',
        },
      },
      'v8_win_nosnap_shared_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_win_nosnap_shared_rel_ng_triggered',
            ],
          },
          'platform': 'win',
        },
      },
      'v8_win64_asan_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_win64_asan_rel_ng_triggered',
            ],
          },
          'platform': 'win',
        },
      },
      'v8_win64_msvc_compile_rel': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
          },
          'platform': 'win',
        },
      },
      'v8_win64_msvc_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_win64_msvc_rel_ng_triggered',
            ],
          },
          'platform': 'win',
        },
      },
      'v8_win64_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_win64_rel_ng_triggered',
            ],
          },
          'platform': 'win',
        },
      },
      'v8_win64_dbg': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Debug',
          },
          'platform': 'win',
        },
      },
      'v8_mac64_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_mac64_rel_ng_triggered',
            ],
          },
          'platform': 'mac',
        },
      },
      'v8_mac64_dbg_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Debug',
            'triggers': [
              'v8_mac64_dbg_ng_triggered',
            ],
          },
          'platform': 'mac',
        },
      },
      'v8_mac64_gc_stress_dbg': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Debug',
          },
          'platform': 'mac',
        },
      },
      'v8_mac64_asan_rel': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
          },
          'platform': 'mac',
        },
      },
      'v8_linux_arm_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_linux_arm_rel_ng_triggered',
            ],
          },
          'platform': 'linux',
        },
      },
      'v8_linux_arm_dbg': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Debug',
          },
          'platform': 'linux',
        },
      },
      'v8_linux_arm64_rel_ng': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'triggers': [
              'v8_linux_arm64_rel_ng_triggered',
            ],
          },
          'platform': 'linux',
        },
      },
      'v8_linux_arm64_dbg': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Debug',
          },
          'platform': 'linux',
        },
      },
      'v8_linux_arm64_gc_stress_dbg': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Debug',
          },
          'platform': 'linux',
        },
      },
      'v8_android_arm_compile_rel': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
            'target_arch': 'arm',
            'target_platform': 'android',
          },
          'platform': 'linux',
        },
      },
      'v8_mips_compile_rel': {
        'chromium_apply_config': ['default_compiler', 'mb'],
        'enable_swarming': False,
        'testing': {
          'properties': {
            'build_config': 'Release',
            'target_arch': 'mips',
          },
          'platform': 'linux',
        },
      },
      'v8_linux_mipsel_compile_rel': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
          },
          'platform': 'linux',
        },
      },
      'v8_linux_mips64el_compile_rel': {
        'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
        'testing': {
          'properties': {
            'build_config': 'Release',
          },
          'platform': 'linux',
        },
      },
    },
  },
}

####### Waterfall: client.v8.branches
BRANCH_BUILDERS = {}

def AddBranchBuilder(name, build_config, presubmit=False,
                     unittests_only=False):
  tests = []
  if presubmit:
    tests.append(Presubmit)
  if unittests_only:
    tests.append(Unittests)
  else:
    if build_config == 'Debug':
      tests.append(V8Testing(3))
    elif 'arm' in name:
      tests.append(V8Testing(2))
    elif 'mips' in name:
      tests.append(V8Testing(4))
    else:
      tests.append(V8Testing)
    if 'mips' not in name:
      tests.extend([Test262, Mozilla])
  return {
    'chromium_apply_config': ['default_compiler', 'goma', 'mb'],
    'v8_config_kwargs': {
      'BUILD_CONFIG': build_config,
    },
    'tests': tests,
    'testing': {'platform': 'linux'},
    'swarming_task_attrs': {
      'expiration': 4 * 60 * 60,
      'hard_timeout': 90 * 60,
      'priority': 35,
    },
  }

def fill_branch_builders():
  for build_config, name_suffix in (('Release', ''), ('Debug', ' - debug')):
    for branch_name in ('stable branch', 'beta branch'):
      name = 'V8 Linux - %s%s' % (branch_name, name_suffix)
      BRANCH_BUILDERS[name] = AddBranchBuilder(
          name, build_config, presubmit=True)
      name = 'V8 Linux64 - %s%s' % (branch_name, name_suffix)
      BRANCH_BUILDERS[name] = AddBranchBuilder(name, build_config)
      name = 'V8 arm - sim - %s%s' % (branch_name, name_suffix)
      BRANCH_BUILDERS[name] = AddBranchBuilder(name, build_config)

  for branch_name in ('stable branch', 'beta branch'):
    name = 'V8 mipsel - sim - %s' % branch_name
    BRANCH_BUILDERS[name] = AddBranchBuilder(
        name, 'Release')

    name = 'V8 mips64el - sim - %s' % branch_name
    BRANCH_BUILDERS[name] = AddBranchBuilder(
        name, 'Release', unittests_only=True)

    name = 'V8 ppc64 - sim - %s' % branch_name
    BRANCH_BUILDERS[name] = AddBranchBuilder(
        name, 'Release', unittests_only=True)

    name = 'V8 s390x - sim - %s' % branch_name
    BRANCH_BUILDERS[name] = AddBranchBuilder(
        name, 'Release', unittests_only=True)

fill_branch_builders()

BUILDERS['client.v8.branches'] = {'builders': BRANCH_BUILDERS}

BUILDERS = freeze(BUILDERS)
BRANCH_BUILDERS = freeze(BRANCH_BUILDERS)


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
    # Statically defined triggers.
    for triggered in bot_config.get('triggers', []):
      PARENT_MAP[triggered] = (builder, bot_config)
    # Simulated dynamically defined triggers.
    for triggered in bot_config.get('testing', {}).get('properties', {}).get(
        'triggers', []):
      PARENT_MAP[triggered] = (builder, bot_config)

fill_parent_map()
