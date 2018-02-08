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
def gc_stress(c):
  c.testing.test_args.append('--gc-stress')


@config_ctx()
def no_harness(c):
  c.testing.test_args.append('--no-harness')


@config_ctx()
def stress_incremental_marking(c):
  c.testing.test_args.append('--extra-flags=--stress-incremental-marking')


@config_ctx()
def verify_heap_skip_remembered_set(c):
  c.testing.test_args.append('--extra-flags=--verify-heap-skip-remembered-set')
