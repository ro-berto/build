# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import List, Single, Static


def BaseConfig(**_kwargs):
  shard_count = _kwargs.get('SHARD_COUNT', 1)
  shard_run = _kwargs.get('SHARD_RUN', 1)
  assert shard_count >= 1
  assert shard_run >= 1
  assert shard_run <= shard_count

  return ConfigGroup(
    gyp_env = ConfigGroup(
      AR = Single(basestring, required=False),
      CC = Single(basestring, required=False),
      CXX = Single(basestring, required=False),
      CXX_host = Single(basestring, required=False),
      LINK = Single(basestring, required=False),
      RANLIB = Single(basestring, required=False),
    ),
    mips_cross_compile = Single(bool, empty_val=False, required=False),
    # Test configuration that is the equal for all tests of a builder. It
    # might be refined later in the test runner for distinct tests.
    testing = ConfigGroup(
      test_args = List(basestring),
      may_shard = Single(bool, empty_val=True, required=False),

      SHARD_COUNT = Static(shard_count),
      SHARD_RUN = Static(shard_run),
    ),
  )


config_ctx = config_item_context(BaseConfig)


@config_ctx()
def v8(c):
  pass


@config_ctx()
def deopt_fuzz_normal(c):
  c.testing.test_args.append('--coverage=0.4')
  c.testing.test_args.append('--distribution-mode=smooth')


@config_ctx()
def deopt_fuzz_random(c):
  c.testing.test_args.append('--coverage=0.3')
  c.testing.test_args.append('--coverage-lift=50')
  c.testing.test_args.append('--distribution-mode=random')


@config_ctx()
def enable_armv8(c):
  c.testing.test_args.extend(['--extra-flags=--enable-armv8'])


@config_ctx()
def gc_stress(c):
  c.testing.test_args.append('--gc-stress')


@config_ctx()
def gcov_coverage(c):
  c.testing.test_args.extend(['--gcov-coverage'])


@config_ctx()
def mips_cross_compile(c):
  c.mips_cross_compile = True


@config_ctx()
def msan(c):
  c.testing.test_args.append('--msan')


@config_ctx()
def no_i18n(c):
  c.testing.test_args.append('--noi18n')


@config_ctx()
def no_snapshot(c):
  c.testing.test_args.append('--no-snap')


@config_ctx()
def no_harness(c):
  c.testing.test_args.append('--no-harness')


@config_ctx()
def predictable(c):
  c.testing.test_args.append('--predictable')


@config_ctx()
def stress_incremental_marking(c):
  c.testing.test_args.append('--extra-flags=--stress-incremental-marking')


@config_ctx()
def verify_heap_skip_remembered_set(c):
  c.testing.test_args.append('--extra-flags=--verify-heap-skip-remembered-set')
